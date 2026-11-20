from dataclasses import dataclass, fields
from enum import Enum
from typing import Any

from sentinel_hub.constants import ServiceUrl
from sentinel_hub.data_collections_bands import Band, Bands, MetaBands


class _CollectionType:
    """Types of Sentinel Hub data collections."""

    SENTINEL1 = "Sentinel-1"
    SENTINEL2 = "Sentinel-2"
    SENTINEL3 = "Sentinel-3"
    SENTINEL5P = "Sentinel-5P"


class _SensorType:
    """Satellite sensors."""

    C_SAR = "C-SAR"
    MSI = "MSI"
    OLCI = "OLCI"
    SLSTR = "SLSTR"
    SYNERGY = "OLCI-SLSTR"
    TROPOMI = "TROPOMI"


class _ProcessingLevel:
    """Processing levels."""

    GRD = "GRD"
    L1B = "L1B"
    L1C = "L1C"
    L2 = "L2"
    L2A = "L2A"


class _SwathMode:
    """Swath (acquisition) modes for SAR sensors."""

    IW = "IW"
    EW = "EW"
    SM = "SM"
    WV = "WV"


class _Polarization:
    """SAR polarizations."""

    DV = "DV"
    DH = "DH"
    SV = "SV"
    SH = "SH"
    HH = "HH"
    HV = "HV"
    VV = "VV"
    VH = "VH"


class _Resolution:
    """Product resolution (specific to Sentinel-1 collections)."""

    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class OrbitDirection:
    """Orbit directions."""

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"
    BOTH = "BOTH"


def _shallow_asdict(dataclass_instance: Any) -> dict[str, Any]:
    """
    Returns a dictionary of fields and values, but is not recursive and does not deepcopy
    like `asdict`.
    """
    # This definition needs to be above the class definitions in the file
    return {
        field.name: getattr(dataclass_instance, field.name)
        for field in fields(dataclass_instance)
    }


@dataclass(frozen=True)
class DataCollectionDefinition:
    """An immutable definition of a data collection, used as the value of `DataCollection` members."""

    api_id: str | None = None
    catalog_id: str | None = None
    service_url: str | None = None
    collection_type: str | None = None
    sensor_type: str | None = None
    processing_level: str | None = None
    swath_mode: str | None = None
    polarization: str | None = None
    resolution: str | None = None
    orbit_direction: str | None = None
    bands: tuple[Band, ...] | None = None
    metabands: tuple[Band, ...] | None = None
    has_cloud_coverage: bool = False

    def __post_init__(self):  # type: ignore[no-untyped-def] # not typechecked because we mutate immutable dataclasses
        """
        In case a list of bands or metabands has been given this makes sure to cast it into
        a tuple.
        """
        if isinstance(self.bands, list):
            object.__setattr__(self, "bands", tuple(self.bands))
        if isinstance(self.metabands, list):
            object.__setattr__(self, "metabands", tuple(self.metabands))

    def __repr__(self) -> str:
        """A nicer representation of parameters that define a data collection."""
        valid_params = {
            name: value
            for name, value in _shallow_asdict(self).items()
            if value is not None
        }
        params_repr = "\n  ".join(
            f"{name}: {value}" for name, value in valid_params.items()
        )
        return f"{self.__class__.__name__}(\n  {params_repr}\n)"

    def derive(self, **params: Any) -> DataCollectionDefinition:
        """
        Create a new data collection definition from current definition and parameters that
        override current parameters.
        """
        derived_params = _shallow_asdict(self)
        derived_params.update(params)

        return DataCollectionDefinition(**derived_params)


