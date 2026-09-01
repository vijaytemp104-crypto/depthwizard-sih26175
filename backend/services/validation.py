"""Independent file-based DSM validation adapted from Harinandana's foundation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds


def create_valid_pixel_mask(prediction, reference, *, prediction_nodata=None,
                            reference_nodata=None, reference_valid_mask=None):
    prediction = np.asarray(prediction)
    reference = np.asarray(reference)
    if prediction.shape != reference.shape:
        raise ValueError("prediction and reference must have exactly the same shape")
    valid = np.isfinite(prediction) & np.isfinite(reference)
    if prediction_nodata is not None:
        valid &= prediction != prediction_nodata
    if reference_nodata is not None:
        valid &= reference != reference_nodata
    if reference_valid_mask is not None:
        reference_valid_mask = np.asarray(reference_valid_mask)
        if reference_valid_mask.shape != reference.shape or reference_valid_mask.dtype != np.bool_:
            raise ValueError("reference_valid_mask must be boolean and match the reference shape")
        valid &= reference_valid_mask
    return valid


def compute_metrics(prediction, reference):
    prediction = np.asarray(prediction, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    if prediction.shape != reference.shape or prediction.size == 0:
        raise ValueError("metrics require non-empty aligned values")
    difference = prediction - reference
    correlation = None
    warning = None
    if prediction.size < 2 or np.ptp(prediction) == 0 or np.ptp(reference) == 0:
        warning = "Pearson correlation is undefined for fewer than two values or a constant array."
    else:
        correlation = float(np.corrcoef(prediction, reference)[0, 1])
    return {
        "rmse": float(np.sqrt(np.mean(difference ** 2))),
        "mae": float(np.mean(np.abs(difference))),
        "correlation": correlation,
        "correlation_warning": warning,
        "valid_pixel_count": int(prediction.size),
    }


def skipped_validation(reason="Independent validation reference was not supplied."):
    return {
        "status": "skipped", "reference_source": None, "rmse": None, "mae": None,
        "correlation": None, "valid_pixel_count": None, "valid_pixel_fraction": None,
        "units": None, "artifacts": {"metrics": None, "error_map": None}, "reason": reason,
    }


def validate_rasters(prediction_path: Path, reference_path: Path, output_dir: Path,
                     *, reference_source: str | None = None) -> dict:
    """Reproject a continuous elevation reference to the authoritative prediction grid."""
    with rasterio.open(prediction_path) as prediction_ds, rasterio.open(reference_path) as reference_ds:
        if prediction_ds.crs is None or reference_ds.crs is None:
            raise ValueError("Prediction and validation reference must both have CRS metadata.")
        prediction = prediction_ds.read(1)
        prediction_bounds = prediction_ds.bounds
        reference_in_prediction_crs = transform_bounds(
            reference_ds.crs, prediction_ds.crs, *reference_ds.bounds, densify_pts=21)
        if (reference_in_prediction_crs[2] <= prediction_bounds.left or
                reference_in_prediction_crs[0] >= prediction_bounds.right or
                reference_in_prediction_crs[3] <= prediction_bounds.bottom or
                reference_in_prediction_crs[1] >= prediction_bounds.top):
            raise ValueError("Prediction and validation reference have no geographic overlap.")

        aligned = (
            prediction_ds.crs == reference_ds.crs
            and prediction_ds.transform.almost_equals(reference_ds.transform)
            and prediction_ds.width == reference_ds.width
            and prediction_ds.height == reference_ds.height
        )
        destination_nodata = np.float32(-9999.0)
        reference = np.full(prediction.shape, destination_nodata, dtype=np.float32)
        reproject(
            source=rasterio.band(reference_ds, 1), destination=reference,
            src_transform=reference_ds.transform, src_crs=reference_ds.crs,
            src_nodata=reference_ds.nodata, dst_transform=prediction_ds.transform,
            dst_crs=prediction_ds.crs, dst_nodata=destination_nodata,
            resampling=Resampling.bilinear,
        )
        valid = create_valid_pixel_mask(
            prediction, reference, prediction_nodata=prediction_ds.nodata,
            reference_nodata=destination_nodata)
        count = int(np.count_nonzero(valid))
        if count == 0:
            raise ValueError("No valid overlapping prediction/reference pixels remain after masking.")
        values = compute_metrics(prediction[valid], reference[valid])
        correlation_warning = values.pop("correlation_warning")
        warnings = [correlation_warning] if correlation_warning else []
        diagnostics = {
            "reference_reprojected": not aligned,
            "resampling": "bilinear",
            "prediction_shape": list(prediction.shape),
            "reference_original_shape": [reference_ds.height, reference_ds.width],
            "prediction_resolution": list(prediction_ds.res),
            "reference_original_resolution": list(reference_ds.res),
            "overlap": True,
        }
        error = np.full(prediction.shape, destination_nodata, dtype=np.float32)
        error[valid] = np.abs(prediction[valid] - reference[valid]).astype(np.float32)
        error_profile = prediction_ds.profile.copy()
        error_profile.update(dtype="float32", count=1, nodata=float(destination_nodata))
        error_path = output_dir / "error_map.tif"
        with rasterio.open(error_path, "w", **error_profile) as error_ds:
            error_ds.write(error, 1)
        result = {
            "status": "succeeded", "reference_source": reference_source or reference_path.name,
            **values, "valid_pixel_fraction": count / prediction.size, "units": "metres",
            "prediction_crs": prediction_ds.crs.to_string(),
            "reference_crs": reference_ds.crs.to_string(), "alignment": diagnostics,
            "warnings": warnings,
            "artifacts": {"metrics": "metrics.json", "error_map": "error_map.tif"},
            "reason": None,
        }
    (output_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
