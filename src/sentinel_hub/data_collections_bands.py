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
    GRAMS_CM2 = "GRAMS_CM2"
    ATMCM = "ATMCM"
    LOG10_1_M = "LOG10_1_M"
    LOG10_GRAMS_M2 = "LOG10_GRAMS_M2"
    LOG10_MILLIGRAMS_M3 = "LOG10_MILLIGRAMS_M3"
    MICROEINSTEINS_S_M2 = "MICROEINSTEINS_S_M2"
    ANGSTROM_EXPONENT = "ANGSTROM_EXPONENT"


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
    SENTINEL3_OLCI = tuple(
        Band(
            f"B{index:02}", (Unit.REFLECTANCE, Unit.RADIANCE), (np.float32, np.float32)
        )
        for index in range(1, 22)
    )
    SENTINEL3_SLSTR = (
        *(
            Band(
                f"S{index}", (Unit.REFLECTANCE, Unit.RADIANCE), (np.float32, np.float32)
            )
            for index in range(1, 7)
        ),
        *(
            Band(name, (Unit.BRIGHTNESS_TEMPERATURE,), (np.float32,))
            for name in ["S7", "S8", "S9", "F1", "F2"]
        ),
    )
    SENTINEL3_OLCI_L2 = (
        Band("GIFAPAR", (Unit.FRACTION,), (np.float32,)),
        Band("IWV_L", (Unit.KG_M2,), (np.float32,)),
        Band("OTCI", (Unit.INDEX,), (np.float32,)),
        *(
            Band(name, (Unit.REFLECTANCE,), (np.float32,))
            for name in ["RC681", "RC865"]
        ),
        Band("IWV_W", (Unit.KG_M2,), (np.float32,)),
        *(
            Band(name, (Unit.LOG10_MILLIGRAMS_M3,), (np.float32,))
            for name in ["CHL_OC4ME", "CHL_NN"]
        ),
        Band("TSM_NN", (Unit.LOG10_GRAMS_M2,), (np.float32,)),
        Band("PAR", (Unit.MICROEINSTEINS_S_M2,), (np.float32,)),
        *(
            Band(name, (Unit.LOG10_1_M,), (np.float32,))
            for name in ["KD490_M07", "ADG443_NN"]
        ),
        Band("A865", (Unit.ANGSTROM_EXPONENT,), (np.float32,)),
        Band("T865", (Unit.OPTICAL_DEPTH,), (np.float32,)),
        *(
            Band(f"B{index:02}", (Unit.REFLECTANCE,), (np.float32,))
            for index in range(1, 22)
            if index not in (13, 14, 15, 19, 20)
        ),
    )
    SENTINEL3_SLSTR_L2 = (
        *(
            Band(name, (Unit.KELVIN,), (np.float32,))
            for name in ["LST", "LST_uncertainty"]
        ),
        Band("NDVI", (Unit.INDEX,), (np.float32,)),
    )
    SENTINEL3_SYNERGY_L2 = (
        *(
            Band(name, (Unit.REFLECTANCE,), (np.float32,))
            for name in [
                *(f"B{index:02}" for index in [*range(1, 13), 16, 17, 18, 21]),
                *(f"S{index}" for index in [1, 2, 3, 5, 6]),
            ]
        ),
        # 10-day (V10) and 1-day (VG1) vegetation composites
        *(
            Band(f"{name}_{suffix}", (unit,), (np.float32,))
            for suffix in ["V10", "VG1"]
            for name, unit in [
                ("B0", Unit.REFLECTANCE),
                ("B2", Unit.REFLECTANCE),
                ("B3", Unit.REFLECTANCE),
                ("MIR", Unit.REFLECTANCE),
                ("NDVI", Unit.INDEX),
                ("OG", Unit.ATMCM),
                ("WVG", Unit.GRAMS_CM2),
                ("AG", Unit.OPTICAL_DEPTH),
            ]
        ),
        Band("TOA_NDVI_VG1", (Unit.INDEX,), (np.float32,)),
    )
    SENTINEL5P = (
        *(
            Band(name, (Unit.MOL_M2,), (np.float32,))
            for name in ["CO", "HCHO", "NO2", "O3", "SO2"]
        ),
        Band("CH4", (Unit.PPB,), (np.float32,)),
        *(
            Band(name, (Unit.INDEX,), (np.float32,))
            for name in ["AER_AI_340_380", "AER_AI_354_388"]
        ),
        *(
            Band(name, (Unit.PASCALS,), (np.float32,))
            for name in ["CLOUD_BASE_PRESSURE", "CLOUD_TOP_PRESSURE"]
        ),
        *(
            Band(name, (Unit.METERS,), (np.float32,))
            for name in ["CLOUD_BASE_HEIGHT", "CLOUD_TOP_HEIGHT"]
        ),
        Band("CLOUD_OPTICAL_THICKNESS", (Unit.OPTICAL_DEPTH,), (np.float32,)),
        Band("CLOUD_FRACTION", (Unit.FRACTION,), (np.float32,)),
    )


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
    SENTINEL3_OLCI = (
        Band("QUALITY_FLAGS", (Unit.DN,), (np.uint32,)),
        *(
            Band(name, (Unit.DEGREES,), (np.float32,))
            for name in ["SAA", "SZA", "VAA", "VZA"]
        ),
        Band("HUMIDITY", (Unit.PERCENT,), (np.float32,)),
        Band("SEA_LEVEL_PRESSURE", (Unit.HECTOPASCALS,), (np.float32,)),
        *(
            Band(name, (Unit.KG_M2,), (np.float32,))
            for name in ["TOTAL_COLUMN_OZONE", "TOTAL_COLUMN_WATER_VAPOUR"]
        ),
        Band("dataMask", (Unit.DN,), (bool,)),
    )
    SENTINEL3_SLSTR = (Band("dataMask", (Unit.DN,), (bool,)),)
    SENTINEL3_OLCI_L2 = (
        Band("LQSF", (Unit.DN,), (np.uint32,)),
        Band("dataMask", (Unit.DN,), (bool,)),
    )
    SENTINEL3_SLSTR_L2 = (
        *(Band(name, (Unit.DN,), (np.uint16,)) for name in ["CLOUD", "CONFIDENCE"]),
        *(Band(name, (Unit.DN,), (np.uint8,)) for name in ["BAYES", "POINTING"]),
        Band("dataMask", (Unit.DN,), (bool,)),
    )
    SENTINEL3_SYNERGY_L2 = (
        *(
            Band(f"{name}_{suffix}", (Unit.DEGREES,), (np.float32,))
            for suffix in ["V10", "VG1"]
            for name in ["SAA", "SZA", "VAA", "VZA"]
        ),
        Band("dataMask", (Unit.DN,), (bool,)),
    )
    SENTINEL5P = (Band("dataMask", (Unit.DN,), (bool,)),)
