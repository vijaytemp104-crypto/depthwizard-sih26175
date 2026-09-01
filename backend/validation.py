"""Orchestration of alignment, masking, and independent-reference metrics."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from backend.alignment import check_alignment
from backend.masking import create_valid_pixel_mask
from backend.metrics import mae, pearson_correlation, rmse


def _result(
    *,
    status: str,
    reference_source: Optional[str],
    units: Optional[str],
    reason: Optional[str],
    rmse_value: Optional[float] = None,
    mae_value: Optional[float] = None,
    correlation: Optional[float] = None,
    valid_pixel_count: Optional[int] = None,
) -> dict:
    """Create the stable validation result structure."""
    return {
        "status": status,
        "reference_source": reference_source,
        "rmse": rmse_value,
        "mae": mae_value,
        "correlation": correlation,
        "valid_pixel_count": valid_pixel_count,
        "units": units,
        "artifacts": {"metrics": None, "error_map": None},
        "reason": reason,
    }


def validate_elevation(
    prediction: np.ndarray,
    reference: Optional[np.ndarray] = None,
    *,
    reference_source: Optional[str] = None,
    units: Optional[str] = None,
    prediction_nodata: Optional[float] = None,
    reference_nodata: Optional[float] = None,
    reference_valid_mask: Optional[np.ndarray] = None,
    prediction_crs: Optional[Any] = None,
    reference_crs: Optional[Any] = None,
    prediction_transform: Optional[Any] = None,
    reference_transform: Optional[Any] = None,
    prediction_width: Optional[int] = None,
    prediction_height: Optional[int] = None,
    reference_width: Optional[int] = None,
    reference_height: Optional[int] = None,
    require_geospatial_metadata: bool = False,
) -> dict:
    """Validate prediction against an independent reference without modifying either.

    No result is calculated when the independent reference is absent, alignment
    cannot be established, or no pixels remain valid after masking.
    """
    if reference is None:
        return _result(
            status="skipped",
            reference_source=None,
            units=None,
            reason="Independent reference elevation data was not supplied.",
        )

    try:
        check_alignment(
            prediction,
            reference,
            prediction_crs=prediction_crs,
            reference_crs=reference_crs,
            prediction_transform=prediction_transform,
            reference_transform=reference_transform,
            prediction_width=prediction_width,
            prediction_height=prediction_height,
            reference_width=reference_width,
            reference_height=reference_height,
            require_geospatial_metadata=require_geospatial_metadata,
        )
        valid_mask = create_valid_pixel_mask(
            prediction,
            reference,
            prediction_nodata=prediction_nodata,
            reference_nodata=reference_nodata,
            reference_valid_mask=reference_valid_mask,
        )
    except ValueError as error:
        return _result(
            status="failed",
            reference_source=reference_source,
            units=units,
            reason=f"Alignment or validity check failed: {error}",
        )

    valid_count = int(np.count_nonzero(valid_mask))
    if valid_count == 0:
        return _result(
            status="failed",
            reference_source=reference_source,
            units=units,
            reason="No valid aligned prediction/reference pixels are available for validation.",
        )

    prediction_values = np.asarray(prediction)[valid_mask]
    reference_values = np.asarray(reference)[valid_mask]
    return _result(
        status="succeeded",
        reference_source=reference_source,
        units=units,
        rmse_value=rmse(prediction_values, reference_values),
        mae_value=mae(prediction_values, reference_values),
        correlation=pearson_correlation(prediction_values, reference_values),
        valid_pixel_count=valid_count,
        reason=None,
    )
