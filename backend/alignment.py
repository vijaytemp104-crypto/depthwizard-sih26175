"""Explicit, non-mutating alignment checks for elevation arrays."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np


def _check_declared_dimensions(
    array: np.ndarray,
    *,
    name: str,
    width: Optional[int],
    height: Optional[int],
) -> None:
    """Ensure supplied spatial dimensions match a two-dimensional elevation grid."""
    if width is None and height is None:
        return
    if array.ndim != 2:
        raise ValueError(f"{name} width/height metadata requires a 2D elevation array")

    actual_height, actual_width = array.shape
    if width is not None and width != actual_width:
        raise ValueError(
            f"{name} width metadata ({width}) does not match array width ({actual_width})"
        )
    if height is not None and height != actual_height:
        raise ValueError(
            f"{name} height metadata ({height}) does not match array height ({actual_height})"
        )


def check_alignment(
    prediction: np.ndarray,
    reference: np.ndarray,
    *,
    prediction_crs: Optional[Any] = None,
    reference_crs: Optional[Any] = None,
    prediction_transform: Optional[Any] = None,
    reference_transform: Optional[Any] = None,
    prediction_width: Optional[int] = None,
    prediction_height: Optional[int] = None,
    reference_width: Optional[int] = None,
    reference_height: Optional[int] = None,
    require_geospatial_metadata: bool = False,
) -> bool:
    """Return ``True`` when supplied alignment evidence agrees, else raise ``ValueError``.

    The function only checks existing arrays and metadata.  It never resizes,
    reshapes, reprojects, interpolates, or otherwise modifies either input.
    Missing CRS/transform data is acceptable for non-geospatial validation. Set
    ``require_geospatial_metadata`` when that evidence is required instead.
    """
    prediction_array = np.asarray(prediction)
    reference_array = np.asarray(reference)

    if prediction_array.shape != reference_array.shape:
        raise ValueError("prediction and reference arrays must have exactly the same shape")

    _check_declared_dimensions(
        prediction_array,
        name="prediction",
        width=prediction_width,
        height=prediction_height,
    )
    _check_declared_dimensions(
        reference_array,
        name="reference",
        width=reference_width,
        height=reference_height,
    )

    if require_geospatial_metadata:
        if prediction_crs is None or reference_crs is None:
            raise ValueError("geospatial alignment requires CRS metadata for both arrays")
        if prediction_transform is None or reference_transform is None:
            raise ValueError("geospatial alignment requires transform metadata for both arrays")

    if (
        prediction_crs is not None
        and reference_crs is not None
        and prediction_crs != reference_crs
    ):
        raise ValueError("prediction and reference CRS metadata do not match")

    if (
        prediction_transform is not None
        and reference_transform is not None
        and not np.array_equal(prediction_transform, reference_transform)
    ):
        raise ValueError("prediction and reference transform metadata do not match")

    return True
