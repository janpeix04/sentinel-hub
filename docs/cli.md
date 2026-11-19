# Command line interface

Installing the package adds a `sentinel-hub` command. It covers the common tasks without
writing Python: configuring credentials, listing collections and bands, generating
evalscripts, searching the catalog, downloading imagery and computing statistics.

```bash
sentinel-hub --help              # or: python -m sentinel_hub --help
sentinel-hub <command> --help    # options of a single command
```

During development run it through uv: `uv run sentinel-hub ...`.

- [Global options](#global-options)
- [config](#config)
- [collections and bands](#collections-and-bands)
- [evalscript](#evalscript)
- [search](#search)
- [process](#process)
- [stats](#stats)
- [Common arguments](#common-arguments)

## Global options

| Option | Description |
|---|---|
| `--profile NAME` | Config profile to use (default `default-profile`, or `SH_PROFILE`). Goes **before** the command. |
| `--version` | Print the package version. |

## config

```bash
sentinel-hub config set sh_client_id "<your client ID>"
sentinel-hub config set sh_client_secret "<your client secret>"
sentinel-hub config show                  # credentials masked
sentinel-hub config show --show-secrets
sentinel-hub config path                  # location of config.toml
sentinel-hub --profile work config set sh_client_id "<other ID>"
```

`config set` accepts any `SHConfig` parameter (see [configuration.md](configuration.md))
and converts numbers automatically. `config show` prints the resolved configuration, so
`SH_CLIENT_ID` / `SH_CLIENT_SECRET` environment variables are taken into account.

## collections and bands

```bash
sentinel-hub collections                 # enum names and API IDs
sentinel-hub bands SENTINEL2_L2A         # bands, meta-bands and their units
```

Wherever a collection is expected you can pass the enum name (case-insensitive,
`SENTINEL2_L2A`) or the API ID (`sentinel-2-l2a`).

## evalscript

Prints a generated evalscript (see [evalscript.md](evalscript.md)).

```bash
sentinel-hub evalscript SENTINEL2_L2A --bands B04,B03,B02 --merged-output default
sentinel-hub evalscript SENTINEL2_L2A --bands B08 --meta-bands dataMask -o ndvi_base.js
```

| Option | Description |
|---|---|
| `--bands` | Comma-separated bands (default: all bands of the collection). |
| `--meta-bands` | Comma-separated meta-bands, e.g. `dataMask,SCL`. |
| `--merged-output ID` | Return all bands in a single output with this ID. |
| `--no-dn` | Don't prefer DN units over the default unit. |
| `-o FILE` | Write to a file instead of stdout. |

## search

Catalog (STAC) search, see [catalog-api.md](catalog-api.md).

```bash
sentinel-hub search SENTINEL2_L2A \
  --bbox 13.35,45.85,13.55,46.0 --time 2024-06-01/2024-06-30 \
  --filter "eo:cloud_cover < 20" --format timestamps
```

| Option | Description |
|---|---|
| `--time` | `START/END` or a single date. |
| `--filter` | CQL2 text filter. |
| `--ids` | Comma-separated feature IDs. |
| `--max-results N` | Stop after N results (default: all pages). |
| `--format` | `ids` (default), `timestamps` or `json` (a GeoJSON FeatureCollection). |
| `-o FILE` | Write to a file instead of stdout. |

The area (`--bbox` / `--geometry`) is optional for `search`.

## process

Downloads processed imagery with the Process API, see [process-api.md](process-api.md).
The response is written to `--output` exactly as the service returns it, so TIFFs keep
their georeferencing.

```bash
# true colour GeoTIFF at 10 m
sentinel-hub process SENTINEL2_L2A \
  --bbox 13.35,45.85,13.55,46.0 --time 2024-06-01/2024-06-30 --maxcc 0.2 \
  --bands B04,B03,B02 --resolution 10 -o true_color.tif

# custom evalscript, fixed size, PNG
sentinel-hub process SENTINEL2_L2A --geometry field.geojson --time 2024-06-01/2024-06-30 \
  --evalscript ndvi.js --size 512,512 -o ndvi.png
```

| Option | Description |
|---|---|
| `-o FILE` | **Required.** Output file. |
| `--format` | `tiff`, `png`, `jpg`, `json` or `tar`. Inferred from the `-o` extension by default. |
| `--response-id` | Evalscript output ID to return (default `default`). |
| `--progress` | Show a progress bar. |

When `--bands` is used the generated evalscript merges them into the `default` output.

## stats

Computes statistics with the Statistical API, see [statistical-api.md](statistical-api.md).
Prints JSON to stdout, or writes it with `-o`.

```bash
sentinel-hub stats SENTINEL2_L2A \
  --bbox 13.35,45.85,13.55,46.0 --time 2024-06-01/2024-06-30 \
  --interval P10D --last-interval SHORTEN --bands B04,B08 --resolution 10 -o stats.json
```

| Option | Description |
|---|---|
| `--time` | **Required.** `START/END`. |
| `--interval` | ISO 8601 aggregation interval (default `P1D`). |
| `--last-interval` | `SKIP`, `SHORTEN` or `EXTEND`. |
| `--progress` | Show a progress bar. |

With `--bands`, `dataMask` is added to the generated evalscript automatically (the
Statistical API requires it). A custom `--evalscript` must return a `dataMask` output itself.

## Common arguments

Used by `process` and `stats` (area also by `search`):

| Option | Description |
|---|---|
| `--bbox` | `min_x,min_y,max_x,max_y`. |
| `--geometry FILE` | GeoJSON file with a polygon: a geometry, a Feature or a FeatureCollection with one feature. |
| `--crs` | CRS of `--bbox` / `--geometry`, e.g. `4326` (default) or `32633`. |
| `--size` | Output size in pixels, `WIDTH,HEIGHT`. |
| `--resolution` | Output resolution in meters. For WGS84 areas it is converted to a pixel size with `bbox_to_dimensions`. |
| `--evalscript FILE` | Evalscript file. |
| `--bands` | Generate the evalscript from comma-separated bands instead. |
| `--maxcc` | Max cloud coverage, between 0 and 1. |
| `--mosaicking-order` | `mostRecent`, `leastRecent` or `leastCC`. |
| `--upsampling` / `--downsampling` | `NEAREST`, `BILINEAR` or `BICUBIC`. |

Invalid input exits with status 2 and an error message on stderr.
