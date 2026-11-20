from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp")

from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError

from sentinel_hub import SHCatalog, SHRequest, SHStatistical
from sentinel_hub.download.models import DownloadResponse
from sentinel_hub.mcp_server import (
    compute_statistics,
    generate_evalscript,
    list_bands,
    list_collections,
    process_image,
    search_catalog,
    server,
    show_config,
)

BBOX = [13.35, 45.85, 13.55, 46.0]
TIME = "2024-06-01/2024-06-30"


def test_tools_registered() -> None:
    tools = {tool.name for tool in asyncio.run(server.list_tools())}
    assert tools == {
        "list_collections",
        "list_bands",
        "generate_evalscript",
        "show_config",
        "search_catalog",
        "process_image",
        "compute_statistics",
    }


def test_call_tool_error_is_reported() -> None:
    with pytest.raises(ToolError, match="Unknown data collection"):
        asyncio.run(server.call_tool("list_bands", {"collection": "landsat"}))


def test_list_collections() -> None:
    collections = list_collections()
    assert {"name": "SENTINEL2_L2A", "api_id": "sentinel-2-l2a"} in collections


def test_list_bands() -> None:
    bands = list_bands("sentinel-2-l2a")
    assert "B04" in [band["name"] for band in bands["bands"]]
    assert "dataMask" in [band["name"] for band in bands["meta_bands"]]


def test_generate_evalscript() -> None:
    evalscript = generate_evalscript(
        "SENTINEL2_L2A", bands=["B04", "B03", "B02"], merged_output="default"
    )
    assert evalscript.startswith("//VERSION=3")
    assert "default: [sample.B04, sample.B03, sample.B02]" in evalscript

    with pytest.raises(ToolError, match="B99"):
        generate_evalscript("SENTINEL2_L2A", bands=["B99"])


def test_show_config_masks_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SH_CLIENT_ID", "my-client-id")
    monkeypatch.setenv("SH_CLIENT_SECRET", "my-very-secret-value")
    config = show_config()
    assert config["credentials_set"] is True
    assert "my-very-secret-value" not in json.dumps(config)


def test_search_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    features = [
        {
            "id": f"S2_{index}",
            "properties": {"datetime": f"2024-06-0{index}", "eo:cloud_cover": 5},
        }
        for index in range(1, 6)
    ]

    def fake_search(self: SHCatalog, collection: str, **kwargs: Any) -> Any:
        captured.update(kwargs, collection=collection)
        return iter(features)

    monkeypatch.setattr(SHCatalog, "search", fake_search)
    result = search_catalog("SENTINEL2_L2A", bbox=BBOX, time=TIME, max_results=3)

    assert result["count"] == 3
    assert result["features"][0] == {
        "id": "S2_1",
        "datetime": "2024-06-01",
        "cloud_cover": 5,
    }
    assert captured["time"] == ("2024-06-01", "2024-06-30")
    assert captured["limit"] == 3


def test_process_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_get_data(self: SHRequest, **kwargs: Any) -> list[DownloadResponse]:
        captured["payload"] = self.payload
        return [DownloadResponse(request=self.download_list[0], content=b"png-bytes")]

    monkeypatch.setattr(SHRequest, "get_data", fake_get_data)
    output = tmp_path / "out" / "image.png"
    result = process_image(
        "SENTINEL2_L2A",
        str(output),
        bbox=BBOX,
        time=TIME,
        size=[100, 50],
        bands=["B04", "B03", "B02"],
        maxcc=0.2,
    )

    assert output.read_bytes() == b"png-bytes"
    assert str(output) in result[0]
    assert isinstance(result[1], Image)
    payload = captured["payload"]
    assert payload["output"]["width"] == 100
    assert payload["output"]["responses"][0]["format"]["type"] == "image/png"
    assert payload["input"]["data"][0]["dataFilter"]["maxCloudCoverage"] == 20


def test_process_image_geometry_feature(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def fake_get_data(self: SHRequest, **kwargs: Any) -> list[DownloadResponse]:
        captured["payload"] = self.payload
        return [DownloadResponse(request=self.download_list[0], content=b"tiff")]

    monkeypatch.setattr(SHRequest, "get_data", fake_get_data)
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [[13.35, 45.85], [13.55, 45.85], [13.55, 46.0], [13.35, 45.85]]
        ],
    }
    result = process_image(
        "SENTINEL2_L2A",
        str(tmp_path / "image.tif"),
        geometry={"type": "Feature", "properties": {}, "geometry": polygon},
        resolution=100,
        bands=["B04"],
    )

    assert len(result) == 1
    assert "geometry" in captured["payload"]["input"]["bounds"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"bbox": BBOX, "size": [10, 10]}, "evalscript is required"),
        ({"bbox": BBOX, "bands": ["B04"]}, "output size is required"),
        ({"bands": ["B04"], "size": [10, 10]}, "area of interest is required"),
        (
            {"bbox": BBOX, "bands": ["B04"], "size": [10, 10], "resolution": 10},
            "not both",
        ),
        ({"bbox": [1, 2, 3], "bands": ["B04"], "size": [10, 10]}, "bbox"),
    ],
)
def test_process_image_invalid(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(ToolError, match=message):
        process_image("SENTINEL2_L2A", "x.tif", **kwargs)


def test_process_image_unknown_format() -> None:
    with pytest.raises(ToolError, match="Cannot infer the format"):
        process_image("SENTINEL2_L2A", "x.bmp", bbox=BBOX, bands=["B04"], size=[10, 10])


def test_compute_statistics(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get_data(self: SHStatistical, **kwargs: Any) -> list[dict]:
        captured["payload"] = self.payload
        return [{"data": [], "status": "OK"}]

    monkeypatch.setattr(SHStatistical, "get_data", fake_get_data)
    result = compute_statistics(
        "SENTINEL2_L2A",
        TIME,
        bbox=BBOX,
        bands=["B04"],
        interval="P10D",
        last_interval="SHORTEN",
        resolution=100,
    )

    assert result == {"data": [], "status": "OK"}
    aggregation = captured["payload"]["aggregation"]
    assert aggregation["aggregationInterval"] == {
        "of": "P10D",
        "lastIntervalBehavior": "SHORTEN",
    }
    assert "dataMask" in aggregation["evalscript"]


def test_compute_statistics_rejects_data_mask() -> None:
    with pytest.raises(ToolError, match="dataMask"):
        compute_statistics(
            "SENTINEL2_L2A", TIME, bbox=BBOX, bands=["dataMask"], size=[10, 10]
        )
