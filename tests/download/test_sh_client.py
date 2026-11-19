from __future__ import annotations

import pytest
import requests
from requests_mock import Mocker

from sentinel_hub import (
    DownloadRequest,
    SHConfig,
    SHDownloadClient,
    SHSession,
    __version__,
)
from sentinel_hub.exception import OutOfRequestsException

FAST_SH_ENDPOINT = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/collections"


@pytest.mark.sh_integration()
def test_client_with_fixed_session(session: SHSession) -> None:
    blank_config = SHConfig(use_defaults=True)
    client = SHDownloadClient(session=session, config=blank_config)

    obtained_session = client.get_session()
    assert obtained_session is session

    info = client.get_json(FAST_SH_ENDPOINT, use_session=True)
    assert info

    with pytest.raises(ValueError):
        SHDownloadClient(session=blank_config, config=blank_config)  # type: ignore[arg-type]


@pytest.mark.sh_integration()
def test_client_headers(session: SHSession, requests_mock: Mocker) -> None:
    blank_config = SHConfig(use_defaults=True)
    client = SHDownloadClient(session=session, config=blank_config)

    requests_mock.get(url="/fake-endpoint")
    fake_url = "https://xyz.sentinel-hub.com/fake-endpoint"

    client.get_json(fake_url)

    assert len(requests_mock.request_history) == 1
    mocked_request = requests_mock.request_history[0]

    assert mocked_request.url == fake_url
    assert mocked_request.headers["User-Agent"] == f"sentinel-hub/v{__version__}"


@pytest.mark.sh_integration()
@pytest.mark.parametrize("client_object", [SHDownloadClient, SHDownloadClient()])
def test_session_caching_and_clearing(
    client_object: SHDownloadClient | type[SHDownloadClient], session: SHSession
) -> None:
    client_object.clear_cache()
    assert SHDownloadClient._CACHED_SESSIONS == {}

    client_object.cache_session(session)
    assert len(SHDownloadClient._CACHED_SESSIONS) == 1
    assert list(SHDownloadClient._CACHED_SESSIONS.values()) == [session]

    client_object.clear_cache()
    assert SHDownloadClient._CACHED_SESSIONS == {}


@pytest.mark.sh_integration()
def test_double_session_caching(session: SHSession) -> None:
    another_session = SHSession()

    client = SHDownloadClient()
    client.cache_session(session)
    assert client.get_session() is session

    client.cache_session(another_session)
    assert client.get_session() is another_session

    client_with_fixed_session = SHDownloadClient(session=session)
    assert client_with_fixed_session.get_session() is session

    client_with_fixed_session.cache_session(another_session)
    assert client_with_fixed_session.get_session() is session


@pytest.mark.sh_integration()
def test_universal_session_caching(session: SHSession) -> None:
    SHDownloadClient.clear_cache()

    config_without_credentials = SHConfig(use_defaults=True)
    client = SHDownloadClient(config=config_without_credentials)

    with pytest.raises(ValueError):
        client.get_session()

    SHDownloadClient.cache_session(session, universal=False)
    with pytest.raises(ValueError):
        client.get_session()

    SHDownloadClient.cache_session(session, universal=True)
    cached_session = client.get_session()
    assert cached_session is session


@pytest.mark.sh_integration()
def test_client_with_max_retries(session: SHSession) -> None:
    blank_config = SHConfig(use_defaults=True)
    blank_config.max_retries = 1
    client = SHDownloadClient(session=session, config=blank_config)

    class MockResponse:
        def __init__(self):
            self.status_code = requests.status_codes.codes.TOO_MANY_REQUESTS

    client._do_download = lambda _: MockResponse()
    with pytest.raises(OutOfRequestsException):
        client.download(download_requests=[DownloadRequest()])
