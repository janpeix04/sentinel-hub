from dataclasses import dataclass
from enum import Enum

import numpy as np


class Unit(Enum):
    """Collection of all units used by Sentinel Hub."""

    DN = "DN"
    PPB = "PPB"
    INDEX = "INDEX"
    KELVIN = "KELVIN"
    METERS = "METERS"
    MOL_M2 = "MOL_M2"
    KG_M2 = "KG_M2"
    DEGREES = "DEGREES"
    PASCALS = "PASCALS"
    PERCENT = "PERCENT"
    FRACTION = "FRACTION"
    RADIANCE = "RADIANCE"
    KILOMETERS = "KILOMETERS"
    REFLECTANCE = "REFLECTANCE"
    LINEAR_POWER = "LINEAR_POWER"
    OPTICAL_DEPTH = "OPTICAL_DEPTH"
    BRIGHTNESS_TEMPERATURE = "BRIGHTNESS_TEMPERATURE"
    SURFACE_TEMPERATURE = "SURFACE_TEMPERATURE"
    HECTOPASCALS = "HECTOPASCALS"


@dataclass(frozen=True)
class Band:
    """
    Information about a band available in a collection.

    Units and output types need to have the same order i.e. the unit at position 2 has to match
    the output type at position 2. The unit (and output type) at position 0 is considered the
    default.
    """

    name: str
    units: tuple[Unit, ...]
    output_types: tuple[type, ...]


class Bands:
    """
    Different collections of bands taken from Sentinel Hub docs:
    <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data.html>.
    """

    SENTINEL2_L1C = tuple(
        Band(name, (Unit.REFLECTANCE, Unit.DN), (np.float32, np.uint16))
        for name in [
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B8A",
            "B09",
            "B10",
            "B11",
            "B12",
        ]
    )
    SENTINEL2_L2A = tuple(
        Band(name, (Unit.REFLECTANCE, Unit.DN), (np.float32, np.uint16))
        for name in [
            "B01",
            "B02",
            "B03",
            "B04",
            "B05",
            "B06",
            "B07",
            "B08",
            "B8A",
            "B09",
            "B11",
            "B12",
        ]
    )
    SENTINEL1 = tuple(
        Band(name, (Unit.LINEAR_POWER,), (np.float32,))
        for name in ["VV", "HH", "VH", "HV"]
    )
    SENTINEL1_IW = tuple(
        Band(name, (Unit.LINEAR_POWER,), (np.float32,)) for name in ["VV", "VH"]
    )
    SENTINEL1_EW = tuple(
        Band(name, (Unit.LINEAR_POWER,), (np.float32,)) for name in ["HH", "HV"]
    )
    SENTINEL1_EW_SH = (Band("HH", (Unit.LINEAR_POWER,), (np.float32,)),)


class MetaBands:
    """
    Different collections of bands taken from Sentinel Hub docs:
    <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data.html>.
    """

    SENTINEL2_L1C = (
        *(
            Band(name, (Unit.DEGREES,), (np.float32,))
            for name in [
                "sunAzimuthAngles",
                "viewAzimuthMean",
                "sunZenithAngles",
                "viewZenithMean",
            ]
        ),
        *(Band(name, (Unit.DN,), (np.uint8,)) for name in ["CLP", "CLM"]),
        Band("dataMask", (Unit.DN,), (bool,)),
    )
    SENTINEL2_L2A = (
        Band("AOT", (Unit.OPTICAL_DEPTH, Unit.DN), (np.float32, np.uint16)),
        *(
            Band(name, (Unit.DEGREES,), (np.float32,))
            for name in [
                "sunAzimuthAngles",
                "viewAzimuthMean",
                "sunZenithAngles",
                "viewZenithMean",
            ]
        ),
        *(Band(name, (Unit.PERCENT,), (np.uint8,)) for name in ["SNW", "CLD"]),
        *(Band(name, (Unit.DN,), (np.uint8,)) for name in ["SCL", "CLP", "CLM"]),
        Band("dataMask", (Unit.DN,), (bool,)),
    )
    SENTINEL1 = (
        Band("localIncidenceAngle", (Unit.DEGREES,), (np.float32,)),
        Band("scatteringArea", (Unit.DN,), (np.float32,)),
        Band("shadowMask", (Unit.DN,), (np.uint8,)),
        Band("dataMask", (Unit.DN,), (bool,)),
    )
