import numpy as np
import pytest

from backend.alignment import check_alignment


def test_matching_shapes_and_metadata_are_aligned():
    prediction = np.array([[1.0, 2.0], [3.0, 4.0]])
    reference = np.array([[10.0, 20.0], [30.0, 40.0]])
    transform = (30.0, 0.0, 500000.0, 0.0, -30.0, 2100000.0)

    assert check_alignment(
        prediction,
        reference,
        prediction_crs="EPSG:32643",
        reference_crs="EPSG:32643",
        prediction_transform=transform,
        reference_transform=transform,
        prediction_width=2,
        prediction_height=2,
        reference_width=2,
        reference_height=2,
        require_geospatial_metadata=True,
    ) is True


def test_shape_mismatch_raises_value_error():
    with pytest.raises(ValueError, match="same shape"):
        check_alignment(np.zeros((2, 2)), np.zeros((1, 4)))


def test_crs_mismatch_raises_value_error():
    with pytest.raises(ValueError, match="CRS"):
        check_alignment(
            np.zeros((2, 2)),
            np.zeros((2, 2)),
            prediction_crs="EPSG:4326",
            reference_crs="EPSG:32643",
        )


def test_transform_mismatch_raises_value_error():
    with pytest.raises(ValueError, match="transform"):
        check_alignment(
            np.zeros((2, 2)),
            np.zeros((2, 2)),
            prediction_transform=(1, 0, 0, 0, -1, 2),
            reference_transform=(2, 0, 0, 0, -1, 2),
        )


def test_width_mismatch_raises_value_error():
    with pytest.raises(ValueError, match="prediction width"):
        check_alignment(
            np.zeros((2, 3)), np.zeros((2, 3)), prediction_width=2
        )


def test_height_mismatch_raises_value_error():
    with pytest.raises(ValueError, match="reference height"):
        check_alignment(
            np.zeros((2, 3)), np.zeros((2, 3)), reference_height=3
        )


def test_missing_optional_metadata_is_valid_for_non_geospatial_arrays():
    assert check_alignment(np.zeros((2, 2)), np.ones((2, 2))) is True


def test_alignment_check_never_resizes_or_reprojects_inputs():
    prediction = np.array([[1.0, 2.0], [3.0, 4.0]])
    reference = np.array([[5.0, 6.0], [7.0, 8.0]])
    original_prediction = prediction.copy()
    original_reference = reference.copy()

    check_alignment(
        prediction,
        reference,
        prediction_width=2,
        prediction_height=2,
        reference_width=2,
        reference_height=2,
    )

    assert prediction.shape == (2, 2)
    assert reference.shape == (2, 2)
    assert np.array_equal(prediction, original_prediction)
    assert np.array_equal(reference, original_reference)


@pytest.mark.parametrize(
    ("prediction_crs", "reference_crs"),
    [(None, "EPSG:32643"), ("EPSG:32643", None)],
)
def test_required_geospatial_alignment_rejects_missing_crs(
    prediction_crs, reference_crs
):
    with pytest.raises(ValueError, match="CRS"):
        check_alignment(
            np.zeros((2, 2)),
            np.zeros((2, 2)),
            prediction_crs=prediction_crs,
            reference_crs=reference_crs,
            prediction_transform=(1, 0, 0, 0, -1, 2),
            reference_transform=(1, 0, 0, 0, -1, 2),
            require_geospatial_metadata=True,
        )


@pytest.mark.parametrize(
    ("prediction_transform", "reference_transform"),
    [((1, 0, 0, 0, -1, 2), None), (None, (1, 0, 0, 0, -1, 2))],
)
def test_required_geospatial_alignment_rejects_missing_transform(
    prediction_transform, reference_transform
):
    with pytest.raises(ValueError, match="transform"):
        check_alignment(
            np.zeros((2, 2)),
            np.zeros((2, 2)),
            prediction_crs="EPSG:32643",
            reference_crs="EPSG:32643",
            prediction_transform=prediction_transform,
            reference_transform=reference_transform,
            require_geospatial_metadata=True,
        )
