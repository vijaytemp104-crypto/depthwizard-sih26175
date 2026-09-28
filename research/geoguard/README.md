# ChakraVIEW GeoGuard-SC research workspace

This directory is an isolated research workspace for **GeoGuard-SC: Support-Consistent Benefit-Aware Elevation Refinement**. It does not replace or modify ChakraVIEW's production inference, calibration, validation, MissionView, API, or frontend.

The first experiment asks whether a single RGB image can propose elevation corrections that improve an imperfect reference while preserving strict geographic separation from independent truth. No model training, model download, or dataset acquisition is performed by this scaffold.

## Required experimental triplet

Every area of interest (AOI) must provide three independently documented inputs:

1. **RGB imagery** — georeferenced optical imagery, with source, acquisition date, CRS, ground sampling distance, licence, and checksum.
2. **Imperfect/coarse elevation reference** — the surface available to the operational algorithm, with its elevation type, support/resolution, units, horizontal CRS, vertical datum, date, nodata, licence, and checksum.
3. **Independent high-resolution truth** — the surface used only for supervised training in training roles or for evaluation in its assigned validation/test role, with matching metadata and provenance.

The primary future real-data pairing is NAIP RGB with USGS 3DEP LiDAR-derived surface truth and a separately sourced coarse reference. GAMUS AGL is intended only as a faster development dataset. Proposed AOIs remain `metadata_pending` until file-level availability, licence, dates, coordinate systems, vertical datums, units, coverage, and checksums are verified.

## Quantity contract

- **RGB:** optical image values. RGB carries appearance, not elevation units.
- **Relative monocular depth:** an ordering or relative scene-geometry signal whose scale and offset are not generally physical.
- **Camera depth:** distance/range in a defined camera coordinate convention. It requires camera geometry to relate it to mapped vertical elevation.
- **DSM:** digital surface model: elevation of the visible/top surface, including buildings and vegetation where captured.
- **DTM:** digital terrain model: estimated bare-earth elevation.
- **AGL / nDSM:** height above a terrain reference, commonly `DSM - DTM`; it is not an absolute elevation datum.
- **Coarse reference:** the imperfect elevation observation supplied to the model. Its type, support, units, vertical datum, date, and uncertainty must remain explicit.
- **Independent truth:** higher-quality evidence not derived from the candidate prediction or the same calibration operation. Its support and interpolation status must be retained.

> **RELATIVE DEPTH IS NOT METRIC ELEVATION.**
>
> **CAMERA DEPTH IS NOT DSM.**
>
> **AGL/nDSM IS NOT ABSOLUTE DSM.**
>
> **A DTM MUST NOT BE USED AS IF IT WERE A DSM.**

Truth used for final evaluation must not also be used for calibration, registration fitting, threshold selection, corruption tuning, or model selection. Coordinate transformations must not silently relabel vertical datums or assume metres. A projected horizontal CRS does not prove that horizontal or vertical values use metres.

## Directory responsibilities

- `configs/`: future research-only run configurations.
- `manifests/`: schema, proposed AOIs, split policy, and later immutable data manifests.
- `scripts/`: small research utilities such as manifest validation.
- `qa/`: read-only dataset and triplet quality checks.
- `experiments/`: preregistered experiment contracts and later research code.
- `tests/`: synthetic tests for research tooling.
- `outputs/`: generated research results; ignored by Git.

Local datasets, caches, model checkpoints, LAS/LAZ point clouds, TIFF rasters, NumPy arrays, and model weights must not be committed. The repository ignore rules cover the generated/local paths.

## Initial commands

Validate a completed manifest:

```powershell
python research/geoguard/scripts/validate_manifest.py path/to/manifest.json
```

Inspect one triplet (requires Rasterio):

```powershell
python research/geoguard/qa/check_triplet.py --rgb path/to/rgb.tif --reference path/to/reference.tif --truth path/to/truth.tif
```

Run the focused standard-library tests:

```powershell
python -m unittest discover -s research/geoguard/tests -p "test_*.py" -v
```

`proposed_split.json` is a planning document, not a scientifically complete manifest. The validator is expected to reject records with missing units, vertical datums, dates, paths, licences, or other required acquisition metadata until those fields are verified.
