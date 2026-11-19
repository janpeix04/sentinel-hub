from typing import Any

from sentinel_hub.api.base_request import InputDataDict, SHBaseApiRequest
from sentinel_hub.api.utils import _update_other_args
from sentinel_hub.constants import MimeType
from sentinel_hub.download import SHDownloadClient
from sentinel_hub.geometry import BBox, Geometry
from sentinel_hub.types import JsonDict


class SHRequest(SHBaseApiRequest):
    """
    Sentinel Hub Process API interface.

    For more information check Process API documentation:
    <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html>.
    """

    _SERVICE_ENDPOINT = "process"

    def __init__(
        self,
        evalscript: str,
        input_data: list[JsonDict | InputDataDict],
        responses: list[JsonDict],
        bbox: BBox | None = None,
        geometry: Geometry | None = None,
        size: tuple[int, int] | None = None,
        resolution: tuple[float, float] | None = None,
        **kwargs: Any,
    ):
        """
        For details of certain parameters check the Process API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>.
        """
        if not isinstance(evalscript, str):
            raise TypeError("'evalscript' should be a string")

        parsed_mime_type = MimeType.from_string(responses[0]["format"]["type"])
        self._mime_type = MimeType.TAR if len(responses) > 1 else parsed_mime_type

        self.payload = self.body(
            request_bounds=self.bounds(bbox=bbox, geometry=geometry),
            request_data=input_data,
            request_output=self.output(
                size=size, resolution=resolution, responses=responses
            ),
            evalscript=evalscript,
        )

        super().__init__(SHDownloadClient, **kwargs)

    @property
    def mime_type(self) -> MimeType:
        return self._mime_type

    @staticmethod
    def body(
        request_bounds: JsonDict,
        request_data: list[JsonDict],
        evalscript: str,
        request_output: JsonDict | None = None,
        other_args: JsonDict | None = None,
    ) -> JsonDict:
        """
        Generate the Process API request body.

        Evalscript:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Evalscript.html>.
        """
        request_body = {
            "input": {"bounds": request_bounds, "data": request_data},
            "evalscript": evalscript,
        }

        if request_output is not None:
            request_body["output"] = request_output

        if other_args:
            _update_other_args(request_body, other_args)

        return request_body

    @staticmethod
    def output_response(
        identifier: str,
        response_format: str | MimeType,
        other_args: JsonDict | None = None,
    ) -> JsonDict:
        """Generate an element of `output.responses` as described in the Process API reference."""
        output_response = {
            "identifier": identifier,
            "format": {"type": MimeType(response_format).get_string()},
        }

        if other_args:
            _update_other_args(output_response, other_args)

        return output_response

    @staticmethod
    def output(
        responses: list[JsonDict],
        size: tuple[int, int] | None = None,
        resolution: tuple[float, float] | None = None,
        other_args: dict | None = None,
    ) -> JsonDict:
        """Generate an `output` part of the request as described in the Process API reference."""
        if size and resolution:
            raise ValueError(
                "Either size or resolution argument should be given, not both."
            )

        request_output: JsonDict = {"responses": responses}

        if size:
            request_output["width"], request_output["height"] = size
        if resolution:
            request_output["resx"], request_output["resy"] = resolution

        if other_args:
            _update_other_args(request_output, other_args)

        return request_output
