from __future__ import annotations

import datetime as dt

import dateutil.tz
import pytest

from sentinel_hub import CRS, BBox, Geometry, SHCatalog, SHConfig
from sentinel_hub.api.catalog import CatalogSearchIterator

TEST_BBOX = BBox((46.16, -16.15, 46.51, -15.58), CRS.WGS84)
SENTINEL1_IW_FILTER = (
    "sar:instrument_mode='IW' AND s1:polarization='DV' AND s1:resolution='HIGH'"
)

pytestmark = pytest.mark.sh_integration


@pytest.fixture(name="catalog")
def catalog_fixture(config: SHConfig) -> SHCatalog:
    return SHCatalog(config=config)


def test_info(catalog: SHCatalog, config: SHConfig) -> None:
    info = catalog.get_info()

    assert isinstance(info, dict)
    for link in info["links"]:
        assert link["href"].startswith(
            (config.sh_base_url, "https://documentation.dataspace.copernicus.eu")
        )


def test_conformance(catalog: SHCatalog) -> None:
    conformance = catalog.get_conformance()
    assert isinstance(conformance, dict)


def test_get_collections(catalog: SHCatalog) -> None:
    collections = catalog.get_collections()

    assert isinstance(collections, list)
    assert len(collections) >= 3


@pytest.mark.parametrize("collection_id", ["sentinel-2-l1c", "sentinel-1-grd"])
def test_get_collection(catalog: SHCatalog, collection_id: str) -> None:
    collection_info = catalog.get_collection(collection_id)
    assert isinstance(collection_info, dict)


def test_get_feature(catalog: SHCatalog) -> None:
    feature_id = "S2A_MSIL2A_20210113T071211_N0500_R020_T38LPH_20230520T064324.SAFE"
    feature_info = catalog.get_feature("sentinel-2-l2a", feature_id)

    assert isinstance(feature_info, dict)
    assert feature_info["id"] == feature_id


def test_search_bbox(catalog: SHCatalog) -> None:
    time_interval = "2021-01-01T00:00:00", "2021-01-15T00:00:10"

    search_iterator = catalog.search(
        "sentinel-2-l1c",
        time=time_interval,
        bbox=TEST_BBOX.transform(CRS.POP_WEB),
        limit=2,
    )

    assert isinstance(search_iterator, CatalogSearchIterator)

    for result in search_iterator:
        assert isinstance(result, dict)
        assert time_interval[0] <= result["properties"]["datetime"] <= time_interval[1]


def test_search_filter(catalog: SHCatalog) -> None:
    time_interval = "2021-01-01T00:00:00", "2021-01-31T00:00:10"
    min_cc, max_cc = 10, 20
    common_kwargs = {
        "time": time_interval,
        "bbox": TEST_BBOX.transform(CRS.POP_WEB),
        "limit": 2,
    }

    unbounded_search_iterator = catalog.search("sentinel-2-l1c", **common_kwargs)
    assert len(list(unbounded_search_iterator)) == 6

    text_filter_iterator = catalog.search(
        "sentinel-2-l1c",
        filter=f"eo:cloud_cover>{min_cc} AND eo:cloud_cover<{max_cc}",
        **common_kwargs,
    )
    text_filtered = list(text_filter_iterator)

    assert len(text_filtered) == 2
    assert all(
        min_cc < result["properties"]["eo:cloud_cover"] < max_cc
        for result in text_filtered
    )

    json_filter_iterator = catalog.search(
        "sentinel-2-l1c",
        filter={
            "op": "and",
            "args": [
                {"op": ">", "args": [{"property": "eo:cloud_cover"}, min_cc]},
                {"op": "<", "args": [{"property": "eo:cloud_cover"}, max_cc]},
            ],
        },
        filter_lang="cql2-json",
        **common_kwargs,
    )

    assert text_filtered == list(json_filter_iterator)


def test_search_geometry_and_iterator_methods(catalog: SHCatalog) -> None:
    search_geometry = Geometry(TEST_BBOX.geometry, crs=TEST_BBOX.crs)

    search_iterator = catalog.search(
        "sentinel-2-l1c",
        time=("2021-01-01", "2021-01-5"),
        geometry=search_geometry,
        filter="eo:cloud_cover<40",
    )
    results = list(search_iterator)

    assert len(results) == 1
    assert search_iterator.get_timestamps() == [
        dt.datetime(2021, 1, 3, 7, 14, 7, 540000, tzinfo=dateutil.tz.tzutc())
    ]
    assert search_iterator.get_ids() == [
        "S2A_MSIL1C_20210103T071211_N0500_R020_T38LPH_20230228T175137.SAFE"
    ]

    geometries = search_iterator.get_geometries()
    assert len(geometries) == 1
    assert isinstance(geometries[0], Geometry)
    assert geometries[0].geometry.intersects(search_geometry.geometry)


@pytest.mark.parametrize(
    ("collection_id", "search_filter", "feature_id"),
    [
        (
            "sentinel-2-l1c",
            None,
            "S2A_MSIL1C_20210113T071211_N0500_R020_T38LPH_20230520T010221.SAFE",
        ),
        (
            "sentinel-2-l2a",
            None,
            "S2A_MSIL2A_20210113T071211_N0500_R020_T38LPH_20230520T064324.SAFE",
        ),
        (
            "sentinel-1-grd",
            SENTINEL1_IW_FILTER,
            "S1A_IW_GRDH_1SDV_20210113T022710_20210113T022735_036113_043BC9_E7C4_COG.SAFE",
        ),
        ("landsat-ot-l1", None, "LC08_L1TP_160071_20210113_20210308_02_T1"),
    ],
)
def test_search_for_collection(
    catalog: SHCatalog, collection_id: str, search_filter: str | None, feature_id: str
) -> None:
    search_iterator = catalog.search(
        collection_id,
        time=("2021-01-01T00:00:00", "2021-01-15T00:00:10"),
        bbox=TEST_BBOX,
        filter=search_filter,
        limit=1,
    )
    result = next(search_iterator)
    assert isinstance(result, dict)
    assert result["id"] == feature_id


def test_search_with_ids(catalog: SHCatalog) -> None:
    tile_id = "LC08_L1TP_160071_20210113_20210308_02_T1"

    search_iterator = catalog.search("landsat-ot-l1", ids=[tile_id])
    results = list(search_iterator)
    assert len(results) == 1
    assert results[0]["id"] == tile_id
