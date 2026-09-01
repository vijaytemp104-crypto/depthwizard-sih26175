"""Metrics for already aligned, valid prediction and reference pixels."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


def _validate_aligned_inputs(
    prediction: np.ndarray, reference: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Return arrays after confirming they represent the same aligned grid."""
    prediction_array = np.asarray(prediction, dtype=float)
    reference_array = np.asarray(reference, dtype=float)

    if prediction_array.size != reference_array.size:
        raise ValueError("prediction and reference must contain the same number of values")
    if prediction_array.shape != reference_array.shape:
        raise ValueError("prediction and reference must have the same shape")

    return prediction_array, reference_array


def rmse(prediction: np.ndarray, reference: np.ndarray) -> Optional[float]:
    """Return root mean squared error, or ``None`` when no values are supplied."""
    prediction_array, reference_array = _validate_aligned_inputs(prediction, reference)
    if prediction_array.size == 0:
        return None

    difference = prediction_array - reference_array
    return float(np.sqrt(np.mean(difference**2)))


def mae(prediction: np.ndarray, reference: np.ndarray) -> Optional[float]:
    """Return mean absolute error, or ``None`` when no values are supplied."""
    prediction_array, reference_array = _validate_aligned_inputs(prediction, reference)
    if prediction_array.size == 0:
        return None

    return float(np.mean(np.abs(prediction_array - reference_array)))


def pearson_correlation(
    prediction: np.ndarray, reference: np.ndarray
) -> Optional[float]:
    """Return Pearson correlation, or ``None`` when it is mathematically undefined."""
    prediction_array, reference_array = _validate_aligned_inputs(prediction, reference)
    if prediction_array.size < 2:
        return None

    if np.ptp(prediction_array) == 0 or np.ptp(reference_array) == 0:
        return None

    prediction_centered = prediction_array - np.mean(prediction_array)
    reference_centered = reference_array - np.mean(reference_array)
    denominator = np.sqrt(
        np.sum(prediction_centered**2) * np.sum(reference_centered**2)
    )
    if denominator == 0:
        return None

    return float(np.sum(prediction_centered * reference_centered) / denominator)


def valid_pixel_count(prediction: np.ndarray, reference: np.ndarray) -> int:
    """Return the number of already-filtered, aligned pixel values."""
    prediction_array, _ = _validate_aligned_inputs(prediction, reference)
    return int(prediction_array.size)
