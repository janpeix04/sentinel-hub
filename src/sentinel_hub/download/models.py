import datetime as dt
import functools
import hashlib
import json
import os
import platform
import warnings
from dataclasses import dataclass, field, fields
from typing import Any

from requests import Response

from sentinel_hub.constants import MimeType, RequestType
from sentinel_hub.decoding import decode_data
from sentinel_hub.exception import SHRuntimeWarning
from sentinel_hub.io_utils import read_data, write_data
from sentinel_hub.types import JsonDict


@dataclass
class DownloadRequest:
    """
    A class defining a single download request.

    The class is a container with all parameters needed to execute a
    single download request and save or return downloaded data.
    """

    url: str | None = None
    headers: JsonDict = field(default_factory=dict)
    request_type: RequestType = RequestType.GET
    post_values: JsonDict | None = None
    use_session: bool = False
    data_type: MimeType = MimeType.RAW
    save_response: bool = False
    data_folder: str | None = None
    filename: str | None = None
    return_data: bool = True
    extra_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Additional parsing of init parameters."""
        self.request_type = RequestType(self.request_type)
        self.data_type = MimeType(self.data_type)

    def __hash__(self) -> int:
        """This dataclass is mutable, but we still assign its id as its hash."""
        return id(self)

    def raise_if_invalid(self) -> None:
        """Method that raises an error if something is wrong with request parameters."""
        if self.save_response and self.data_folder is None:
            raise ValueError(
                "Data folder is not specified. Please give a data folder name "
                "in the initialization of your request."
            )

    def get_request_params(self, include_metadata: bool = False) -> JsonDict:
        """Provides parameters that define the request in form of a dictionary."""
        params = {"url": self.url, "payload": self.post_values}
        if include_metadata:
            params = {
                **params,
                "headers": self.headers,
                "timestamp": dt.datetime.now().isoformat(),
            }
        return params

    def get_hashed_name(self) -> str:
        """It takes request url and payload and calculates a unique hashed string from them."""
        params = self.get_request_params(include_metadata=False)
        hashable = json.dumps(params)
        return hashlib.md5(hashable.encode("utf-8")).hexdigest()

    def get_relative_paths(self) -> tuple[str | None, str]:
        """A method that calculates file paths relative to `data_folder`."""
        if self.filename is not None:
            return None, self.filename

        hashed_name = self.get_hashed_name()

        request_path = os.path.join(hashed_name, "request.json")
        response_path = os.path.join(
            hashed_name, f"response.{self.data_type.extension}"
        )
        return request_path, response_path

    def get_storage_paths(self) -> tuple[str | None, str | None]:
        """A method that calculates file paths where request paylod and response will be save."""
        if self.data_folder is None:
            return None, None

        request_path, response_path = self.get_relative_paths()

        if request_path is not None:
            request_path = os.path.join(self.data_folder, request_path)
        response_path = os.path.join(self.data_folder, response_path)

        self._check_path(response_path)
        return request_path, response_path

    @staticmethod
    def _check_path(file_path: str) -> None:
        """Checks file path and warns about potential problems during saving."""
        message_problem = None
        if len(file_path) > 255 and platform.system() == "Windows":
            message_problem = "File path"
        elif len(os.path.basename(file_path)) > 255:
            message_problem = "Filename of"

        if message_problem:
            message = (
                f"{message_problem} {file_path} is longer than 255 character "
                "which might cause an error while saving on disk."
            )
            warnings.warn(message, category=SHRuntimeWarning)
