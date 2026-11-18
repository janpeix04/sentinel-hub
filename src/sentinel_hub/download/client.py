import json
import logging
import os
import warnings
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from typing import Any
from xml.etree import ElementTree

import requests
from tqdm.auto import tqdm

from sentinel_hub.config import SHConfig
from sentinel_hub.constants import MimeType, RequestType
from sentinel_hub.download.handlers import fail_user_errors, retry_temporary_errors
from sentinel_hub.download.models import DownloadRequest, DownloadResponse
from sentinel_hub.exception import (
    DownloadFailedException,
    HashedNameCollisionException,
    MissingDataInRequestException,
    SHRuntimeWarning,
)
from sentinel_hub.io_utils import read_data
from sentinel_hub.types import JsonDict

logger = logging.getLogger(__name__)


class DownloadClient:
    """
    A basic download client object.

    It does the following:
     - downloads the data with multiple threads in parallel,
     - handles any exception that occur during download,
     - decodes downloaded data,
     - reads and writes locally stored/cached data.
    """

    def __init__(
        self,
        *,
        redownload: bool = False,
        raise_download_errors: bool = True,
        config: SHConfig | None = None,
    ):
        self.redownload = redownload
        self.raise_download_errors = raise_download_errors
        self.config = config or SHConfig()

    def download(
        self,
        download_requests: Iterable[DownloadRequest],
        max_threads: int | None = None,
        decode_data: bool = True,
        show_progress: bool = False,
    ) -> list[Any]:
        """Download one or multiple requests, provided as a request list."""
        requests_list = list(download_requests)
        results = [None] * len(requests_list)
        single_download_method = (
            self._single_download_decoded if decode_data else self._single_download
        )

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            download_list = [
                executor.submit(single_download_method, request)
                for request in requests_list
            ]
            future_order = {future: i for i, future in enumerate(download_list)}

            progress_context = (
                tqdm(total=len(download_list)) if show_progress else nullcontext()
            )

            with progress_context as progress_bar:
                for future in as_completed(download_list):
                    try:
                        results[future_order[future]] = future.result()
                    except DownloadFailedException as exception:
                        if self.raise_download_errors:
                            raise
                        warnings.warn(str(exception), category=SHRuntimeWarning)

                    if progress_bar:
                        progress_bar.update(1)
            return results

    def _single_download_decoded(self, request: DownloadRequest) -> Any:
        """Downloads a response and decodes it into data. By decoding a single response."""
        response = self._single_download(request)
        return None if response is None else response.decode()

    def _single_download(self, request: DownloadRequest) -> DownloadResponse | None:
        """Method for downloading a single request."""
        request.raise_if_invalid()

        if not (request.save_response or request.return_data):
            return None

        request_path, response_path = request.get_storage_paths()

        no_local_data = (
            self.redownload
            or response_path is None
            or not os.path.exists(response_path)
        )

        if no_local_data:
            response = self._execute_download(request)
        else:
            if not request.return_data or response_path is None:
                return None

            logger.debug(
                "Reading locally stored data from %s instead of downloading.",
                response_path,
            )
            self._check_cached_request_is_matching(request, request_path)
            response = DownloadResponse.from_local(request)

        processed_response = self._process_response(request, response)

        if (
            request.save_response
            and response_path
            and (no_local_data or processed_response is not response)
        ):
            processed_response.to_local()
            logger.debug("Saved response data to %s.", response_path)

        if request.return_data:
            return processed_response
        return None

    @retry_temporary_errors
    @fail_user_errors
    def _execute_download(self, request: DownloadRequest) -> DownloadResponse:
        """A default way of executing a single download request."""
        if request.url is None:
            raise ValueError(f"Faulty request {request}, no URL specified.")

        logger.debug(
            "Sending %s request to %s. Hash of sent request is %s.",
            request.request_type.value,
            request.url,
            request.get_hashed_name(),
        )

        response = requests.request(
            request.request_type.value,
            url=request.url,
            json=request.post_values,
            headers=request.headers,
            timeout=self.config.download_timeout_seconds,
        )

        response.raise_for_status()
        logger.debug(
            "Successful %s request to %s.", request.request_type.value, request.url
        )
        return DownloadResponse.from_response(response, request)

    @staticmethod
    def _check_cached_request_is_matching(
        request: DownloadRequest, request_path: str | None
    ) -> None:
        """
        Ensures that the cached request matches the current one.
        Serves as protection against hash collisions.
        """
        if not request_path:
            return

        cached_request_info = read_data(request_path, MimeType.JSON)
        cached_request_info = cached_request_info.get("request", cached_request_info)

        del cached_request_info["timestamp"]
        del cached_request_info["headers"]

        current_request_info = request.get_request_params(include_metadata=False)
        current_request_info_json = json.loads(json.dumps(current_request_info))

        if cached_request_info != current_request_info_json:
            raise HashedNameCollisionException(
                f"Request has hashed name {request.get_hashed_name()}, "
                f"which matches request saved at {request_path}, but the "
                "requests are differnt. Possible hash collision."
            )

    def _process_response(
        self, _: DownloadRequest, response: DownloadResponse
    ) -> DownloadResponse:
        """
        This method is meant to be overwritten by inherited implementations
        of the client object.
        """
        return response

    def get_json(
        self,
        url: str,
        post_values: JsonDict | None = None,
        headers: JsonDict | None = None,
        request_type: RequestType | None = None,
        **kwargs: Any,
    ) -> JsonDict | list | str | None:
        """Download request as JSON data type."""
        json_headers = headers or {}

        if request_type is None:
            request_type = RequestType.GET if post_values is None else RequestType.POST

        if request_type is RequestType.POST and "Content-Type" not in json_headers:
            json_headers = {"Content-Type": MimeType.JSON.get_string(), **json_headers}

        request = DownloadRequest(
            url=url,
            headers=json_headers,
            request_type=request_type,
            post_values=post_values,
            data_type=MimeType.JSON,
            **kwargs,
        )
        return self._single_download_decoded(request)

    def get_json_dict(
        self, url: str, *args: Any, extract_key: str | None = None, **kwargs: Any
    ) -> JsonDict:
        """
        Download request as JSON data type, failing if the result is not a dictionary.

        For other parameters see `get_json` method.
        """
        response = self.get_json(url, *args, **kwargs)

        if not isinstance(response, dict):
            raise MissingDataInRequestException(
                f"Response from {url} was expected to be a dictionary, "
                f"but got {type(response)}."
            )

        if extract_key is None:
            return response
        if extract_key in response and isinstance(response[extract_key], dict):
            return response[extract_key]

        explanation = (
            f"Value is of type {type(response[extract_key])}."
            if extract_key in response
            else "Key is missing."
        )
        raise MissingDataInRequestException(
            f"Response from {url} was expected to have {extract_key} "
            f"mapping to a dictionary. {explanation}"
        )

    def get_xml(self, url: str, **kwargs: Any) -> ElementTree.ElementTree:
        """Download request as XML data type."""
        request = DownloadRequest(url=url, data_type=MimeType.XML, **kwargs)
        return self._single_download_decoded(request)
