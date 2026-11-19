from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from sentinel_hub.constants import CRS

if TYPE_CHECKING:
    from .geometry import BBox

ERR = 0.1


def bbox_to_dimensions(
    bbox: BBox, resolution: float | tuple[float, float]
) -> tuple[int, int]:
    """
    Calculates width and height in pixels for a given bbox of a given pixel resolution (in
    meters). The result is rounded to the nearest integers."""
    utm_bbox = to_utm_bbox(bbox)
    east1, north1 = utm_bbox.lower_left
    east2, north2 = utm_bbox.upper_right

    resx, resy = (
        resolution if isinstance(resolution, tuple) else (resolution, resolution)
    )

    return round(abs(east2 - east1) / resx), round(abs(north2 - north1) / resy)


def bbox_to_resolution(
    bbox: BBox, width: int, height: int, meters: bool = True
) -> tuple[float, float]:
    """
    Calculates pixel resolution for a given bbox of a given width and height. By default, it
    returns result in meters."""
    if meters:
        bbox = to_utm_bbox(bbox)
    east1, north1 = bbox.lower_left
    east2, north2 = bbox.upper_right
    return abs(east2 - east1) / width, abs(north2 - north1) / height


def get_image_dimension(
    bbox: BBox, width: int | None = None, height: int | None = None
) -> int:
    """
    Given bounding box and one of the parameters width or height it will return the other
    parameter that will best fit the bounding box dimensions."""
    utm_bbox = to_utm_bbox(bbox)
    east1, north1 = utm_bbox.lower_left
    east2, north2 = utm_bbox.upper_right
    if isinstance(width, int):
        return round(width * abs(north2 - north1) / abs(east2 - east1))
    if isinstance(height, int):
        return round(height * abs(east2 - east1) / abs(north2 - north1))
    raise ValueError(
        "At least one of the parameters `width` and `height` must be given."
    )


def to_utm_bbox(bbox: BBox) -> BBox:
    """Transform bbox into UTM CRS."""
    if CRS.is_utm(bbox.crs):
        return bbox
    lng, lat = bbox.middle
    utm_crs = get_utm_crs(lng, lat, source_crs=bbox.crs)
    return bbox.transform(utm_crs)


def utm_to_pixel(
    east: float, north: float, transform: Sequence[float], truncate: bool = True
) -> tuple[float, float] | tuple[int, int]:
    """Convert a UTM coordinate to image coordinate given a transform."""
    column = (east - transform[0]) / transform[1]
    row = (north - transform[3]) / transform[5]
    if truncate:
        return int(row + ERR), int(column + ERR)
    return row, column


def pixel_to_utm(
    row: float, column: float, transform: Sequence[float]
) -> tuple[float, float]:
    """Convert pixel coordinate to UTM coordinate given a transform."""
    east = transform[0] + column * transform[1]
    north = transform[3] + row * transform[5]
    return east, north


def get_utm_crs(lng: float, lat: float, source_crs: CRS = CRS.WGS84) -> CRS:
    """Get CRS for UTM zone in which (lat, lng) is contained."""
    if source_crs is not CRS.WGS84:
        lng, lat = transform_point((lng, lat), source_crs, CRS.WGS84)
    return CRS.get_utm_from_wgs84(lng, lat)


def transform_point(
    point: tuple[float, float], source_crs: CRS, target_crs: CRS, always_xy: bool = True
) -> tuple[float, float]:
    """Maps point form src_crs to tgt_crs."""
    if source_crs == target_crs:
        return point
    transform_function = CRS.get_transform_function(
        source_crs, target_crs, always_xy=always_xy
    )
    return cast(tuple[float, float], transform_function(*point))
