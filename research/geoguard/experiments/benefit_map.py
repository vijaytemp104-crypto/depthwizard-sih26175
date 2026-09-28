#!/usr/bin/env python3
"""Evaluate a candidate and create truth-aware GeoGuard benefit diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.transform import from_bounds


OUTPUT_NODATA = -9999.0
MASK_NODATA = 255


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--mask", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--support-size-m", type=float, default=30.0)
    parser.add_argument("--minimum-support-coverage", type=float, default=0.8)
    parser.add_argument("--neutral-tolerance-m", type=float, default=0.25)
    return parser.parse_args(argv)


def _same_grid(left: Any, right: Any) -> bool:
    return (
        left.crs == right.crs
        and left.transform.almost_equals(right.transform)
        and left.width == right.width
        and left.height == right.height
    )


def _average_ranks(values: np.ndarray) -> np.ndarray:
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


def _correlation(left: np.ndarray, right: np.ndarray) -> float:
    if left.size < 2 or np.ptp(left) == 0 or np.ptp(right) == 0:
        return math.nan
    return float(np.corrcoef(left, right)[0, 1])


def elevation_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | int]:
    prediction64 = np.asarray(prediction, dtype=np.float64).reshape(-1)
    truth64 = np.asarray(truth, dtype=np.float64).reshape(-1)
    if prediction64.shape != truth64.shape or prediction64.size == 0:
        raise ValueError("prediction and truth must contain the same nonzero number of values")
    error = prediction64 - truth64
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
        "bias": float(np.mean(error)),
        "pearson": _correlation(prediction64, truth64),
        "spearman": _correlation(
            _average_ranks(prediction64), _average_ranks(truth64)
        ),
        "valid_pixel_count": int(prediction64.size),
    }


def compute_benefit(
    reference: np.ndarray,
    candidate: np.ndarray,
    truth: np.ndarray,
    valid: np.ndarray,
) -> np.ndarray:
    """Return absolute-reference-error minus absolute-candidate-error in metres."""

    if not (reference.shape == candidate.shape == truth.shape == valid.shape):
        raise ValueError("reference, candidate, truth, and valid mask must share a shape")
    benefit = np.full(reference.shape, np.nan, dtype=np.float64)
    benefit[valid] = np.abs(reference[valid] - truth[valid]) - np.abs(
        candidate[valid] - truth[valid]
    )
    return benefit


def summarize_benefit(
    benefit: np.ndarray,
    valid: np.ndarray,
    neutral_tolerance_m: float,
) -> dict[str, float | int]:
    values = np.asarray(benefit[valid], dtype=np.float64)
    if values.size == 0:
        raise ValueError("no valid benefit pixels")
    helped = values > neutral_tolerance_m
    harmed = values < -neutral_tolerance_m
    neutral = ~(helped | harmed)
    percentiles = np.percentile(values, [5, 25, 75, 95])
    harm_magnitude = -values[harmed]
    return {
        "valid_pixel_count": int(values.size),
        "neutral_tolerance_m": neutral_tolerance_m,
        "helped_percent": float(100 * helped.mean()),
        "harmed_percent": float(100 * harmed.mean()),
        "neutral_percent": float(100 * neutral.mean()),
        "mean_benefit": float(np.mean(values)),
        "median_benefit": float(np.median(values)),
        "p05_benefit": float(percentiles[0]),
        "p25_benefit": float(percentiles[1]),
        "p75_benefit": float(percentiles[2]),
        "p95_benefit": float(percentiles[3]),
        "mean_helped_benefit": float(np.mean(values[helped])) if helped.any() else math.nan,
        "mean_harm_magnitude": float(np.mean(harm_magnitude)) if harmed.any() else math.nan,
        "p95_harm_magnitude": float(np.percentile(harm_magnitude, 95)) if harmed.any() else math.nan,
    }


def _partitions(length: int, approximate_size: int) -> list[np.ndarray]:
    count = max(1, int(np.ceil(length / approximate_size)))
    return [part for part in np.array_split(np.arange(length), count) if part.size]


def aggregate_support_benefit(
    benefit: np.ndarray,
    valid: np.ndarray,
    support_pixels: int,
    minimum_coverage: float,
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[np.ndarray]]:
    rows = _partitions(benefit.shape[0], support_pixels)
    columns = _partitions(benefit.shape[1], support_pixels)
    cell_benefit = np.full((len(rows), len(columns)), np.nan, dtype=np.float64)
    cell_valid = np.zeros(cell_benefit.shape, dtype=bool)
    for row_index, row_values in enumerate(rows):
        for column_index, column_values in enumerate(columns):
            selection = np.ix_(row_values, column_values)
            local_valid = valid[selection]
            if float(local_valid.mean()) < minimum_coverage:
                continue
            cell_benefit[row_index, column_index] = float(
                np.mean(benefit[selection][local_valid])
            )
            cell_valid[row_index, column_index] = True
    return cell_benefit, cell_valid, rows, columns


def build_oracle_mosaic(
    reference: np.ndarray,
    candidate: np.ndarray,
    valid: np.ndarray,
    cell_benefit: np.ndarray,
    cell_valid: np.ndarray,
    rows: list[np.ndarray],
    columns: list[np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Select candidate only in truth-known beneficial support cells."""

    oracle = np.asarray(reference, dtype=np.float64).copy()
    accepted = np.zeros(reference.shape, dtype=bool)
    for row_index, row_values in enumerate(rows):
        for column_index, column_values in enumerate(columns):
            if not cell_valid[row_index, column_index] or cell_benefit[row_index, column_index] <= 0:
                continue
            selection = np.ix_(row_values, column_values)
            local_valid = valid[selection]
            local_oracle = oracle[selection]
            local_candidate = candidate[selection]
            local_oracle[local_valid] = local_candidate[local_valid]
            oracle[selection] = local_oracle
            local_accepted = accepted[selection]
            local_accepted[local_valid] = True
            accepted[selection] = local_accepted
    return oracle, accepted


