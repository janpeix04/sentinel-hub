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

    SENTINEL2 = "Sentinel-2"


class _SensorType:
    """Satellite sensors."""

    MSI = "MSI"


class _ProcessingLevel:
    """Processing levels."""

    L1C = "L1C"
    L2A = "L2A"


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
    wfs_id: str | None = None
    service_url: str | None = None
    collection_type: str | None = None
    sensor_type: str | None = None
    processing_level: str | None = None
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
        wfs_id="DSS1",
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
        wfs_id="DSS2",
        service_url=ServiceUrl.CDSE,
        collection_type=_CollectionType.SENTINEL2,
        sensor_type=_SensorType.MSI,
        processing_level=_ProcessingLevel.L2A,
        bands=Bands.SENTINEL2_L2A,
        metabands=MetaBands.SENTINEL2_L2A,
        has_cloud_coverage=True,
    )

    @classmethod
    def define(
        cls,
        name: str,
        *,
        api_id: str | None = None,
        catalog_id: str | None = None,
        wfs_id: str | None = None,
        service_url: str | None = None,
        collection_type: str | None = None,
        sensor_type: str | None = None,
        processing_level: str | None = None,
        bands: tuple[Band, ...] | None = None,
        metabands: tuple[Band, ...] | None = None,
        has_cloud_coverage: bool = False,
    ) -> DataCollection:
        """
        Define a new data collection.

        Note that all parameters, except `name` are optional. If a data collection definition 
        won't be used for a certain use case (e.g. Process API, WFS, etc.), parameters for that 
        use case don't have to be defined.
        """
        definition = DataCollectionDefinition(
            api_id=api_id,
            catalog_id=catalog_id,
            wfs_id=wfs_id,
            service_url=service_url,
            collection_type=collection_type,
            sensor_type=sensor_type,
            processing_level=processing_level,
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
    def wfs_id(self) -> str:
        """Provides a Sentinel Hub WFS identifier or raises an error if it is not defined."""
        if self.value.wfs_id is None:
            raise ValueError(
                f"Data collection {self.name} is missing a Sentinel Hub WFS identifier"
            )
        return self.value.wfs_id

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

    @classmethod
    def get_available_collections(cls) -> list[DataCollection]:
        """Returns which data collections are available for configured Sentinel Hub OGC URL."""
        return list(cls)
