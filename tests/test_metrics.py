import math

import numpy as np
import pytest

from backend.metrics import mae, pearson_correlation, rmse, valid_pixel_count


def test_rmse_and_mae_match_hand_calculated_values():
    prediction = np.array([10, 20, 30])
    reference = np.array([12, 18, 30])

    assert mae(prediction, reference) == pytest.approx(4 / 3)
    assert rmse(prediction, reference) == pytest.approx(math.sqrt(8 / 3))


def test_pearson_correlation_for_linearly_related_values():
    assert pearson_correlation(np.array([1, 2, 3]), np.array([2, 4, 6])) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("prediction", "reference"),
    [
        (np.array([1]), np.array([1])),
        (np.array([1, 1]), np.array([2, 3])),
        (np.array([1, 2]), np.array([3, 3])),
    ],
)
def test_pearson_correlation_is_none_when_undefined(prediction, reference):
    assert pearson_correlation(prediction, reference) is None


def test_empty_error_metrics_are_not_fabricated():
    empty = np.array([])

    assert rmse(empty, empty) is None
    assert mae(empty, empty) is None
    assert pearson_correlation(empty, empty) is None
    assert valid_pixel_count(empty, empty) == 0


def test_valid_pixel_count_uses_aligned_values():
    prediction = np.array([[1, 2], [3, 4]])
    reference = np.array([[5, 6], [7, 8]])

    assert valid_pixel_count(prediction, reference) == 4


@pytest.mark.parametrize(
    "metric",
    [rmse, mae, pearson_correlation, valid_pixel_count],
)
def test_metrics_reject_mismatched_value_counts(metric):
    with pytest.raises(ValueError, match="same number of values"):
        metric(np.array([1, 2]), np.array([1]))


def test_metrics_reject_differently_shaped_arrays_without_reshaping():
    with pytest.raises(ValueError, match="same shape"):
        rmse(np.array([1, 2]), np.array([[1], [2]]))