def _write_float_raster(path: Path, data: np.ndarray, profile: dict[str, Any], description: str) -> None:
    output = np.full(data.shape, OUTPUT_NODATA, dtype=np.float32)
    finite = np.isfinite(data)
    output[finite] = data[finite].astype(np.float32)
    local_profile = profile.copy()
    local_profile.pop("blockxsize", None)
    local_profile.pop("blockysize", None)
    local_profile.update(count=1, dtype="float32", nodata=OUTPUT_NODATA, compress="deflate")
    with rasterio.open(path, "w", **local_profile) as dataset:
        dataset.write(output, 1)
        dataset.set_band_unit(1, "metre")
        dataset.update_tags(1, units="metre", analytical_value=description, normalization="none")


def _write_visualization(path: Path, benefit: np.ndarray, valid: np.ndarray) -> None:
    from PIL import Image

    values = np.abs(benefit[valid])
    limit = max(float(np.percentile(values, 95)), 1e-6)
    scaled = np.clip(benefit / limit, -1, 1)
    image = np.full((*benefit.shape, 3), 224, dtype=np.uint8)
    positive = valid & (scaled >= 0)
    negative = valid & (scaled < 0)
    strength = np.abs(scaled)
    image[positive, 0] = (245 * (1 - strength[positive])).astype(np.uint8)
    image[positive, 1] = (245 - 90 * strength[positive]).astype(np.uint8)
    image[positive, 2] = (245 - 115 * strength[positive]).astype(np.uint8)
    image[negative, 0] = 245
    image[negative, 1] = (245 * (1 - strength[negative])).astype(np.uint8)
    image[negative, 2] = (245 * (1 - strength[negative])).astype(np.uint8)
    Image.fromarray(image, "RGB").save(path)


