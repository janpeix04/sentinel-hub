import functools
import mimetypes
import re
import warnings
from collections.abc import Callable
from enum import Enum, EnumMeta
from typing import ClassVar

import numpy as np
import pyproj
import utm
from aenum import extend_enum

from sentinel_hub import __version__
from sentinel_hub.exception import SHUserWarning


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


class SHConstants:
    """Common constants used in various requests."""

    LATEST = "latest"
    HEADERS: ClassVar[dict[str, str]] = {"User-Agent": f"sentinel-hub/v{__version__}"}


class CRSMeta(EnumMeta):
    """Metaclass used for building CRS Enum class."""

    _UNSUPPORTED_CRS = pyproj.CRS(4326)

    def __new__(mcs, cls, bases, classdict):
        """This is executed at the beginning of runtime when CRS class is created."""
        for direction, direction_value in [("N", "6"), ("S", "7")]:
            for zone in range(1, 61):
                classdict[f"UTM_{zone}{direction}"] = f"32{direction_value}{zone:02}"

        return super().__new__(mcs, cls, bases, classdict)

    def __call__(cls, crs_value, *args, **kwargs):
        """This is executed whenever CRS('something') is called."""
        crs_value = cls._parse_crs(crs_value)

        if (
            isinstance(crs_value, str)
            and not cls.has_value(crs_value)
            and crs_value.isdigit()
            and len(crs_value) >= 4
        ):
            crs_name = f"EPSG_{crs_value}"
            extend_enum(cls, crs_name, crs_value)

        return super().__call__(crs_value, *args, **kwargs)

    @staticmethod
    def _parse_crs(value: object) -> object:
        """
        Method for parsing different inputs representing the same CRS enum.

        Examples:
         - 4326
         - 'EPSG:3857
         - {'init': 32633}
         - geojson['crs']['properties']['name'] string (urn:ogc:def:crs:...)
         - pyproj.CRS(32743)
        """
        if isinstance(value, dict) and "init" in value:
            value = value["init"]

        if hasattr(value, "to_epsg"):
            if value == CRSMeta._UNSUPPORTED_CRS:
                message = (
                    "sentinel-hub supports only WGS84 coordinate reference system with "
                    "coordinates order lng-lat. Given pyproj.CRS(4326) has coordinate order "
                    "lat-lng. Be careful to use the correct order of coordinates."
                )
                warnings.warn(message, category=SHUserWarning)

            epsg_code = value.to_epsg()
            if epsg_code is not None:
                return str(epsg_code)

            if value == CRS.WGS84.pyproj_crs():
                return "4326"

            error_message = (
                f"Failed to determine an EPSG code of the given CRS:\n{value!r}"
            )
            maybe_epsg = value.to_epsg(min_confidence=0)
            if maybe_epsg is not None:
                error_message = (
                    f"{error_message}\nIt might be EPSG {maybe_epsg} but "
                    "pyproj is not confident enough."
                )
            raise ValueError(error_message)

        if isinstance(value, (int, np.integer)):
            return str(value)

        if isinstance(value, str):
            if "urn:ogc:def:crs" in value.lower():
                crs_template = re.compile(
                    r"urn:ogc:def:crs:.+::(?P<code>.+)", re.IGNORECASE
                )
                match = crs_template.match(value)

                if match is None:
                    raise ValueError(f"The value {value} could not be parsed to a CRS.")

                value = match.group("code")

            if value.upper() == "CRS84":
                return "4326"
            return value.lower().replace("epsg:", "").rstrip()
        return value


class CRS(Enum, metaclass=CRSMeta):
    """
    Coordinate Reference System enumerate class.

    Available CRS constants are WGS84, POP_WEB (i.e. Popular Web Mercator) and constants
    in form UTM_<zone><direction>, where zone is an integer from [1, 60] and direction is
    either N or S (i.e. northern or southren hemisphere).
    """

    WGS84 = "4326"
    POP_WEB = "3857"
    #: UTM enum members are defined in CRSMeta.__new__

    def __str__(self) -> str:
        """Method for casting CRS enum into string."""
        return self.ogc_string()

    def __repr__(self) -> str:
        """Method for retrieving CRS enum representation."""
        return f"CRS('{self.value}')"

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Tests whether CRS contains a constant defined with string `value`."""
        return value in cls._value2member_map_

    @property
    def epsg(self) -> int:
        """EPSG code property."""
        return int(self.value)

    def ogc_string(self) -> str:
        """Returns a string of the form authority:id representing the CRS."""
        return f"EPSG:{CRS(self).value}"

    @property
    def opengis_string(self) -> str:
        """Returns a URL to OGC webpage where the CRS is defined."""
        return f"http://www.opengis.net/def/crs/EPSG/0/{self.epsg}"

    def is_utm(self) -> bool:
        """Checks if crs is one of the 64 possible UTM coordinate reference systems."""
        return self.name.startswith("UTM")

    @functools.lru_cache(maxsize=128)
    def projection(self) -> pyproj.Proj:
        """
        Returns a projection in form of pyproj class.

        For better time performance this method will cache 128 most recent results. Cache
        can be released with `CRS.projection.cache_clear()`.
        """
        return pyproj.Proj(self._get_pyproj_projection_def(), preserve_units=True)

    @functools.lru_cache(maxsize=128)
    def pyproj_crs(self) -> pyproj.CRS:
        """
        Returns a pyproj CRS class.

        For better time performance this method will cache 128 most recent results. Cache
        can be released with `CRS.pyproj_crs.cache_clear()`.
        """
        return pyproj.CRS(self._get_pyproj_projection_def())

    @functools.lru_cache(maxsize=512)
    def get_transform_function(
        self, other: CRS, always_xy: bool = True
    ) -> Callable[..., tuple]:
        """
        Returns a function for transforming geometrical objects from one CRS to another. The
        function will support transformations between any objects that pyproj supports.

        For better time performance this method will cache results. Cache can be released with
        `CRS.get_transform_function.cache_clear()`.
        """
        return pyproj.Transformer.from_proj(
            self.projection(), other.projection(), always_xy=always_xy
        ).transform

    @staticmethod
    def get_utm_from_wgs84(lng: float, lat: float) -> CRS:
        """Convert from WGS84 to UTM coordinate system."""
        _, _, zone, _ = utm.from_latlon(lat, lng)
        direction = "N" if lat >= 0 else "S"
        return CRS[f"UTM_{zone}{direction}"]

    def _get_pyproj_projection_def(self) -> str:
        """
        Returns a pyproj crs definition.

        For WGS84 it ensures lng-lat order.
        """
        return (
            "+proj=longlat +ellps=WGS84 +datum=WGS84 +nodefs"
            if self is CRS.WGS84
            else self.ogc_string()
        )
