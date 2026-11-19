# Exceptions & warnings

All custom errors live in `sentinel_hub.exception`.

## Exceptions

```
BaseSHException
├── DownloadFailedException
│   └── OutOfRequestsException
├── ImageDecodingError
├── HashedNameCollisionException
└── MissingDataInRequestException
```

| Exception | Raised when |
|---|---|
| `BaseSHException` | Base class – catch this to handle any library error |
| `DownloadFailedException` | A download fails permanently (4xx response, or retries exhausted). `.request_exception` holds the original `requests` exception |
| `OutOfRequestsException` | HTTP 429 keeps coming back and `SHConfig.max_retries` is reached |
| `ImageDecodingError` | Downloaded bytes can't be decoded into an image |
| `HashedNameCollisionException` | A cached response on disk has the same hash but a different request |
| `MissingDataInRequestException` | A JSON response doesn't have the expected shape (e.g. not a `dict`) |

```python
from sentinel_hub import DownloadFailedException

try:
    data = request.get_data()
except DownloadFailedException as error:
    print(error)  # includes the server's message
    print(
        error.request_exception.response.status_code
    )  # may be None for connection errors
```

Configuration and input mistakes (missing credentials, invalid `maxcc`, both `size` and
`resolution`, unknown band names, …) raise standard `ValueError` / `TypeError`.

## Warnings

| Warning | Base | Shown | Emitted when |
|---|---|---|---|
| `SHRuntimeWarning` | `RuntimeWarning` | always | Non-fatal download issues, e.g. failures with `raise_download_errors=False`, very long file paths |
| `SHRateLimitWarning` | `SHRuntimeWarning` | always | The service responded with HTTP 429 |
| `SHUserWarning` | `UserWarning` | once per location | Likely user mistakes, e.g. an expired `from_token` session, `pyproj.CRS(4326)` axis order |
| `SHDeprecationWarning` | `DeprecationWarning` | once per location | Deprecated usage, e.g. `BBox` from a string |

Silence a category with the standard `warnings` module:

```python
import warnings
from sentinel_hub.exception import SHRateLimitWarning

warnings.simplefilter("ignore", SHRateLimitWarning)
```