def run(
    reference_path: Path,
    candidate_path: Path,
    truth_path: Path,
    mask_path: Path,
    output_dir: Path,
    *,
    support_size_m: float = 30.0,
    minimum_support_coverage: float = 0.8,
    neutral_tolerance_m: float = 0.25,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (
        rasterio.open(reference_path) as reference_dataset,
        rasterio.open(candidate_path) as candidate_dataset,
        rasterio.open(truth_path) as truth_dataset,
        rasterio.open(mask_path) as mask_dataset,
    ):
        if not all(
            _same_grid(reference_dataset, item)
            for item in (candidate_dataset, truth_dataset, mask_dataset)
        ):
            raise ValueError("reference, candidate, truth, and mask must share one exact grid")
        reference = reference_dataset.read(1, masked=True)
        candidate = candidate_dataset.read(1, masked=True)
        truth = truth_dataset.read(1, masked=True)
        mask = mask_dataset.read(1, masked=True)
        arrays = [np.asarray(item.data) for item in (reference, candidate, truth)]
        valid = (
            ~np.ma.getmaskarray(reference)
            & ~np.ma.getmaskarray(candidate)
            & ~np.ma.getmaskarray(truth)
            & ~np.ma.getmaskarray(mask)
            & np.isfinite(arrays[0])
            & np.isfinite(arrays[1])
            & np.isfinite(arrays[2])
            & (np.asarray(mask.data) != 0)
        )
        benefit = compute_benefit(arrays[0], arrays[1], arrays[2], valid)
        reference_metrics = elevation_metrics(arrays[0][valid], arrays[2][valid])
        candidate_metrics = elevation_metrics(arrays[1][valid], arrays[2][valid])
        benefit_metrics = summarize_benefit(benefit, valid, neutral_tolerance_m)

        pixel_size = float(np.mean(np.abs(reference_dataset.res)))
        support_pixels = max(1, int(round(support_size_m / pixel_size)))
        cell_benefit, cell_valid, rows, columns = aggregate_support_benefit(
            benefit, valid, support_pixels, minimum_support_coverage
        )
        scored = cell_benefit[cell_valid]
        oracle, accepted = build_oracle_mosaic(
            arrays[0], arrays[1], valid, cell_benefit, cell_valid, rows, columns
        )
        oracle_metrics = elevation_metrics(oracle[valid], arrays[2][valid])

        profile = truth_dataset.profile.copy()
        analytical_benefit = np.full(benefit.shape, np.nan)
        analytical_benefit[valid] = benefit[valid]
        _write_float_raster(
            output_dir / "benefit_absolute_error.tif",
            analytical_benefit,
            profile,
            "absolute reference error minus absolute candidate error",
        )
        strict_help = np.full(valid.shape, MASK_NODATA, dtype=np.uint8)
        strict_harm = np.full(valid.shape, MASK_NODATA, dtype=np.uint8)
        strict_help[valid] = (benefit[valid] > 0).astype(np.uint8)
        strict_harm[valid] = (benefit[valid] < 0).astype(np.uint8)
        mask_profile = profile.copy()
        mask_profile.pop("blockxsize", None)
        mask_profile.pop("blockysize", None)
        mask_profile.update(count=1, dtype="uint8", nodata=MASK_NODATA, compress="deflate")
        for name, data, meaning in (
            ("help_mask.tif", strict_help, "1 where candidate absolute error is lower"),
            ("harm_mask.tif", strict_harm, "1 where candidate absolute error is higher"),
        ):
            with rasterio.open(output_dir / name, "w", **mask_profile) as dataset:
                dataset.write(data, 1)
                dataset.update_tags(1, units="dimensionless", analytical_value=meaning)
        _write_float_raster(
            output_dir / "oracle_mosaic.tif",
            np.where(valid, oracle, np.nan),
            profile,
            "truth-aware support-cell oracle; not deployable",
        )

        support_profile = profile.copy()
        support_profile.pop("blockxsize", None)
        support_profile.pop("blockysize", None)
        support_profile.update(
            height=cell_benefit.shape[0],
            width=cell_benefit.shape[1],
            transform=from_bounds(*truth_dataset.bounds, cell_benefit.shape[1], cell_benefit.shape[0]),
        )
        _write_float_raster(
            output_dir / "support_cell_benefit.tif",
            cell_benefit,
            support_profile,
            "mean pixel benefit per approximately native-reference support cell",
        )
        _write_visualization(output_dir / "benefit_help_harm.png", benefit, valid)

    result: dict[str, Any] = {
        "reference": reference_metrics,
        "candidate": candidate_metrics,
        "delta_mae_m": candidate_metrics["mae"] - reference_metrics["mae"],
        "delta_rmse_m": candidate_metrics["rmse"] - reference_metrics["rmse"],
        "delta_bias_m": candidate_metrics["bias"] - reference_metrics["bias"],
        "mae_improvement_percent": 100 * (reference_metrics["mae"] - candidate_metrics["mae"]) / reference_metrics["mae"],
        "rmse_improvement_percent": 100 * (reference_metrics["rmse"] - candidate_metrics["rmse"]) / reference_metrics["rmse"],
        "benefit": benefit_metrics,
        "support": {
            "approximate_support_size_m": support_size_m,
            "support_pixels": support_pixels,
            "minimum_valid_coverage": minimum_support_coverage,
            "scored_cell_count": int(scored.size),
            "beneficial_cell_percent": float(100 * np.mean(scored > 0)),
            "harmful_cell_percent": float(100 * np.mean(scored < 0)),
            "neutral_cell_percent": float(100 * np.mean(scored == 0)),
            "mean_benefit": float(np.mean(scored)),
            "median_benefit": float(np.median(scored)),
            "p05_benefit": float(np.percentile(scored, 5)),
            "p25_benefit": float(np.percentile(scored, 25)),
            "p75_benefit": float(np.percentile(scored, 75)),
            "p95_benefit": float(np.percentile(scored, 95)),
        },
        "oracle": {
            **oracle_metrics,
            "accepted_pixel_count": int(accepted.sum()),
            "accepted_coverage_percent": float(100 * accepted.sum() / valid.sum()),
            "mae_improvement_percent": 100 * (reference_metrics["mae"] - oracle_metrics["mae"]) / reference_metrics["mae"],
            "rmse_improvement_percent": 100 * (reference_metrics["rmse"] - oracle_metrics["rmse"]) / reference_metrics["rmse"],
            "label": "TRUTH-AWARE ORACLE — NOT DEPLOYABLE",
        },
    }
    with (output_dir / "benefit_metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=True)
        stream.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        metrics = run(
            args.reference,
            args.candidate,
            args.truth,
            args.mask,
            args.output_dir,
            support_size_m=args.support_size_m,
            minimum_support_coverage=args.minimum_support_coverage,
            neutral_tolerance_m=args.neutral_tolerance_m,
        )
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(metrics, indent=2, allow_nan=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
