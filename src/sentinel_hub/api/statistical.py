from typing import Any

from sentinel_hub.api.base_request import InputDataDict, SHBaseApiRequest
from sentinel_hub.api.utils import _update_other_args
from sentinel_hub.constants import LastIntervalBehavior, MimeType
from sentinel_hub.download import SHDownloadClient
from sentinel_hub.geometry import BBox, Geometry
from sentinel_hub.time_utils import (
    RawTimeIntervalType,
    parse_time_interval,
    serialize_time,
)
from sentinel_hub.types import JsonDict


class SHStatistical(SHBaseApiRequest):
    """
    Sentinel Hub Statistical API interface.

    For more information check Statistical API documentation:
    <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical.html>.
    """

    _SERVICE_ENDPOINT = "statistics/v1"

    def __init__(
        self,
        aggregation: JsonDict,
        input_data: list[JsonDict | InputDataDict],
        bbox: BBox | None = None,
        geometry: Geometry | None = None,
        calculations: JsonDict | None = None,
        **kwargs: Any,
    ):
        """
        For details of certain parameters check the Statistical API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html#tag/statistical>.
        """
        self.payload = self.body(
            request_bounds=self.bounds(bbox=bbox, geometry=geometry),
            request_data=input_data,
            aggregation=aggregation,
            calculations=calculations,
        )

        super().__init__(SHDownloadClient, **kwargs)

    @property
    def mime_type(self) -> MimeType:
        return MimeType.JSON

    @staticmethod
    def body(
        request_bounds: JsonDict,
        request_data: list[JsonDict],
        aggregation: JsonDict,
        calculations: JsonDict | None = None,
        other_args: JsonDict | None = None,
    ) -> JsonDict:
        """Generate the Statistical API request body."""
        request_body: JsonDict = {
            "input": {"bounds": request_bounds, "data": request_data},
            "aggregation": aggregation,
        }

        if calculations is not None:
            request_body["calculations"] = calculations

        if other_args:
            _update_other_args(request_body, other_args)

        return request_body

    @staticmethod
    def aggregation(
        evalscript: str,
        time_interval: RawTimeIntervalType,
        aggregation_interval: str,
        last_interval_behavior: LastIntervalBehavior | str | None = None,
        size: tuple[int, int] | None = None,
        resolution: tuple[float, float] | None = None,
        other_args: JsonDict | None = None,
    ) -> JsonDict:
        """
        Generate the `aggregation` part of the Statistical API request.

        The evalscript must also return a `dataMask` output. The `aggregation_interval` is an
        ISO 8601 duration (e.g. `P1D`, `P10D`) and `last_interval_behavior` decides what happens
        with the last interval if the time interval is not divisible by it (service default `SKIP`).
        """
        if not isinstance(evalscript, str):
            raise TypeError("'evalscript' should be a string")

        if size and resolution:
            raise ValueError(
                "Either size or resolution argument should be given, not both."
            )

        start_time, end_time = serialize_time(
            parse_time_interval(time_interval), use_tz=True
        )

        aggregation_interval_dict: JsonDict = {"of": aggregation_interval}
        if last_interval_behavior is not None:
            aggregation_interval_dict["lastIntervalBehavior"] = LastIntervalBehavior(
                last_interval_behavior
            ).value

        request_aggregation: JsonDict = {
            "timeRange": {"from": start_time, "to": end_time},
            "aggregationInterval": aggregation_interval_dict,
            "evalscript": evalscript,
        }

        if size:
            request_aggregation["width"], request_aggregation["height"] = size
        if resolution:
            request_aggregation["resx"], request_aggregation["resy"] = resolution

        if other_args:
            _update_other_args(request_aggregation, other_args)

        return request_aggregation
