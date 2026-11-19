from __future__ import annotations

import time
from typing import Any

import pytest
from requests_mock import Mocker

from sentinel_hub import (
    CRS,
    BBox,
    DataCollection,
    Geometry,
    LastIntervalBehavior,
    MimeType,
    MosaickingOrder,
    SHConfig,
    SHStatistical,
)
from sentinel_hub.api.base_request import InputDataDict

EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "dataMask"] }],
    output: [
      { id: "output_B04", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(samples) {
  return {
    output_B04: [samples.B04],
    dataMask: [samples.dataMask]
  };
}
"""

UTM_BBOX = BBox((414315, 4958219, 414859, 4958819), crs=CRS("32633"))

CALCULATIONS = {
    "default": {
        "histograms": {"default": {"nBins": 5, "lowEdge": 0.0, "highEdge": 0.3}},
        "statistics": {"default": {"percentiles": {"k": [33, 50, 75, 90]}}},
    }
}


@pytest.mark.sh_integration
def test_statistical_api() -> None:
    request = SHStatistical(
        aggregation=SHStatistical.aggregation(
            evalscript=EVALSCRIPT,
            time_interval=("2020-07-04T00:00:00", "2020-07-05T00:00:00"),
            aggregation_interval="P1D",
            resolution=(10, 10),
        ),
        input_data=[
            SHStatistical.input_data(
                DataCollection.SENTINEL2_L2A,
                mosaicking_order=MosaickingOrder.LEAST_RECENT,
            )
        ],
        bbox=UTM_BBOX,
        calculations=CALCULATIONS,
    )

    result = request.get_data()[0]

    assert result["status"] == "OK"
    assert len(result["data"]) == 1

    interval_data = result["data"][0]
    assert interval_data["interval"] == {
        "from": "2020-07-04T00:00:00Z",
        "to": "2020-07-05T00:00:00Z",
    }

    band_data = interval_data["outputs"]["output_B04"]["bands"]["B0"]
    stats = band_data["stats"]
    assert stats["sampleCount"] == 3240
    assert stats["noDataCount"] == 0
    assert stats["min"] == pytest.approx(0.0874, rel=1e-3)
    assert stats["max"] == pytest.approx(0.3164, rel=1e-3)
    assert stats["mean"] == pytest.approx(0.121098, rel=1e-3)
    assert stats["stDev"] == pytest.approx(0.033168, rel=1e-3)
    assert stats["percentiles"] == pytest.approx(
        {"33.0": 0.104, "50.0": 0.1104, "75.0": 0.1252, "90.0": 0.165}, rel=1e-3
    )

    histogram = band_data["histogram"]
    assert [histogram_bin["count"] for histogram_bin in histogram["bins"]] == [
        0,
        2261,
        742,
        188,
        45,
    ]
    assert histogram["bins"][0]["lowEdge"] == pytest.approx(0.0)
    assert histogram["bins"][-1]["highEdge"] == pytest.approx(0.3)
    assert histogram["overflowCount"] == 4
    assert histogram["underflowCount"] == 0
    total_count = (
        sum(histogram_bin["count"] for histogram_bin in histogram["bins"])
        + histogram["overflowCount"]
        + histogram["underflowCount"]
    )
    assert total_count == stats["sampleCount"] - stats["noDataCount"]


@pytest.mark.sh_integration
def test_statistical_api_multiple_intervals() -> None:
    request = SHStatistical(
        aggregation=SHStatistical.aggregation(
            evalscript=EVALSCRIPT,
            time_interval=("2020-06-01T00:00:00", "2020-07-31T00:00:00"),
            aggregation_interval="P10D",
            last_interval_behavior=LastIntervalBehavior.SHORTEN,
            size=(54, 60),
        ),
        input_data=[SHStatistical.input_data(DataCollection.SENTINEL2_L2A, maxcc=0.5)],
        bbox=UTM_BBOX,
    )

    result = request.get_data()[0]

    assert result["status"] == "OK"
    intervals = [interval_data["interval"] for interval_data in result["data"]]
    assert intervals, "Expected at least one interval with data"
    assert all(
        interval["from"] < interval["to"] <= "2020-07-31T00:00:00Z"
        for interval in intervals
    )
    for interval_data in result["data"]:
        if "error" in interval_data:
            continue
        stats = interval_data["outputs"]["output_B04"]["bands"]["B0"]["stats"]
        assert stats["sampleCount"] == 54 * 60


def test_aggregation() -> None:
    aggregation = SHStatistical.aggregation(
        evalscript=EVALSCRIPT,
        time_interval=("2020-06-01T00:00:00", "2020-07-31T00:00:00"),
        aggregation_interval="P10D",
        last_interval_behavior="extend",
        resolution=(10, 20),
        other_args={"aggregationInterval": {"of": "P5D"}, "foo": "bar"},
    )

    assert aggregation == {
        "timeRange": {"from": "2020-06-01T00:00:00Z", "to": "2020-07-31T00:00:00Z"},
        "aggregationInterval": {"of": "P5D", "lastIntervalBehavior": "EXTEND"},
        "evalscript": EVALSCRIPT,
        "resx": 10,
        "resy": 20,
        "foo": "bar",
    }


def test_aggregation_size_and_dates() -> None:
    aggregation = SHStatistical.aggregation(
        evalscript=EVALSCRIPT,
        time_interval=("2020-06-01", "2020-06-30"),
        aggregation_interval="P1D",
        size=(100, 200),
    )

    assert aggregation["timeRange"] == {
        "from": "2020-06-01T00:00:00Z",
        "to": "2020-06-30T23:59:59Z",
    }
    assert aggregation["aggregationInterval"] == {"of": "P1D"}
    assert aggregation["width"] == 100
    assert aggregation["height"] == 200
    assert "resx" not in aggregation


@pytest.mark.parametrize(
    "aggregation_kwargs",
    [
        {"size": (10, 10), "resolution": (10, 10)},
        {"last_interval_behavior": "never"},
        {"evalscript": None},
    ],
)
def test_aggregation_invalid(aggregation_kwargs: dict[str, Any]) -> None:
    kwargs = {
        "evalscript": EVALSCRIPT,
        "time_interval": ("2020-06-01", "2020-06-30"),
        "aggregation_interval": "P1D",
        **aggregation_kwargs,
    }
    with pytest.raises((ValueError, TypeError)):
        SHStatistical.aggregation(**kwargs)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("SKIP", LastIntervalBehavior.SKIP),
        ("shorten", LastIntervalBehavior.SHORTEN),
        (LastIntervalBehavior.EXTEND, LastIntervalBehavior.EXTEND),
    ],
)
def test_last_interval_behavior(value: Any, expected: LastIntervalBehavior) -> None:
    assert LastIntervalBehavior(value) is expected


def test_body() -> None:
    bounds = SHStatistical.bounds(bbox=UTM_BBOX)
    data = [SHStatistical.input_data(DataCollection.SENTINEL2_L2A)]
    aggregation = {"of": "P1D"}

    assert SHStatistical.body(bounds, data, aggregation) == {
        "input": {"bounds": bounds, "data": data},
        "aggregation": aggregation,
    }
    assert SHStatistical.body(
        bounds,
        data,
        aggregation,
        calculations=CALCULATIONS,
        other_args={"input": {"bounds": {"properties": {"crs": "x"}}}},
    ) == {
        "input": {
            "bounds": {**bounds, "properties": {"crs": "x"}},
            "data": data,
        },
        "aggregation": aggregation,
        "calculations": CALCULATIONS,
    }


def test_request_payload(config: SHConfig) -> None:
    geometry = Geometry(UTM_BBOX.geometry, crs=UTM_BBOX.crs)
    aggregation = SHStatistical.aggregation(
        evalscript=EVALSCRIPT,
        time_interval=("2020-07-04", "2020-07-05"),
        aggregation_interval="P1D",
        resolution=(10, 10),
    )
    input_data = [SHStatistical.input_data(DataCollection.SENTINEL2_L2A)]

    request = SHStatistical(
        aggregation=aggregation,
        input_data=input_data,
        geometry=geometry,
        calculations=CALCULATIONS,
        config=config,
    )

    assert request.mime_type is MimeType.JSON
    assert request.payload == {
        "input": {
            "bounds": {
                "properties": {"crs": UTM_BBOX.crs.opengis_string},
                "geometry": geometry.get_geojson(with_crs=False),
            },
            "data": input_data,
        },
        "aggregation": aggregation,
        "calculations": CALCULATIONS,
    }
    assert isinstance(request.payload["input"]["data"][0], InputDataDict)

    download_request = request.download_list[0]
    assert download_request.url == f"{config.sh_base_url}/statistics/v1"
    assert download_request.data_type is MimeType.JSON
    assert download_request.headers["accept"] == "application/json"
    assert download_request.post_values == request.payload


def test_request_requires_bounds() -> None:
    with pytest.raises(ValueError):
        SHStatistical(
            aggregation={},
            input_data=[SHStatistical.input_data(DataCollection.SENTINEL2_L2A)],
        )


def test_get_data_mocked(requests_mock: Mocker) -> None:
    config = SHConfig(
        use_defaults=True, sh_client_id="sh-py-test", sh_client_secret="sh-py-test"
    )
    fake_token = {
        "access_token": "x",
        "expires_in": 1000,
        "expires_at": time.time() + 1000,
    }
    fake_response = {
        "data": [
            {
                "interval": {
                    "from": "2020-07-04T00:00:00Z",
                    "to": "2020-07-05T00:00:00Z",
                },
                "outputs": {
                    "output_B04": {
                        "bands": {
                            "B0": {
                                "stats": {
                                    "min": 0.0797,
                                    "max": 0.3096,
                                    "mean": 0.1147,
                                    "stDev": 0.0343,
                                    "sampleCount": 3240,
                                    "noDataCount": 0,
                                }
                            }
                        }
                    }
                },
            }
        ],
        "status": "OK",
    }
    requests_mock.post(url=config.sh_token_url, json=fake_token)
    requests_mock.post(url=f"{config.sh_base_url}/statistics/v1", json=fake_response)

    request = SHStatistical(
        aggregation=SHStatistical.aggregation(
            evalscript=EVALSCRIPT,
            time_interval=("2020-07-04T00:00:00", "2020-07-05T00:00:00"),
            aggregation_interval="P1D",
            resolution=(10, 10),
        ),
        input_data=[SHStatistical.input_data(DataCollection.SENTINEL2_L2A)],
        bbox=UTM_BBOX,
        config=config,
    )

    assert request.get_data() == [fake_response]

    stats_request = requests_mock.request_history[-1]
    assert stats_request.url == f"{config.sh_base_url}/statistics/v1"
    assert stats_request.json() == request.payload
    assert stats_request.headers["Authorization"] == "Bearer x"
