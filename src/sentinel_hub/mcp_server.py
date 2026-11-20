"""
MCP server exposing the `sentinel-hub` package to MCP clients such as Claude Code.

Run `sentinel-hub-mcp` (or `python -m sentinel_hub.mcp_server`) to start it over stdio.
Requires the `mcp` extra: `pip install "sentinel-hub[mcp]"`.
"""

import itertools
import json
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from sentinel_hub._version import __version__
from sentinel_hub.api import SHCatalog, SHRequest, SHStatistical
from sentinel_hub.cli import CLIError, parse_collection, parse_time
from sentinel_hub.config import SHConfig
from sentinel_hub.constants import (
    CRS,
    LastIntervalBehavior,
    MimeType,
    MosaickingOrder,
    ResamplingType,
)
from sentinel_hub.data_collections import DataCollection
from sentinel_hub.evalscript import generate_evalscript as _generate_evalscript
from sentinel_hub.geo_utils import bbox_to_dimensions
from sentinel_hub.geometry import BBox, Geometry
from sentinel_hub.types import JsonDict

ProcessFormat = Literal["tiff", "png", "jpg", "json", "tar"]
MosaickingOrderName = Literal["mostRecent", "leastRecent", "leastCC"]
ResamplingName = Literal["NEAREST", "BILINEAR", "BICUBIC"]

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
REMOTE_READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)

INSTRUCTIONS = """\
Access to Sentinel Hub on the Copernicus Data Space Ecosystem (CDSE) via the local
`sentinel-hub` Python package. Typical flow: `list_collections` / `list_bands` to pick
inputs, `search_catalog` to find acquisition dates, then `process_image` to download
imagery or `compute_statistics` for time series without downloading images.
Areas are given as `bbox` [min_x, min_y, max_x, max_y] and/or a GeoJSON `geometry`,
in `crs` (EPSG code, default 4326 = WGS84 lon/lat). Times are `START/END` or a date.
Remote tools need CDSE credentials (SH_CLIENT_ID / SH_CLIENT_SECRET or config.toml);
use `show_config` to check them.
"""

