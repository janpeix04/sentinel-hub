"""
Command line interface for the `sentinel-hub` package.

Run `sentinel-hub --help` (or `python -m sentinel_hub --help`) for usage.
"""

import argparse
import dataclasses
import itertools
import json
import sys
import typing
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sentinel_hub._version import __version__
from sentinel_hub.api import SHCatalog, SHRequest, SHStatistical
from sentinel_hub.config import DEFAULT_PROFILE, SHConfig, _SHConfig
from sentinel_hub.constants import (
    CRS,
    LastIntervalBehavior,
    MimeType,
    MosaickingOrder,
    ResamplingType,
)
from sentinel_hub.data_collections import DataCollection
from sentinel_hub.evalscript import generate_evalscript
from sentinel_hub.geo_utils import bbox_to_dimensions
from sentinel_hub.geometry import BBox, Geometry
from sentinel_hub.types import JsonDict

PROCESS_FORMATS = ("tiff", "png", "jpg", "json", "tar")
SEARCH_OUTPUTS = ("ids", "timestamps", "json")


class CLIError(Exception):
    """An error caused by invalid command line input."""


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------


def parse_collection(value: str) -> DataCollection:
    """Parses a data collection from its enum name (`SENTINEL2_L2A`) or API ID (`sentinel-2-l2a`)."""
    normalized = value.strip()
    for collection in DataCollection:
        if normalized.upper() == collection.name or normalized == collection.api_id:
            return collection
    available = ", ".join(collection.name for collection in DataCollection)
    raise CLIError(f"Unknown data collection `{value}`. Available: {available}")


def parse_bbox(value: str, crs: str) -> BBox:
    """Parses a `min_x,min_y,max_x,max_y` string into a `BBox`."""
    parts = value.replace(" ", "").split(",")
    if len(parts) != 4:
        raise CLIError(f"Bounding box must be `min_x,min_y,max_x,max_y`, got `{value}`")
    try:
        coords = tuple(float(part) for part in parts)
    except ValueError as exception:
        raise CLIError(f"Bounding box values must be numbers, got `{value}`") from exception
    return BBox(coords, crs=CRS(crs))


def parse_geometry(path: str, crs: str) -> Geometry:
    """Reads a polygon from a GeoJSON file (geometry, Feature or FeatureCollection with one feature)."""
    with open(path, encoding="utf-8") as file:
        geojson = json.load(file)

    if geojson.get("type") == "FeatureCollection":
        if len(geojson["features"]) != 1:
            raise CLIError("GeoJSON FeatureCollection must contain exactly one feature")
        geojson = geojson["features"][0]
    if geojson.get("type") == "Feature":
        geojson = geojson["geometry"]

    return Geometry(geojson, crs=CRS(crs))


def parse_time(value: str | None) -> tuple[str, str] | str | None:
    """Parses `START/END` into a time interval; a single date is passed through as is."""
    if value is None:
        return None
    if "/" in value:
        start, end = value.split("/", maxsplit=1)
        return start, end
    return value


def parse_pair(value: str, cast: type) -> tuple[Any, Any]:
    """Parses `A,B` (or a single `A`, used for both) into a tuple."""
    parts = value.replace(" ", "").split(",")
    if len(parts) == 1:
        parts *= 2
    if len(parts) != 2:
        raise CLIError(f"Expected one or two comma-separated values, got `{value}`")
    try:
        return cast(parts[0]), cast(parts[1])
    except ValueError as exception:
        raise CLIError(f"Invalid value `{value}`") from exception


def parse_list(value: str | None) -> list[str] | None:
    """Parses a comma-separated list."""
    if value is None:
        return None
    return [item for item in value.replace(" ", "").split(",") if item]


def get_area(args: argparse.Namespace) -> tuple[BBox | None, Geometry | None]:
    """Builds the area of interest from `--bbox` and/or `--geometry`."""
    bbox = parse_bbox(args.bbox, args.crs) if args.bbox else None
    geometry = parse_geometry(args.geometry, args.crs) if args.geometry else None
    if bbox is None and geometry is None:
        raise CLIError("An area of interest is required: pass --bbox and/or --geometry")
    return bbox, geometry


