# Process API

`SHRequest` wraps the Sentinel Hub [Process API](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html):
you describe *where* (bbox / geometry), *when* (time interval), *what* (data collection +
[evalscript](evalscript.md)) and *how big* (size or resolution), and get back processed
imagery as NumPy arrays, JSON or files on disk.

- [Minimal example](#minimal-example)
- [Anatomy of a request](#anatomy-of-a-request)
- [Input data](#input-data)
- [Area of interest](#area-of-interest)
- [Output: size, resolution and responses](#output-size-resolution-and-responses)
- [Multiple outputs](#multiple-outputs)
- [Getting and saving data](#getting-and-saving-data)
- [Advanced: raw payload helpers](#advanced-raw-payload-helpers)
- [Reference](#reference)

## Minimal example

```python
from sentinel_hub import CRS, BBox, DataCollection, MimeType, SHRequest

evalscript = """
//VERSION=3
function setup() {
  return { input: [{ bands: ["B02", "B03", "B04"] }], output: { bands: 3 } };
}
function evaluatePixel(s) {
  return [2.5 * s.B04, 2.5 * s.B03, 2.5 * s.B02];
}
"""

request = SHRequest(
    evalscript=evalscript,
    input_data=[
        SHRequest.input_data(
            DataCollection.SENTINEL2_L1C,
            time_interval=("2021-01-03", "2021-01-04"),
            maxcc=0.8,
        )
    ],
    responses=[SHRequest.output_response("default", MimeType.PNG)],
    bbox=BBox((46.16, -16.15, 46.51, -15.58), crs=CRS.WGS84),
    size=(512, 856),
)

image = request.get_data()[0]   # numpy.ndarray, shape (856, 512, 3), dtype uint8
```

## Anatomy of a request

```python
SHRequest(
    evalscript: str,
    input_data: list[dict],
    responses: list[dict],
    bbox: BBox | None = None,
    geometry: Geometry | None = None,
    size: tuple[int, int] | None = None,          # (width, height) in pixels
    resolution: tuple[float, float] | None = None, # (resx, resy) in CRS units
    *,
    data_folder: str | None = None,
    config: SHConfig | None = None,
)
```

The request body is built on construction and stored in `request.payload`, so you can
inspect exactly what will be sent:

```python
import json
print(json.dumps(request.payload, indent=2))
```

## Input data

`SHRequest.input_data(...)` builds one entry of `input.data`:

```python
SHRequest.input_data(
    DataCollection.SENTINEL2_L2A,
    identifier="s2",                         # needed for data fusion
    time_interval=("2024-06-01", "2024-06-30"),
    maxcc=0.3,                               # 0–1, sent as 30 (%)
    mosaicking_order=MosaickingOrder.LEAST_CC,
    upsampling=ResamplingType.BICUBIC,
    downsampling=ResamplingType.BILINEAR,
    other_args={"dataFilter": {"previewMode": "PREVIEW"}},
)
```

| Parameter | Sent as |
|---|---|
| `data_collection` | `type` (the collection's `api_id`) |
| `identifier` | `id` |
| `time_interval` | `dataFilter.timeRange.from` / `.to` (UTC, ISO 8601) |
| `maxcc` | `dataFilter.maxCloudCoverage` (must be in `[0, 1]`) |
| `mosaicking_order` | `dataFilter.mosaickingOrder` – `mostRecent`, `leastRecent`, `leastCC` |
| `upsampling` / `downsampling` | `processing.upsampling` / `.downsampling` – `NEAREST`, `BILINEAR`, `BICUBIC` |
| `other_args` | Deep-merged into the entry for any field not covered above |

For Sentinel-1 collections the collection's `swath_mode`, `polarization`, `resolution` and
`orbit_direction` are added to `dataFilter` automatically (see
[Data Collections](data-collections.md#sentinel-1-grd)). SAR processing options go through
`other_args`:

```python
SHRequest.input_data(
    DataCollection.SENTINEL1_IW_ASC,
    time_interval=("2024-06-01", "2024-06-30"),
    mosaicking_order=MosaickingOrder.MOST_RECENT,
    other_args={
        "processing": {
            "backCoeff": "GAMMA0_TERRAIN",
            "orthorectify": True,
            "demInstance": "COPERNICUS_30",
            "speckleFilter": {"type": "LEE", "windowSizeX": 3, "windowSizeY": 3},
        }
    },
)
# {"type": "sentinel-1-grd",
#  "dataFilter": {"timeRange": {...}, "mosaickingOrder": "mostRecent",
#                 "acquisitionMode": "IW", "polarization": "DV",
#                 "resolution": "HIGH", "orbitDirection": "ASCENDING"},
#  "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": true, ...}}
```

**Data fusion** – pass several inputs with distinct `identifier`s and reference them in the
evalscript (`input: [{datasource: "l1c", ...}, {datasource: "l2a", ...}]`):

```python
input_data = [
    SHRequest.input_data(DataCollection.SENTINEL2_L1C, identifier="l1c", time_interval=ti),
    SHRequest.input_data(DataCollection.SENTINEL2_L2A, identifier="l2a", time_interval=ti),
]
```

The service URL is chosen from the collections' `service_url`. If collections are restricted
to different services, `SHConfig.sh_base_url` breaks the tie; otherwise a `ValueError` is raised.

## Area of interest

Provide a `bbox`, a `geometry`, or both (they must share a CRS). With a geometry, pixels
outside the polygon are masked out.

```python
from sentinel_hub import Geometry

geometry = Geometry(
    {"type": "Polygon", "coordinates": [[[13.4, 45.9], [13.5, 45.9], [13.5, 45.95], [13.4, 45.9]]]},
    crs=CRS.WGS84,
)
SHRequest(..., geometry=geometry, size=(512, 512))
```

See [geometry.md](geometry.md) for everything about `BBox`, `Geometry` and `CRS`.

## Output: size, resolution and responses

Give **either** `size` (pixels) **or** `resolution` (CRS units, e.g. metres for UTM) – not both.

```python
from sentinel_hub import bbox_to_dimensions

size = bbox_to_dimensions(bbox, resolution=10)  # 10 m pixels -> (width, height)
SHRequest(..., bbox=bbox, size=size)

utm_bbox = bbox.transform(CRS.UTM_33N)
SHRequest(..., bbox=utm_bbox, resolution=(10, 10))
```

`SHRequest.output_response(identifier, format)` builds one entry of `output.responses`.
`identifier` must match an output `id` in the evalscript (`"default"` if there is only one).

| Format | Decoded to |
|---|---|
| `MimeType.TIFF` | `numpy.ndarray` (keeps `uint8` / `uint16` / `float32`) |
| `MimeType.PNG`, `MimeType.JPG` | `numpy.ndarray` (`uint8`) |
| `MimeType.JSON` | `dict` (e.g. `userdata`) |

## Multiple outputs

With more than one response, the API returns a TAR archive which is decoded into a
`dict` keyed by file name:

```python
evalscript = generate_evalscript(
    DataCollection.SENTINEL2_L2A,
    bands=["B04", "B08"],
    meta_bands=["dataMask"],
    merged_bands_output="bands",
)

request = SHRequest(
    evalscript=evalscript,
    input_data=[SHRequest.input_data(DataCollection.SENTINEL2_L2A, time_interval=ti)],
    responses=[
        SHRequest.output_response("bands", MimeType.TIFF),
        SHRequest.output_response("dataMask", MimeType.TIFF),
        SHRequest.output_response("userdata", MimeType.JSON),
    ],
    bbox=bbox,
    size=size,
)
data = request.get_data()[0]
data["bands.tif"].shape    # (h, w, 2)
data["dataMask.tif"]       # (h, w)
data["userdata.json"]      # {"norm_factor": ...} – multiply DN values by this to get reflectance
```

## Getting and saving data

```python
data = request.get_data()                       # download & decode
data = request.get_data(save_data=True)         # also save to data_folder
request.save_data()                             # only save, return nothing
```

| Option (`get_data` / `save_data`) | Description |
|---|---|
| `save_data` | Save responses to `data_folder` (`get_data` only) |
| `redownload` | Ignore cached files and download again |
| `decode_data` | `False` returns raw `DownloadResponse` objects (`get_data` only) |
| `data_filter` | List of indices into the download list |
| `max_threads` | Threads used for parallel downloads |
| `raise_download_errors` | Raise on failure (default `True` for `get_data`, `False` for `save_data`) |
| `show_progress` | Show a `tqdm` progress bar |

**Caching.** With `data_folder` set, each request is stored under
`<data_folder>/<md5-hash>/request.json` + `response.<ext>`. The next call with the same
URL and payload reads from disk instead of spending processing units.

```python
request = SHRequest(..., data_folder="./data")
request.get_data(save_data=True)  # downloads
request.get_data()                # reads ./data/<hash>/response.tiff
request.get_filename_list()       # ['<hash>/response.tiff']
```

Other helpers: `get_download_list()`, `get_url_list()`, `is_valid_request()`.

## Advanced: raw payload helpers

All builders are static methods, so you can assemble a payload by hand:

| Method | Builds |
|---|---|
| `SHRequest.input_data(...)` | One `input.data[]` entry |
| `SHRequest.bounds(bbox=None, geometry=None, other_args=None)` | `input.bounds` |
| `SHRequest.output_response(identifier, response_format, other_args=None)` | One `output.responses[]` entry |
| `SHRequest.output(responses, size=None, resolution=None, other_args=None)` | `output` |
| `SHRequest.body(request_bounds, request_data, evalscript, request_output=None, other_args=None)` | Whole request body |

Every `other_args` dict is deep-merged, so you can set any Process API field the helpers
don't expose (e.g. `output.upsampling`, `input.bounds.properties`).

## Reference

- Process API: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html>
- API reference: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>
- Data fusion: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DataFusion.html>
