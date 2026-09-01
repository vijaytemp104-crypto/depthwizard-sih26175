import math

import numpy as np
import pytest

from backend.validation import validate_elevation


def test_successful_validation_uses_hand_calculated_metrics():
    result = validate_elevation(
        np.array([10.0, 20.0, 30.0]),
        np.array([12.0, 18.0, 30.0]),
        reference_source="independent synthetic reference",
        units="metres",
    )

    assert result["status"] == "succeeded"
    assert result["reference_source"] == "independent synthetic reference"
    assert result["rmse"] == pytest.approx(math.sqrt(8 / 3))
    assert result["mae"] == pytest.approx(4 / 3)
    assert result["valid_pixel_count"] == 3
    assert result["units"] == "metres"
    assert result["artifacts"] == {"metrics": None, "error_map": None}
    assert result["reason"] is None


def test_missing_reference_skips_validation_with_null_metrics():
    result = validate_elevation(np.array([1.0, 2.0]), None)

    assert result["status"] == "skipped"
    assert result["reference_source"] is None
    assert result["rmse"] is None
    assert result["mae"] is None
    assert result["correlation"] is None
    assert result["valid_pixel_count"] is None
    assert result["units"] is None
    assert result["artifacts"] == {"metrics": None, "error_map": None}
    assert result["reason"]


def test_all_invalid_pixels_fail_with_null_metrics():
    result = validate_elevation(
        np.array([np.nan, np.inf]),
        np.array([1.0, 2.0]),
        reference_source="independent reference",
        units="metres",
    )

    assert result["status"] == "failed"
    assert result["rmse"] is None
    assert result["mae"] is None
    assert result["correlation"] is None
    assert result["valid_pixel_count"] is None
    assert result["reason"]


def test_shape_mismatch_fails_validation_without_fixing_alignment():
    result = validate_elevation(
        np.zeros((2, 2)), np.zeros((1, 4)), reference_source="independent reference"
    )

    assert result["status"] == "failed"
    assert result["rmse"] is None
    assert result["mae"] is None
    assert result["correlation"] is None
    assert result["valid_pixel_count"] is None
    assert result["reason"]


def test_nodata_pixels_are_excluded_from_metrics():
    result = validate_elevation(
        np.array([10.0, -9999.0, 30.0]),
        np.array([12.0, 18.0, 30.0]),
        prediction_nodata=-9999.0,
        reference_source="independent reference",
        units="metres",
    )

    assert result["status"] == "succeeded"
    assert result["valid_pixel_count"] == 2
    assert result["rmse"] == pytest.approx(math.sqrt(2.0))
    assert result["mae"] == pytest.approx(1.0)


def test_reference_valid_mask_is_respected():
    result = validate_elevation(
        np.array([10.0, 20.0, 30.0]),
        np.array([12.0, 18.0, 30.0]),
        reference_valid_mask=np.array([True, False, True]),
        reference_source="independent reference",
        units="metres",
    )

    assert result["status"] == "succeeded"
    assert result["valid_pixel_count"] == 2
    assert result["rmse"] == pytest.approx(math.sqrt(2.0))
    assert result["mae"] == pytest.approx(1.0)


def test_constant_arrays_succeed_with_undefined_correlation():
    result = validate_elevation(
        np.array([5.0, 5.0]),
        np.array([3.0, 3.0]),
        reference_source="independent reference",
        units="metres",
    )

    assert result["status"] == "succeeded"
    assert result["correlation"] is None
    assert result["rmse"] == pytest.approx(2.0)
    assert result["mae"] == pytest.approx(2.0)
