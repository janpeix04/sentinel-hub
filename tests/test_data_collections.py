from __future__ import annotations

import pickle
from typing import Any

import pytest

from sentinel_hub import DataCollection
from sentinel_hub.data_collections import DataCollectionDefinition, OrbitDirection


@pytest.mark.parametrize(
    ("data_colection_def", "derive_attributes", "expected_attributes"),
    [
        (DataCollectionDefinition(), {}, {"api_id": None}),
        (
            DataCollectionDefinition(api_id="X", catalog_id="Y"),
            {"catalog_id": "Z"},
            {"api_id": "X", "catalog_id": "Z", "collection_type": None},
        ),
        (
            DataCollection.SENTINEL2_L1C.value,
            {"api_id": None},
            {"api_id": None, "catalog_id": "sentinel-2-l1c"},
        ),
    ],
)
def test_derive(
    data_colection_def: DataCollectionDefinition,
    derive_attributes: dict[str, Any],
    expected_attributes: dict[str, Any],
) -> None:
    derived_definition = data_colection_def.derive(**derive_attributes)

    for attribute, value in expected_attributes.items():
        assert value == getattr(derived_definition, attribute)


@pytest.mark.parametrize(
    ("definition_input", "expected"),
    [
        ({}, "DataCollectionDefinition(\n  has_cloud_coverage: False\n)"),
        (
            {"api_id": "X", "_name": "A"},
            "DataCollectionDefinition(\n  api_id: X\n  has_cloud_coverage: False\n)",
        ),
        (
            {"api_id": "Y", "has_cloud_coverage": True},
            "DataCollectionDefinition(\n  api_id: Y\n  has_cloud_coverage: True\n)",
        ),
    ],
)
def test_collection_repr(definition_input: dict[str, Any], expected: str) -> None:
    assert repr(DataCollectionDefinition(**definition_input)) == expected


@pytest.mark.parametrize(
    ("test_definition", "equal_definition"),
    [
        ({"api_id": "X", "_name": "A"}, {"api_id": "X", "_name": "A"}),
        ({"api_id": "X", "_name": "A"}, {"api_id": "X", "_name": "B"}),
        (
            {"api_id": "X", "has_cloud_coverage": False},
            {"api_id": "X", "has_cloud_coverage": False, "_name": "B"},
        ),
        ({"api_id": "X", "has_cloud_coverage": False}, {"api_id": "X"}),
    ],
)
def test_collection_definitions_equal(
    test_definition: dict[str, Any], equal_definition: dict[str, Any]
) -> None:
    def1 = DataCollectionDefinition(**test_definition)
    def2 = DataCollectionDefinition(**equal_definition)
    assert def1 == def2


@pytest.mark.parametrize(
    ("test_definition", "equal_definition"),
    [
        ({"api_id": "X", "_name": "A"}, {"api_id": "Y", "_name": "A"}),
        ({"api_id": "X", "has_cloud_coverage": True}, {"api_id": "X"}),
        ({"api_id": "X", "catalog_id": "Y"}, {"api_id": "X"}),
    ],
)
def test_collection_definitions_not_equal(
    test_definition: dict[str, Any], equal_definition: dict[str, Any]
) -> None:
    def1 = DataCollectionDefinition(**test_definition)
    def2 = DataCollectionDefinition(**equal_definition)
    assert def1 != def2


def test_list_to_tuple_casting() -> None:
    definition = DataCollectionDefinition(bands=["B01"], metabands=["dataMask"])

    assert definition.bands == ("B01",)
    assert definition.metabands == ("dataMask",)


def test_define() -> None:
    data_collection = DataCollection.define(
        "NEW", api_id="X", sensor_type="Sensor", bands=("B01",), has_cloud_coverage=True
    )

    assert data_collection == DataCollection.NEW
    assert DataCollection.NEW.api_id == "X"

    with pytest.raises(ValueError):
        DataCollection.define(
            "NEW_NEW",
            api_id="X",
            sensor_type="Sensor",
            bands=("B01",),
            has_cloud_coverage=True,
        )

    with pytest.raises(ValueError):
        DataCollection.define("NEW", api_id="Y")


