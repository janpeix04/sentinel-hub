from __future__ import annotations

import pytest

from sentinel_hub import DataCollection, generate_evalscript


@pytest.mark.parametrize(
    "data_collection",
    [
        DataCollection.SENTINEL2_L1C,
        DataCollection.SENTINEL2_L2A,
        DataCollection.SENTINEL1_IW,
        DataCollection.SENTINEL3_OLCI,
        DataCollection.SENTINEL3_SLSTR,
        DataCollection.SENTINEL3_OLCI_L2,
        DataCollection.SENTINEL3_SLSTR_L2,
        DataCollection.SENTINEL3_SYNERGY_L2,
        DataCollection.SENTINEL5P,
    ],
)
def test_collection_bands(data_collection: DataCollection) -> None:
    evalscript = generate_evalscript(data_collection=data_collection)
    expected_bands_str = (
        "bands: [" + ", ".join(f'"{b.name}"' for b in data_collection.bands) + "]"
    )
    assert expected_bands_str in evalscript


@pytest.mark.parametrize(
    ("data_collection", "bands"),
    [
        (DataCollection.SENTINEL2_L2A, ["B04", "B03", "B02"]),
        (DataCollection.SENTINEL2_L1C, ["B08", "B10"]),
    ],
    ids=str,
)
def test_explicit_bands(data_collection: DataCollection, bands: list[str]) -> None:
    evalscript = generate_evalscript(data_collection=data_collection, bands=bands)
    expected_bands_str = "bands: [" + ", ".join(f'"{b}"' for b in bands) + "]"
    assert expected_bands_str in evalscript


@pytest.mark.parametrize(
    "meta_bands",
    [["CLM"], ["CLP", "dataMask"]],
    ids=str,
)
def test_explicit_meta_bands(meta_bands: list[str]) -> None:
    data_collection = DataCollection.SENTINEL2_L1C
    evalscript = generate_evalscript(
        data_collection=data_collection, meta_bands=meta_bands
    )

    all_bands = [f"{b.name}" for b in data_collection.bands] + meta_bands
    expected_bands_str = "bands: [" + ", ".join(f'"{b}"' for b in all_bands) + "]"
    assert expected_bands_str in evalscript


@pytest.mark.parametrize(
    ("data_collection", "bands"),
    [
        (DataCollection.SENTINEL2_L2A, ["B10"]),
        (DataCollection.SENTINEL2_L1C, ["SCL"]),
    ],
    ids=str,
)
def test_unavailable_band(data_collection: DataCollection, bands: list[str]) -> None:
    with pytest.raises(ValueError):
        generate_evalscript(data_collection=data_collection, bands=bands)


@pytest.mark.parametrize(
    ("data_collection", "bands", "meta_bands"),
    [
        (DataCollection.SENTINEL2_L1C, ["B08", "B04", "B03", "B02"], ["CLM"]),
        (DataCollection.SENTINEL2_L2A, ["B04", "B03", "B02"], ["CLP", "SCL"]),
    ],
    ids=str,
)
def test_merged_output(
    data_collection: DataCollection, bands: list[str], meta_bands: list[str]
) -> None:
    merged_output = "merged_bands"
    evalscript = generate_evalscript(
        data_collection=data_collection,
        bands=bands,
        meta_bands=meta_bands,
        merged_bands_output=merged_output,
    )

    expected_bands_output_spec = f'{{id: "{merged_output}", bands: {len(bands)}'
    assert expected_bands_output_spec in evalscript

    expected_bands_return_spec = (
        f"{merged_output}: [" + ", ".join(f"sample.{b}" for b in bands) + "]"
    )
    assert expected_bands_return_spec in evalscript

    for meta_band in meta_bands:
        assert f'{{id: "{meta_band}", bands: 1' in evalscript


def test_units() -> None:
    bands = ["B04", "B03", "B02", "B02"]
    data_collection = DataCollection.SENTINEL2_L1C

    evalscript_dn = generate_evalscript(data_collection=data_collection, bands=bands)
    assert evalscript_dn.count('"DN"') == len(bands)
    assert evalscript_dn.count('"REFLECTANCE"') == 0

    evalscript_reflectance = generate_evalscript(
        data_collection=data_collection, bands=bands, prioritize_dn=False
    )
    assert evalscript_reflectance.count('"REFLECTANCE"') == len(bands)
    assert evalscript_reflectance.count('"DN"') == 0


@pytest.mark.parametrize("use_dn", [True, False], ids=lambda x: f"use_dn: {x}")
def test_sample_type(use_dn: bool) -> None:
    data_collection = DataCollection.SENTINEL2_L1C
    evalscript = generate_evalscript(
        data_collection=data_collection, prioritize_dn=use_dn
    )

    expected_uint_count = len(data_collection.bands) if use_dn else 0
    assert evalscript.count('"UINT16"') == expected_uint_count

    expected_float_count = len(data_collection.bands) if not use_dn else 0
    assert evalscript.count('"FLOAT32"') == expected_float_count


def test_sentinel3_units() -> None:
    evalscript = generate_evalscript(
        data_collection=DataCollection.SENTINEL3_SLSTR,
        bands=["S2", "S3", "S8"],
        meta_bands=["dataMask"],
    )

    assert 'units: ["REFLECTANCE", "REFLECTANCE", "BRIGHTNESS_TEMPERATURE", "DN"]' in (
        evalscript
    )
    assert evalscript.count('"FLOAT32"') == 3
    assert evalscript.count('"UINT8"') == 1


def test_sentinel5p_units() -> None:
    evalscript = generate_evalscript(
        data_collection=DataCollection.SENTINEL5P,
        bands=["NO2", "CH4", "CLOUD_FRACTION"],
        meta_bands=["dataMask"],
    )

    assert 'units: ["MOL_M2", "PPB", "FRACTION", "DN"]' in evalscript
    assert evalscript.count('"FLOAT32"') == 3
    assert evalscript.count('"UINT8"') == 1


def test_sentinel3_l2_flag_sample_types() -> None:
    evalscript = generate_evalscript(
        data_collection=DataCollection.SENTINEL3_SLSTR_L2,
        bands=["LST"],
        meta_bands=["CLOUD", "BAYES"],
    )

    assert 'units: ["KELVIN", "DN", "DN"]' in evalscript
    assert '{id: "CLOUD", bands: 1, sampleType: "UINT16"}' in evalscript
    assert '{id: "BAYES", bands: 1, sampleType: "UINT8"}' in evalscript


@pytest.mark.parametrize(
    ("data_collection", "meta_band"),
    [
        (DataCollection.SENTINEL3_OLCI, "QUALITY_FLAGS"),
        (DataCollection.SENTINEL3_OLCI_L2, "LQSF"),
    ],
)
def test_band_without_sample_type(
    data_collection: DataCollection, meta_band: str
) -> None:
    with pytest.raises(ValueError, match=meta_band):
        generate_evalscript(
            data_collection=data_collection,
            bands=["B08"],
            meta_bands=[meta_band],
        )


@pytest.mark.parametrize("use_dn", [True, False], ids=lambda x: f"use_dn: {x}")
def test_sample_type_merged(use_dn: bool) -> None:
    evalscript = generate_evalscript(
        data_collection=DataCollection.SENTINEL2_L1C,
        merged_bands_output="bands",
        prioritize_dn=use_dn,
    )

    expected_uint_count = 1 if use_dn else 0
    assert evalscript.count('"UINT16"') == expected_uint_count

    expected_float_count = 1 if not use_dn else 0
    assert evalscript.count('"FLOAT32"') == expected_float_count
