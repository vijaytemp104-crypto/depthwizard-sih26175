"""Metric elevation calibration for relative monocular depth."""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class CalibrationResult:
    method: str
    slope: float
    intercept: float
    valid_pixels: int
    rmse_metres: float
    r_squared: float

    def to_dict(self) -> dict:
        result = asdict(self)
        result["coefficients"] = {"a": result.pop("slope"), "b": result.pop("intercept")}
        return result


def fit_calibration(depth: np.ndarray, elevation: np.ndarray) -> CalibrationResult:
    if depth.shape != elevation.shape:
        raise ValueError(f"Depth and DEM shapes differ: {depth.shape} vs {elevation.shape}")
    valid = np.isfinite(depth) & np.isfinite(elevation)
    count = int(valid.sum())
    if count < 2:
        raise ValueError("At least two valid depth/elevation pairs are required")
    x = depth[valid].astype(np.float64)
    y = elevation[valid].astype(np.float64)
    if np.ptp(x) <= np.finfo(np.float32).eps:
        raise ValueError("Valid depth values have no variation; calibration is undefined")

    # Ordinary least squares learns a metric anchor without copying the DEM.
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    residual = y - predicted
    rmse = float(np.sqrt(np.mean(residual**2)))
    total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - float(np.sum(residual**2)) / total if total > 0 else 1.0
    return CalibrationResult("ordinary_least_squares", float(slope), float(intercept), count, rmse, r_squared)


def apply_calibration(depth: np.ndarray, result: CalibrationResult) -> np.ndarray:
    output = np.full(depth.shape, np.nan, dtype=np.float32)
    valid = np.isfinite(depth)
    output[valid] = result.slope * depth[valid] + result.intercept
    return output
