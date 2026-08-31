# DepthWizard shared pipeline contracts

These contracts define stable cross-team boundaries before implementation. `pipeline_contract.json` is the machine-readable canonical reference; `example_result.json` is an illustrative successful georeferenced result, not a performance claim.

## Ownership and stable artifacts

- Shawn owns final integration, application state, and ingest coordination.
- Manish owns monocular depth inference: `depth.npy`, `depth.png`, `model_metadata.json`.
- Ayush owns metric calibration/geospatial output: `calibrated_dsm.tif`, `terrain.json`, `calibration.json`.
- Harinandana owns independent validation: `metrics.json` and optional `error_map`.
- Optional trust additions are `confidence_map` and `evidence_passport.json`; neither substitutes for independent validation.

Pipeline stages are `ingest`, `depth`, `calibration`, `validation`, `terrain`, and `evidence`. Job states are `pending`, `running`, `succeeded`, and `failed`. Stage states add `skipped`; every skipped stage requires a reason.

## Relative, metric, and geospatial rules

Input is one overhead RGB satellite/aerial image. Primary types are PNG, JPG/JPEG, and GeoTIFF/TIF/TIFF. PNG/JPG normally lacks trustworthy geographic scale and therefore produces relative depth/DSM unless legitimate calibration evidence is supplied. Never label uncalibrated relative depth as exact metres. Raw depth is relative, not absolute elevation.

GeoTIFF CRS, affine transform, bounds, pixel size/resolution, and nodata must be preserved where applicable. Missing or inapplicable values are `null`, never fabricated.

Metric calibration may use SRTM/reference DEM, limited GCPs, or other explicitly documented elevation evidence. Baseline calibration may use `E = aD + b`. If evidence is unavailable or invalid, calibration is unavailable/failed, `calibrated` is false, units are not metres, and a reason is required.

Validation metrics appear only with an independent valid reference. When not performed, RMSE, MAE, correlation, and valid-pixel count are `null`. Missing validation is not zero error.

## Raster orientation, paths, and errors

Raster arrays use `height x width`, row-major convention: first index row/y, second index column/x. `depth.npy` preserves the agreed source image grid dimensions. Terrain height rows follow the same convention.

Artifact paths are repository-relative, such as `outputs/JOB-001/depth.npy`, never machine-specific absolute paths. User-facing errors contain `code`, `stage`, `message`, `detail`, and `recoverable`; Python stack traces must not be exposed.

Consumers should tolerate additive optional keys, but producers must not change the meaning of defined keys.

## CONTRACT CHANGE RULE

Any change to:

- artifact filename
- JSON key
- array orientation
- raster dimensions
- CRS representation
- endpoint-facing result structure
- units
- stage names

must be approved by Shawn before teammates rely on it.
