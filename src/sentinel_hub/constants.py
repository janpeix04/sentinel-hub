import mimetypes
from enum import Enum


class ServiceUrl:
    """Copernicus Data Space Ecosystem (CDSE) service URLs."""

    CDSE = "https://sh.dataspace.copernicus.eu"
    CDSE_TOKEN = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"


class MimeType(Enum):
    """
    Enum class to represent supported file formats.

    Supported file formats are TIFF 8-bit, TIFF 16-bit, TIFF 32-bit float, PNG,
    JPEG, JPEG2000, JSON, CSV, ZIP, HDF5, XML, GML, RAW.
    """

    TIFF = "tiff"
    PNG = "png"
    JPG = "jpg"
    JP2 = "jp2"
    JSON = "json"
    CSV = "csv"
    ZIP = "zip"
    HDF = "hdf"
    XML = "xml"
    GML = "gml"
    TXT = "txt"
    TAR = "tar"
    RAW = "raw"
    SAFE = "safe"
    PICKLE = "pkl"
    NPY = "npy"
    GPKG = "gpkg"
    GEOJSON = "geojson"
    GZIP = "gz"

    @property
    def extension(self) -> str:
        """Returns file extension of the MimeType object."""
        return self.value

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Tests whether MimeType contains a constant defined with string `value`."""
        return value in cls._value2member_map_

    @staticmethod
    def from_string(mime_type_str: str) -> MimeType:
        """Parses mime type from a file extension string."""
        guessed_extension = mimetypes.guess_extension(mime_type_str)

        if guessed_extension:
            mime_type_str = guessed_extension.strip(".")
        else:
            mime_type_str = mime_type_str.split("/")[-1]

        if MimeType.has_value(mime_type_str):
            return MimeType(mime_type_str)

        try:
            return {
                "tif": MimeType.TIFF,
                "jpeg": MimeType.JPG,
                "hdf5": MimeType.HDF,
                "h5": MimeType.HDF,
            }[mime_type_str]
        except KeyError as exception:
            raise ValueError(
                f"Data format {mime_type_str} is not supported."
            ) from exception

    def is_image_format(self) -> bool:
        """Checks whether file format is an image format."""
        return self in frozenset(
            [MimeType.TIFF, MimeType.JPG, MimeType.JP2, MimeType.PNG]
        )

    def is_api_format(self) -> bool:
        """Checks if mime type is supported by Sentinel Hub API"""
        return self in frozenset(
            [MimeType.TIFF, MimeType.JPG, MimeType.PNG, MimeType.JSON]
        )

    def get_string(self) -> str:
        """Get file format as string."""
        if self is MimeType.JP2:
            return "image/jpeg2000"
        if self is MimeType.XML:
            return "text/xml"
        if self is MimeType.RAW:
            return self.value
        return mimetypes.types_map["." + self.value]

    def matches_extension(self, path: str) -> bool:
        """
        Checks if mime type enum is used as the lsat file extension in
        given file path.
        """
        return path.endswith(f".{self.extension}")

    def get_expected_max_value(self) -> float | int:
        """
        Returns max value of image `MimeType` format and raises an error
        if it is not an image format.
        """
        try:
            return {
                MimeType.TIFF: 65535,
                MimeType.JPG: 255,
                MimeType.PNG: 255,
                MimeType.JP2: 10000,
            }[self]
        except KeyError as exception:
            raise ValueError(
                f"Type {self} is not supported by this method."
            ) from exception


class RequestType(Enum):
    """Enum constant class for GET/POST request type."""

    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"
    PATCH = "PATCH"