def test_define_from() -> None:
    bands = ["B01", "XYZ"]
    data_collection = DataCollection.define_from(
        DataCollection.SENTINEL2_L2A, "NEW_S2", api_id="X", bands=bands
    )

    assert data_collection == DataCollection.NEW_S2
    assert data_collection.api_id == "X"
    assert data_collection.catalog_id == DataCollection.SENTINEL2_L2A.catalog_id
    assert data_collection.bands == tuple(bands)


def test_custom_collection_pickling() -> None:
    data_collection = DataCollection.SENTINEL2_L1C.define_from(
        "PICKLED_S2", service_url=None
    )

    assert pickle.loads(pickle.dumps(data_collection)) is data_collection


@pytest.mark.parametrize(
    "data_collection",
    [
        DataCollection.SENTINEL2_L1C,
        DataCollection.SENTINEL2_L2A,
        DataCollection.SENTINEL1,
        DataCollection.SENTINEL1_IW,
        DataCollection.SENTINEL1_EW_SH_DES,
    ],
)
@pytest.mark.parametrize(
    "attribute",
    [
        "api_id",
        "catalog_id",
        "service_url",
        "bands",
        "metabands",
        "sensor_type",
        "processing_level",
    ],
)
def test_attributes(data_collection: DataCollection, attribute: str) -> None:
    value = getattr(data_collection, attribute)
    assert value is not None
    assert value == getattr(data_collection.value, attribute)


@pytest.mark.parametrize(
    ("data_collection", "catalog_id", "has_cloud_coverage"),
    [
        (DataCollection.SENTINEL2_L1C, "sentinel-2-l1c", True),
        (DataCollection.SENTINEL2_L2A, "sentinel-2-l2a", True),
    ],
)
def test_sentinel2_definitions(
    data_collection: DataCollection, catalog_id: str, has_cloud_coverage: bool
) -> None:
    assert data_collection.catalog_id == catalog_id
    assert data_collection.has_cloud_coverage is has_cloud_coverage


@pytest.mark.parametrize(
    (
        "data_collection",
        "swath_mode",
        "polarization",
        "resolution",
        "orbit_direction",
        "band_names",
    ),
    [
        (
            DataCollection.SENTINEL1,
            None,
            None,
            None,
            OrbitDirection.BOTH,
            ["VV", "HH", "VH", "HV"],
        ),
        (DataCollection.SENTINEL1_IW, "IW", "DV", "HIGH", "BOTH", ["VV", "VH"]),
        (
            DataCollection.SENTINEL1_IW_ASC,
            "IW",
            "DV",
            "HIGH",
            "ASCENDING",
            ["VV", "VH"],
        ),
        (
            DataCollection.SENTINEL1_IW_DES,
            "IW",
            "DV",
            "HIGH",
            "DESCENDING",
            ["VV", "VH"],
        ),
        (DataCollection.SENTINEL1_EW, "EW", "DH", "MEDIUM", "BOTH", ["HH", "HV"]),
        (
            DataCollection.SENTINEL1_EW_ASC,
            "EW",
            "DH",
            "MEDIUM",
            "ASCENDING",
            ["HH", "HV"],
        ),
        (
            DataCollection.SENTINEL1_EW_DES,
            "EW",
            "DH",
            "MEDIUM",
            "DESCENDING",
            ["HH", "HV"],
        ),
        (DataCollection.SENTINEL1_EW_SH, "EW", "SH", "MEDIUM", "BOTH", ["HH"]),
        (DataCollection.SENTINEL1_EW_SH_ASC, "EW", "SH", "MEDIUM", "ASCENDING", ["HH"]),
        (
            DataCollection.SENTINEL1_EW_SH_DES,
            "EW",
            "SH",
            "MEDIUM",
            "DESCENDING",
            ["HH"],
        ),
    ],
)
def test_sentinel1_definitions(
    data_collection: DataCollection,
    swath_mode: str | None,
    polarization: str | None,
    resolution: str | None,
    orbit_direction: str,
    band_names: list[str],
) -> None:
    assert data_collection.api_id == "sentinel-1-grd"
    assert data_collection.catalog_id == "sentinel-1-grd"
    assert data_collection.service_url == DataCollection.SENTINEL2_L2A.service_url
    assert data_collection.processing_level == "GRD"
    assert data_collection.has_cloud_coverage is False
    assert data_collection.is_sentinel1

    assert data_collection.swath_mode == swath_mode
    assert data_collection.polarization == polarization
    assert data_collection.resolution == resolution
    assert data_collection.orbit_direction == orbit_direction

    assert [band.name for band in data_collection.bands] == band_names
    assert [band.name for band in data_collection.metabands] == [
        "localIncidenceAngle",
        "scatteringArea",
        "shadowMask",
        "dataMask",
    ]


