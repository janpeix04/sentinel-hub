from __future__ import annotations

import json
from typing import Any

import pytest
from oauthlib.oauth2.rfc6749.errors import InvalidClientError
from shapely.geometry import Polygon

from sentinel_hub import (
    CRS,
    BBox,
    DataCollection,
    Geometry,
    MimeType,
    MosaickingOrder,
    ResamplingType,
    SHConfig,
    SHRequest,
    bbox_to_dimensions,
)
from sentinel_hub.api.base_request import InputDataDict
from tests.testing_utils import assert_statistics_match


@pytest.mark.sh_integration
def test_single_jpg() -> None:
    evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"],
                    units: "REFLECTANCE"
                }],
                output: {
                    bands: 3
                }
            };
        }

        function evaluatePixel(sample) {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
        }
    """

    request = SHRequest(
        evalscript=evalscript,
        input_data=[
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2021-01-03", "2021-01-04"),
                maxcc=0.8,
            )
        ],
        responses=[SHRequest.output_response("default", MimeType.JPG)],
        bbox=BBox(bbox=[46.16, -16.15, 46.51, -15.58], crs=CRS.WGS84),
        size=(512, 856),
    )

    img = request.get_data(max_threads=3)[0]

    assert_statistics_match(
        img,
        exp_shape=(856, 512, 3),
        exp_min=9,
        exp_max=255,
        exp_mean=72.62152803129868,
        exp_median=69,
        exp_std=23.244730116467558,
        rel_delta=1e-4,
    )


@pytest.mark.sh_integration
def test_other_args(config: SHConfig, output_folder: str) -> None:
    evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: ["B02", "B03", "B04"],
                sampleType: "UINT16",
                output: { bands: 3 }
            };
        }

        function evaluatePixel(sample) {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
        }
    """

    request = SHRequest(
        evalscript=evalscript,
        input_data=[
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2021-01-03", "2021-01-04"),
                maxcc=0.8,
                upsampling=ResamplingType.NEAREST,
                downsampling=ResamplingType.NEAREST,
                other_args={"processing": {"atmosphericCorrection": "NONE"}},
            )
        ],
        responses=[SHRequest.output_response("default", "tiff")],
        bbox=BBox(bbox=[46.16, -16.15, 46.51, -15.58], crs=CRS.WGS84),
        size=(512, 856),
        config=config,
        data_folder=output_folder,
    )

    img = request.get_data(max_threads=3)[0]

    assert_statistics_match(
        img,
        exp_shape=(856, 512, 3),
        exp_min=0,
        exp_max=255,
        exp_mean=72.6393617053641,
        exp_median=69,
        exp_std=23.50576630057375,
        rel_delta=1e-4,
    )


@pytest.mark.sh_integration
def test_preview_mode() -> None:
    evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"],
                    units: "DN"
                }],
                output: {
                    bands: 3,
                    sampleType: "UINT16"
                }
            };
        }

        function evaluatePixel(sample) {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
        }
    """

    request = SHRequest(
        evalscript=evalscript,
        input_data=[
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2017-10-14T00:12:03", "2017-12-15T23:12:04"),
                mosaicking_order=MosaickingOrder.LEAST_CC,
                other_args={"dataFilter": {"previewMode": "PREVIEW"}},
            )
        ],
        responses=[SHRequest.output_response("default", MimeType.TIFF)],
        bbox=BBox(
            bbox=[
                1155360.393335921,
                5285081.168940068,
                1156965.063795706,
                5286609.808304847,
            ],
            crs=CRS.POP_WEB,
        ),
        resolution=(260.0, 260.0),
    )

    img = request.get_data(max_threads=3)[0]

    assert_statistics_match(
        img,
        exp_shape=(6, 6, 3),
        exp_min=295,
        exp_max=3130,
        exp_mean=1815.0,
        exp_median=1925.0,
        exp_std=602.4617707250686,
        rel_delta=1e-4,
    )


@pytest.mark.sh_integration
def test_resolution_parameter() -> None:
    evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"],
                    units: "DN"
                }],
                output: {
                    bands: 3,
                    sampleType: "UINT16"
                }
            };
        }

        function evaluatePixel(sample) {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
        }
    """

    request = SHRequest(
        evalscript=evalscript,
        input_data=[
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2017-10-14T00:12:03", "2017-12-15T23:12:04"),
                mosaicking_order=MosaickingOrder.LEAST_CC,
            )
        ],
        responses=[SHRequest.output_response("default", MimeType.TIFF)],
        bbox=BBox(
            bbox=[
                1155360.393335921,
                5285081.168940068,
                1156965.063795706,
                5286609.808304847,
            ],
            crs=CRS.POP_WEB,
        ),
        resolution=(10.0, 10.0),
    )

    img = request.get_data(max_threads=3)[0]

    assert_statistics_match(
        img,
        exp_shape=(153, 160, 3),
        exp_min=685,
        exp_max=7208,
        exp_mean=1871.6107706971677,
        exp_median=1918.0,
        exp_std=616.2380086827825,
        rel_delta=1e-4,
    )


