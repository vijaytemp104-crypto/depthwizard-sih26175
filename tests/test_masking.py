import numpy as np
import pytest

from backend.masking import create_valid_pixel_mask


def test_normal_arrays_are_all_valid():
    prediction = np.array([[1.0, 2.0], [3.0, 4.0]])
    reference = np.array([[10.0, 20.0], [30.0, 40.0]])

    result = create_valid_pixel_mask(prediction, reference)

    assert result.dtype == np.bool_
    assert np.array_equal(result, np.array([[True, True], [True, True]]))


def test_nan_values_are_invalid():
    result = create_valid_pixel_mask(
        np.array([1.0, np.nan]), np.array([2.0, 3.0])
    )

    assert np.array_equal(result, np.array([True, False]))


@pytest.mark.parametrize(
    ("prediction", "reference"),
    [
        (np.array([1.0, np.inf]), np.array([2.0, 3.0])),
        (np.array([1.0, 2.0]), np.array([3.0, -np.inf])),
    ],
)
def test_infinite_values_are_invalid(prediction, reference):
    result = create_valid_pixel_mask(
        prediction, reference
    )

    assert np.array_equal(result, np.array([True, False]))


def test_prediction_nodata_is_invalid():
    result = create_valid_pixel_mask(
        np.array([1.0, -9999.0]),
        np.array([2.0, 3.0]),
        prediction_nodata=-9999.0,
    )

    assert np.array_equal(result, np.array([True, False]))


def test_reference_nodata_is_invalid():
    result = create_valid_pixel_mask(
        np.array([1.0, 2.0]),
        np.array([3.0, -9999.0]),
        reference_nodata=-9999.0,
    )

    assert np.array_equal(result, np.array([True, False]))


def test_reference_valid_mask_limits_valid_pixels():
    result = create_valid_pixel_mask(
        np.array([[1.0, 2.0], [3.0, 4.0]]),
        np.array([[5.0, 6.0], [7.0, 8.0]]),
        reference_valid_mask=np.array([[True, False], [False, True]]),
    )

    assert np.array_equal(result, np.array([[True, False], [False, True]]))


def test_combined_invalid_conditions_are_all_excluded():
    result = create_valid_pixel_mask(
        np.array([1.0, np.nan, -9999.0, np.inf, 5.0]),
        np.array([10.0, 20.0, 30.0, 40.0, -9999.0]),
        prediction_nodata=-9999.0,
        reference_nodata=-9999.0,
        reference_valid_mask=np.array([True, True, True, True, False]),
    )

    assert np.array_equal(result, np.array([True, False, False, False, False]))


def test_mismatched_array_shapes_raise_value_error():
    with pytest.raises(ValueError, match="exactly the same shape"):
        create_valid_pixel_mask(np.array([1.0, 2.0]), np.array([[1.0], [2.0]]))


def test_mismatched_reference_valid_mask_shape_raises_value_error():
    with pytest.raises(ValueError, match="reference_valid_mask"):
        create_valid_pixel_mask(
            np.array([1.0, 2.0]),
            np.array([3.0, 4.0]),
            reference_valid_mask=np.array([[True, False]]),
        )
