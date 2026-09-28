#!/usr/bin/env python3
"""Fit relative depth to a coarse elevation reference without using truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


OUTPUT_NODATA = -9999.0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relative-depth", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--mask", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--reference-resolution-m", type=float, default=30.0)
    parser.add_argument("--minimum-support-coverage", type=float, default=0.8)
    return parser.parse_args(argv)


def _same_grid(left: Any, right: Any) -> bool:
    return (
        left.crs == right.crs
        and left.transform.almost_equals(right.transform)
        and left.width == right.width
        and left.height == right.height
    )


def _partitions(length: int, approximate_size: int) -> list[np.ndarray]:
    count = max(1, int(np.ceil(length / approximate_size)))
    return [part for part in np.array_split(np.arange(length), count) if part.size]


def aggregate_support_pairs(
    relative_depth: np.ndarray,
    reference: np.ndarray,
    valid: np.ndarray,
    support_pixels: int,
    minimum_coverage: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Average paired values over approximately native-reference support cells."""

    if relative_depth.shape != reference.shape or valid.shape != reference.shape:
        raise ValueError("relative depth, reference, and valid mask must share a shape")
    if relative_depth.ndim != 2:
        raise ValueError("input arrays must be two-dimensional")
    if support_pixels < 1:
        raise ValueError("support_pixels must be positive")
    if not 0 < minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be in (0, 1]")

    depth_values: list[float] = []
    reference_values: list[float] = []
    for rows in _partitions(relative_depth.shape[0], support_pixels):
        for columns in _partitions(relative_depth.shape[1], support_pixels):
            selection = np.ix_(rows, columns)
            cell_valid = valid[selection]
            if float(cell_valid.mean()) < minimum_coverage:
                continue
            depth_values.append(float(np.mean(relative_depth[selection][cell_valid])))
            reference_values.append(float(np.mean(reference[selection][cell_valid])))
    if len(depth_values) < 3:
        raise ValueError("fewer than three valid coarse-support observations")
    return np.asarray(depth_values), np.asarray(reference_values)


def fit_affine_huber(
    relative_depth: np.ndarray,
    elevation: np.ndarray,
    *,
    huber_delta: float = 1.345,
    maximum_iterations: int = 50,
    tolerance: float = 1e-10,
) -> tuple[float, float, int]:
    """Fit elevation = a * relative_depth + b with Huber IRLS."""

    depth = np.asarray(relative_depth, dtype=np.float64).reshape(-1)
    target = np.asarray(elevation, dtype=np.float64).reshape(-1)
    finite = np.isfinite(depth) & np.isfinite(target)
    depth = depth[finite]
    target = target[finite]
    if depth.size < 3 or np.ptp(depth) == 0:
        raise ValueError("at least three finite observations with depth variation are required")

    design = np.column_stack((depth, np.ones(depth.size)))
    coefficients = np.linalg.lstsq(design, target, rcond=None)[0]
    iteration = 0
    for iteration in range(1, maximum_iterations + 1):
        residual = target - design @ coefficients
        median = np.median(residual)
        scale = 1.4826 * np.median(np.abs(residual - median))
        if not np.isfinite(scale) or scale <= np.finfo(np.float64).eps:
            break
        threshold = huber_delta * scale
        absolute = np.abs(residual)
        weights = np.ones_like(absolute)
        outliers = absolute > threshold
        weights[outliers] = threshold / absolute[outliers]
        root_weights = np.sqrt(weights)
        updated = np.linalg.lstsq(
            design * root_weights[:, None], target * root_weights, rcond=None
        )[0]
        if np.max(np.abs(updated - coefficients)) <= tolerance:
            coefficients = updated
            break
        coefficients = updated
    return float(coefficients[0]), float(coefficients[1]), iteration


def run(
    relative_depth_path: Path,
    reference_path: Path,
    mask_path: Path,
    output_dir: Path,
    *,
    reference_resolution_m: float = 30.0,
    minimum_support_coverage: float = 0.8,
) -> dict[str, float | int | str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (
        rasterio.open(relative_depth_path) as depth_dataset,
        rasterio.open(reference_path) as reference_dataset,
        rasterio.open(mask_path) as mask_dataset,
    ):
        if not _same_grid(depth_dataset, reference_dataset) or not _same_grid(
            reference_dataset, mask_dataset
        ):
            raise ValueError("relative depth, reference, and mask must share one exact grid")
        relative = depth_dataset.read(1, masked=True)
        reference = reference_dataset.read(1, masked=True)
        mask = mask_dataset.read(1, masked=True)
        relative_data = np.asarray(relative.data)
        reference_data = np.asarray(reference.data)
        valid = (
            ~np.ma.getmaskarray(relative)
            & ~np.ma.getmaskarray(reference)
            & ~np.ma.getmaskarray(mask)
            & np.isfinite(relative_data)
            & np.isfinite(reference_data)
            & (np.asarray(mask.data) != 0)
        )

        pixel_size = float(np.mean(np.abs(depth_dataset.res)))
        support_pixels = max(1, int(round(reference_resolution_m / pixel_size)))
        support_depth, support_reference = aggregate_support_pairs(
            relative_data,
            reference_data,
            valid,
            support_pixels,
            minimum_support_coverage,
        )
        a, b, iterations = fit_affine_huber(support_depth, support_reference)
        support_residual = a * support_depth + b - support_reference

        candidate = np.full(relative.shape, OUTPUT_NODATA, dtype=np.float32)
        candidate[valid] = (a * relative_data[valid] + b).astype(np.float32)
        profile = depth_dataset.profile.copy()
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)
        profile.update(count=1, dtype="float32", nodata=OUTPUT_NODATA, compress="deflate")
        output_path = output_dir / "ai_candidate_affine.tif"
        with rasterio.open(output_path, "w", **profile) as output:
            output.write(candidate, 1)
            output.set_band_unit(1, "metre")
            output.update_tags(
                1,
                units="metre",
                calibration_source="coarse reference only; independent truth not used",
                calibration_method="Huber IRLS at approximate native-reference support",
                normalization="none",
            )

    metrics: dict[str, float | int | str] = {
        "fitting_method": "Huber IRLS on support-cell means",
        "truth_used_for_fit": "no",
        "reference_resolution_m": reference_resolution_m,
        "support_pixels": support_pixels,
        "minimum_support_coverage": minimum_support_coverage,
        "support_observation_count": int(support_depth.size),
        "a": a,
        "b": b,
        "iterations": iterations,
        "support_residual_mae": float(np.mean(np.abs(support_residual))),
        "support_residual_rmse": float(np.sqrt(np.mean(np.square(support_residual)))),
        "support_residual_bias": float(np.mean(support_residual)),
    }
    with (output_dir / "affine_fit.json").open("w", encoding="utf-8") as stream:
        json.dump(metrics, stream, indent=2)
        stream.write("\n")
    return metrics


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        metrics = run(
            args.relative_depth,
            args.reference,
            args.mask,
            args.output_dir,
            reference_resolution_m=args.reference_resolution_m,
            minimum_support_coverage=args.minimum_support_coverage,
        )
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