server = MCPServer(
    name="sentinel-hub",
    version=__version__,
    instructions=INSTRUCTIONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collection(value: str) -> DataCollection:
    try:
        return parse_collection(value)
    except CLIError as exception:
        raise ToolError(str(exception)) from exception


def _area(
    bbox: list[float] | None, geometry: JsonDict | None, crs: str
) -> tuple[BBox | None, Geometry | None]:
    """Builds the area of interest from a bbox list and/or a GeoJSON geometry, Feature or FeatureCollection."""
    try:
        area_crs = CRS(crs)
    except ValueError as exception:
        raise ToolError(f"Unsupported CRS `{crs}`") from exception

    area_bbox = None
    if bbox is not None:
        if len(bbox) != 4:
            raise ToolError("`bbox` must be [min_x, min_y, max_x, max_y]")
        area_bbox = BBox(tuple(bbox), crs=area_crs)

    area_geometry = None
    if geometry is not None:
        if geometry.get("type") == "FeatureCollection":
            if len(geometry["features"]) != 1:
                raise ToolError(
                    "GeoJSON FeatureCollection must contain exactly one feature"
                )
            geometry = geometry["features"][0]
        if geometry.get("type") == "Feature":
            geometry = geometry["geometry"]
        area_geometry = Geometry(geometry, crs=area_crs)

    return area_bbox, area_geometry


def _required_area(
    bbox: list[float] | None, geometry: JsonDict | None, crs: str
) -> tuple[BBox | None, Geometry | None]:
    area_bbox, area_geometry = _area(bbox, geometry, crs)
    if area_bbox is None and area_geometry is None:
        raise ToolError(
            "An area of interest is required: pass `bbox` and/or `geometry`"
        )
    return area_bbox, area_geometry


def _output_size(
    bbox: BBox | None,
    geometry: Geometry | None,
    size: list[int] | None,
    resolution: float | None,
) -> tuple[tuple[int, int] | None, tuple[float, float] | None]:
    """Same rules as the CLI: `resolution` becomes a pixel size for WGS84 areas and is passed as is otherwise."""
    if size and resolution:
        raise ToolError("Pass either `size` or `resolution`, not both")
    if size:
        if len(size) != 2:
            raise ToolError("`size` must be [width, height]")
        return (size[0], size[1]), None
    if resolution:
        area_bbox = bbox if bbox is not None else geometry.bbox
        if area_bbox.crs is CRS.WGS84:
            return bbox_to_dimensions(area_bbox, resolution=resolution), None
        return None, (resolution, resolution)
    raise ToolError("An output size is required: pass `size` or `resolution`")


def _evalscript(
    collection: DataCollection,
    evalscript: str | None,
    bands: list[str] | None,
    **kwargs: Any,
) -> str:
    if evalscript and bands:
        raise ToolError("Pass either `evalscript` or `bands`, not both")
    if evalscript:
        return evalscript
    if bands:
        try:
            return _generate_evalscript(collection, bands=bands, **kwargs)
        except ValueError as exception:
            raise ToolError(str(exception)) from exception
    raise ToolError("An evalscript is required: pass `evalscript` or `bands`")


def _input_data(
    collection: DataCollection,
    maxcc: float | None,
    mosaicking_order: str | None,
    upsampling: str | None,
    downsampling: str | None,
    **kwargs: Any,
) -> JsonDict:
    return SHRequest.input_data(
        collection,
        maxcc=maxcc,
        mosaicking_order=MosaickingOrder(mosaicking_order)
        if mosaicking_order
        else None,
        upsampling=ResamplingType(upsampling) if upsampling else None,
        downsampling=ResamplingType(downsampling) if downsampling else None,
        **kwargs,
    )


def _summarize_feature(feature: JsonDict) -> JsonDict:
    properties = feature.get("properties", {})
    return {
        "id": feature["id"],
        "datetime": properties.get("datetime"),
        "cloud_cover": properties.get("eo:cloud_cover"),
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@server.tool(annotations=READ_ONLY)
def list_collections() -> list[JsonDict]:
    """List the predefined data collections with their enum name and API ID."""
    return [
        {"name": collection.name, "api_id": collection.api_id}
        for collection in DataCollection
    ]


@server.tool(annotations=READ_ONLY)
def list_bands(collection: str) -> JsonDict:
    """
    List the bands and meta-bands of a data collection with their units.

    Args:
        collection: Enum name (`SENTINEL2_L2A`) or API ID (`sentinel-2-l2a`).
    """
    data_collection = _collection(collection)
    return {
        group: [
            {"name": band.name, "units": [unit.value for unit in band.units]}
            for band in bands
        ]
        for group, bands in (
            ("bands", data_collection.bands),
            ("meta_bands", data_collection.metabands),
        )
    }


@server.tool(annotations=READ_ONLY)
def generate_evalscript(
    collection: str,
    bands: list[str] | None = None,
    meta_bands: list[str] | None = None,
    merged_output: str | None = None,
    prioritize_dn: bool = True,
) -> str:
    """
    Generate a `//VERSION=3` evalscript from band names.

    Args:
        collection: Enum name or API ID of the data collection.
        bands: Bands to output (default: all bands of the collection).
        meta_bands: Meta-bands to output, e.g. ["dataMask"].
        merged_output: Merge all bands into a single output with this ID.
        prioritize_dn: Prefer DN units where the band supports them.
    """
    try:
        return _generate_evalscript(
            _collection(collection),
            bands=bands,
            meta_bands=meta_bands,
            merged_bands_output=merged_output,
            prioritize_dn=prioritize_dn,
        ).strip()
    except ValueError as exception:
        raise ToolError(str(exception)) from exception


@server.tool(annotations=READ_ONLY)
def show_config(profile: str | None = None) -> JsonDict:
    """
    Show the active Sentinel Hub configuration with credentials masked.

    Args:
        profile: Config profile to use (default profile if omitted).
    """
    config = SHConfig(profile=profile)
    return {
        "config_location": str(SHConfig.get_config_location()),
        "credentials_set": bool(config.sh_client_id and config.sh_client_secret),
        **config.to_dict(mask_credentials=True),
    }


@server.tool(annotations=REMOTE_READ)
def search_catalog(
    collection: str,
    bbox: list[float] | None = None,
    geometry: JsonDict | None = None,
    crs: str = "4326",
    time: str | None = None,
    filter: str | None = None,
    ids: list[str] | None = None,
    max_results: int = 50,
    full: bool = False,
    profile: str | None = None,
) -> JsonDict:
    """
    Search the Sentinel Hub catalog (STAC) for acquisitions.

    Args:
        collection: Enum name or API ID of the data collection.
        bbox: Area as [min_x, min_y, max_x, max_y] in `crs`.
        geometry: Area as a GeoJSON polygon (geometry, Feature or single-feature FeatureCollection) in `crs`.
        crs: EPSG code of `bbox` / `geometry` (default: 4326).
        time: `START/END` (e.g. 2024-06-01/2024-06-30) or a single date.
        filter: CQL2 text filter, e.g. "eo:cloud_cover < 20".
        ids: Feature IDs to fetch.
        max_results: Stop after this many results (default: 50).
        full: Return full STAC features instead of id / datetime / cloud cover summaries.
        profile: Config profile to use.
    """
    data_collection = _collection(collection)
    area_bbox, area_geometry = _area(bbox, geometry, crs)

    catalog = SHCatalog(config=SHConfig(profile=profile))
    results = catalog.search(
        data_collection.catalog_id,
        time=parse_time(time),
        bbox=area_bbox,
        geometry=area_geometry,
        ids=ids,
        filter=filter,
        limit=min(max_results, 100),
    )
    features = list(itertools.islice(results, max_results))
    return {
        "count": len(features),
        "features": features if full else [_summarize_feature(f) for f in features],
    }


@server.tool(annotations=ToolAnnotations(open_world_hint=True, destructive_hint=False))
def process_image(
    collection: str,
    output_path: str,
    bbox: list[float] | None = None,
    geometry: JsonDict | None = None,
    crs: str = "4326",
    time: str | None = None,
    size: list[int] | None = None,
    resolution: float | None = None,
    bands: list[str] | None = None,
    evalscript: str | None = None,
    format: ProcessFormat | None = None,
    response_id: str = "default",
    maxcc: float | None = None,
    mosaicking_order: MosaickingOrderName | None = None,
    upsampling: ResamplingName | None = None,
    downsampling: ResamplingName | None = None,
    profile: str | None = None,
) -> list[str | Image]:
    """
    Download processed imagery with the Process API and save it to a file.
    PNG and JPEG results are also returned as an image preview.

    Args:
        collection: Enum name or API ID of the data collection.
        output_path: File to write, e.g. "out/image.tif". Relative paths resolve against the server's working directory.
        bbox: Area as [min_x, min_y, max_x, max_y] in `crs`.
        geometry: Area as a GeoJSON polygon in `crs`.
        crs: EPSG code of `bbox` / `geometry` (default: 4326).
        time: `START/END` or a single date.
        size: Output size in pixels as [width, height]. Pass this or `resolution`.
        resolution: Output resolution in meters per pixel. Pass this or `size`.
        bands: Bands to request; an evalscript merging them into one output is generated. Pass this or `evalscript`.
        evalscript: Custom evalscript source code.
        format: Response format (default: inferred from the `output_path` suffix).
        response_id: Evalscript output ID (default: "default").
        maxcc: Max cloud coverage between 0 and 1.
        mosaicking_order: How to pick scenes when several match.
        upsampling: Resampling for upsampling (NEAREST, BILINEAR, BICUBIC).
        downsampling: Resampling for downsampling (NEAREST, BILINEAR, BICUBIC).
        profile: Config profile to use.
    """
    data_collection = _collection(collection)
    area_bbox, area_geometry = _required_area(bbox, geometry, crs)
    output_size, output_resolution = _output_size(
        area_bbox, area_geometry, size, resolution
    )
    script = _evalscript(
        data_collection, evalscript, bands, merged_bands_output=response_id
    )

    output = Path(output_path).resolve()
    output_format = format or _format_from_suffix(output)
    request = SHRequest(
        evalscript=script,
        input_data=[
            _input_data(
                data_collection,
                maxcc,
                mosaicking_order,
                upsampling,
                downsampling,
                time_interval=parse_time(time),
            )
        ],
        responses=[SHRequest.output_response(response_id, MimeType(output_format))],
        bbox=area_bbox,
        geometry=area_geometry,
        size=output_size,
        resolution=output_resolution,
        config=SHConfig(profile=profile),
    )
    response = request.get_data(decode_data=False)[0]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)

    result: list[str | Image] = [
        f"Saved {len(response.content)} bytes ({output_format}) to {output}"
    ]
    if output_format in ("png", "jpg"):
        result.append(
            Image(
                data=response.content,
                format="png" if output_format == "png" else "jpeg",
            )
        )
    return result


def _format_from_suffix(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    suffix = {"tif": "tiff", "jpeg": "jpg"}.get(suffix, suffix)
    if suffix not in ProcessFormat.__args__:
        raise ToolError(
            f"Cannot infer the format from `{path.name}`; pass `format` "
            f"({', '.join(ProcessFormat.__args__)})"
        )
    return suffix


@server.tool(annotations=REMOTE_READ)
def compute_statistics(
    collection: str,
    time: str,
    bbox: list[float] | None = None,
    geometry: JsonDict | None = None,
    crs: str = "4326",
    interval: str = "P1D",
    last_interval: Literal["SKIP", "SHORTEN", "EXTEND"] | None = None,
    size: list[int] | None = None,
    resolution: float | None = None,
    bands: list[str] | None = None,
    evalscript: str | None = None,
    maxcc: float | None = None,
    mosaicking_order: MosaickingOrderName | None = None,
    upsampling: ResamplingName | None = None,
    downsampling: ResamplingName | None = None,
    profile: str | None = None,
) -> JsonDict:
    """
    Compute statistics per time interval with the Statistical API, without downloading images.

    Args:
        collection: Enum name or API ID of the data collection.
        time: `START/END`, e.g. 2024-06-01/2024-06-30.
        bbox: Area as [min_x, min_y, max_x, max_y] in `crs`.
        geometry: Area as a GeoJSON polygon in `crs`.
        crs: EPSG code of `bbox` / `geometry` (default: 4326).
        interval: ISO 8601 aggregation interval (default: P1D).
        last_interval: What to do with a last interval shorter than `interval`.
        size: Output size in pixels as [width, height]. Pass this or `resolution`.
        resolution: Output resolution in meters per pixel. Pass this or `size`.
        bands: Bands to compute statistics for (`dataMask` is added automatically). Pass this or `evalscript`.
        evalscript: Custom evalscript; it must output a `dataMask`.
        maxcc: Max cloud coverage between 0 and 1.
        mosaicking_order: How to pick scenes when several match.
        upsampling: Resampling for upsampling (NEAREST, BILINEAR, BICUBIC).
        downsampling: Resampling for downsampling (NEAREST, BILINEAR, BICUBIC).
        profile: Config profile to use.
    """
    data_collection = _collection(collection)
    area_bbox, area_geometry = _required_area(bbox, geometry, crs)
    output_size, output_resolution = _output_size(
        area_bbox, area_geometry, size, resolution
    )
    if bands and "dataMask" in bands:
        raise ToolError("`dataMask` is added automatically, leave it out of `bands`")
    script = _evalscript(data_collection, evalscript, bands, meta_bands=["dataMask"])

    request = SHStatistical(
        aggregation=SHStatistical.aggregation(
            evalscript=script,
            time_interval=parse_time(time),
            aggregation_interval=interval,
            last_interval_behavior=LastIntervalBehavior(last_interval)
            if last_interval
            else None,
            size=output_size,
            resolution=output_resolution,
        ),
        input_data=[
            _input_data(
                data_collection, maxcc, mosaicking_order, upsampling, downsampling
            )
        ],
        bbox=area_bbox,
        geometry=area_geometry,
        config=SHConfig(profile=profile),
    )
    return request.get_data()[0]


@server.resource(
    "sentinel-hub://collections/{collection}/bands",
    mime_type="application/json",
)
def bands_resource(collection: str) -> str:
    """Bands and meta-bands of a data collection."""
    return json.dumps(list_bands(collection), indent=2)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
