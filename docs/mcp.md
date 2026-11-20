# MCP server

`sentinel-hub` ships a [Model Context Protocol](https://modelcontextprotocol.io/) server, so
MCP clients such as [Claude Code](https://claude.com/claude-code) can search the catalog,
download imagery and compute statistics through this package.

## Installation

The server needs the optional `mcp` extra:

```bash
# with uv
uv add "sentinel-hub[mcp] @ git+https://github.com/janpeix04/sentinel-hub.git"

# or with pip
pip install "sentinel-hub[mcp] @ git+https://github.com/janpeix04/sentinel-hub.git"
```

Then [set up your CDSE credentials](configuration.md). The server reads them the same way as
`SHConfig` (env vars `SH_CLIENT_ID` / `SH_CLIENT_SECRET` or `config.toml`).

## Running

```bash
sentinel-hub-mcp                    # stdio transport
python -m sentinel_hub.mcp_server   # same thing
```

## Connecting Claude Code

Inside this repository nothing needs to be done: the checked-in [`.mcp.json`](../.mcp.json)
registers the server, and Claude Code asks you to approve it the first time you open the project.

To use it from any other directory, register it once:

```bash
# from a checkout of this repository
claude mcp add sentinel-hub --scope user -- uv run --directory /path/to/sentinel-hub --extra mcp sentinel-hub-mcp

# or, if the package is installed in the active environment
claude mcp add sentinel-hub -- sentinel-hub-mcp
```

Check the connection with `claude mcp list` or `/mcp` inside Claude Code.

## Tools

| Tool | What it does | Calls the service |
|---|---|---|
| `list_collections` | Predefined data collections with enum name and API ID | no |
| `list_bands` | Bands and meta-bands of a collection with their units | no |
| `generate_evalscript` | Build a `//VERSION=3` evalscript from band names | no |
| `show_config` | Active configuration with credentials masked | no |
| `search_catalog` | STAC search by time, area, IDs and CQL2 filter | yes |
| `process_image` | Process API download saved to a file; PNG / JPEG are also returned as an image preview | yes |
| `compute_statistics` | Statistical API time series without downloading images | yes |

The server also exposes the resource `sentinel-hub://collections/{collection}/bands`.

Inputs follow the [CLI](cli.md) conventions:

- **Collection** – enum name (`SENTINEL2_L2A`) or API ID (`sentinel-2-l2a`).
- **Area** – `bbox` as `[min_x, min_y, max_x, max_y]` and/or `geometry` as a GeoJSON polygon,
  Feature or single-feature FeatureCollection, both in `crs` (EPSG code, default `4326`).
- **Time** – `START/END` (e.g. `2024-06-01/2024-06-30`) or a single date.
- **Output size** – `size` as `[width, height]` in pixels, or `resolution` in meters per pixel
  (converted to a pixel size for WGS84 areas).
- **Evalscript** – `bands` to generate one, or `evalscript` with custom source code.

`process_image` writes `output_path` relative to the server's working directory (the project
root when started from `.mcp.json`).

## Example prompts

- *"Find Sentinel-2 L2A scenes over Trieste in June 2024 with less than 20 % clouds."*
- *"Download a true colour PNG of bbox 13.35,45.85,13.55,46.0 for June 2024 at 20 m to `out/trieste.png`."*
- *"Give me mean NDVI per 10 days over that area for summer 2024."*
