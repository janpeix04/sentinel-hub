# Evalscripts

An [evalscript](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Evalscript.html)
is a small JavaScript program that tells Sentinel Hub which bands to read and how to turn
them into output pixels. Every [Process API](process-api.md) request needs one.

You can write evalscripts by hand, or let `generate_evalscript` build one from a list of
band names.

- [Generating an evalscript](#generating-an-evalscript)
- [Merged vs. separate outputs](#merged-vs-separate-outputs)
- [Units and sample types](#units-and-sample-types)
- [Using it in a request](#using-it-in-a-request)
- [Reference](#reference)

## Generating an evalscript

```python
from sentinel_hub import DataCollection, generate_evalscript

evalscript = generate_evalscript(
    DataCollection.SENTINEL2_L2A,
    bands=["B02", "B03", "B04"],
    meta_bands=["dataMask"],
)
print(evalscript)
```

```javascript
//VERSION=3

function setup() {
    return {
        input: [{
            bands: ["B02", "B03", "B04", "dataMask"],
            units: ["DN", "DN", "DN", "DN"]
        }],
        output: [{id: "B02", bands: 1, sampleType: "UINT16"}, {id: "B03", bands: 1, sampleType: "UINT16"}, {id: "B04", bands: 1, sampleType: "UINT16"}, {id: "dataMask", bands: 1, sampleType: "UINT8"}]
    }
}

function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
    outputMetadata.userData = {
        "norm_factor":  inputMetadata.normalizationFactor
    }
}

function evaluatePixel(sample) {
    return { B02: [sample.B02], B03: [sample.B03], B04: [sample.B04], dataMask: [sample.dataMask] };
}
```

Defaults:

- `bands=None` → all bands of the collection (see [data-collections.md](data-collections.md#bands-and-metabands)).
- `meta_bands=None` → no metabands.
- Unknown band names raise a `ValueError` that lists the available bands and metabands.
- Generated scripts use `SIMPLE` mosaicking (one sample per pixel).

## Merged vs. separate outputs

By default every band becomes its **own output** (one response per band). Set
`merged_bands_output` to stack all `bands` into a **single multi-band output**; metabands
still get their own outputs.

```python
generate_evalscript(
    DataCollection.SENTINEL2_L2A,
    bands=["B04", "B03", "B02"],
    meta_bands=["dataMask"],
    merged_bands_output="bands",
)
# output: [{id: "bands", bands: 3, sampleType: "UINT16"}, {id: "dataMask", bands: 1, sampleType: "UINT8"}]
```

The merged output uses the sample type of the first band, so merge bands of the same type.

## Units and sample types

Each band may support several units. `prioritize_dn=True` (default) picks `DN` whenever the
band supports it; otherwise the band's first (default) unit is used. The output
`sampleType` follows from the band's output type:

| Band output type | `sampleType` |
|---|---|
| `bool` | `UINT8` |
| `numpy.uint8` | `UINT8` |
| `numpy.uint16` | `UINT16` |
| `numpy.float32` | `FLOAT32` |

| `prioritize_dn` | Sentinel-2 `B04` | `sunZenithAngles` |
|---|---|---|
| `True` | `DN` → `UINT16` | `DEGREES` → `FLOAT32` |
| `False` | `REFLECTANCE` → `FLOAT32` | `DEGREES` → `FLOAT32` |

The script also writes `norm_factor` into `userdata`. Request a `userdata` JSON response to
get it, and multiply `DN` values by it to obtain reflectance.

## Using it in a request

The response identifiers must match the output IDs in the script:

```python
from sentinel_hub import MimeType, SHRequest

request = SHRequest(
    evalscript=evalscript,  # merged_bands_output="bands" + meta_bands=["dataMask"]
    input_data=[SHRequest.input_data(DataCollection.SENTINEL2_L2A, time_interval=("2024-06-01", "2024-06-30"))],
    responses=[
        SHRequest.output_response("bands", MimeType.TIFF),
        SHRequest.output_response("dataMask", MimeType.TIFF),
        SHRequest.output_response("userdata", MimeType.JSON),
    ],
    bbox=bbox,
    size=(512, 512),
)
tar = request.get_data()[0]
reflectance = tar["bands.tif"] * tar["userdata.json"]["norm_factor"]
```

## Reference

```python
generate_evalscript(
    data_collection: DataCollection,
    bands: list[str] | None = None,
    meta_bands: list[str] | None = None,
    merged_bands_output: str | None = None,
    prioritize_dn: bool = True,
) -> str
```

| Parameter | Description |
|---|---|
| `data_collection` | Collection whose band specs are used |
| `bands` | Band names; `None` = all bands |
| `meta_bands` | Metaband names (e.g. `dataMask`, `SCL`, `CLM`) |
| `merged_bands_output` | If set, ID of a single output holding all `bands` |
| `prioritize_dn` | Prefer `DN` units when available |

Helper: `sentinel_hub.evalscript.parse_data_collection_bands(data_collection, bands)` returns
the `Band` objects for the given names, validating that they exist.
