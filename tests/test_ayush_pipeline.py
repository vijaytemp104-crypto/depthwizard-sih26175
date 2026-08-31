import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from backend.services.ayush.calibration import apply_calibration, fit_calibration
from backend.services.ayush.depth import load_depth
from backend.services.ayush.geospatial import align_dem, depth_grid, load_dem
from backend.services.ayush.pipeline import run_pipeline
from backend.services.ayush.sample_data import generate_sample_data


def test_synthetic_calibration_recovers_linear_mapping():
    depth = np.linspace(0.1, 1.0, 100, dtype=np.float32).reshape(10, 10)
    dem = 82.5 * depth + 510.0
    result = fit_calibration(depth, dem)
    assert result.slope == pytest.approx(82.5, rel=1e-6)
    assert result.intercept == pytest.approx(510.0, rel=1e-6)
    assert result.valid_pixels == 100
    assert np.allclose(apply_calibration(depth, result), dem)


def test_dem_loading_reports_metadata(tmp_path):
    _, dem_path = generate_sample_data(tmp_path)
    dem, metadata = load_dem(dem_path)
    assert dem.shape == (48, 64)
    assert metadata.crs == "EPSG:32643"
    assert metadata.resolution == (20.0, 20.0)
    assert np.isnan(dem[0, 0])


def test_alignment_handles_dimensions_resolution_and_crs(tmp_path):
    _, dem_path = generate_sample_data(tmp_path)
    _, meta = load_dem(dem_path)
    target_crs, transform, _ = depth_grid(tmp_path / "no-sidecar.npy", (96, 128), meta)
    aligned, _, changed = align_dem(dem_path, (96, 128), target_crs, transform)
    assert aligned.shape == (96, 128)
    assert changed is True
    # A deliberately different target CRS must be reprojected, never silently relabelled.
    transformed, _, changed_crs = align_dem(dem_path, (24, 32), rasterio.crs.CRS.from_epsg(4326), from_origin(77, 20, 0.001, 0.001))
    assert transformed.shape == (24, 32)
    assert changed_crs is True


def test_pipeline_creates_reopenable_dsm_and_json(tmp_path):
    depth_path, dem_path = generate_sample_data(tmp_path / "samples")
    outputs = run_pipeline(depth_path, dem_path, tmp_path / "outputs")
    with rasterio.open(outputs["dsm"]) as dsm:
        assert dsm.shape == (96, 128)
        assert dsm.crs.to_epsg() == 32643
        assert dsm.nodata == -9999.0
        assert dsm.read(1)[4, 8] == dsm.nodata
    calibration = json.loads(outputs["calibration"].read_text())
    assert calibration["coefficients"]["a"] == pytest.approx(115.0, rel=0.03)
    assert calibration["reference"]["resampled_or_reprojected"] is True
    terrain = json.loads(outputs["terrain"].read_text())
    assert (terrain["height"], terrain["width"]) == (96, 128)
    assert terrain["elevation"][4][8] is None


def test_invalid_depth_values_and_shapes(tmp_path):
    path = tmp_path / "depth.npy"
    np.save(path, np.array([[1.0, np.nan], [np.inf, 2.0]], dtype=np.float32))
    depth = load_depth(path)
    dem = np.array([[10.0, 20.0], [30.0, 12.0]], dtype=np.float32)
    result = fit_calibration(depth, dem)
    assert result.valid_pixels == 2
    calibrated = apply_calibration(depth, result)
    assert np.isnan(calibrated[0, 1]) and np.isnan(calibrated[1, 0])

    np.save(path, np.zeros((2, 2, 2), dtype=np.float32))
    with pytest.raises(ValueError, match="2-D"):
        load_depth(path)
    with pytest.raises(ValueError, match="shapes differ"):
        fit_calibration(np.ones((2, 2)), np.ones((3, 3)))
