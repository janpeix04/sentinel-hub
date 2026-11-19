import functools
import logging
import time
from collections.abc import Callable
from typing import Protocol

import requests

from sentinel_hub.config import SHConfig
from sentinel_hub.decoding import decode_sentinel_hub_error_msg
from sentinel_hub.download.models import DownloadRequest
from sentinel_hub.exception import DownloadFailedException


class _HasConfig(Protocol):
    """Interface of object with a config."""

    config: SHConfig


logger = logging.getLogger(__name__)


def fail_user_errors[Self, T](
    download_func: Callable[[Self, DownloadRequest], T],
) -> Callable[[Self, DownloadRequest], T]:
    """Decorator function for handling user errors."""

    @functools.wraps(download_func)
    def new_download_func(self: Self, request: DownloadRequest) -> T:
        try:
            return download_func(self, request)
        except requests.HTTPError as exception:
            if (
                exception.response.status_code
                < requests.status_codes.codes.INTERNAL_SERVER_ERROR
                and exception.response.status_code
                != requests.status_codes.codes.TOO_MANY_REQUESTS
            ):
                raise DownloadFailedException(
                    _create_download_failed_message(exception, request.url),
                    request_exception=exception,
                ) from exception
            raise

    return new_download_func


def retry_temporary_errors[SelfWithConfig: _HasConfig, T](
    download_func: Callable[[SelfWithConfig, DownloadRequest], T],
):
    """Decorator function for handling server and connection errors."""
    backoff_coefficient = 3

    @functools.wraps(download_func)
    def new_download_func(self: SelfWithConfig, request: DownloadRequest) -> T:
        download_attempts = self.config.max_download_attempts
        sleep_time = self.config.download_sleep_time

        for attempt in range(download_attempts):
            try:
                return download_func(self, request)
            except requests.RequestException as exception:
                attempt_left = download_attempts - (attempt + 1)

                if not (
                    _is_temporary_problem(exception)
                    or (
                        isinstance(exception, requests.HTTPError)
                        and exception.response.status_code
                        >= requests.status_codes.codes.INTERNAL_SERVER_ERROR
                    )
                ):
                    raise

                if attempt_left <= 0:
                    message = _create_download_failed_message(exception, request.url)
                    raise DownloadFailedException(
                        message, request_exception=exception
                    ) from exception

                logger.debug(
                    "Download attempt failed: %s\n%d attempts left, will retry in %ds",
                    exception,
                    attempt_left,
                    sleep_time,
                )
                time.sleep(sleep_time)
                sleep_time *= backoff_coefficient
        raise DownloadFailedException(
            "No download attempts available - configuration parameter "
            "max_download_attempts should be greater than 0."
        )

    return new_download_func


def _is_temporary_problem(exception: Exception) -> bool:
    """
    Checks if the obtained exception is temporary and if download
    attempt should be repeated.
    """
    return isinstance(
        exception,
        (
            requests.ConnectionError,
            requests.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ),
    )


def _create_download_failed_message(exception: Exception, url: str | None) -> str:
    """Creates message describing why download has failed."""
    message = f"Failed to download from:\n{url}\nwith {exception.__class__.__name__}:\n{exception}"

    if _is_temporary_problem(exception):
        if isinstance(exception, requests.ConnectionError):
            message += "\nPlease check your internet connection and try again."
        else:
            message += (
                "\nThere might be a problem in connection or the server "
                "failed to process your request. Please try again."
            )
    elif isinstance(exception, requests.HTTPError):
        server_message = decode_sentinel_hub_error_msg(exception.response)
        message += f'\nServer response: "{server_message}"'

    return message
