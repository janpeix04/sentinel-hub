from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sentinel_hub import CRS, BBox, DataCollection, SHConfig, SHRequest, SHStatistical
from sentinel_hub.cli import (
    CLIError,
    main,
    parse_bbox,
    parse_collection,
    parse_pair,
    parse_time,
)
from sentinel_hub.download.models import DownloadResponse

BBOX = "13.35,45.85,13.55,46.0"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("SENTINEL2_L2A", DataCollection.SENTINEL2_L2A),
        ("sentinel2_l2a", DataCollection.SENTINEL2_L2A),
        ("sentinel-2-l1c", DataCollection.SENTINEL2_L1C),
        ("SENTINEL5P", DataCollection.SENTINEL5P),
    ],
)
def test_parse_collection(value: str, expected: DataCollection) -> None:
    assert parse_collection(value) is expected


def test_parse_collection_unknown() -> None:
    with pytest.raises(CLIError, match="Unknown data collection"):
        parse_collection("landsat")


def test_parse_bbox() -> None:
    assert parse_bbox(BBOX, "4326") == BBox((13.35, 45.85, 13.55, 46.0), crs=CRS.WGS84)
    assert parse_bbox("1, 2, 3, 4", "32633").crs is CRS.UTM_33N


@pytest.mark.parametrize("value", ["1,2,3", "a,b,c,d"])
def test_parse_bbox_invalid(value: str) -> None:
    with pytest.raises(CLIError):
        parse_bbox(value, "4326")


def test_parse_time() -> None:
    assert parse_time(None) is None
    assert parse_time("2024-06-01") == "2024-06-01"
    assert parse_time("2024-06-01/2024-06-30") == ("2024-06-01", "2024-06-30")


def test_parse_pair() -> None:
    assert parse_pair("512,256", int) == (512, 256)
    assert parse_pair("10", float) == (10.0, 10.0)
    with pytest.raises(CLIError):
        parse_pair("1,2,3", int)


def test_collections(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["collections"]) == 0
    out = capsys.readouterr().out
    assert "SENTINEL2_L2A" in out
    assert "sentinel-2-l2a" in out


