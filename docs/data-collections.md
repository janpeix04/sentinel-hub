# Data Collections

A **data collection** tells the library which dataset to query and how: its Process API
identifier, its Catalog API identifier, the service it lives on, and which bands it offers.
Collections are members of the `DataCollection` enum.

- [Predefined collections](#predefined-collections)
- [Inspecting a collection](#inspecting-a-collection)
- [Bands and metabands](#bands-and-metabands)
- [Defining custom collections](#defining-custom-collections)
- [Reference](#reference)

## Predefined collections

| Enum member | `api_id` / `catalog_id` | Processing level | Cloud coverage |
|---|---|---|---|
| `DataCollection.SENTINEL2_L1C` | `sentinel-2-l1c` | L1C (top-of-atmosphere) | ✅ |
| `DataCollection.SENTINEL2_L2A` | `sentinel-2-l2a` | L2A (bottom-of-atmosphere) | ✅ |

Both point at the CDSE Sentinel Hub service (`ServiceUrl.CDSE`).

```python
from sentinel_hub import DataCollection

DataCollection.get_available_collections()
# [<DataCollection.SENTINEL2_L1C: ...>, <DataCollection.SENTINEL2_L2A: ...>]
```

## Inspecting a collection

Every field of the underlying `DataCollectionDefinition` is available as an attribute:

```python
>>> s2 = DataCollection.SENTINEL2_L2A
>>> s2.api_id
'sentinel-2-l2a'
>>> s2.catalog_id
'sentinel-2-l2a'
>>> s2.service_url
'https://sh.dataspace.copernicus.eu'
>>> s2.processing_level
'L2A'
>>> s2.has_cloud_coverage
True
>>> [band.name for band in s2.bands]
['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B11', 'B12']
```

`api_id`, `catalog_id`, `bands` and `metabands` raise a `ValueError` if the
collection does not define them. `catalog_id` falls back to `api_id` when it is not set.

## Bands and metabands

Each band is a `Band(name, units, output_types)`. `units` and `output_types` are aligned
tuples; the first entry is the default.

**Sentinel-2 bands** – units `REFLECTANCE` (`float32`) or `DN` (`uint16`):

| Collection | Bands |
|---|---|
| L1C | `B01 B02 B03 B04 B05 B06 B07 B08 B8A B09 B10 B11 B12` |
| L2A | `B01 B02 B03 B04 B05 B06 B07 B08 B8A B09 B11 B12` (no `B10`) |

**Metabands:**

| Metaband | Unit | Output type | L1C | L2A |
|---|---|---|---|---|
| `sunAzimuthAngles`, `sunZenithAngles`, `viewAzimuthMean`, `viewZenithMean` | `DEGREES` | `float32` | ✅ | ✅ |
| `CLP` (cloud probability), `CLM` (cloud mask) | `DN` | `uint8` | ✅ | ✅ |
| `dataMask` | `DN` | `bool` | ✅ | ✅ |
| `AOT` (aerosol optical thickness) | `OPTICAL_DEPTH` / `DN` | `float32` / `uint16` | | ✅ |
| `SNW` (snow), `CLD` (cloud) probability | `PERCENT` | `uint8` | | ✅ |
| `SCL` (scene classification) | `DN` | `uint8` | | ✅ |

```python
from sentinel_hub.data_collections_bands import Unit

b04 = next(b for b in DataCollection.SENTINEL2_L2A.bands if b.name == "B04")
b04.units         # (Unit.REFLECTANCE, Unit.DN)
b04.output_types  # (numpy.float32, numpy.uint16)
```

Band specs are used by the [evalscript generator](evalscript.md) to pick units and
sample types.

## Defining custom collections

Use `DataCollection.define` for a brand-new collection, e.g. a BYOC collection:

```python
byoc = DataCollection.define(
    "MY_BYOC",
    api_id="byoc-1234abcd-...",
    catalog_id="byoc-1234abcd-...",
    service_url="https://sh.dataspace.copernicus.eu",
)
```

Or derive one from an existing collection with `define_from`, overriding only what changes:

```python
s2_custom = DataCollection.SENTINEL2_L2A.define_from(
    "SENTINEL2_L2A_CUSTOM", service_url="https://my-mirror.example.com"
)
```

Rules:

- Only `name` is required; parameters a use case doesn't need can be left out.
- Defining the exact same name + definition twice is a no-op (returns the existing member).
- Reusing a name for a different definition, or a definition under a different name,
  raises `ValueError`.
- Custom collections survive pickling, so they work with multiprocessing.

## Reference

`DataCollection.define(name, *, api_id, catalog_id, service_url, collection_type, sensor_type, processing_level, bands, metabands, has_cloud_coverage)`

| Parameter | Meaning |
|---|---|
| `api_id` | Identifier used in Process API `input.data[].type` |
| `catalog_id` | Identifier used in Catalog API searches |
| `service_url` | Base URL the collection is restricted to (overrides `SHConfig.sh_base_url` in requests) |
| `collection_type`, `sensor_type`, `processing_level` | Descriptive metadata |
| `bands`, `metabands` | Tuples of `Band` |
| `has_cloud_coverage` | Whether `maxcc` filtering makes sense |

| Method / property | Description |
|---|---|
| `DataCollection.define(...)` | Create a new collection |
| `collection.define_from(name, **params)` | Derive a new collection |
| `DataCollection.get_available_collections()` | List all members, including custom ones |
| `collection.value` | The underlying `DataCollectionDefinition` |
| `definition.derive(**params)` | New definition with overridden fields |
