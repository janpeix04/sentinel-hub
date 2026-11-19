import logging
import time
import warnings
from collections.abc import Callable
from threading import Lock
from typing import Any, ClassVar, TypeVar

import requests
from requests import Response

from sentinel_hub.config import SHConfig
from sentinel_hub.constants import SHConstants
from sentinel_hub.download.client import DownloadClient
from sentinel_hub.download.handlers import fail_user_errors, retry_temporary_errors
from sentinel_hub.download.models import DownloadRequest, DownloadResponse
from sentinel_hub.download.rate_limit import SHRateLimit
from sentinel_hub.download.session import SHSession
from sentinel_hub.exception import (
    OutOfRequestsException,
    SHRateLimitWarning,
    SHRuntimeWarning,
)
from sentinel_hub.types import JsonDict

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SHDownloadClient(DownloadClient):
    """Download client specifically configured for download form Sentinel Hub service."""

    _CACHED_SESSIONS: ClassVar[dict[tuple[str, str], SHSession]] = {}
    _UNIVERSAL_CACHE_KEY = "universal-user", "default-url"

    def __init__(
        self,
        *,
        session: SHSession | None = None,
        default_retry_time: float = 30.0,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)

        if session is not None and not isinstance(session, SHSession):
            raise ValueError(
                f"A session parameter has to be an instance of {SHSession.__name__} or "
                f"None, but {session} was given."
            )

        self.session = session
        self.default_retry_time = default_retry_time * 1000  # rescale to milliseconds

        self.rate_limit = SHRateLimit(
            num_processes=self.config.number_of_download_processes
        )
        self.lock: Lock | None = None

    def download(self, *args: Any, **kwargs: Any) -> Any:
        """The main download method."""
        # Because the Lock object cannot be pickled we create it only here and remove it afterward
        self.lock = Lock()
        try:
            return super().download(*args, **kwargs)
        finally:
            self.lock = None

    @retry_temporary_errors
    @fail_user_errors
    def _execute_download(self, request: DownloadRequest) -> DownloadResponse:
        """
        Executes the download with a single thread and uses a rate limit object, which
        is shared between all threads.
        """
        download_attempts = 0

        while True:
            sleep_time = self._execute_thread_safe(self.rate_limit.register_next)

            if sleep_time == 0:
                download_attempts += 1
                logger.debug(
                    "Sending %s request to %s. Hash of sent request is %s.",
                    request.request_type.value,
                    request.url,
                    request.get_hashed_name(),
                )
                response = self._do_download(request)

                if (
                    response.status_code
                    == requests.status_codes.codes.TOO_MANY_REQUESTS
                ):
                    warnings.warn(
                        "Download rate limit hit.", category=SHRateLimitWarning
                    )

                    if (
                        self.config.max_retries is not None
                        and download_attempts >= self.config.max_retries
                    ):
                        raise OutOfRequestsException(
                            "Maximum number of download attempts reached."
                        )

                    self._execute_thread_safe(
                        self.rate_limit.update,
                        response.headers,
                        default=self.default_retry_time,
                    )
                    continue
                response.raise_for_status()

                logger.debug(
                    "Successful %s request to %s.",
                    request.request_type.value,
                    request.url,
                )
                return DownloadResponse.from_response(response, request)
            logger.debug("Request needs to wait. Sleeping for %0.2f.", sleep_time)
            time.sleep(sleep_time)

    def _execute_thread_safe(
        self, thread_unsafe_function: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """Executes a function inside a thread lock and handles potential errors."""
        if self.lock is None:
            return thread_unsafe_function(*args, **kwargs)

        with self.lock:
            return thread_unsafe_function(*args, **kwargs)

    def _do_download(self, request: DownloadRequest) -> Response:
        """Runs the download."""
        if request.url is None:
            raise ValueError(f"Faulty request {request}, no URL specified.")

        return requests.request(
            request.request_type.value,
            url=request.url,
            json=request.post_values,
            headers=self._prepare_headers(request),
            timeout=self.config.download_timeout_seconds,
        )

    def _prepare_headers(self, request: DownloadRequest) -> JsonDict:
        """
        Prepares final headers by potentially joining them with session headers. Note
        that in the current implementation of this method requests headers have priority
        to overwrite default and session headers with the same keys.
        """
        session_headers: JsonDict = {}
        if request.use_session:
            session_headers = self._execute_thread_safe(self._get_session_headers)

        return {**SHConstants.HEADERS, **session_headers, **request.headers}

    def _get_session_headers(self) -> JsonDict:
        """
        Provides up-to-date session headers.

        Note that calling session_headers property triggers update if session has expired
        therefore this has to be called in a thread-safe way.
        """
        return self.get_session().session_headers

    def get_session(self) -> SHSession:
        """Provides the session object used by the client."""
        if self.session:
            return self.session

        cache_key = self._get_cache_key(self.config)
        if cache_key in SHDownloadClient._CACHED_SESSIONS:
            session = SHDownloadClient._CACHED_SESSIONS[cache_key]
        elif SHDownloadClient._UNIVERSAL_CACHE_KEY in SHDownloadClient._CACHED_SESSIONS:
            session = SHDownloadClient._CACHED_SESSIONS[
                SHDownloadClient._UNIVERSAL_CACHE_KEY
            ]
        else:
            session = SHSession(config=self.config)
            SHDownloadClient._CACHED_SESSIONS[cache_key] = session
        return session

    @staticmethod
    def cache_session(session: SHSession, universal: bool = False) -> None:
        """
        Cache a Sentinel Hub session for to be reused by all instance of `SHDownloadClient`
        and its child classes within the same Python runtime environment.
        """
        if not isinstance(session, SHSession):
            raise TypeError(
                f"Given object should be an instance of {SHSession.__name__} but "
                f"{session} was given."
            )

        cache_key = (
            SHDownloadClient._UNIVERSAL_CACHE_KEY
            if universal
            else SHDownloadClient._get_cache_key(session)
        )
        SHDownloadClient._CACHED_SESSIONS[cache_key] = session

    @staticmethod
    def _get_cache_key(config_or_session: SHSession | SHConfig) -> tuple[str, str]:
        """
        Calculates a cache key for the given session or config object. The key consists
        of an OAuth client ID and a base service URL.
        """
        if isinstance(config_or_session, SHConfig):
            return config_or_session.sh_client_id, config_or_session.sh_base_url

        if isinstance(config_or_session, SHSession):
            base_url = config_or_session.config.sh_base_url

            # If session was generated from token then config_or_session.config.sh_client_id could have wrong client id
            sh_client_id = config_or_session.info().get("azp", "")
            if not sh_client_id:
                warnings.warn(
                    "Failed to read client ID from OAuth token. Session caching might not work correctly.",
                    category=SHRuntimeWarning,
                )
            return sh_client_id, base_url

        raise ValueError(
            f"Expected a config or a session object but got {config_or_session}."
        )

    @staticmethod
    def clear_cache() -> None:
        """Clears cached sessions."""
        SHDownloadClient._CACHED_SESSIONS = {}
