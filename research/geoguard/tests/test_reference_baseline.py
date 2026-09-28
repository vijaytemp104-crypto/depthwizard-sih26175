from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


MODULE_PATH = Path(__file__).parents[1] / "experiments" / "reference_baseline.py"
SPEC = importlib.util.spec_from_file_location("geoguard_reference_baseline", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load baseline from {MODULE_PATH}")
BASELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASELINE)


def write_raster(path: Path, values: np.ndarray, *, nodata: float | int) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype=values.dtype,
        crs="EPSG:32617",
        transform=from_origin(500000, 4000000, 1, 1),
        nodata=nodata,
    ) as dataset:
        dataset.write(values, 1)


def run_case(
    tmp_path: Path,
    reference: np.ndarray,
    truth: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict[str, float | int]:
    if mask is None:
        mask = np.ones(reference.shape, dtype=np.uint8)
    write_raster(tmp_path / "reference.tif", reference.astype(np.float32), nodata=-9999.0)
    write_raster(tmp_path / "truth.tif", truth.astype(np.float32), nodata=-9999.0)
    write_raster(tmp_path / "mask.tif", mask.astype(np.uint8), nodata=0)
    return BASELINE.run(
        tmp_path / "reference.tif",
        tmp_path / "truth.tif",
        tmp_path / "mask.tif",
        tmp_path / "output",
    )


def test_perfect_reference_has_zero_error(tmp_path: Path) -> None:
    truth = np.array([[1, 2], [3, 4]], dtype=np.float32)
    metrics = run_case(tmp_path, truth.copy(), truth)
    assert metrics["mae"] == 0
    assert metrics["rmse"] == 0
    assert metrics["bias"] == 0


def test_known_constant_offset_is_exact(tmp_path: Path) -> None:
    truth = np.array([[1, 2], [3, 4]], dtype=np.float32)
    metrics = run_case(tmp_path, truth + 2.5, truth)
    assert metrics["mae"] == 2.5
    assert metrics["rmse"] == 2.5
    assert metrics["bias"] == 2.5


def test_mask_and_nodata_are_excluded(tmp_path: Path) -> None:
    truth = np.array([[1, 2], [3, -9999]], dtype=np.float32)
    reference = np.array([[1, 102], [13, -9999]], dtype=np.float32)
    mask = np.array([[1, 0], [1, 1]], dtype=np.uint8)
    metrics = run_case(tmp_path, reference, truth, mask)
    assert metrics["valid_pixel_count"] == 2
    assert metrics["mae"] == 5
    assert metrics["rmse"] == math.sqrt(50)
    assert metrics["bias"] == 5


def test_constant_arrays_report_undefined_correlations(tmp_path: Path) -> None:
    reference = np.full((2, 2), 7, dtype=np.float32)
    truth = np.full((2, 2), 3, dtype=np.float32)
    metrics = run_case(tmp_path, reference, truth)
    assert math.isnan(metrics["pearson"])
    assert math.isnan(metrics["spearman"])