def test_bands(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bands", "sentinel-2-l2a"]) == 0
    out = capsys.readouterr().out
    assert "B04" in out
    assert "dataMask" in out


def test_evalscript(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["evalscript", "SENTINEL2_L2A", "--bands", "B04,B03,B02", "--merged-output", "default"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("//VERSION=3")
    assert "default: [sample.B04, sample.B03, sample.B02]" in out

    output = tmp_path / "script.js"
    assert main(["evalscript", "SENTINEL2_L2A", "--bands", "B08", "-o", str(output)]) == 0
    assert '"B08"' in output.read_text(encoding="utf-8")


def test_evalscript_unknown_band(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["evalscript", "SENTINEL2_L2A", "--bands", "B99"])
    assert exc_info.value.code == 2
    assert "B99" in capsys.readouterr().err


def test_config_set_and_show(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["config", "set", "sh_client_id", "my-client-id"]) == 0
    assert main(["config", "set", "max_download_attempts", "7"]) == 0
    assert main(["--profile", "other", "config", "set", "download_timeout_seconds", "30"]) == 0

    config = SHConfig()
    assert config.sh_client_id == "my-client-id"
    assert config.max_download_attempts == 7
    assert SHConfig(profile="other").download_timeout_seconds == 30.0

    capsys.readouterr()
    assert main(["config", "show", "--show-secrets"]) == 0
    assert json.loads(capsys.readouterr().out)["sh_client_id"] == "my-client-id"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["config", "set", "unknown_key", "1"], "Unknown config parameter"),
        (["config", "set", "max_download_attempts", "many"], "expects a int value"),
    ],
)
def test_config_set_invalid(args: list[str], message: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(args)
    assert message in capsys.readouterr().err


def test_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_get_data(self: SHRequest, **kwargs: Any) -> list[DownloadResponse]:
        captured["payload"] = self.payload
        captured["kwargs"] = kwargs
        return [DownloadResponse(request=self.download_list[0], content=b"tiff-bytes")]

    monkeypatch.setattr(SHRequest, "get_data", fake_get_data)
    output = tmp_path / "out" / "image.tif"
    args = ["process", "SENTINEL2_L2A", "--bbox", BBOX, "--time", "2024-06-01/2024-06-30"]
    args += ["--bands", "B04,B03,B02", "--size", "100,50", "--maxcc", "0.2", "-o", str(output)]
    assert main(args) == 0

    assert output.read_bytes() == b"tiff-bytes"
    assert captured["kwargs"]["decode_data"] is False
    payload = captured["payload"]
    assert payload["output"]["width"] == 100
    assert payload["output"]["height"] == 50
    assert payload["output"]["responses"][0]["format"]["type"] == "image/tiff"
    assert payload["input"]["data"][0]["dataFilter"]["maxCloudCoverage"] == 20
    assert payload["input"]["bounds"]["bbox"] == [13.35, 45.85, 13.55, 46.0]


@pytest.mark.parametrize(
    ("extra_args", "message"),
    [
        (["--size", "10,10", "-o", "x.tif"], "evalscript is required"),
        (["--bands", "B04", "-o", "x.tif"], "output size is required"),
        (["--bands", "B04", "--size", "10,10", "--resolution", "10", "-o", "x.tif"], "not both"),
        (["--bands", "B04", "--size", "10,10", "-o", "x.bmp"], "Cannot infer the format"),
    ],
)
def test_process_invalid(extra_args: list[str], message: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["process", "SENTINEL2_L2A", "--bbox", BBOX, *extra_args])
    assert message in capsys.readouterr().err


def test_process_requires_area(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["process", "SENTINEL2_L2A", "--bands", "B04", "--size", "10,10", "-o", "x.tif"])
    assert "area of interest is required" in capsys.readouterr().err


def test_stats(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    captured: dict[str, Any] = {}

    def fake_get_data(self: SHStatistical, **kwargs: Any) -> list[dict]:
        captured["payload"] = self.payload
        return [{"data": [], "status": "OK"}]

    monkeypatch.setattr(SHStatistical, "get_data", fake_get_data)
    args = ["stats", "SENTINEL2_L2A", "--bbox", BBOX, "--time", "2024-06-01/2024-06-30"]
    args += ["--bands", "B04", "--interval", "P10D", "--last-interval", "SHORTEN", "--resolution", "100"]
    assert main(args) == 0

    assert json.loads(capsys.readouterr().out) == {"data": [], "status": "OK"}
    aggregation = captured["payload"]["aggregation"]
    assert aggregation["aggregationInterval"] == {"of": "P10D", "lastIntervalBehavior": "SHORTEN"}
    assert "dataMask" in aggregation["evalscript"]
    assert aggregation["width"] > 0


@pytest.mark.sh_integration
def test_search_live(capsys: pytest.CaptureFixture[str]) -> None:
    args = ["search", "SENTINEL2_L2A", "--bbox", BBOX, "--time", "2024-06-01/2024-06-30"]
    args += ["--filter", "eo:cloud_cover < 20", "--max-results", "5", "--format", "json"]
    assert main(args) == 0
    features = json.loads(capsys.readouterr().out)["features"]
    assert 0 < len(features) <= 5
    assert all(feature["properties"]["eo:cloud_cover"] < 20 for feature in features)


@pytest.mark.sh_integration
def test_process_live(tmp_path: Path) -> None:
    output = tmp_path / "image.png"
    args = ["process", "SENTINEL2_L2A", "--bbox", BBOX, "--time", "2024-06-01/2024-06-30"]
    args += ["--bands", "B04,B03,B02", "--size", "64,64", "--maxcc", "0.2", "-o", str(output)]
    assert main(args) == 0
    assert output.read_bytes().startswith(b"\x89PNG")
