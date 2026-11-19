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
| `DataCollection.SENTINEL3_OLCI` | `sentinel-3-olci` | L1B (top-of-atmosphere, 300 m) | |
| `DataCollection.SENTINEL3_SLSTR` | `sentinel-3-slstr` | L1B (top-of-atmosphere, 500 m / 1 km) | ✅ |
| `DataCollection.SENTINEL3_OLCI_L2` | `sentinel-3-olci-l2` | L2 (land and water products, 300 m) | ✅ |
| `DataCollection.SENTINEL3_SLSTR_L2` | `sentinel-3-slstr-l2` | L2 (land surface temperature, 1 km) | ✅ |
| `DataCollection.SENTINEL3_SYNERGY_L2` | `sentinel-3-synergy-l2` | L2 (OLCI + SLSTR surface reflectance) | |
| `DataCollection.SENTINEL5P` | `sentinel-5p-l2` | L2 (atmospheric trace gases, aerosols, clouds) | |

All point at the CDSE Sentinel Hub service (`ServiceUrl.CDSE`).

```python
from sentinel_hub import DataCollection

DataCollection.get_available_collections()
# [<DataCollection.SENTINEL2_L1C: ...>, <DataCollection.SENTINEL2_L2A: ...>,
#  <DataCollection.SENTINEL1: ...>, <DataCollection.SENTINEL1_IW: ...>, ...,
#  <DataCollection.SENTINEL3_OLCI: ...>, <DataCollection.SENTINEL3_SLSTR: ...>, ...,
#  <DataCollection.SENTINEL5P: ...>]
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

### Sentinel-3

Sentinel-3 has Level-1B collections (top-of-atmosphere values, no atmospheric correction) and
Level-2 collections (derived geophysical products).

**Level-1B**

- **OLCI** ([CDSE S3OLCI docs](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S3OLCI.html))
  is a 21-band ocean and land colour imager at 300 m. It has no cloud-cover filter, so `maxcc` does
  not apply.
- **SLSTR** ([CDSE S3SLSTR docs](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S3SLSTR.html))
  is a radiometer with 6 optical bands at 500 m and 5 thermal bands at 1 km. It supports `maxcc`
  and `MosaickingOrder.LEAST_CC`.

SLSTR acquires at night on ascending passes, so the optical bands are usually black there; thermal
bands work on both. To restrict SLSTR to daytime (descending) passes, set `orbit_direction`; to use
the oblique (rear) view instead of nadir, pass `view` through `other_args`:

```python
from sentinel_hub import DataCollection, SHRequest
from sentinel_hub.data_collections import OrbitDirection

