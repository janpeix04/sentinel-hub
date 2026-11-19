# Download & sessions

Under the hood every API call goes through the `sentinel_hub.download` package. You rarely
need it directly – `SHCatalog` and `SHRequest` use it for you – but it is the place to look
for authentication, retries, rate limiting, caching and multiprocessing.

- [Overview](#overview)
- [Authentication: SHSession](#authentication-shsession)
- [Download clients](#download-clients)
- [DownloadRequest and DownloadResponse](#downloadrequest-and-downloadresponse)
- [Retries and error handling](#retries-and-error-handling)
- [Rate limiting](#rate-limiting)
- [Sharing a session across processes](#sharing-a-session-across-processes)

## Overview

| Class | Role |
|---|---|
| `SHSession` | Fetches and refreshes the OAuth2 token from CDSE |
| `DownloadClient` | Generic multi-threaded downloader with retries and on-disk caching |
| `SHDownloadClient` | `DownloadClient` + Sentinel Hub auth headers, session caching and rate limiting |
| `DownloadRequest` | Everything needed to perform one HTTP request |
| `DownloadResponse` | Raw response + metadata, decodable into Python objects |
| `SessionSharing`, `collect_shared_session` | Reuse one token across worker processes |

## Authentication: SHSession

```python
from sentinel_hub import SHConfig, SHSession

session = SHSession(config=SHConfig())
session.token  # dict with access_token, expires_at, ... (auto-refreshed)
session.session_headers  # {"Authorization": "Bearer ..."}
session.info()  # decoded JWT claims, e.g. session.info()["azp"] == client ID
```

- Needs `sh_client_id` and `sh_client_secret` (see [configuration.md](configuration.md)),
  otherwise `ValueError`.
- The token is refreshed automatically when it has less than
  `refresh_before_expiry` seconds left (default `120`).
- `SHSession.from_token(token)` wraps an existing token without refreshing it; you get an
  `SHUserWarning` once it expires.

## Download clients

`SHDownloadClient` is what the APIs use. You can also use it for ad-hoc requests:

```python
from sentinel_hub import SHDownloadClient

client = SHDownloadClient(config=config)
info = client.get_json_dict(
    "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/collections",
    use_session=True,  # attach the Authorization header
)
```

| Method | Description |
|---|---|
| `download(requests, max_threads=None, decode_data=True, show_progress=False)` | Execute many `DownloadRequest`s in a thread pool; returns results in input order |
| `get_json(url, post_values=None, headers=None, request_type=None, **kwargs)` | GET (or POST if `post_values`) and decode JSON |
| `get_json_dict(url, ..., extract_key=None)` | Like `get_json`, but requires a `dict` (optionally returns `response[extract_key]`) |

Constructor options: `redownload=False`, `raise_download_errors=True`, `config=None`, plus for
`SHDownloadClient`: `session=None`, `default_retry_time=30.0` (seconds).

**Session caching.** `SHDownloadClient` keeps one `SHSession` per *(client ID, base URL)* for
the whole Python process, so creating many requests doesn't fetch many tokens.

```python
SHDownloadClient.cache_session(session)  # register a session
SHDownloadClient.cache_session(session, universal=True)  # use it for every config
SHDownloadClient.clear_cache()
```

**On-disk caching.** If a request has `save_response=True` and a `data_folder`, the client
stores `request.json` and `response.<ext>` under `<data_folder>/<md5(url + payload)>/`. Later
calls read the file instead of downloading (unless `redownload=True`). A mismatch between the
cached and current request raises `HashedNameCollisionException`.

## DownloadRequest and DownloadResponse

```python
from sentinel_hub import DownloadRequest, MimeType
from sentinel_hub.constants import RequestType

request = DownloadRequest(
    url="https://sh.dataspace.copernicus.eu/api/v1/process",
    request_type=RequestType.POST,
    post_values=payload,
    headers={"content-type": "application/json"},
    data_type=MimeType.TIFF,
    use_session=True,
    data_folder="./data",
    save_response=True,
)
data = client.download([request])[0]
```

| Field | Default | Description |
|---|---|---|
| `url` | `None` | Target URL |
| `headers` | `{}` | Extra headers (override session headers) |
| `request_type` | `GET` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `post_values` | `None` | JSON body |
| `use_session` | `False` | Add the Sentinel Hub `Authorization` header |
| `data_type` | `RAW` | Expected `MimeType`, drives decoding |
| `save_response` | `False` | Write the response to disk |
| `data_folder` | `None` | Root folder for saved responses |
| `filename` | `None` | Custom relative file name instead of the hash folder |
| `return_data` | `True` | Return the decoded data |

Useful methods: `get_hashed_name()`, `get_relative_paths()`, `get_storage_paths()`.

`DownloadResponse` (returned when `decode_data=False`) has `content`, `headers`,
`status_code`, `elapsed`, `response_type`, and `decode()`.

## Retries and error handling

| Situation | Behaviour |
|---|---|
| Connection error, timeout, chunked-encoding error, HTTP 5xx | Retried up to `max_download_attempts` times, waiting `download_sleep_time` seconds, ×3 after each attempt |
| HTTP 4xx (except 429) | Fails immediately with `DownloadFailedException`, including the server's error message |
| HTTP 429 Too Many Requests | Handled by the rate limiter (below) |
| All attempts exhausted | `DownloadFailedException` |

With `raise_download_errors=False`, failures emit an `SHRuntimeWarning` and the result is `None`.

All of these are tuned through [`SHConfig`](configuration.md#3-configuration-reference):
`max_download_attempts`, `download_sleep_time`, `download_timeout_seconds`,
`number_of_download_processes`, `max_retries`.

## Rate limiting

`SHDownloadClient` shares an `SHRateLimit` across its threads:

- Requests are spaced by `0.05 s × number_of_download_processes` (max 60 s).
- On HTTP 429 an `SHRateLimitWarning` is emitted, the client waits for the `Retry-After`
  header (or `default_retry_time`), then retries.
- If `max_retries` is set and reached, `OutOfRequestsException` is raised.

## Sharing a session across processes

When parallelising with `multiprocessing`, avoid fetching a token in every worker: share
one through shared memory.

```python
from concurrent.futures import ProcessPoolExecutor
from sentinel_hub import SHDownloadClient, SHSession
from sentinel_hub.download import SessionSharing, collect_shared_session


def worker(request):
    SHDownloadClient.cache_session(collect_shared_session(), universal=True)
    return request.get_data()[0]


session = SHSession(config=config)
with SessionSharing(session):
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(worker, requests))
```

`SessionSharing` runs a background `SessionSharingThread` that writes the token into a
`SharedMemory` block and refreshes it before it expires; the block is released when the
`with` block exits. The session must be self-refreshing (not created with `from_token`).
