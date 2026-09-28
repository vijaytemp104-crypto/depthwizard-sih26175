from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


EXPERIMENTS = Path(__file__).parents[1] / "experiments"


def load_module(name: str):
    path = EXPERIMENTS / f"{name}.py"
    specification = importlib.util.spec_from_file_location(f"geoguard_{name}", path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


AFFINE = load_module("affine_candidate")
BENEFIT = load_module("benefit_map")


def test_exact_affine_relationship_recovers_coefficients_without_truth() -> None:
    depth = np.arange(1, 11, dtype=np.float64)
    reference = 3.25 * depth - 7.5
    a, b, _ = AFFINE.fit_affine_huber(depth, reference)
    assert np.isclose(a, 3.25)
    assert np.isclose(b, -7.5)
    assert "truth" not in AFFINE.fit_affine_huber.__code__.co_varnames


def test_support_pair_aggregation() -> None:
    depth = np.arange(16, dtype=np.float64).reshape(4, 4)
    reference = depth * 2
    valid = np.ones((4, 4), dtype=bool)
    support_depth, support_reference = AFFINE.aggregate_support_pairs(
        depth, reference, valid, support_pixels=2, minimum_coverage=1.0
    )
    np.testing.assert_allclose(support_depth, [2.5, 4.5, 10.5, 12.5])
    np.testing.assert_allclose(support_reference, 2 * support_depth)


def test_positive_negative_and_equal_benefit_are_signed_in_metres() -> None:
    truth = np.array([[10.0, 10.0, 10.0]])
    reference = np.array([[14.0, 11.0, 12.0]])
    candidate = np.array([[11.0, 14.0, 8.0]])
    valid = np.ones(reference.shape, dtype=bool)
    benefit = BENEFIT.compute_benefit(reference, candidate, truth, valid)
    np.testing.assert_allclose(benefit, [[3.0, -3.0, 0.0]])


def test_masked_invalid_pixels_are_excluded() -> None:
    truth = np.zeros((1, 2))
    reference = np.array([[2.0, 100.0]])
    candidate = np.array([[1.0, 0.0]])
    valid = np.array([[True, False]])
    benefit = BENEFIT.compute_benefit(reference, candidate, truth, valid)
    assert benefit[0, 0] == 1.0
    assert np.isnan(benefit[0, 1])
    summary = BENEFIT.summarize_benefit(benefit, valid, neutral_tolerance_m=0.25)
    assert summary["valid_pixel_count"] == 1


def test_support_cell_aggregation_and_oracle_acceptance() -> None:
    benefit = np.array([[2.0, 2.0, -3.0, -3.0], [2.0, 2.0, -3.0, -3.0]])
    valid = np.ones(benefit.shape, dtype=bool)
    cells, cell_valid, rows, columns = BENEFIT.aggregate_support_benefit(
        benefit, valid, support_pixels=2, minimum_coverage=1.0
    )
    np.testing.assert_allclose(cells, [[2.0, -3.0]])
    reference = np.full(benefit.shape, 10.0)
    candidate = np.full(benefit.shape, 20.0)
    oracle, accepted = BENEFIT.build_oracle_mosaic(
        reference, candidate, valid, cells, cell_valid, rows, columns
    )
    np.testing.assert_allclose(oracle[:, :2], 20.0)
    np.testing.assert_allclose(oracle[:, 2:], 10.0)
    assert accepted[:, :2].all()
    assert not accepted[:, 2:].any()


def test_benefit_values_retain_metric_magnitude() -> None:
    benefit = BENEFIT.compute_benefit(
        np.array([[5.75]]),
        np.array([[4.25]]),
        np.array([[4.0]]),
        np.array([[True]]),
    )
    assert benefit[0, 0] == 1.5


def test_written_analytical_benefit_band_unit_is_metres(tmp_path: Path) -> None:
    profile = {
        "driver": "GTiff",
        "height": 1,
        "width": 1,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32617",
        "transform": from_origin(500000, 4000000, 1, 1),
    }
    output = tmp_path / "benefit.tif"
    BENEFIT._write_float_raster(
        output, np.array([[1.5]]), profile, "test benefit"
    )
    with rasterio.open(output) as dataset:
        assert dataset.units[0] == "metre"
        assert dataset.read(1)[0, 0] == 1.5