slstr_day = DataCollection.SENTINEL3_SLSTR.define_from(
    "SENTINEL3_SLSTR_DES", orbit_direction=OrbitDirection.DESCENDING
)
SHRequest.input_data(
    slstr_day, maxcc=0.2, other_args={"dataFilter": {"view": "OBLIQUE"}}
)
```

**Level-2**

- **OLCI L2** ([CDSE S3OLCIL2 docs](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S3OLCIL2.html))
  has land products (FAPAR, OTCI chlorophyll index, rectified reflectance) and water products
  (chlorophyll, suspended matter, PAR, aerosols), plus surface reflectance `B01`–`B21`.
  `B13`, `B14`, `B15`, `B19` and `B20` are not available. It supports `maxcc` and
  `MosaickingOrder.LEAST_CC`.
- **SLSTR L2** ([CDSE S3SLSTRL2 docs](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S3SLSTRL2.html))
  has land surface temperature (`LST`) with its uncertainty, `NDVI`, and the cloud and quality
  bitmasks. It supports `maxcc`, `MosaickingOrder.LEAST_CC` and `orbit_direction`. LST comes
  from thermal bands, so both day and night passes are usable.
- **SYN L2** ([CDSE S3SYNL2 docs](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S3SYNL2.html))
  combines OLCI and SLSTR into surface reflectance (`SY_2_SYN`). The same collection also
  serves the 1 km vegetation products: 10-day composites (`*_V10`) and 1-day composites
  (`*_VG1`). You pick the product by the band names in your evalscript. There is no
  cloud-cover filter.

### Sentinel-5P L2

TROPOMI Level-2 products: trace-gas columns, aerosol indices and cloud properties
([CDSE S5PL2 docs](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S5PL2.html)).
There is no cloud-cover filter, so `maxcc` does not apply. Pass these options through
`other_args`:

- **`timeliness`** (`dataFilter`): `NRTI` (near real-time), `OFFL` (offline) or `RPRO`
  (reprocessed). If unset, the service prefers `RPRO`, then `OFFL`, then `NRTI`.
- **`minQa`** (`processing`): minimum `qa_value` in percent (0–100). Pixels below it are
  masked out. The default is 75 for `NO2` and 50 for the other products.

```python
SHRequest.input_data(
    DataCollection.SENTINEL5P,
    time_interval=("2024-06-01", "2024-06-01"),
    other_args={"dataFilter": {"timeliness": "OFFL"}, "processing": {"minQa": 75}},
)
```

With the default simple mosaicking, the service only uses data from the 24 hours before the
end of `time_interval`.

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

**Sentinel-3 L1B bands** – all `float32`:

| Collection | Bands | Units (default first) |
|---|---|---|
| OLCI | `B01` … `B21` | `REFLECTANCE` / `RADIANCE` |
| SLSTR | `S1 S2 S3 S4 S5 S6` (optical) | `REFLECTANCE` / `RADIANCE` |
| SLSTR | `S7 S8 S9 F1 F2` (thermal) | `BRIGHTNESS_TEMPERATURE` (kelvin) |

**Sentinel-3 L1B metabands:**

| Metaband | Unit | Output type | OLCI | SLSTR |
|---|---|---|---|---|
| `SAA`, `SZA`, `VAA`, `VZA` (sun / view azimuth and zenith) | `DEGREES` | `float32` | ✅ | |
| `HUMIDITY` | `PERCENT` | `float32` | ✅ | |
| `SEA_LEVEL_PRESSURE` | `HECTOPASCALS` | `float32` | ✅ | |
| `TOTAL_COLUMN_OZONE`, `TOTAL_COLUMN_WATER_VAPOUR` | `KG_M2` | `float32` | ✅ | |
| `QUALITY_FLAGS` (bit-packed) | `DN` | `uint32` | ✅ | |
| `dataMask` | `DN` | `bool` | ✅ | ✅ |

**Sentinel-3 L2 bands** – all `float32`, one unit each:

| Collection | Bands | Unit |
|---|---|---|
| OLCI L2 | `GIFAPAR` (green FAPAR) | `FRACTION` |
| OLCI L2 | `IWV_L`, `IWV_W` (water vapour, land / water) | `KG_M2` |
| OLCI L2 | `OTCI` (terrestrial chlorophyll index) | `INDEX` |
| OLCI L2 | `RC681`, `RC865` (rectified reflectance), `B01`–`B12`, `B16`–`B18`, `B21` | `REFLECTANCE` |
| OLCI L2 | `CHL_OC4ME`, `CHL_NN` (algal pigment, log10 mg/m³) | `LOG10_MILLIGRAMS_M3` |
| OLCI L2 | `TSM_NN` (total suspended matter, log10 g/m³) | `LOG10_GRAMS_M2` |
| OLCI L2 | `PAR` (photosynthetically active radiation) | `MICROEINSTEINS_S_M2` |
| OLCI L2 | `KD490_M07`, `ADG443_NN` (attenuation / CDM absorption, log10 1/m) | `LOG10_1_M` |
| OLCI L2 | `A865` (aerosol Ångström exponent) | `ANGSTROM_EXPONENT` |
| OLCI L2 | `T865` (aerosol optical thickness) | `OPTICAL_DEPTH` |
| SLSTR L2 | `LST`, `LST_uncertainty` | `KELVIN` |
| SLSTR L2 | `NDVI` | `INDEX` |
| SYN L2 | `B01`–`B12`, `B16`–`B18`, `B21`, `S1`–`S3`, `S5`, `S6` | `REFLECTANCE` |
| SYN L2 | `B0`, `B2`, `B3`, `MIR` (`_V10` / `_VG1`) | `REFLECTANCE` |
| SYN L2 | `NDVI` (`_V10` / `_VG1`), `TOA_NDVI_VG1` | `INDEX` |
| SYN L2 | `OG` (ozone, `_V10` / `_VG1`) | `ATMCM` |
| SYN L2 | `WVG` (water vapour, `_V10` / `_VG1`) | `GRAMS_CM2` |
| SYN L2 | `AG` (aerosol optical thickness, `_V10` / `_VG1`) | `OPTICAL_DEPTH` |

`LOG10_GRAMS_M2` is the unit name the API uses for `TSM_NN`, even though the quantity is
per m³.

**Sentinel-3 L2 metabands:**

| Metaband | Unit | Output type | Collection |
|---|---|---|---|
| `LQSF` (land quality and science flags) | `DN` | `uint32` | OLCI L2 |
| `CLOUD`, `CONFIDENCE` (bitmasks) | `DN` | `uint16` | SLSTR L2 |
| `BAYES`, `POINTING` (bitmasks) | `DN` | `uint8` | SLSTR L2 |
| `SAA`, `SZA`, `VAA`, `VZA` (`_V10` / `_VG1`) | `DEGREES` | `float32` | SYN L2 |
| `dataMask` | `DN` | `bool` | all |

The Process API has no 32-bit integer output type, so `generate_evalscript` rejects
`QUALITY_FLAGS` and `LQSF`. Decode them in a custom evalscript instead (for
`QUALITY_FLAGS`, use `decodeS3OLCIQualityFlags`).

**Sentinel-5P bands** – all `float32`, one unit each:

| Bands | Unit | Quantity |
|---|---|---|
| `CO`, `HCHO`, `NO2`, `O3`, `SO2` | `MOL_M2` | Column density (mol/m²); `HCHO` and `NO2` are tropospheric |
| `CH4` | `PPB` | Column-averaged dry-air mixing ratio |
| `AER_AI_340_380`, `AER_AI_354_388` | `INDEX` | UV aerosol index |
| `CLOUD_BASE_PRESSURE`, `CLOUD_TOP_PRESSURE` | `PASCALS` | Cloud pressure |
| `CLOUD_BASE_HEIGHT`, `CLOUD_TOP_HEIGHT` | `METERS` | Cloud height |
| `CLOUD_OPTICAL_THICKNESS` | `OPTICAL_DEPTH` | Cloud optical thickness |
| `CLOUD_FRACTION` | `FRACTION` | Effective radiometric cloud fraction |

The only metaband is `dataMask` (`DN`, `bool`). Use it to tell no-data pixels apart from real
zero values.

```python
from sentinel_hub.data_collections_bands import Unit