def get_output_size(
    args: argparse.Namespace, bbox: BBox | None, geometry: Geometry | None
) -> tuple[tuple[int, int] | None, tuple[float, float] | None]:
    """
    Resolves the output size. `--size` is passed directly. `--resolution` is converted to a
    pixel size for WGS84 areas (where the service would interpret it in degrees) and passed
    as is for projected CRSs.
    """
    if args.size and args.resolution:
        raise CLIError("Pass either --size or --resolution, not both")
    if args.size:
        return parse_pair(args.size, int), None
    if args.resolution:
        resolution = float(args.resolution)
        area_bbox = bbox if bbox is not None else geometry.bbox
        if area_bbox.crs is CRS.WGS84:
            return bbox_to_dimensions(area_bbox, resolution=resolution), None
        return None, (resolution, resolution)
    raise CLIError("An output size is required: pass --size or --resolution")


def get_config(args: argparse.Namespace) -> SHConfig:
    return SHConfig(profile=args.profile)


def get_evalscript(
    args: argparse.Namespace,
    collection: DataCollection,
    *,
    merged_bands_output: str | None = None,
    meta_bands: list[str] | None = None,
) -> str:
    """Reads `--evalscript` from a file or generates one from `--bands`."""
    if args.evalscript and args.bands:
        raise CLIError("Pass either --evalscript or --bands, not both")
    if args.evalscript:
        return Path(args.evalscript).read_text(encoding="utf-8")
    if args.bands:
        try:
            return generate_evalscript(
                collection,
                bands=parse_list(args.bands),
                meta_bands=meta_bands,
                merged_bands_output=merged_bands_output,
            )
        except ValueError as exception:
            raise CLIError(str(exception)) from exception
    raise CLIError("An evalscript is required: pass --evalscript FILE or --bands B04,B03,B02")


def get_input_data(args: argparse.Namespace, collection: DataCollection, **kwargs: Any) -> JsonDict:
    return SHRequest.input_data(
        collection,
        maxcc=args.maxcc,
        mosaicking_order=MosaickingOrder(args.mosaicking_order) if args.mosaicking_order else None,
        upsampling=ResamplingType(args.upsampling) if args.upsampling else None,
        downsampling=ResamplingType(args.downsampling) if args.downsampling else None,
        **kwargs,
    )


