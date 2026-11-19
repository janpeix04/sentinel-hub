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
| `DataCollection.SENTINEL1` and variants (see below) | `sentinel-1-grd` | GRD (Ground Range Detected SAR) | |

All point at the CDSE Sentinel Hub service (`ServiceUrl.CDSE`).

```python
from sentinel_hub import DataCollection

DataCollection.get_available_collections()
# [<DataCollection.SENTINEL2_L1C: ...>, <DataCollection.SENTINEL2_L2A: ...>,
#  <DataCollection.SENTINEL1: ...>, <DataCollection.SENTINEL1_IW: ...>, ...]
```

### Sentinel-1 GRD

All Sentinel-1 collections share the `sentinel-1-grd` identifier. The variants differ only in
the filters they add to the request's `dataFilter`, so the service returns just the matching
acquisitions ([CDSE S1GRD docs](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html)):

| Enum member | `acquisitionMode` | `polarization` | `resolution` | `orbitDirection` | Bands |
|---|---|---|---|---|---|
| `SENTINEL1` | – | – | – | – (both) | `VV HH VH HV` |
| `SENTINEL1_IW` | `IW` | `DV` | `HIGH` | – (both) | `VV VH` |
| `SENTINEL1_IW_ASC` / `_DES` | `IW` | `DV` | `HIGH` | `ASCENDING` / `DESCENDING` | `VV VH` |
| `SENTINEL1_EW` | `EW` | `DH` | `MEDIUM` | – (both) | `HH HV` |
| `SENTINEL1_EW_ASC` / `_DES` | `EW` | `DH` | `MEDIUM` | `ASCENDING` / `DESCENDING` | `HH HV` |
| `SENTINEL1_EW_SH` | `EW` | `SH` | `MEDIUM` | – (both) | `HH` |
| `SENTINEL1_EW_SH_ASC` / `_DES` | `EW` | `SH` | `MEDIUM` | `ASCENDING` / `DESCENDING` | `HH` |

`SENTINEL1` applies no filters and lists all four polarisation bands. Only the bands present
in a product can actually be returned (an IW `DV` product has `VV` and `VH`, not `HH`), so
prefer a variant when you know the mode you need. Most land imagery is IW `DV`; EW is
mostly used over polar regions and sea ice.

For other combinations, such as Stripmap mode or a single polarisation, derive a collection:

```python
s1_sm = DataCollection.SENTINEL1.define_from(
    "SENTINEL1_SM_VV", swath_mode="SM", polarization="SV", resolution="HIGH"
)
```

Processing options such as `backCoeff`, `orthorectify`, `demInstance` or `speckleFilter`
are set per request, not on the collection. Pass them through `other_args`
(see [Process API](process-api.md#input-data)).

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

**Sentinel-1 bands** – `VV`, `HH`, `VH`, `HV` in `LINEAR_POWER` (`float32`); typical range
0–0.5, convert to decibels (`10 * log10(x)`) for visualisation. The available subset depends
on the collection variant (see [Sentinel-1 GRD](#sentinel-1-grd)).

**Sentinel-1 metabands:**

| Metaband | Unit | Output type | Requires |
|---|---|---|---|
| `localIncidenceAngle` | `DEGREES` | `float32` | `orthorectify: true` |
| `scatteringArea` | `DN` | `float32` | `backCoeff: GAMMA0_TERRAIN` |
| `shadowMask` | `DN` | `uint8` | `backCoeff: GAMMA0_TERRAIN` |
| `dataMask` | `DN` | `bool` | – |

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

`DataCollection.define(name, *, api_id, catalog_id, service_url, collection_type, sensor_type, processing_level, swath_mode, polarization, resolution, orbit_direction, bands, metabands, has_cloud_coverage)`

| Parameter | Meaning |
|---|---|
| `api_id` | Identifier used in Process API `input.data[].type` |
| `catalog_id` | Identifier used in Catalog API searches |
| `service_url` | Base URL the collection is restricted to (overrides `SHConfig.sh_base_url` in requests) |
| `collection_type`, `sensor_type`, `processing_level` | Descriptive metadata |
| `swath_mode` | Sentinel-1 only: `dataFilter.acquisitionMode` – `IW`, `EW`, `SM`, `WV` |
| `polarization` | Sentinel-1 only: `dataFilter.polarization` – `DV`, `DH`, `SV`, `SH`, `HH`, `HV`, `VV`, `VH` |
| `resolution` | Sentinel-1 only: `dataFilter.resolution` – `HIGH`, `MEDIUM` |
| `orbit_direction` | Sentinel-1 only: `dataFilter.orbitDirection` – `ASCENDING`, `DESCENDING`; `BOTH` adds no filter (see `OrbitDirection`) |
| `bands`, `metabands` | Tuples of `Band` |
| `has_cloud_coverage` | Whether `maxcc` filtering makes sense |

The Sentinel-1 filters are only sent when `collection_type` is Sentinel-1 (`collection.is_sentinel1`).

| Method / property | Description |
|---|---|
| `DataCollection.define(...)` | Create a new collection |
| `collection.define_from(name, **params)` | Derive a new collection |
| `collection.is_sentinel1` | `True` for Sentinel-1 collections |
| `collection.contains_orbit_direction(direction)` | Whether the collection includes acquisitions in that orbit direction |
| `DataCollection.get_available_collections()` | List all members, including custom ones |
| `collection.value` | The underlying `DataCollectionDefinition` |
| `definition.derive(**params)` | New definition with overridden fields |