b04 = next(b for b in DataCollection.SENTINEL2_L2A.bands if b.name == "B04")
b04.units  # (Unit.REFLECTANCE, Unit.DN)
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
| `orbit_direction` | `dataFilter.orbitDirection` – `ASCENDING`, `DESCENDING`; `BOTH` adds no filter (see `OrbitDirection`). Supported by Sentinel-1, SLSTR and SLSTR L2 |
| `bands`, `metabands` | Tuples of `Band` |
| `has_cloud_coverage` | Whether `maxcc` filtering makes sense |

`swath_mode`, `polarization` and `resolution` are only sent when `collection_type` is
Sentinel-1 (`collection.is_sentinel1`). `orbit_direction` is sent for any collection that sets it.

| Method / property | Description |
|---|---|
| `DataCollection.define(...)` | Create a new collection |
| `collection.define_from(name, **params)` | Derive a new collection |
| `collection.is_sentinel1` | `True` for Sentinel-1 collections |
| `collection.is_sentinel3` | `True` for Sentinel-3 collections |
| `collection.is_sentinel5p` | `True` for Sentinel-5P collections |
| `collection.contains_orbit_direction(direction)` | Whether the collection includes acquisitions in that orbit direction |
| `DataCollection.get_available_collections()` | List all members, including custom ones |
| `collection.value` | The underlying `DataCollectionDefinition` |
| `definition.derive(**params)` | New definition with overridden fields |