def write_output(content: str, output: str | None) -> None:
    """Writes text to a file, or to stdout if no file is given."""
    if output is None:
        sys.stdout.write(content if content.endswith("\n") else f"{content}\n")
        return
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(content, encoding="utf-8")
    print(f"Saved to {output}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_config_show(args: argparse.Namespace) -> None:
    config = get_config(args)
    print(json.dumps(config.to_dict(mask_credentials=not args.show_secrets), indent=2))


def cmd_config_set(args: argparse.Namespace) -> None:
    fields = {field.name: field for field in dataclasses.fields(_SHConfig)}
    key = args.key.lower()
    if key not in fields:
        raise CLIError(f"Unknown config parameter `{args.key}`. Available: {', '.join(fields)}")

    config = SHConfig.load(profile=args.profile) if _profile_exists(args.profile) else SHConfig(
        use_defaults=True
    )
    setattr(config, key, _cast_config_value(fields[key], args.value))
    config.save(profile=args.profile)
    print(f"Set `{key}` in profile `{args.profile or DEFAULT_PROFILE}`", file=sys.stderr)


def cmd_config_path(args: argparse.Namespace) -> None:
    print(SHConfig.get_config_location())


def _profile_exists(profile: str | None) -> bool:
    try:
        SHConfig.load(profile=profile)
    except KeyError:
        return False
    return True


def _cast_config_value(field: dataclasses.Field, value: str) -> Any:
    """Converts a string value to the type of the given config field."""
    field_types = typing.get_args(field.type) or (field.type,)
    if type(None) in field_types and value.lower() in ("none", "null", ""):
        return None
    for field_type in (int, float):
        if field_type in field_types:
            try:
                return field_type(value)
            except ValueError as exception:
                raise CLIError(
                    f"`{field.name}` expects a {field_type.__name__} value, got `{value}`"
                ) from exception
    return value


def cmd_collections(args: argparse.Namespace) -> None:
    rows = [(collection.name, collection.api_id) for collection in DataCollection]
    width = max(len(name) for name, _ in rows)
    for name, api_id in rows:
        print(f"{name:<{width}}  {api_id}")


def cmd_bands(args: argparse.Namespace) -> None:
    collection = parse_collection(args.collection)
    groups = [("Bands", collection.bands), ("Meta-bands", collection.metabands)]
    for title, bands in groups:
        print(f"{title}:")
        for band in bands:
            units = ", ".join(unit.value for unit in band.units)
            print(f"  {band.name:<24} {units}")


def cmd_evalscript(args: argparse.Namespace) -> None:
    collection = parse_collection(args.collection)
    try:
        evalscript = generate_evalscript(
            collection,
            bands=parse_list(args.bands),
            meta_bands=parse_list(args.meta_bands),
            merged_bands_output=args.merged_output,
            prioritize_dn=not args.no_dn,
        )
    except ValueError as exception:
        raise CLIError(str(exception)) from exception
    write_output(evalscript.strip(), args.output)


def cmd_search(args: argparse.Namespace) -> None:
    collection = parse_collection(args.collection)
    bbox = parse_bbox(args.bbox, args.crs) if args.bbox else None
    geometry = parse_geometry(args.geometry, args.crs) if args.geometry else None

    catalog = SHCatalog(config=get_config(args))
    results = catalog.search(
        collection.catalog_id,
        time=parse_time(args.time),
        bbox=bbox,
        geometry=geometry,
        ids=parse_list(args.ids),
        filter=args.filter,
        limit=min(args.max_results, 100) if args.max_results else 100,
    )
    features = list(itertools.islice(results, args.max_results))

    if args.format == "ids":
        content = "\n".join(feature["id"] for feature in features)
    elif args.format == "timestamps":
        content = "\n".join(feature["properties"]["datetime"] for feature in features)
    else:
        content = json.dumps({"type": "FeatureCollection", "features": features}, indent=2)

    print(f"Found {len(features)} feature(s)", file=sys.stderr)
    write_output(content, args.output)


def cmd_process(args: argparse.Namespace) -> None:
    collection = parse_collection(args.collection)
    bbox, geometry = get_area(args)
    size, resolution = get_output_size(args, bbox, geometry)
    evalscript = get_evalscript(args, collection, merged_bands_output="default")

    output_format = args.format or _format_from_path(args.output)
    request = SHRequest(
        evalscript=evalscript,
        input_data=[get_input_data(args, collection, time_interval=parse_time(args.time))],
        responses=[SHRequest.output_response(args.response_id, MimeType(output_format))],
        bbox=bbox,
        geometry=geometry,
        size=size,
        resolution=resolution,
        config=get_config(args),
    )
    response = request.get_data(decode_data=False, show_progress=args.progress)[0]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    print(f"Saved to {output}", file=sys.stderr)


def _format_from_path(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    suffix = {"tif": "tiff", "jpeg": "jpg"}.get(suffix, suffix)
    if suffix not in PROCESS_FORMATS:
        raise CLIError(
            f"Cannot infer the format from `{path}`; pass --format ({', '.join(PROCESS_FORMATS)})"
        )
    return suffix


def cmd_stats(args: argparse.Namespace) -> None:
    collection = parse_collection(args.collection)
    bbox, geometry = get_area(args)
    size, resolution = get_output_size(args, bbox, geometry)
    if args.bands and "dataMask" in (parse_list(args.bands) or []):
        raise CLIError("`dataMask` is added automatically, leave it out of --bands")
    evalscript = get_evalscript(args, collection, meta_bands=["dataMask"])

    request = SHStatistical(
        aggregation=SHStatistical.aggregation(
            evalscript=evalscript,
            time_interval=parse_time(args.time),
            aggregation_interval=args.interval,
            last_interval_behavior=LastIntervalBehavior(args.last_interval) if args.last_interval else None,
            size=size,
            resolution=resolution,
        ),
        input_data=[get_input_data(args, collection)],
        bbox=bbox,
        geometry=geometry,
        config=get_config(args),
    )
    data = request.get_data(show_progress=args.progress)[0]
    write_output(json.dumps(data, indent=2), args.output)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _add_area_args(parser: argparse.ArgumentParser, required: bool) -> None:
    group = parser.add_argument_group("area of interest")
    group.add_argument("--bbox", help="bounding box as `min_x,min_y,max_x,max_y`")
    group.add_argument("--geometry", metavar="FILE", help="GeoJSON file with a polygon")
    group.add_argument("--crs", default="4326", help="CRS of --bbox / --geometry (default: 4326)")
    if required:
        group.description = "at least one of --bbox / --geometry is required"


def _add_input_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("input data")
    group.add_argument("--maxcc", type=float, help="max cloud coverage, between 0 and 1")
    group.add_argument(
        "--mosaicking-order", choices=[order.value for order in MosaickingOrder]
    )
    resampling = [resampling.value for resampling in ResamplingType]
    group.add_argument("--upsampling", choices=resampling)
    group.add_argument("--downsampling", choices=resampling)


def _add_output_size_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("output size (one is required)")
    group.add_argument("--size", help="output size in pixels as `WIDTH,HEIGHT`")
    group.add_argument("--resolution", help="output resolution in meters per pixel")


def _add_evalscript_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("evalscript (one is required)")
    group.add_argument("--evalscript", metavar="FILE", help="path to an evalscript file")
    group.add_argument("--bands", help="comma-separated bands to generate an evalscript from")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-hub",
        description="Command line client for the Sentinel Hub APIs on the Copernicus Data Space Ecosystem.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--profile", help=f"config profile to use (default: {DEFAULT_PROFILE})")
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # config
    config_parser = subparsers.add_parser("config", help="show or edit the configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True, metavar="ACTION")
    show = config_subparsers.add_parser("show", help="print the active configuration")
    show.add_argument("--show-secrets", action="store_true", help="do not mask credentials")
    show.set_defaults(func=cmd_config_show)
    set_parser = config_subparsers.add_parser("set", help="set a parameter in config.toml")
    set_parser.add_argument("key", help="parameter name, e.g. sh_client_id")
    set_parser.add_argument("value")
    set_parser.set_defaults(func=cmd_config_set)
    path = config_subparsers.add_parser("path", help="print the location of config.toml")
    path.set_defaults(func=cmd_config_path)

    # collections / bands / evalscript
    collections = subparsers.add_parser("collections", help="list predefined data collections")
    collections.set_defaults(func=cmd_collections)

    bands = subparsers.add_parser("bands", help="list bands of a data collection")
    bands.add_argument("collection", help="e.g. SENTINEL2_L2A or sentinel-2-l2a")
    bands.set_defaults(func=cmd_bands)

    evalscript = subparsers.add_parser("evalscript", help="generate an evalscript from band names")
    evalscript.add_argument("collection")
    evalscript.add_argument("--bands", help="comma-separated bands (default: all bands)")
    evalscript.add_argument("--meta-bands", help="comma-separated meta-bands, e.g. dataMask")
    evalscript.add_argument("--merged-output", metavar="ID", help="merge bands into a single output with this ID")
    evalscript.add_argument("--no-dn", action="store_true", help="do not prefer DN units")
    evalscript.add_argument("-o", "--output", help="output file (default: stdout)")
    evalscript.set_defaults(func=cmd_evalscript)

    # search
    search = subparsers.add_parser("search", help="search the catalog (STAC)")
    search.add_argument("collection")
    _add_area_args(search, required=False)
    search.add_argument("--time", help="`START/END` or a single date, e.g. 2024-06-01/2024-06-30")
    search.add_argument("--filter", help="CQL2 text filter, e.g. \"eo:cloud_cover < 20\"")
    search.add_argument("--ids", help="comma-separated feature IDs")
    search.add_argument("--max-results", type=int, help="stop after this many results")
    search.add_argument("--format", choices=SEARCH_OUTPUTS, default="ids", help="output format (default: ids)")
    search.add_argument("-o", "--output", help="output file (default: stdout)")
    search.set_defaults(func=cmd_search)

    # process
    process = subparsers.add_parser("process", help="download processed imagery (Process API)")
    process.add_argument("collection")
    process.add_argument("-o", "--output", required=True, help="output file, e.g. image.tif")
    process.add_argument("--time", help="`START/END` or a single date")
    process.add_argument("--format", choices=PROCESS_FORMATS, help="response format (default: from --output)")
    process.add_argument("--response-id", default="default", help="evalscript output ID (default: default)")
    process.add_argument("--progress", action="store_true", help="show a progress bar")
    _add_area_args(process, required=True)
    _add_output_size_args(process)
    _add_evalscript_args(process)
    _add_input_args(process)
    process.set_defaults(func=cmd_process)

    # stats
    stats = subparsers.add_parser("stats", help="compute statistics (Statistical API)")
    stats.add_argument("collection")
    stats.add_argument("--time", required=True, help="`START/END`")
    stats.add_argument("--interval", default="P1D", help="ISO 8601 aggregation interval (default: P1D)")
    stats.add_argument(
        "--last-interval", choices=[behavior.value for behavior in LastIntervalBehavior]
    )
    stats.add_argument("-o", "--output", help="output JSON file (default: stdout)")
    stats.add_argument("--progress", action="store_true", help="show a progress bar")
    _add_area_args(stats, required=True)
    _add_output_size_args(stats)
    _add_evalscript_args(stats)
    _add_input_args(stats)
    stats.set_defaults(func=cmd_stats)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except CLIError as exception:
        parser.exit(2, f"{parser.prog}: error: {exception}\n")
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
