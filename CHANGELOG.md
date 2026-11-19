# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Statistical API** – `SHStatistical` for statistics, percentiles and histograms per
  aggregation interval, with the `SHStatistical.aggregation` helper and the
  `LastIntervalBehavior` enum. Documented in `docs/statistical-api.md`.
- **Sentinel-1 GRD** – `DataCollection.SENTINEL1` plus `SENTINEL1_IW`, `SENTINEL1_EW` and
  `SENTINEL1_EW_SH` variants (each with `_ASC` / `_DES`), with band and metaband specs.
  New collection fields `swath_mode`, `polarization`, `resolution` and `orbit_direction`
  are sent as Process / Statistical API `dataFilter` entries; `OrbitDirection` enum,
  `DataCollection.is_sentinel1` and `contains_orbit_direction`. Documented in
  `docs/data-collections.md`.
- **Sentinel-3** – `DataCollection.SENTINEL3_OLCI` and `SENTINEL3_SLSTR` (L1B) with band and
  metaband specs, and `DataCollection.is_sentinel3`.
- **Sentinel-5P** – `DataCollection.SENTINEL5P` (TROPOMI L2) with trace-gas, aerosol and
  cloud bands, and `DataCollection.is_sentinel5p`.

### Changed

- `orbit_direction` is now sent as `dataFilter.orbitDirection` for any collection that sets
  it, not only Sentinel-1, so it also works for SLSTR.
- `generate_evalscript` raises a `ValueError` naming the band when a band's output type has
  no Process API sample type, instead of a `KeyError`.

## [0.1.0] - 2026-11-19

First release of `sentinel-hub`, a Python client for the Sentinel Hub APIs on the
Copernicus Data Space Ecosystem (CDSE).

### Added

- **Configuration** – `SHConfig` with `config.toml` profiles, `SH_CLIENT_ID` /
  `SH_CLIENT_SECRET` / `SH_PROFILE` environment variables and masked credentials.
- **Data collections** – predefined `SENTINEL2_L1C` and `SENTINEL2_L2A` with band and
  metaband specs; custom collections via `DataCollection.define` / `define_from`.
- **Catalog API** – `SHCatalog` for service info, collections, features and STAC search
  (time, bbox, geometry, IDs, CQL2 filters) with lazy pagination.
- **Process API** – `SHRequest` with input data filters, data fusion, bbox / geometry
  bounds, size or resolution, single and multi-output (TAR) responses, and on-disk caching.
- **Evalscripts** – `generate_evalscript` builds `//VERSION=3` evalscripts from band lists.
- **Geometry** – `BBox`, `Geometry` and `CRS` with reprojection, buffering and partitioning.
- **Utilities** – geo helpers (`bbox_to_dimensions`, UTM conversions), time helpers
  (`parse_time_interval`, `filter_times`, …) and file I/O (`read_data`, `write_data`).
- **Downloads** – OAuth2 `SHSession`, `SHDownloadClient` with retries and back-off,
  rate-limit handling, multi-threading, session caching and cross-process session sharing.
- **Documentation** – README and per-topic guides in `docs/`.
- **License** – MIT.

[Unreleased]: https://github.com/janpeix04/sentinel-hub/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/janpeix04/sentinel-hub/releases/tag/v0.1.0
