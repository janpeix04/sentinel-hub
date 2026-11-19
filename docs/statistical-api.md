# Statistical API

`SHStatistical` wraps the Sentinel Hub [Statistical API](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical.html):
instead of downloading images, you get statistics (min, max, mean, standard deviation,
percentiles and histograms) computed on the service for an area of interest, split into
aggregation intervals (e.g. one value per day, per 10 days or per month).

- [Minimal example](#minimal-example)
- [Anatomy of a request](#anatomy-of-a-request)
- [Evalscript requirements](#evalscript-requirements)
- [Aggregation](#aggregation)
- [Calculations: percentiles and histograms](#calculations-percentiles-and-histograms)
- [Reading the response](#reading-the-response)
- [Getting and saving data](#getting-and-saving-data)
- [Advanced: raw payload helpers](#advanced-raw-payload-helpers)
- [Reference](#reference)

## Minimal example

```python
from sentinel_hub import CRS, BBox, DataCollection, SHStatistical

evalscript = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(s) {
  return {
    ndvi: [(s.B08 - s.B04) / (s.B08 + s.B04)],
    dataMask: [s.dataMask]
  };
}
"""

request = SHStatistical(
    aggregation=SHStatistical.aggregation(
        evalscript=evalscript,
        time_interval=("2024-06-01", "2024-08-31"),
        aggregation_interval="P10D",
        resolution=(10, 10),
    ),
    input_data=[SHStatistical.input_data(DataCollection.SENTINEL2_L2A, maxcc=0.3)],
    bbox=BBox((414315, 4958219, 414859, 4958819), crs=CRS("32633")),
)

result = request.get_data()[0]  # dict, the decoded JSON response
for interval in result["data"]:
    stats = interval["outputs"]["ndvi"]["bands"]["B0"]["stats"]
    print(interval["interval"]["from"], stats["mean"])
```

## Anatomy of a request

```python
SHStatistical(
    aggregation: dict,                      # see SHStatistical.aggregation(...)
    input_data: list[dict],                 # see SHStatistical.input_data(...)
    bbox: BBox | None = None,
    geometry: Geometry | None = None,
    calculations: dict | None = None,       # percentiles / histograms per output and band
    *,
    data_folder: str | None = None,
    config: SHConfig | None = None,
)
```

- **`input_data`** and **`bbox` / `geometry`** work exactly as in the Process API – see
  [Input data](process-api.md#input-data) and [Area of interest](process-api.md#area-of-interest).
  The time range is **not** set on the input data but in the aggregation.
  With a `geometry`, only pixels inside the polygon are counted.
- **`aggregation`** holds the evalscript, time range, aggregation interval and output resolution.
- **`calculations`** is optional; without it you get the basic statistics only.

The request is sent to `{config.sh_base_url}/statistics/v1`. The body is built on
construction and stored in `request.payload`:

```python
import json

print(json.dumps(request.payload, indent=2))
```

## Evalscript requirements

- `evaluatePixel()` **must** return a `dataMask` output. Pixels with `dataMask == 0` are
  excluded from the statistics; no-data pixels are **not** excluded automatically, so pass
  the input `dataMask` through (or combine it with your own mask, e.g. to drop water or clouds).
- The default output `sampleType` is `FLOAT32`.
- Each output can have its own mask: name it `dataMask` inside the output's `bands` array,
  e.g. `output: [{ id: "ndvi", bands: ["ndvi", "dataMask"] }]`.
- Data is mosaicked per aggregation interval before statistics are computed. For temporal
  statistics (e.g. maximum NDVI per month) use `mosaicking: "ORBIT"` or `"TILE"` in `setup()`
  and compute the value in the evalscript.

See [evalscript.md](evalscript.md) and the
[Evalscript reference](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Evalscript.html).

## Aggregation

`SHStatistical.aggregation(...)` builds the `aggregation` part of the request:

```python
from sentinel_hub import LastIntervalBehavior

SHStatistical.aggregation(
    evalscript=evalscript,
    time_interval=("2024-06-01", "2024-08-31"),
    aggregation_interval="P10D",  # ISO 8601 duration
    last_interval_behavior=LastIntervalBehavior.SHORTEN,
    resolution=(10, 10),  # or size=(width, height)
    other_args={"aggregationInterval": {"of": "P1M"}},  # deep-merged
)
```

| Parameter | Sent as |
|---|---|
| `evalscript` | `evalscript` (must be a `str`, otherwise `TypeError`) |
| `time_interval` | `timeRange.from` / `.to` (UTC, ISO 8601). A plain date as the end is expanded to `23:59:59` |
| `aggregation_interval` | `aggregationInterval.of` – e.g. `"P1D"`, `"P10D"`, `"P1M"`; at least one day |
| `last_interval_behavior` | `aggregationInterval.lastIntervalBehavior` – see below |
| `size` | `width` / `height` in pixels |
| `resolution` | `resx` / `resy` in CRS units (metres for UTM) |
| `other_args` | Deep-merged into the aggregation for any field not covered above |

Give **either** `size` **or** `resolution`, not both (`ValueError`). As with the Process API,
`resolution` is in the units of the request CRS, so use a UTM `BBox` for metres.

**Last interval.** If the time range is not divisible by the aggregation interval:

| `LastIntervalBehavior` | Effect |
|---|---|
| `SKIP` | The last, shorter interval is dropped (service default) |
| `SHORTEN` | The last interval ends at the end of the time range |
| `EXTEND` | The last interval is extended past the time range so all intervals are equally long |

Plain strings are accepted too and are case-insensitive (`"shorten"`).

> **Tip:** a date-only end such as `"2024-06-30"` becomes `2024-06-30T23:59:59Z`, so with
> `P10D` from `2024-06-01` the last interval (`06-21` → `07-01`) does not fit and is
> **skipped** by default. Use `SHORTEN` if you need data up to the very end of the range.

## Calculations: percentiles and histograms

`calculations` is a plain dict keyed by **output id** (or `"default"` for all outputs). Inside,
`statistics` and `histograms` are keyed by **band name** (or `"default"` for all bands):

```python
calculations = {
    "default": {
        "statistics": {"default": {"percentiles": {"k": [10, 50, 90]}}},
        "histograms": {"default": {"nBins": 5, "lowEdge": 0.0, "highEdge": 0.3}},
    },
    "ndvi": {
        "histograms": {"B0": {"binWidth": 0.1, "lowEdge": -1.0, "highEdge": 1.0}},
    },
}

SHStatistical(..., calculations=calculations)
```

Histogram options – use one of:

| Key | Meaning |
|---|---|
| `nBins` | Number of equally wide bins between `lowEdge` and `highEdge` |
| `binWidth` | Width of each bin |
| `bins` | Explicit list of bin edges, e.g. `[0, 0.2, 0.5, 1]` |

`lowEdge` / `highEdge` are optional and default to the band's `min` / `max`.

## Reading the response

`get_data()` returns a list with one decoded JSON dict per request:

```python
{
    "status": "OK",
    "data": [
        {
            "interval": {"from": "2020-07-04T00:00:00Z", "to": "2020-07-05T00:00:00Z"},
            "outputs": {
                "output_B04": {
                    "bands": {
                        "B0": {
                            "stats": {
                                "min": 0.0874,
                                "max": 0.3164,
                                "mean": 0.1211,
                                "stDev": 0.0332,
                                "sampleCount": 3240,
                                "noDataCount": 0,
                                "percentiles": {
                                    "33.0": 0.104,
                                    "50.0": 0.1104,
                                    "75.0": 0.1252,
                                    "90.0": 0.165,
                                },
                            },
                            "histogram": {
                                "bins": [
                                    {"lowEdge": 0.0, "highEdge": 0.06, "count": 0},
                                    ...,
                                ],
                                "overflowCount": 4,
                                "underflowCount": 0,
                            },
                        }
                    }
                }
            },
        }
    ],
}
```

Things to know:

- There is one entry in `data` per aggregation interval **that has data**; intervals without
  any acquisition are omitted.
- Bands are named `B0`, `B1`, … unless the evalscript gives them names
  (`bands: ["red", "nir"]`).
- `sampleCount` counts all pixels, `noDataCount` those with `dataMask == 0`.
- If processing of a single interval fails, the service still returns `"status": "OK"` and
  puts an `error` object in that interval instead of `outputs` – check for it:

```python
for interval in result["data"]:
    if "error" in interval:
        print(interval["interval"], interval["error"])
```

## Getting and saving data

`SHStatistical` shares `get_data()`, `save_data()`, `data_folder` caching and the other
helpers with `SHRequest` – see [Getting and saving data](process-api.md#getting-and-saving-data).
Responses are saved as `<data_folder>/<md5-hash>/response.json`.

To compute statistics for many areas, build one request per area and download them in
parallel with a single client:

```python
from sentinel_hub import SHDownloadClient

requests = [SHStatistical(..., bbox=bbox) for bbox in bboxes]
download_list = [r.download_list[0] for r in requests]
results = SHDownloadClient(config=config).download(download_list, max_threads=5)
```

## Advanced: raw payload helpers

| Method | Builds |
|---|---|
| `SHStatistical.input_data(...)` | One `input.data[]` entry (same as `SHRequest.input_data`) |
| `SHStatistical.bounds(bbox=None, geometry=None, other_args=None)` | `input.bounds` |
| `SHStatistical.aggregation(evalscript, time_interval, aggregation_interval, ...)` | `aggregation` |
| `SHStatistical.body(request_bounds, request_data, aggregation, calculations=None, other_args=None)` | Whole request body |

## Reference

- Statistical API: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical.html>
- Examples: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical/Examples.html>
- API reference: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html#tag/statistical>