def test_sentinel1_collections_are_distinct() -> None:
    names = [
        "SENTINEL1",
        *(
            f"SENTINEL1_{mode}{suffix}"
            for mode in ["IW", "EW", "EW_SH"]
            for suffix in ["", "_ASC", "_DES"]
        ),
    ]
    collections = [DataCollection[name] for name in names]

    assert all(collection.is_sentinel1 for collection in collections)
    assert len({collection.value for collection in collections}) == len(names)


@pytest.mark.parametrize(
    "data_collection", [DataCollection.SENTINEL2_L1C, DataCollection.SENTINEL2_L2A]
)
def test_is_not_sentinel1(data_collection: DataCollection) -> None:
    assert not data_collection.is_sentinel1


@pytest.mark.parametrize(
    ("data_collection", "orbit_direction", "expected"),
    [
        (DataCollection.SENTINEL1, OrbitDirection.ASCENDING, True),
        (DataCollection.SENTINEL1, OrbitDirection.DESCENDING, True),
        (DataCollection.SENTINEL1_IW_ASC, OrbitDirection.ASCENDING, True),
        (DataCollection.SENTINEL1_IW_ASC, "ascending", True),
        (DataCollection.SENTINEL1_IW_ASC, OrbitDirection.DESCENDING, False),
        (DataCollection.SENTINEL1_EW_DES, OrbitDirection.DESCENDING, True),
        (DataCollection.SENTINEL1_EW_DES, OrbitDirection.ASCENDING, False),
        (DataCollection.SENTINEL2_L2A, OrbitDirection.DESCENDING, True),
    ],
)
def test_contains_orbit_direction(
    data_collection: DataCollection, orbit_direction: str, expected: bool
) -> None:
    assert data_collection.contains_orbit_direction(orbit_direction) is expected


def test_define_sentinel1_variant() -> None:
    data_collection = DataCollection.SENTINEL1.define_from(
        "SENTINEL1_SM_VV_ASC",
        swath_mode="SM",
        polarization="SV",
        resolution="HIGH",
        orbit_direction=OrbitDirection.ASCENDING,
    )

    assert data_collection.is_sentinel1
    assert data_collection.swath_mode == "SM"
    assert data_collection.polarization == "SV"
    assert data_collection.resolution == "HIGH"
    assert data_collection.orbit_direction == "ASCENDING"
    assert data_collection.api_id == "sentinel-1-grd"


def test_catalog_id_falls_back_to_api_id() -> None:
    data_collection = DataCollection.define("ONLY_API_ID", api_id="only-api-id")
    assert data_collection.catalog_id == "only-api-id"


def test_attributes_empty_fail() -> None:
    data_collection = DataCollection.define("EMPTY")

    for attr_name in ["api_id", "catalog_id", "bands", "metabands"]:
        with pytest.raises(ValueError):
            getattr(data_collection, attr_name)

    assert data_collection.service_url is None


def test_get_available_collections() -> None:
    number_of_collection = len(DataCollection.get_available_collections())
    DataCollection.define("NEW_NEW", api_id="Z")
    collections = DataCollection.get_available_collections()

    assert len(collections) == number_of_collection + 1
    assert all(isinstance(collection, DataCollection) for collection in collections)
