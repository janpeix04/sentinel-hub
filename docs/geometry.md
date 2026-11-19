# Geometry & CRS

Three classes describe *where* on Earth a request applies:

- **`CRS`** – a coordinate reference system (WGS84, Web Mercator, UTM zones, any EPSG code).
- **`BBox`** – an axis-aligned bounding box in a CRS.
- **`Geometry`** – a polygon or multipolygon in a CRS.

- [CRS](#crs)
- [BBox](#bbox)
- [Geometry](#geometry)
- [Reference](#reference)

## CRS

```python
from sentinel_hub import CRS

CRS.WGS84  # EPSG:4326, longitude/latitude order
CRS.POP_WEB  # EPSG:3857, Popular Web Mercator
CRS.UTM_33N  # EPSG:32633 – all UTM_1N … UTM_60N and UTM_1S … UTM_60S exist
```

`CRS(...)` accepts many representations; unknown EPSG codes are added on the fly:

```python
CRS(4326) is CRS.WGS84
CRS("EPSG:3857") is CRS.POP_WEB
CRS("urn:ogc:def:crs:EPSG::32633") is CRS.UTM_33N
CRS("CRS84") is CRS.WGS84
CRS({"init": 32633})
CRS(pyproj.CRS(3035))  # -> CRS('3035'), a new member EPSG_3035
```

| Member | Description |
|---|---|
| `crs.epsg` | EPSG code as `int` |
| `crs.ogc_string()` / `str(crs)` | `"EPSG:4326"` |
| `crs.opengis_string` | `"http://www.opengis.net/def/crs/EPSG/0/4326"` (used in API payloads) |
| `crs.is_utm()` | `True` for UTM zones |
| `crs.pyproj_crs()` / `crs.projection()` | `pyproj.CRS` / `pyproj.Proj` (cached) |
| `crs.get_transform_function(other, always_xy=True)` | Cached `pyproj` transform function |
| `CRS.get_utm_from_wgs84(lng, lat)` | UTM zone containing a WGS84 point |

> **Axis order:** the library always uses **x, y** = **longitude, latitude** for WGS84.
> Passing `pyproj.CRS(4326)` (which is lat/lng) emits an `SHUserWarning` as a reminder.

## BBox

```python
from sentinel_hub import BBox, CRS

bbox = BBox((13.35, 45.85, 13.55, 46.0), crs=CRS.WGS84)  # (min_x, min_y, max_x, max_y)
bbox = BBox(
    ((13.35, 45.85), (13.55, 46.0)), crs=CRS.WGS84
)  # ((min_x, min_y), (max_x, max_y))
bbox = BBox(
    {"min_x": 13.35, "min_y": 45.85, "max_x": 13.55, "max_y": 46.0}, crs=CRS.WGS84
)
```

Corners are normalised, so the order of the two points doesn't matter. Initialising from a
string, another `BBox` or a shapely geometry still works but is deprecated.

### Properties

```python
list(bbox)  # [13.35, 45.85, 13.55, 46.0]
bbox.lower_left  # (13.35, 45.85)
bbox.upper_right  # (13.55, 46.0)
bbox.middle  # (13.45, 45.925)
bbox.crs  # CRS.WGS84
bbox.geometry  # shapely Polygon
bbox.wkt  # 'POLYGON ((13.35 45.85, ...))'
bbox.geojson  # GeoJSON dict incl. "crs"
bbox.get_geojson(with_crs=False)
bbox.get_polygon()  # 5 clockwise vertices, first == last
```

### Transformations

```python
bbox.transform(
    CRS.UTM_33N
)  # transforms the 2 corners (reversible, may not fully cover)
bbox.transform_bounds(
    CRS.UTM_33N
)  # transforms the outline (always covers the original)
bbox.reverse()  # swap x and y
bbox.apply(lambda x, y: (x + 1, y))  # apply a function to both corners
```

### Buffering and partitioning

```python
bbox.buffer(0.1)  # grow 10 % in each direction (relative)
bbox.buffer((0.2, 0.0))  # grow only horizontally
bbox.buffer(-0.5)  # shrink by half
bbox.buffer(500, relative=False)  # grow by 500 CRS units

grid = bbox.get_partition(num_x=2, num_y=3)  # 2 × 3 equal tiles -> list[list[BBox]]
grid = utm_bbox.get_partition(
    size_x=5000, size_y=5000
)  # 5 km tiles (may overshoot the edge)
```

`bbox.get_transform_vector(resx, resy)` returns a GDAL-style geotransform
`(min_x, resx, 0, max_y, 0, -resy)`; see [geo-utils.md](geo-utils.md) for pixel ↔ UTM helpers.

## Geometry

```python
from shapely.geometry import Polygon
from sentinel_hub import Geometry, CRS

geometry = Geometry(Polygon([(13.4, 45.9), (13.5, 45.9), (13.5, 45.95)]), crs=CRS.WGS84)
geometry = Geometry(
    "POLYGON ((13.4 45.9, 13.5 45.9, 13.5 45.95, 13.4 45.9))", crs=CRS.WGS84
)
geometry = Geometry({"type": "Polygon", "coordinates": [[...]]}, crs=CRS.WGS84)

# GeoJSON with an embedded "crs" member (defaults to WGS84 if none)
geometry = Geometry.from_geojson(geojson_dict)
```

Only `Polygon` and `MultiPolygon` are supported; other types raise `TypeError`.

```python
geometry.geometry  # shapely object
geometry.bbox  # enclosing BBox
geometry.wkt, geometry.geojson
geometry.transform(CRS.POP_WEB)  # reproject every vertex
geometry.reverse()  # swap x and y
geometry.apply(lambda x, y: (x, y + 0.01))
```

Both `BBox` and `Geometry` compare equal only when coordinates **and** CRS match.

## Reference

| `BBox` method | Returns |
|---|---|
| `transform(crs, always_xy=True)` | `BBox` |
| `transform_bounds(crs, always_xy=True)` | `BBox` |
| `buffer(buffer, *, relative=True)` | `BBox` |
| `get_partition(num_x, num_y, size_x, size_y)` | `list[list[BBox]]` |
| `get_polygon(reverse=False)` | `tuple` of 5 points |
| `get_transform_vector(resx, resy)` | 6-tuple |
| `reverse()`, `apply(fn)` | `BBox` |

| `Geometry` method | Returns |
|---|---|
| `Geometry.from_geojson(geojson, crs=None)` | `Geometry` |
| `transform(crs, always_xy=True)` | `Geometry` |
| `reverse()`, `apply(fn)` | `Geometry` |
| `bbox` | `BBox` |
