import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from backend.services.validation import compute_metrics, create_valid_pixel_mask, validate_rasters


def write_raster(path, values, *, crs="EPSG:32643", transform=None, nodata=-9999.0):
    values = np.asarray(values, dtype=np.float32)
    transform = transform or from_origin(500000, 2200000, 10, 10)
    with rasterio.open(path, "w", driver="GTiff", width=values.shape[1], height=values.shape[0],
                       count=1, dtype="float32", crs=crs, transform=transform, nodata=nodata) as target:
        target.write(values, 1)
    return path


def test_harinandana_metrics_known_values_and_undefined_correlation():
    metrics = compute_metrics(np.array([1, 2, 3]), np.array([1, 4, 3]))
    assert metrics["rmse"] == pytest.approx(np.sqrt(4 / 3))
    assert metrics["mae"] == pytest.approx(2 / 3)
    assert metrics["valid_pixel_count"] == 3
    constant = compute_metrics(np.ones(3), np.arange(3))
    assert constant["correlation"] is None
    assert "undefined" in constant["correlation_warning"]


def test_harinandana_mask_excludes_nan_inf_nodata_and_reference_mask():
    prediction = np.array([1, np.nan, np.inf, -9999, 5, 6])
    reference = np.array([1, 2, 3, 4, -9999, 6])
    allowed = np.array([True, True, True, True, True, False])
    mask = create_valid_pixel_mask(prediction, reference, prediction_nodata=-9999,
                                   reference_nodata=-9999, reference_valid_mask=allowed)
    assert mask.tolist() == [True, False, False, False, False, False]


def test_file_validation_writes_metrics_error_map_and_preserves_grid(tmp_path):
    prediction = write_raster(tmp_path / "prediction.tif", [[10, 12], [14, -9999]])
    reference = write_raster(tmp_path / "reference.tif", [[9, 14], [14, -9999]])
    result = validate_rasters(prediction, reference, tmp_path, reference_source="SYNTHETIC TEST")
    assert result["status"] == "succeeded"
    assert result["rmse"] == pytest.approx(np.sqrt(5 / 3))
    assert result["mae"] == pytest.approx(1.0)
    assert result["valid_pixel_count"] == 3
    assert json.loads((tmp_path / "metrics.json").read_text())["status"] == "succeeded"
    with rasterio.open(tmp_path / "error_map.tif") as error_map:
        assert error_map.crs.to_epsg() == 32643
        assert error_map.shape == (2, 2)
        assert error_map.nodata == -9999.0
        assert error_map.read(1)[0].tolist() == [1.0, 2.0]


def test_transform_mismatch_is_reprojected_to_prediction_grid(tmp_path):
    prediction = write_raster(tmp_path / "prediction.tif", np.arange(16).reshape(4, 4))
    reference = write_raster(tmp_path / "reference.tif", np.arange(4).reshape(2, 2),
                             transform=from_origin(500000, 2200000, 20, 20))
    result = validate_rasters(prediction, reference, tmp_path)
    assert result["alignment"]["reference_reprojected"] is True
    assert result["alignment"]["resampling"] == "bilinear"
    assert result["valid_pixel_count"] > 0


def test_crs_mismatch_is_geospatially_reprojected(tmp_path):
    prediction = write_raster(tmp_path / "prediction.tif", np.arange(16).reshape(4, 4),
                              crs="EPSG:4326", transform=from_origin(77, 13, 0.01, 0.01))
    reference = write_raster(tmp_path / "reference.tif", np.arange(16).reshape(4, 4),
                             crs="EPSG:3857", transform=from_origin(8571600, 1459732, 1200, 1200))
    result = validate_rasters(prediction, reference, tmp_path)
    assert result["alignment"]["reference_reprojected"] is True


def test_no_overlap_and_zero_valid_pixels_fail_cleanly(tmp_path):
    prediction = write_raster(tmp_path / "prediction.tif", np.ones((2, 2)))
    far = write_raster(tmp_path / "far.tif", np.ones((2, 2)),
                       transform=from_origin(900000, 900000, 10, 10))
    with pytest.raises(ValueError, match="no geographic overlap"):
        validate_rasters(prediction, far, tmp_path)
    empty = write_raster(tmp_path / "empty.tif", np.full((2, 2), -9999.0))
    with pytest.raises(ValueError, match="No valid overlapping"):
        validate_rasters(prediction, empty, tmp_path)
