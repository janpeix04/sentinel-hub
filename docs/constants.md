# Constants

Enums and constants from `sentinel_hub.constants`. `CRS` is covered in
[geometry.md](geometry.md#crs).

- [MimeType](#mimetype)
- [ResamplingType](#resamplingtype)
- [MosaickingOrder](#mosaickingorder)
- [ServiceUrl](#serviceurl)
- [SHConstants](#shconstants)
- [RequestType](#requesttype)

## MimeType

File / response formats.

| Member | Extension | | Member | Extension |
|---|---|---|---|---|
| `TIFF` | `tiff` | | `TAR` | `tar` |
| `PNG` | `png` | | `ZIP` | `zip` |
| `JPG` | `jpg` | | `GZIP` | `gz` |
| `JP2` | `jp2` | | `HDF` | `hdf` |
| `JSON` | `json` | | `NPY` | `npy` |
| `CSV` | `csv` | | `PICKLE` | `pkl` |
| `XML` | `xml` | | `GPKG` | `gpkg` |
| `GML` | `gml` | | `GEOJSON` | `geojson` |
| `TXT` | `txt` | | `SAFE` | `safe` |
| `RAW` | `raw` | | | |

```python
from sentinel_hub import MimeType

MimeType.TIFF.extension                 # 'tiff'
MimeType.TIFF.get_string()              # 'image/tiff'
MimeType.from_string("image/png")       # MimeType.PNG  (also 'tif', 'jpeg', 'h5', ...)
MimeType.has_value("jpg")               # True
MimeType.PNG.is_image_format()          # True  (TIFF, PNG, JPG, JP2)
```

## ResamplingType

Used for `upsampling` / `downsampling` in [`SHRequest.input_data`](process-api.md#input-data).
Case-insensitive: `ResamplingType("bilinear")` works.

| Member | Value |
|---|---|
| `NEAREST` | `"NEAREST"` |
| `BILINEAR` | `"BILINEAR"` |
| `BICUBIC` | `"BICUBIC"` |

## MosaickingOrder

Which scene wins when several overlap, used in [`SHRequest.input_data`](process-api.md#input-data).

| Member | Value | Meaning |
|---|---|---|
| `MOST_RECENT` | `"mostRecent"` | Newest acquisition on top (service default) |
| `LEAST_RECENT` | `"leastRecent"` | Oldest acquisition on top |
| `LEAST_CC` | `"leastCC"` | Least cloudy acquisition on top |

## ServiceUrl

| Attribute | Value |
|---|---|
| `ServiceUrl.CDSE` | `https://sh.dataspace.copernicus.eu` |
| `ServiceUrl.CDSE_TOKEN` | `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token` |

These are the defaults of `SHConfig.sh_base_url` and `SHConfig.sh_token_url`.

## SHConstants

| Attribute | Value |
|---|---|
| `SHConstants.HEADERS` | `{"User-Agent": "sentinel-hub/v<version>"}` – sent with every request |

## RequestType

HTTP methods for `DownloadRequest`: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
Import with `from sentinel_hub.constants import RequestType`.