@pytest.mark.sh_integration
def test_multipart_tar() -> None:
    evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"],
                    units: "DN"
                }],
                output: {
                    bands: 3,
                    sampleType: "UINT16"
                }
            };
        }

        function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
            outputMetadata.userData = { "norm_factor":  inputMetadata.normalizationFactor }
        }

        function evaluatePixel(sample) {
            return [sample.B02, sample.B03, sample.B04];
        }
    """

    request = SHRequest(
        evalscript=evalscript,
        input_data=[
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2021-01-03", "2021-01-04"),
                maxcc=0.8,
            )
        ],
        responses=[
            SHRequest.output_response("default", MimeType.TIFF),
            SHRequest.output_response("userdata", MimeType.JSON),
        ],
        bbox=BBox(bbox=[46.16, -16.15, 46.51, -15.58], crs=CRS.WGS84),
        size=(512, 856),
    )

    tar = request.get_data(max_threads=3)[0]

    assert "default.tif" in tar
    assert "userdata.json" in tar

    img_data = tar["default.tif"]

    assert_statistics_match(
        img_data,
        exp_shape=(856, 512, 3),
        exp_min=0,
        exp_max=5788,
        exp_mean=1139.450685875438,
        exp_median=1084,
        exp_std=368.91787574790516,
        rel_delta=1e-4,
    )

    json_data = tar["userdata.json"]

    assert "norm_factor" in json_data
    assert json_data["norm_factor"] == 1


@pytest.mark.sh_integration
def test_multipart_geometry() -> None:
    evalscript = """
        //VERSION=3

        function setup() {
        return {
            input: ["B02", "B03", "B04", "dataMask"],
            output: { id:"default", bands: 3}
        }
        }

        function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
        var sum = (r_count + g_count + b_count);
        var r_rat = r_count / sum;
        var g_rat = g_count / sum;
        var b_rat = b_count / sum;
        outputMetadata.userData = { "rgb_ratios":  [r_rat, g_rat, b_rat] }
        }

        var r_count = 0;
        var g_count = 0;
        var b_count = 0;

        function evaluatePixel(sample) {

            b_count += sample.B02;
            g_count += sample.B03;
            r_count += sample.B04;

            if (sample.dataMask == 0) {
                return [1,1,1];
            }

            return [sample.B04*2.5, sample.B03*2.5, sample.B02*2.5];
        }
    """

    points = [
        (3983945.16471594, 4455475.78793186),
        (3983888.00256275, 4455757.47439827),
        (3983881.86585896, 4455756.21837259),
        (3983806.23113651, 4456128.92147268),
        (3983795.43856837, 4456181.52922753),
        (3983782.49665288, 4456243.16761979),
        (3983769.24786918, 4456304.74059236),
        (3983755.69254332, 4456366.24660331),
        (3983741.83100914, 4456427.68411298),
        (3983731.89973217, 4456470.84795843),
        (3983633.33670483, 4456895.81023678),
        (3983639.43692276, 4456897.23726002),
        (3983537.58701916, 4457336.35298979),
        (3983531.486563, 4457334.92584801),
        (3983451.81567033, 4457678.40439185),
        (3983444.09684707, 4457713.91738361),
        (3983433.21703553, 4457774.95105094),
        (3983425.2423303, 4457836.4359853),
        (3983420.19086095, 4457898.23280495),
        (3983418.07413054, 4457960.2014162),
        (3983418.89698951, 4458022.20133071),
        (3983422.65762374, 4458084.09198476),
        (3983429.05535825, 4458143.30899922),
        (3983435.27377231, 4458142.55298424),
        (3983439.97457434, 4458175.43769638),
        (3983450.97468474, 4458236.14788553),
        (3983466.88315168, 4458303.87476693),
        (3983460.83517165, 4458305.51224157),
        (3983466.80900589, 4458327.76588705),
        (3983484.9991527, 4458387.02138291),
        (3983505.97749719, 4458445.340412),
        (3983538.67409472, 4458522.43435024),
        (3983584.70089337, 4458635.18822735),
        (3983780.40768297, 4459048.67824218),
        (3983801.72985096, 4459096.84527808),
        (3983883.42859759, 4459278.64097453),
        (3984316.01202946, 4460214.51826613),
        (3984398.97672295, 4460080.53793049),
        (3984534.50220822, 4459799.86484374),
        (3984577.77550522, 4459774.02321167),
        (3984491.40157364, 4459687.94895666),
        (3984776.22996932, 4459142.13379129),
        (3984819.68594039, 4459029.12887873),
        (3984907.71921624, 4458981.665405),
        (3984888.9490588, 4458770.02890185),
        (3985209.2168573, 4458503.41559024),
        (3985821.45298221, 4458006.99923219),
        (3985788.76207523, 4457880.30735337),
        (3985793.50611539, 4457877.12247581),
        (3985784.68739608, 4457859.48509427),
        (3985732.13693102, 4457697.05635426),
        (3985820.89433686, 4457656.86419316),
        (3985677.94930497, 4457315.34906349),
        (3985611.18897298, 4457337.80151946),
        (3985327.61285454, 4457451.86990929),
        (3985146.68294768, 4456972.64460213),
        (3985446.37981687, 4456852.84034971),
        (3985488.11295695, 4456837.9565739),
        (3985384.27368677, 4456550.32595766),
        (3985005.77351172, 4455718.96868536),
        (3984372.83691021, 4455665.6888113),
        (3984231.62160324, 4455623.03272949),
        (3984096.30921154, 4455487.68759209),
        (3983945.16471594, 4455475.78793186),
    ]

    sgeo = Polygon(points)
    crs = CRS("epsg:3857")
    geo = Geometry(sgeo, crs=crs)
    bbox = BBox(sgeo.bounds, crs=crs)
    size = bbox_to_dimensions(bbox, 10)

    request = SHRequest(
        evalscript=evalscript,
        input_data=[
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2017-11-15T07:12:03", "2017-12-15T07:12:04"),
            )
        ],
        responses=[
            SHRequest.output_response("default", MimeType.TIFF),
            SHRequest.output_response("userdata", MimeType.JSON),
        ],
        geometry=geo,
        size=size,
    )

    tar = request.get_data(max_threads=3)[0]

    img = tar["default.tif"]

    assert_statistics_match(
        img,
        exp_shape=(382, 181, 3),
        exp_min=25,
        exp_max=255,
        exp_mean=145.32359009960177,
        exp_median=80.0,
        exp_std=95.22898132994702,
        rel_delta=1e-4,
    )

    json_data = tar["userdata.json"]

    assert "rgb_ratios" in json_data

    expected_ratios = [0.29119553279326116, 0.322848668255891, 0.3859557989508479]
    assert json_data["rgb_ratios"] == pytest.approx(expected_ratios)


@pytest.mark.sh_integration
def test_bad_credentials() -> None:
    evalscript = """
                //VERSION=3

                function setup() {
                    return {
                        input: ["B02", "B03", "B04"],
                        sampleType: "UINT16",
                        output: { bands: 3 }
                    };
                }

                function evaluatePixel(sample) {
                    return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
                }
            """
    request_params: dict[str, Any] = {
        "evalscript": evalscript,
        "input_data": [
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2017-12-15T07:12:03", "2017-12-15T07:12:04"),
            )
        ],
        "responses": [SHRequest.output_response("default", "tiff")],
        "bbox": BBox(bbox=[46.16, -16.15, 46.51, -15.58], crs=CRS.WGS84),
        "size": (512, 856),
    }

    bad_credentials_config = SHConfig()
    bad_credentials_config.sh_client_id = "test"
    bad_credentials_config.sh_client_secret = "test"

    request = SHRequest(**request_params, config=bad_credentials_config)
    with pytest.raises(InvalidClientError):
        request.get_data()

    missing_credentials_config = SHConfig()
    missing_credentials_config.sh_client_id = ""
    missing_credentials_config.sh_client_secret = ""

    request = SHRequest(**request_params, config=missing_credentials_config)
    with pytest.raises(ValueError):
        request.get_data()


@pytest.mark.sh_integration
def test_bbox_geometry() -> None:
    evalscript = """
        //VERSION=3

        function setup() {
            return {
                input: [{
                    bands: ["B02", "B03", "B04"],
                    units: "REFLECTANCE"
                }],
                output: {
                    bands: 3
                }
            };
        }

        function evaluatePixel(sample) {
            return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
        }
    """

    delta = 0.2
    bbox = BBox(bbox=[46.16, -16.15, 46.51, -15.58], crs=CRS.WGS84)
    geometry = Geometry(bbox.geometry, crs=bbox.crs)
    bbox_translated = BBox(
        bbox=[46.16 + delta, -16.15 + delta, 46.51 + delta, -15.58 + delta],
        crs=CRS.WGS84,
    )

    request = SHRequest(
        evalscript=evalscript,
        input_data=[
            SHRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2021-01-03", "2021-01-04"),
                maxcc=0.8,
            )
        ],
        responses=[SHRequest.output_response("default", MimeType.JPG)],
        geometry=geometry,
        bbox=bbox_translated,
        size=(512, 856),
    )

    img = request.get_data(max_threads=3)[0]

    assert_statistics_match(
        img,
        exp_shape=(856, 512, 3),
        exp_min=0,
        exp_max=255,
        exp_mean=21.39401558849299,
        exp_median=0,
        exp_std=36.681242059898324,
        rel_delta=1e-4,
    )


def test_basic_functionalities() -> None:
    normal_dict = {"a": 10, "b": {"c": 20, 30: "d"}}
    service_url = "xyz"
    input_data_dict = InputDataDict(normal_dict, service_url=service_url)

    assert {**input_data_dict} == {**normal_dict}
    assert input_data_dict.service_url == service_url

    input_data_dict_repr = repr(input_data_dict)
    assert input_data_dict_repr.startswith(InputDataDict.__name__)
    assert service_url in input_data_dict_repr

    assert json.dumps(input_data_dict) == json.dumps(normal_dict)


def test_input_data() -> None:
    input_data = SHRequest.input_data(
        data_collection=DataCollection.SENTINEL2_L2A,
        identifier="l2a",
        time_interval=("2021-01-03", "2021-01-04"),
        maxcc=0.8,
        mosaicking_order=MosaickingOrder.LEAST_CC,
        upsampling="bilinear",
        downsampling=ResamplingType.NEAREST,
        other_args={"dataFilter": {"previewMode": "PREVIEW"}},
    )

    assert isinstance(input_data, InputDataDict)
    assert input_data.service_url == DataCollection.SENTINEL2_L2A.service_url
    assert {**input_data} == {
        "type": "sentinel-2-l2a",
        "id": "l2a",
        "dataFilter": {
            "timeRange": {"from": "2021-01-03T00:00:00Z", "to": "2021-01-04T23:59:59Z"},
            "maxCloudCoverage": 80,
            "mosaickingOrder": "leastCC",
            "previewMode": "PREVIEW",
        },
        "processing": {"upsampling": "BILINEAR", "downsampling": "NEAREST"},
    }


def test_input_data_without_filters() -> None:
    input_data = SHRequest.input_data(data_collection=DataCollection.SENTINEL2_L1C)
    assert {**input_data} == {"type": "sentinel-2-l1c"}


@pytest.mark.parametrize(
    ("data_collection", "expected_data_filter"),
    [
        (DataCollection.SENTINEL1, None),
        (
            DataCollection.SENTINEL1_IW,
            {"acquisitionMode": "IW", "polarization": "DV", "resolution": "HIGH"},
        ),
        (
            DataCollection.SENTINEL1_IW_ASC,
            {
                "acquisitionMode": "IW",
                "polarization": "DV",
                "resolution": "HIGH",
                "orbitDirection": "ASCENDING",
            },
        ),
        (
            DataCollection.SENTINEL1_EW_SH_DES,
            {
                "acquisitionMode": "EW",
                "polarization": "SH",
                "resolution": "MEDIUM",
                "orbitDirection": "DESCENDING",
            },
        ),
    ],
)
def test_input_data_sentinel1(
    data_collection: DataCollection, expected_data_filter: dict[str, Any] | None
) -> None:
    input_data = SHRequest.input_data(data_collection=data_collection)

    assert input_data["type"] == "sentinel-1-grd"
    assert input_data.service_url == data_collection.service_url
    assert input_data.get("dataFilter") == expected_data_filter


def test_input_data_sentinel1_with_other_filters() -> None:
    input_data = SHRequest.input_data(
        data_collection=DataCollection.SENTINEL1_IW_DES,
        time_interval=("2024-06-01", "2024-06-30"),
        mosaicking_order=MosaickingOrder.MOST_RECENT,
        other_args={
            "dataFilter": {"timeliness": "NRT3h"},
            "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": True},
        },
    )

    assert {**input_data} == {
        "type": "sentinel-1-grd",
        "dataFilter": {
            "timeRange": {"from": "2024-06-01T00:00:00Z", "to": "2024-06-30T23:59:59Z"},
            "mosaickingOrder": "mostRecent",
            "acquisitionMode": "IW",
            "polarization": "DV",
            "resolution": "HIGH",
            "orbitDirection": "DESCENDING",
            "timeliness": "NRT3h",
        },
        "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": True},
    }


@pytest.mark.parametrize(
    ("data_collection", "api_id"),
    [
        (DataCollection.SENTINEL3_OLCI, "sentinel-3-olci"),
        (DataCollection.SENTINEL3_SLSTR, "sentinel-3-slstr"),
        (DataCollection.SENTINEL3_OLCI_L2, "sentinel-3-olci-l2"),
        (DataCollection.SENTINEL3_SLSTR_L2, "sentinel-3-slstr-l2"),
        (DataCollection.SENTINEL3_SYNERGY_L2, "sentinel-3-synergy-l2"),
    ],
)
def test_input_data_sentinel3(data_collection: DataCollection, api_id: str) -> None:
    input_data = SHRequest.input_data(data_collection=data_collection)

    assert {**input_data} == {"type": api_id}
    assert input_data.service_url == data_collection.service_url


def test_input_data_sentinel3_slstr_filters() -> None:
    input_data = SHRequest.input_data(
        data_collection=DataCollection.SENTINEL3_SLSTR,
        maxcc=0.2,
        mosaicking_order=MosaickingOrder.LEAST_CC,
        other_args={"dataFilter": {"orbitDirection": "DESCENDING", "view": "OBLIQUE"}},
    )

    assert {**input_data} == {
        "type": "sentinel-3-slstr",
        "dataFilter": {
            "maxCloudCoverage": 20,
            "mosaickingOrder": "leastCC",
            "orbitDirection": "DESCENDING",
            "view": "OBLIQUE",
        },
    }


def test_input_data_sentinel5p() -> None:
    input_data = SHRequest.input_data(
        data_collection=DataCollection.SENTINEL5P,
        time_interval=("2024-06-01", "2024-06-01"),
        other_args={
            "dataFilter": {"timeliness": "OFFL"},
            "processing": {"minQa": 75},
        },
    )

    assert input_data.service_url == DataCollection.SENTINEL5P.service_url
    assert {**input_data} == {
        "type": "sentinel-5p-l2",
        "dataFilter": {
            "timeRange": {"from": "2024-06-01T00:00:00Z", "to": "2024-06-01T23:59:59Z"},
            "timeliness": "OFFL",
        },
        "processing": {"minQa": 75},
    }


@pytest.mark.parametrize("maxcc", [-0.1, 1.1])
def test_input_data_invalid_maxcc(maxcc: float) -> None:
    with pytest.raises(ValueError):
        SHRequest.input_data(data_collection=DataCollection.SENTINEL2_L1C, maxcc=maxcc)


def test_bounds() -> None:
    bbox = BBox((46.16, -16.15, 46.51, -15.58), crs=CRS.WGS84)
    geometry = Geometry(bbox.geometry, crs=bbox.crs)

    bounds = SHRequest.bounds(bbox=bbox, geometry=geometry)

    assert bounds["properties"]["crs"] == CRS.WGS84.opengis_string
    assert bounds["bbox"] == list(bbox)
    assert bounds["geometry"] == geometry.get_geojson(with_crs=False)


@pytest.mark.parametrize(
    "bounds_kwargs",
    [
        {},
        {"bbox": (46.16, -16.15, 46.51, -15.58)},
        {
            "bbox": BBox((46.16, -16.15, 46.51, -15.58), crs=CRS.WGS84),
            "geometry": Geometry(
                BBox((0, 0, 1, 1), crs=CRS.POP_WEB).geometry, crs=CRS.POP_WEB
            ),
        },
    ],
)
def test_bounds_invalid(bounds_kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        SHRequest.bounds(**bounds_kwargs)


def test_output_size_and_resolution() -> None:
    responses = [SHRequest.output_response("default", MimeType.TIFF)]

    assert SHRequest.output(responses, size=(10, 20)) == {
        "responses": responses,
        "width": 10,
        "height": 20,
    }
    assert SHRequest.output(responses, resolution=(10.0, 20.0)) == {
        "responses": responses,
        "resx": 10.0,
        "resy": 20.0,
    }
    with pytest.raises(ValueError):
        SHRequest.output(responses, size=(10, 20), resolution=(10.0, 20.0))


@pytest.mark.parametrize(
    ("responses", "expected_mime_type"),
    [
        ([SHRequest.output_response("default", MimeType.PNG)], MimeType.PNG),
        (
            [
                SHRequest.output_response("default", MimeType.TIFF),
                SHRequest.output_response("userdata", MimeType.JSON),
            ],
            MimeType.TAR,
        ),
    ],
)
def test_request_payload(
    responses: list[dict[str, Any]], expected_mime_type: MimeType, config: SHConfig
) -> None:
    bbox = BBox((46.16, -16.15, 46.51, -15.58), crs=CRS.WGS84)
    request = SHRequest(
        evalscript="//VERSION=3",
        input_data=[SHRequest.input_data(DataCollection.SENTINEL2_L1C)],
        responses=responses,
        bbox=bbox,
        size=(512, 856),
        config=config,
    )

    assert request.mime_type is expected_mime_type
    assert request.payload["input"]["bounds"]["bbox"] == list(bbox)
    assert request.payload["output"]["responses"] == responses

    download_request = request.download_list[0]
    assert download_request.url == f"{config.sh_base_url}/api/v1/process"
    assert download_request.headers["accept"] == expected_mime_type.get_string()


def test_evalscript_must_be_string() -> None:
    with pytest.raises(TypeError):
        SHRequest(
            evalscript=None,  # type: ignore[arg-type]
            input_data=[],
            responses=[SHRequest.output_response("default", MimeType.TIFF)],
            bbox=BBox((0, 0, 1, 1), crs=CRS.WGS84),
        )