class DataCollection(Enum):
    """
    An enum class for data collections.

    Only the predefined data collections below are supported, new members cannot be added.
    Filters that are not part of a collection (e.g. a Sentinel-1 acquisition mode or an
    orbit direction) are passed per request through `other_args`.
    """

    SENTINEL2_L1C = DataCollectionDefinition(
        api_id="sentinel-2-l1c",
        catalog_id="sentinel-2-l1c",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL2,
        sensor_type=_SensorType.MSI,
        processing_level=_ProcessingLevel.L1C,
        bands=Bands.SENTINEL2_L1C,
        metabands=MetaBands.SENTINEL2_L1C,
        has_cloud_coverage=True,
    )
    SENTINEL2_L2A = DataCollectionDefinition(
        api_id="sentinel-2-l2a",
        catalog_id="sentinel-2-l2a",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL2,
        sensor_type=_SensorType.MSI,
        processing_level=_ProcessingLevel.L2A,
        bands=Bands.SENTINEL2_L2A,
        metabands=MetaBands.SENTINEL2_L2A,
        has_cloud_coverage=True,
    )
    SENTINEL1 = DataCollectionDefinition(
        api_id="sentinel-1-grd",
        catalog_id="sentinel-1-grd",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL1,
        sensor_type=_SensorType.C_SAR,
        processing_level=_ProcessingLevel.GRD,
        orbit_direction=OrbitDirection.BOTH,
        bands=Bands.SENTINEL1,
        metabands=MetaBands.SENTINEL1,
    )
    SENTINEL1_IW = SENTINEL1.derive(
        swath_mode=_SwathMode.IW,
        polarization=_Polarization.DV,
        resolution=_Resolution.HIGH,
        bands=Bands.SENTINEL1_IW,
    )
    SENTINEL1_IW_ASC = SENTINEL1_IW.derive(orbit_direction=OrbitDirection.ASCENDING)
    SENTINEL1_IW_DES = SENTINEL1_IW.derive(orbit_direction=OrbitDirection.DESCENDING)
    SENTINEL1_EW = SENTINEL1.derive(
        swath_mode=_SwathMode.EW,
        polarization=_Polarization.DH,
        resolution=_Resolution.MEDIUM,
        bands=Bands.SENTINEL1_EW,
    )
    SENTINEL1_EW_ASC = SENTINEL1_EW.derive(orbit_direction=OrbitDirection.ASCENDING)
    SENTINEL1_EW_DES = SENTINEL1_EW.derive(orbit_direction=OrbitDirection.DESCENDING)
    SENTINEL1_EW_SH = SENTINEL1_EW.derive(
        polarization=_Polarization.SH,
        bands=Bands.SENTINEL1_EW_SH,
    )
    SENTINEL1_EW_SH_ASC = SENTINEL1_EW_SH.derive(
        orbit_direction=OrbitDirection.ASCENDING
    )
    SENTINEL1_EW_SH_DES = SENTINEL1_EW_SH.derive(
        orbit_direction=OrbitDirection.DESCENDING
    )
    SENTINEL3_OLCI = DataCollectionDefinition(
        api_id="sentinel-3-olci",
        catalog_id="sentinel-3-olci",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL3,
        sensor_type=_SensorType.OLCI,
        processing_level=_ProcessingLevel.L1B,
        bands=Bands.SENTINEL3_OLCI,
        metabands=MetaBands.SENTINEL3_OLCI,
    )
    SENTINEL3_SLSTR = DataCollectionDefinition(
        api_id="sentinel-3-slstr",
        catalog_id="sentinel-3-slstr",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL3,
        sensor_type=_SensorType.SLSTR,
        processing_level=_ProcessingLevel.L1B,
        bands=Bands.SENTINEL3_SLSTR,
        metabands=MetaBands.SENTINEL3_SLSTR,
        has_cloud_coverage=True,
    )
    SENTINEL3_OLCI_L2 = SENTINEL3_OLCI.derive(
        api_id="sentinel-3-olci-l2",
        catalog_id="sentinel-3-olci-l2",
        processing_level=_ProcessingLevel.L2,
        bands=Bands.SENTINEL3_OLCI_L2,
        metabands=MetaBands.SENTINEL3_OLCI_L2,
        has_cloud_coverage=True,
    )
    SENTINEL3_SLSTR_L2 = SENTINEL3_SLSTR.derive(
        api_id="sentinel-3-slstr-l2",
        catalog_id="sentinel-3-slstr-l2",
        processing_level=_ProcessingLevel.L2,
        bands=Bands.SENTINEL3_SLSTR_L2,
        metabands=MetaBands.SENTINEL3_SLSTR_L2,
    )
    SENTINEL3_SYNERGY_L2 = DataCollectionDefinition(
        api_id="sentinel-3-synergy-l2",
        catalog_id="sentinel-3-synergy-l2",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL3,
        sensor_type=_SensorType.SYNERGY,
        processing_level=_ProcessingLevel.L2,
        bands=Bands.SENTINEL3_SYNERGY_L2,
        metabands=MetaBands.SENTINEL3_SYNERGY_L2,
    )
    SENTINEL5P = DataCollectionDefinition(
        api_id="sentinel-5p-l2",
        catalog_id="sentinel-5p-l2",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL5P,
        sensor_type=_SensorType.TROPOMI,
        processing_level=_ProcessingLevel.L2,
        bands=Bands.SENTINEL5P,
        metabands=MetaBands.SENTINEL5P,
    )

    @property
    def api_id(self) -> str:
        """Provides a Sentinel Hub Process API identifier or raises an error if it is not defined."""
        if self.value.api_id is None:
            raise ValueError(
                f"Data collection {self.name} is missing a Sentinel Hub Process API identifier"
            )
        return self.value.api_id

    @property
    def catalog_id(self) -> str:
        """Provides a Sentinel Hub Catalog API identifier or raises an error if it is not defined."""
        if self.value.catalog_id is not None:
            return self.value.catalog_id
        if self.value.api_id is not None:
            # A fallback because Process API and Catalog API IDs should now be unified
            return self.value.api_id
        raise ValueError(
            f"Data collection {self.name} is missing a Sentinel Hub Catalog API identifier"
        )

    @property
    def bands(self) -> tuple[Band, ...]:
        """Provides band information available for the data collection."""
        if self.value.bands is None:
            raise ValueError(f"Data collection {self.name} does not define bands")
        return self.value.bands

    @property
    def metabands(self) -> tuple[Band, ...]:
        """Provides metaband information available for the data collection."""
        if self.value.metabands is None:
            raise ValueError(f"Data collection {self.name} does not define metabands")
        return self.value.metabands

    def __getattr__(self, item: str) -> Any:
        """
        The following insures that any attribute from DataCollectionDefinition, which is
        already not a property or an attribute of DataCollection, becomes an attribute of
        DataCollection.
        """
        if (
            not item.startswith("_")
            and hasattr(self, "value")
            and isinstance(self.value, DataCollectionDefinition)
        ):
            definition_dict = _shallow_asdict(self.value)
            if item in definition_dict:
                return definition_dict[item]

        return super().__getattribute__(item)

    @property
    def is_sentinel1(self) -> bool:
        """Checks if data collection is a Sentinel-1 collection type."""
        return self.collection_type == _CollectionType.SENTINEL1

    @property
    def is_sentinel3(self) -> bool:
        """Checks if data collection is a Sentinel-3 collection type."""
        return self.collection_type == _CollectionType.SENTINEL3

    @property
    def is_sentinel5p(self) -> bool:
        """Checks if data collection is a Sentinel-5P collection type."""
        return self.collection_type == _CollectionType.SENTINEL5P

    def contains_orbit_direction(self, orbit_direction: str) -> bool:
        """Checks if a data collection contains given orbit direction."""
        defined_direction = self.orbit_direction
        if (
            defined_direction is None
            or defined_direction.upper() == OrbitDirection.BOTH
        ):
            return True
        return orbit_direction.upper() == defined_direction.upper()

    @classmethod
    def get_available_collections(cls) -> list[DataCollection]:
        """Returns all predefined data collections."""
        return list(cls)
