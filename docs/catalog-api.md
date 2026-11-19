# Catalog API

`SHCatalog` wraps the Sentinel Hub [Catalog API](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Catalog.html),
a [STAC](https://stacspec.org/)-compliant service for discovering which satellite scenes
exist for a place and time – before you spend processing units downloading them.

- [Creating a client](#creating-a-client)
- [Service information](#service-information)
- [Collections and features](#collections-and-features)
- [Searching](#searching)
- [Working with results](#working-with-results)
- [Reference](#reference)

## Creating a client

```python
from sentinel_hub import SHCatalog, SHConfig

catalog = SHCatalog()  # uses SHConfig()
catalog = SHCatalog(config=SHConfig(profile="work"))
```

The service URL is `{config.sh_base_url}/api/v1/catalog/1.0.0`. Requests are
authenticated automatically through an `SHDownloadClient` (see [download.md](download.md)).

## Service information

```python
catalog.get_info()  # landing page: title, description, links
catalog.get_conformance()  # list of conformance classes the API implements
```

## Collections and features

```python
collections = catalog.get_collections()  # list of STAC collection dicts
[c["id"] for c in collections]
# ['sentinel-2-l1c', 'sentinel-2-l2a', ...]

s2 = catalog.get_collection("sentinel-2-l2a")  # one collection
s2["extent"]["temporal"]

feature = catalog.get_feature(
    "sentinel-2-l2a",
    "S2A_MSIL2A_20240615T100031_N0510_R122_T33TUL_20240615T161308.SAFE",
)
feature["properties"]["eo:cloud_cover"]
```

Tip: use `DataCollection.SENTINEL2_L2A.catalog_id` instead of hard-coding the ID.

## Searching

`search()` runs a STAC search and returns a lazy `CatalogSearchIterator`.

```python
from sentinel_hub import CRS, BBox, DataCollection

bbox = BBox((13.35, 45.85, 13.55, 46.0), crs=CRS.WGS84)

results = catalog.search(
    DataCollection.SENTINEL2_L2A.catalog_id,
    bbox=bbox,
    time=("2024-06-01", "2024-06-30"),
    filter="eo:cloud_cover < 20",
    fields={
        "include": ["id", "properties.datetime", "properties.eo:cloud_cover"],
        "exclude": [],
    },
    limit=50,
)
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `collection_id` | `str` | Catalog collection ID (required, positional) |
| `time` | `str`, `date`, or `(start, end)` | A single day or an interval. `None` / `".."` leaves an end open. See [time-utils.md](time-utils.md) |
| `bbox` | `BBox` | Area of interest. Reprojected to WGS84 automatically |
| `geometry` | `Geometry` | Polygon area of interest (sent as `intersects`). Reprojected to WGS84 automatically |
| `ids` | `list[str]` | Restrict to specific feature IDs |
| `filter` | `str` or `dict` | A [CQL2](https://docs.ogc.org/is/21-065r2/21-065r2.html) filter |
| `filter_lang` | `"cql2-text"` \| `"cql2-json"` | Language of `filter` (default `cql2-text`) |
| `fields` | `dict` | `{"include": [...], "exclude": [...]}` to trim the response |
| `limit` | `int` | Page size per request (default `100`) |
| `**kwargs` | | Extra fields added verbatim to the search payload |

### Filter examples

```python
# CQL2 text
catalog.search(cid, time=..., bbox=bbox, filter="eo:cloud_cover < 10")

# CQL2 JSON
catalog.search(
    cid,
    time=...,
    bbox=bbox,
    filter={"op": "<", "args": [{"property": "eo:cloud_cover"}, 10]},
    filter_lang="cql2-json",
)

# Search by IDs only
catalog.search(cid, ids=["S2A_MSIL2A_..."])
```

## Working with results

`CatalogSearchIterator` fetches pages only when you iterate, follows the `next` token
automatically, and keeps already-fetched features in memory so iterating again is free.

```python
for feature in results:
    print(feature["id"], feature["properties"]["datetime"])

all_features = list(results)
results.get_ids()  # list[str]
results.get_timestamps()  # list[datetime.datetime]
results.get_geometries()  # list[Geometry] (WGS84)
```

Combine timestamps with [`filter_times`](time-utils.md#filter_times) to drop near-duplicate
acquisitions (e.g. adjacent tiles from the same pass):

```python
import datetime as dt
from sentinel_hub import filter_times

unique_times = filter_times(results.get_timestamps(), dt.timedelta(hours=1))
```

## Reference

| Method | HTTP | Returns |
|---|---|---|
| `get_info()` | `GET /` | `dict` |
| `get_conformance()` | `GET /conformance` | `dict` |
| `get_collections()` | `GET /collections` | `list[dict]` |
| `get_collection(collection_id)` | `GET /collections/{id}` | `dict` |
| `get_feature(collection_id, feature_id)` | `GET /collections/{id}/items/{feature_id}` | `dict` |
| `search(collection_id, ...)` | `POST /search` | `CatalogSearchIterator` |

API reference: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>
