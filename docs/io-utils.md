# File I/O

`read_data` and `write_data` read and write the formats the library works with, choosing a
reader/writer from the file extension (or an explicit `MimeType`). They are also what the
download layer uses to cache responses.

- [Reading](#reading)
- [Writing](#writing)
- [Supported formats](#supported-formats)
- [Decoding API responses](#decoding-api-responses)

## Reading

```python
from sentinel_hub import MimeType, read_data

image = read_data("data/image.tif")  # numpy array
meta = read_data("data/request.json")  # dict
raw = read_data("data/blob.bin", MimeType.RAW)  # bytes, format given explicitly
files = read_data(
    "data/response.tar"
)  # {"default.tif": ndarray, "userdata.json": dict}
```

Raises `FileNotFoundError` if the file does not exist and `ValueError` for unsupported formats.

## Writing

```python
from sentinel_hub import write_data

write_data("out/image.tif", array)  # parent folders are created
write_data("out/image.tif", array, compress=True)  # LZMA-compressed TIFF
write_data("out/image.png", array_uint8)
write_data("out/meta.json", {"a": 1})  # pretty-printed, sorted keys
write_data("out/table.csv", [["a", "b"], [1, 2]])  # ';'-delimited
write_data("out/log.txt", "line\n", add=True)  # append
```

## Supported formats

| Format | `read_data` returns | `write_data` accepts |
|---|---|---|
| TIFF (`.tif`, `.tiff`) | `ndarray` (via `tifffile`) | `ndarray`, optional LZMA compression |
| PNG, JPEG | `ndarray` (via Pillow) | `ndarray` |
| JPEG 2000 (`.jp2`) | `ndarray`, 15-bit images corrected | `ndarray` |
| NumPy (`.npy`) | `ndarray` | `ndarray` |
| JSON | `dict` / `list` | any JSON-serialisable object |
| CSV | `list[list[str]]` (`;` delimiter) | iterable of rows |
| TXT | `str` | `str` (`add=True` appends) |
| RAW | `bytes` | `bytes` |
| XML, GML, SAFE | `ElementTree` | `ElementTree` (XML, GML) |
| TAR | `dict[filename, decoded value]` | – |

## Decoding API responses

`sentinel_hub.decoding` turns raw response bytes into Python objects. It is called
automatically by the download clients, but is usable on its own:

```python
from sentinel_hub.constants import MimeType
from sentinel_hub.decoding import decode_data, decode_tar

decode_data(content, MimeType.TIFF)  # ndarray
decode_data(content, MimeType.JSON)  # dict
decode_data(content, MimeType.ZIP)  # BytesIO
decode_tar(content)  # {"default.tif": ndarray, ...}
```

Other helpers: `decode_image`, `decode_jp2_image`, `get_data_format(filename)`,
`decode_sentinel_hub_error_msg(response)`.
