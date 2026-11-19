from typing import cast

from sentinel_hub.constants import CRS


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
