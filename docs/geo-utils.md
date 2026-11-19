# Geo utilities

Helpers in `sentinel_hub.geo_utils` for converting between real-world distances, pixel
grids and UTM coordinates. All are importable from `sentinel_hub`.

- [Image size from resolution](#image-size-from-resolution)
- [UTM helpers](#utm-helpers)
- [Pixel ↔ UTM](#pixel--utm)
- [Reference](#reference)

## Image size from resolution

Sentinel-2 bands have 10 m, 20 m or 60 m pixels. To request an image at a given ground
resolution for a WGS84 bbox, compute the pixel size:

```python
from sentinel_hub import (
    BBox,
    CRS,
    bbox_to_dimensions,
    bbox_to_resolution,
    get_image_dimension,
)

bbox = BBox((13.35, 45.85, 13.55, 46.0), crs=CRS.WGS84)

bbox_to_dimensions(bbox, resolution=10)  # (width, height) at 10 m, here (1583, 1636)
bbox_to_dimensions(bbox, resolution=(10, 20))  # different x / y resolution

bbox_to_resolution(bbox, width=512, height=512)  # (resx, resy) in metres
bbox_to_resolution(
    bbox, width=512, height=512, meters=False
)  # in CRS units (degrees here)

get_image_dimension(bbox, width=512)  # height that keeps the aspect ratio
get_image_dimension(bbox, height=512)  # width that keeps the aspect ratio
```

Distances are measured in the UTM zone of the bbox centre, so results are in metres
regardless of the input CRS.

## UTM helpers

```python
from sentinel_hub import get_utm_crs, to_utm_bbox, transform_point

get_utm_crs(13.45, 45.92)  # CRS.UTM_33N
get_utm_crs(1497000, 5768000, source_crs=CRS.POP_WEB)

to_utm_bbox(bbox)  # BBox in the UTM zone of its centre (returned as-is if already UTM)

transform_point((13.45, 45.92), CRS.WGS84, CRS.UTM_33N)  # (easting, northing)
```

## Pixel ↔ UTM

Using a geotransform `(min_x, resx, 0, max_y, 0, -resy)` from `BBox.get_transform_vector`:

```python
from sentinel_hub import pixel_to_utm, utm_to_pixel

utm_bbox = to_utm_bbox(bbox)
transform = utm_bbox.get_transform_vector(10, 10)

row, col = utm_to_pixel(easting, northing, transform)  # ints
row, col = utm_to_pixel(easting, northing, transform, truncate=False)  # floats
easting, northing = pixel_to_utm(row, col, transform)
```

## Reference

| Function | Returns | Description |
|---|---|---|
| `bbox_to_dimensions(bbox, resolution)` | `(width, height)` | Pixel size for a resolution in metres |
| `bbox_to_resolution(bbox, width, height, meters=True)` | `(resx, resy)` | Resolution for a pixel size |
| `get_image_dimension(bbox, width=None, height=None)` | `int` | The missing dimension, preserving aspect ratio |
| `to_utm_bbox(bbox)` | `BBox` | Reproject to the local UTM zone |
| `get_utm_crs(lng, lat, source_crs=CRS.WGS84)` | `CRS` | UTM zone containing a point |
| `transform_point(point, source_crs, target_crs, always_xy=True)` | `(x, y)` | Reproject one point |
| `utm_to_pixel(east, north, transform, truncate=True)` | `(row, column)` | UTM → pixel |
| `pixel_to_utm(row, column, transform)` | `(east, north)` | Pixel → UTM |
