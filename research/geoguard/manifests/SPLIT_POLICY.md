# GeoGuard-SC geographic split policy

The unit of separation is a ground footprint, not an extracted image patch. Roles are assigned before patch extraction, corruption, resampling, model fitting, calibration, or threshold selection.

## Mandatory rules

1. Assign every source footprint to exactly one of `train`, `model_validation`, `gate_calibration`, or `blind_test` before extracting patches.
2. All overlapping views, repeat acquisitions, resolutions, crops, tiles, derived rasters, synthetic corruptions, and dates of the same ground footprint remain in the same role.
3. Never form train/test sets by randomly splitting neighboring patches. Spatial autocorrelation makes that result misleading.
4. Apply an initial buffer of at least **1 km** between development roles. Increase the buffer if the largest image context, LiDAR interpolation reach, reference support, or receptive field extends farther.
5. Deduplicate footprints across datasets as well as within a dataset. Dataset names and AOI IDs do not prove geographic independence.
6. Do not use truth-derived registration, vertical shifts, affine fits, masks, interpolation parameters, or scene-specific corrections on blind-test inputs.
7. Do not calibrate a final-test prediction with LiDAR or other blind-test truth.
8. Do not tune model, gate, uncertainty, consistency, or decision thresholds on blind-test truth.
9. A final-test failure remains a reported final-test failure. It does not become new tuning data for the same claimed evaluation.
10. Fit normalization, corruption distributions, class weights, calibration transforms, and uncertainty calibration on their designated development roles only.
11. Record source dates and keep temporal duplicates or derived products with their original footprint role.
12. Freeze and hash the final AOI/file manifest before the first blind-test evaluation.

## Role responsibilities

- `train`: predictor fitting and geographically out-of-fold gate-label generation only.
- `model_validation`: model architecture, optimizer, loss, backbone, and feature selection.
- `gate_calibration`: benefit margin, risk/uncertainty calibration, REFINE/RETAIN/FLAG thresholds, and operating point.
- `blind_test`: one frozen evaluation after all preceding choices are fixed.

Truth from `model_validation` must not leak into `gate_calibration`, and neither may be reused as `train`. A reference product may be globally available, but its truth-derived corrections and learned parameters remain role-specific.

## Legacy cases

Existing Boulder, Acadia, and Baltimore results are legacy regression/demo cases. The team has already inspected their outputs and used them during development discussions. They are **not untouched research tests** and must not be presented as blind GeoGuard evidence.

## Proposed split status

`proposed_split.json` lists planning targets only. `metadata_pending` means the imagery, reference, independent truth, dates, licences, vertical references, usable coverage, and lack of cross-dataset exposure have not yet been verified. County assignment is not evidence of data availability.
