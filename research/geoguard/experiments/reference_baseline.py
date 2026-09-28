#!/usr/bin/env python3
"""Evaluate an aligned coarse elevation reference against independent truth."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


OUTPUT_NODATA = -9999.0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--mask", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def _same_grid(left: Any, right: Any) -> bool:
    return (
        left.crs == right.crs
        and left.transform.almost_equals(right.transform)
        and left.width == right.width
        and left.height == right.height
    )


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Return one-based average ranks with deterministic tie handling."""

    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    starts = np.flatnonzero(
        np.concatenate(([True], sorted_values[1:] != sorted_values[:-1]))
    )
    ends = np.concatenate((starts[1:], [values.size]))
    average = (starts + ends - 1) / 2.0 + 1.0
    sorted_ranks = np.repeat(average, ends - starts)
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = sorted_ranks
    return ranks


def _pearson(left: np.ndarray, right: np.ndarray) -> float:
    if left.size < 2 or np.ptp(left) == 0 or np.ptp(right) == 0:
        return math.nan
    return float(np.corrcoef(left, right)[0, 1])


def compute_metrics(reference: np.ndarray, truth: np.ndarray) -> dict[str, float | int]:
    """Compute baseline metrics from already filtered one-dimensional arrays."""

    if reference.shape != truth.shape or reference.ndim != 1:
        raise ValueError("reference and truth must be same-length one-dimensional arrays")
    if reference.size == 0:
        raise ValueError("no common valid pixels")

    reference64 = reference.astype(np.float64, copy=False)
    truth64 = truth.astype(np.float64, copy=False)
    error = reference64 - truth64
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
        "bias": float(np.mean(error)),
        "pearson": _pearson(reference64, truth64),
        "spearman": _pearson(_average_ranks(reference64), _average_ranks(truth64)),
        "valid_pixel_count": int(reference.size),
    }


def run(reference_path: Path, truth_path: Path, mask_path: Path, output_dir: Path) -> dict[str, float | int]:
    output_dir.mkdir(parents=True, exist_ok=True)

    with (
        rasterio.open(reference_path) as reference_dataset,
        rasterio.open(truth_path) as truth_dataset,
        rasterio.open(mask_path) as mask_dataset,
    ):
        if not _same_grid(reference_dataset, truth_dataset) or not _same_grid(
            truth_dataset, mask_dataset
        ):
            raise ValueError("reference, truth, and mask must share one exact grid")
        if reference_dataset.count != 1 or truth_dataset.count != 1 or mask_dataset.count != 1:
            raise ValueError("reference, truth, and mask must each contain exactly one band")

        reference = reference_dataset.read(1, masked=True)
        truth = truth_dataset.read(1, masked=True)
        mask = mask_dataset.read(1, masked=True)
        reference_data = np.asarray(reference.data)
        truth_data = np.asarray(truth.data)
        common_valid = (
            (~np.ma.getmaskarray(reference))
            & (~np.ma.getmaskarray(truth))
            & (~np.ma.getmaskarray(mask))
            & np.isfinite(reference_data)
            & np.isfinite(truth_data)
            & (np.asarray(mask.data) != 0)
        )

        metrics = compute_metrics(reference_data[common_valid], truth_data[common_valid])
        metrics["valid_fraction"] = float(common_valid.mean())

        error = np.full(reference.shape, OUTPUT_NODATA, dtype=np.float32)
        error[common_valid] = (
            reference_data[common_valid].astype(np.float64)
            - truth_data[common_valid].astype(np.float64)
        ).astype(np.float32)
        absolute_error = np.full(reference.shape, OUTPUT_NODATA, dtype=np.float32)
        absolute_error[common_valid] = np.abs(error[common_valid])

        profile = truth_dataset.profile.copy()
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)
        profile.update(
            count=1,
            dtype="float32",
            nodata=OUTPUT_NODATA,
            compress="deflate",
            tiled=truth_dataset.width >= 16 and truth_dataset.height >= 16,
        )
        for name, data, description in (
            ("reference_error.tif", error, "reference minus truth"),
            ("reference_abs_error.tif", absolute_error, "absolute reference error"),
        ):
            with rasterio.open(output_dir / name, "w", **profile) as output:
                output.write(data, 1)
                output.set_band_unit(1, "metre")
                output.update_tags(
                    1,
                    units="metre",
                    analytical_value=description,
                    normalization="none",
                )

    with (output_dir / "reference_metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(metrics, stream, indent=2, allow_nan=True)
        stream.write("\n")
    return metrics


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        metrics = run(args.reference, args.truth, args.mask, args.output_dir)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(metrics, indent=2, allow_nan=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
