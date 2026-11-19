import copy
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any

from sentinel_hub.config import SHConfig
from sentinel_hub.download import DownloadClient, DownloadRequest
from sentinel_hub.types import JsonDict


class DataRequest(metaclass=ABCMeta):
    """
    A base abstract class for all implementations of data request interface.

    Every data request type can write the fetched data to disk and then read it again (and
    hence avoid the need to download the same data again).
    """

    def __init__(
        self,
        download_client_class: Callable,
        *,
        data_folder: str | None = None,
        config: SHConfig | None = None,
    ):
        self.download_client_class = download_client_class
        self.data_folder = data_folder
        self.config = config or SHConfig()

        self.download_list: list[DownloadRequest] = []
        self.create_request()

    @abstractmethod
    def create_request(self) -> None:
        """An abstract method for logic of creating download requests."""

    def get_download_list(self) -> list[DownloadRequest]:
        """Returns a list of download requests for requested data."""
        return self.download_list

    def get_filename_list(self) -> list[str]:
        """
        Returns a list of file names (or paths relative to `data_folder`) where the requested
        data will be saved or read from, if it has already been downloaded and saved."""
        return [request.get_relative_paths()[1] for request in self.download_list]

    def get_url_list(self) -> list[str | None]:
        """Returns a list of urls for requested data."""
        return [request.url for request in self.download_list]

    def is_valid_request(self) -> bool:
        """Checks if initialized class instance successfully prepared a list of items to download."""
        return isinstance(self.download_list, list) and all(
            isinstance(request, DownloadRequest) for request in self.download_list
        )

    def get_data(
        self,
        *,
        save_data: bool = False,
        redownload: bool = False,
        data_filter: list[int] | None = None,
        max_threads: int | None = None,
        decode_data: bool = True,
        raise_download_errors: bool = True,
        show_progress: bool = False,
    ) -> list[Any]:
        """
        Get requested data either by downloading it or by reading it from the disk (if it
        was previously downloaded and saved).
        """
        self._preprocess_request(save_data, True)
        return self._execute_data_download(
            data_filter,
            redownload,
            max_threads,
            raise_download_errors,
            decode_data=decode_data,
            show_progress=show_progress,
        )

    def save_data(
        self,
        *,
        data_filter: list[int] | None = None,
        redownload: bool = False,
        max_threads: int | None = None,
        raise_download_errors: bool = False,
        show_progress: bool = False,
    ) -> None:
        """
        Saves data to disk. If ``redownload=True`` then the data is redownloaded using
        `max_threads` workers.
        """
        self._preprocess_request(True, False)
        self._execute_data_download(
            data_filter,
            redownload,
            max_threads,
            raise_download_errors,
            show_progress=show_progress,
        )

    def _execute_data_download(
        self,
        data_filter: list[int] | None = None,
        redownload: bool = False,
        max_threads: int | None = None,
        raise_download_errors: bool = False,
        decode_data: bool = True,
        show_progress: bool = False,
    ) -> list[Any]:
        """Calls download module and executes the download process."""
        is_repeating_filter = False
        if data_filter is None:
            filtered_download_list = self.download_list
        elif isinstance(data_filter, (list, tuple)):
            try:
                filtered_download_list = [
                    self.download_list[index] for index in data_filter
                ]
            except IndexError as exception:
                raise IndexError(
                    "Indices of data_filter are out of range"
                ) from exception

            filtered_download_list, mapping_list = self._filter_repeating_items(
                filtered_download_list
            )
            is_repeating_filter = len(filtered_download_list) < len(mapping_list)
        else:
            raise ValueError("data_filter parameter must be a list of indices")

        client = self.download_client_class(
            redownload=redownload,
            raise_download_errors=raise_download_errors,
            config=self.config,
        )
        data_list = client.download(
            filtered_download_list,
            max_threads=max_threads,
            decode_data=decode_data,
            show_progress=show_progress,
        )

        if is_repeating_filter:
            data_list = [copy.deepcopy(data_list[index]) for index in mapping_list]

        return data_list

    @staticmethod
    def _filter_repeating_items(
        download_list: list[DownloadRequest],
    ) -> tuple[list[DownloadRequest], list[int]]:
        """
        Because of data_filter some requests in download list might be the same. In order not
        to download them again this method will reduce the list of requests. It will also
        return a mapping list which can be used to reconstruct the previous list of download
        requests."""
        unique_requests_map = {}
        mapping_list = []
        unique_download_list: list[DownloadRequest] = []
        for download_request in download_list:
            if download_request not in unique_requests_map:
                unique_requests_map[download_request] = len(unique_download_list)
                unique_download_list.append(download_request)
            mapping_list.append(unique_requests_map[download_request])
        return unique_download_list, mapping_list

    def _preprocess_request(self, save_data: bool, return_data: bool) -> None:
        """Prepares requests for download and creates empty folders."""
        if not self.is_valid_request():
            raise ValueError("Cannot obtain data because request is invalid")

        if save_data and self.data_folder is None:
            raise ValueError(
                "Request parameter `data_folder` is not specified. "
                "In order to save data please set `data_folder` to location on your disk."
            )

        for download_request in self.download_list:
            download_request.save_response = save_data
            download_request.return_data = return_data
            download_request.data_folder = self.data_folder


class FeatureIterator[T](metaclass=ABCMeta):
    """
    An implementation of a base feature iteration class.

    Main functionalities:
     - The iterator will load only as many features as needed at any moment
     - It will keep downloaded features in memory so that iterating over it again will not have to download the same
       features again.
    """

    def __init__(
        self, client: DownloadClient, url: str, params: JsonDict | None = None
    ):
        self.client = client
        self.url = url
        self.params = params or {}

        self.index = 0
        self.features: list[T] = []
        self.finished = False

    def __iter__(self) -> FeatureIterator[T]:
        """Method called at the beginning of a new iteration."""
        self.index = 0
        return self

    def __next__(self) -> T:
        """Method called to provide the next feature in iteration."""
        while self.index >= len(self.features) and not self.finished:
            new_features = self._fetch_features()
            self.features.extend(new_features)

        if self.index < len(self.features):
            self.index += 1
            return self.features[self.index - 1]

        raise StopIteration

    @abstractmethod
    def _fetch_features(self) -> Iterable[T]:
        """Collects and returns more features from the service."""
