"""Validity masking for aligned elevation prediction/reference arrays."""

from __future__ import annotations

from typing import Optional

import numpy as np


def create_valid_pixel_mask(
    prediction: np.ndarray,
    reference: np.ndarray,
    *,
    prediction_nodata: Optional[float] = None,
    reference_nodata: Optional[float] = None,
    reference_valid_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Return valid pixels shared by aligned prediction and reference arrays.

    Inputs are never reshaped or reprojected.  Valid values must be finite in
    both arrays, distinct from any supplied nodata values, and permitted by an
    optional reference validity mask.
    """
    prediction_array = np.asarray(prediction)
    reference_array = np.asarray(reference)

    if prediction_array.shape != reference_array.shape:
        raise ValueError("prediction and reference must have exactly the same shape")

    valid = np.isfinite(prediction_array) & np.isfinite(reference_array)

    if prediction_nodata is not None:
        valid &= prediction_array != prediction_nodata
    if reference_nodata is not None:
        valid &= reference_array != reference_nodata

    if reference_valid_mask is not None:
        reference_mask_array = np.asarray(reference_valid_mask)
        if reference_mask_array.shape != reference_array.shape:
            raise ValueError(
                "reference_valid_mask must have exactly the same shape as reference"
            )
        if reference_mask_array.dtype != np.bool_:
            raise ValueError("reference_valid_mask must be boolean")
        valid &= reference_mask_array

    return valid
