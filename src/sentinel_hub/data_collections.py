from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any

from aenum import extend_enum

from sentinel_hub.constants import ServiceUrl
from sentinel_hub.data_collections_bands import Band, Bands, MetaBands

if TYPE_CHECKING:
    from enum import Enum, EnumMeta
else:
    from aenum import Enum, EnumMeta


class _CollectionType:
    """Types of Sentinel Hub data collections."""

    SENTINEL1 = "Sentinel-1"
    SENTINEL2 = "Sentinel-2"
    SENTINEL3 = "Sentinel-3"


class _SensorType:
    """Satellite sensors."""

    C_SAR = "C-SAR"
    MSI = "MSI"
    OLCI = "OLCI"
    SLSTR = "SLSTR"


class _ProcessingLevel:
    """Processing levels."""

    GRD = "GRD"
    L1B = "L1B"
    L1C = "L1C"
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


class _DataCollectionMeta(EnumMeta):
    """Metaclass that builds DataCollection class enums."""

    def __call__(cls, value, *args, **kwargs):  # type: ignore[no-untyped-def]
        """
        This is executed whenever `DataCollection('something')` is called.

        This solves a problem of pickling a custom DataCollection and unpickling it in
        another process.
        """
        if (
            isinstance(value, DataCollectionDefinition)
            and value not in cls._value2member_map_
            and value._name
        ):
            cls._try_add_data_collection(value._name, value)

        return super().__call__(value, *args, **kwargs)


@dataclass(frozen=True)
class DataCollectionDefinition:
    """
    An immutable definition of a data collection.

    Check `DataCollection.define` for more info about attributes of this class.
    """

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
    # The following parameter is used to preserve custom DataCollection name during pickling and unpickling process:
    _name: str | None = field(default=None, compare=False)

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
            f"{name}: {value}"
            for name, value in valid_params.items()
            if name != "_name"
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


class DataCollection(Enum, metaclass=_DataCollectionMeta):
    """
    An enum class for data collections.

    It contains a number of predefined data collections, which are the most commonly used with
    Sentinel Hub service. Additionally, it also allows defining new data collections by
    specifying data collection parameters relevant for the service. Check
    `DataCollection.define` and similar methods for more.
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

    @classmethod
    def define(
        cls,
        name: str,
        *,
        api_id: str | None = None,
        catalog_id: str | None = None,
        service_url: str | None = None,
        collection_type: str | None = None,
        sensor_type: str | None = None,
        processing_level: str | None = None,
        swath_mode: str | None = None,
        polarization: str | None = None,
        resolution: str | None = None,
        orbit_direction: str | None = None,
        bands: tuple[Band, ...] | None = None,
        metabands: tuple[Band, ...] | None = None,
        has_cloud_coverage: bool = False,
    ) -> DataCollection:
        """
        Define a new data collection.

        Note that all parameters, except `name` are optional. If a data collection definition
        won't be used for a certain use case (e.g. Process API, Catalog API), parameters for that
        use case don't have to be defined.
        """
        definition = DataCollectionDefinition(
            api_id=api_id,
            catalog_id=catalog_id,
            service_url=service_url,
            collection_type=collection_type,
            sensor_type=sensor_type,
            processing_level=processing_level,
            swath_mode=swath_mode,
            polarization=polarization,
            resolution=resolution,
            orbit_direction=orbit_direction,
            bands=bands,
            metabands=metabands,
            has_cloud_coverage=has_cloud_coverage,
            _name=name,
        )
        cls._try_add_data_collection(name, definition)
        return cls(definition)

    def define_from(self, name: str, **params: Any) -> DataCollection:
        """Define a new data collection from an existing one."""
        definition = self.value
        new_definition = definition.derive(**params, _name=name)

        self._try_add_data_collection(name, new_definition)
        return DataCollection(new_definition)

    @classmethod
    def _try_add_data_collection(
        cls, name: str, definition: DataCollectionDefinition
    ) -> None:
        """
        Tries adding a new data collection definition. If the exact enum has already been
        defined then it won't do anything. However, if either a name or a definition has
        already been matched with another name or definition then it will raise an error.
        """
        is_name_defined = name in cls.__members__
        is_enum_defined = is_name_defined and cls.__members__[name].value == definition
        is_definition_defined = definition in cls._value2member_map_

        if is_enum_defined:
            return

        if not is_name_defined and not is_definition_defined:
            extend_enum(cls, name, definition)
            return

        if is_name_defined:
            raise ValueError(
                f"Data collection name `{name}` is already taken by another data collection"
            )

        existing_collection = cls._value2member_map_[definition]
        raise ValueError(
            f"Data collection definition is already taken by {existing_collection}. Two different "
            "DataCollection enums cannot have the same definition."
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
        """Returns which data collections are available for configured Sentinel Hub OGC URL."""
        return list(cls)
