"""Evaluation, benefit analysis, oracle construction, and cross-fold reporting."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import torch

from config import CONFIG, GEOGUARD_ROOT, OUTPUT_ROOT, TrainingConfig
from dataset import SceneArrays, patch_starts
from model import ResidualUNet


NODATA = -9999.0


def _load_affine_module():
    path = GEOGUARD_ROOT / "experiments" / "affine_candidate.py"
    specification = importlib.util.spec_from_file_location("geoguard_affine_candidate", path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    starts = np.flatnonzero(np.r_[True, sorted_values[1:] != sorted_values[:-1]])
    ends = np.r_[starts[1:], values.size]
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.repeat((starts + ends - 1) / 2 + 1, ends - starts)
    return ranks


def _correlation(left: np.ndarray, right: np.ndarray) -> float:
    if left.size < 2 or np.ptp(left) == 0 or np.ptp(right) == 0:
        return math.nan
    return float(np.corrcoef(left, right)[0, 1])


def elevation_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | int]:
    prediction = np.asarray(prediction, dtype=np.float64).reshape(-1)
    truth = np.asarray(truth, dtype=np.float64).reshape(-1)
    error = prediction - truth
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
        "bias": float(np.mean(error)),
        "pearson": _correlation(prediction, truth),
        "spearman": _correlation(_average_ranks(prediction), _average_ranks(truth)),
        "valid_pixel_count": int(prediction.size),
    }


def compute_pixel_benefit(
    reference: np.ndarray, candidate: np.ndarray, truth: np.ndarray, valid: np.ndarray
) -> np.ndarray:
    benefit = np.full(reference.shape, np.nan, dtype=np.float64)
    benefit[valid] = np.abs(reference[valid] - truth[valid]) - np.abs(
        candidate[valid] - truth[valid]
    )
    return benefit


def summarize_pixel_benefit(benefit: np.ndarray, valid: np.ndarray) -> dict[str, float]:
    values = benefit[valid]
    helped = values > 0
    harmed = values < 0
    harm = -values[harmed]
    return {
        "helped_percent": float(100 * helped.mean()),
        "harmed_percent": float(100 * harmed.mean()),
        "neutral_percent": float(100 * (~(helped | harmed)).mean()),
        "mean_benefit_m": float(values.mean()),
        "median_benefit_m": float(np.median(values)),
        "mean_harm_magnitude_m": float(harm.mean()) if harm.size else math.nan,
        "p95_harm_magnitude_m": float(np.percentile(harm, 95)) if harm.size else math.nan,
    }


def support_oracle(
    reference: np.ndarray,
    candidate: np.ndarray,
    truth: np.ndarray,
    valid: np.ndarray,
    *,
    support_pixels: int,
    minimum_coverage: float,
) -> tuple[np.ndarray, dict[str, float]]:
    benefit = compute_pixel_benefit(reference, candidate, truth, valid)
    oracle = reference.copy()
    accepted = np.zeros(valid.shape, dtype=bool)
    cell_values: list[float] = []
    row_partitions = np.array_split(
        np.arange(valid.shape[0]), max(1, int(np.ceil(valid.shape[0] / support_pixels)))
    )
    column_partitions = np.array_split(
        np.arange(valid.shape[1]), max(1, int(np.ceil(valid.shape[1] / support_pixels)))
    )
    for rows in row_partitions:
        for columns in column_partitions:
            selection = np.ix_(rows, columns)
            local_valid = valid[selection]
            if float(local_valid.mean()) < minimum_coverage:
                continue
            cell_benefit = float(benefit[selection][local_valid].mean())
            cell_values.append(cell_benefit)
            if cell_benefit > 0:
                local_oracle = oracle[selection]
                local_candidate = candidate[selection]
                local_oracle[local_valid] = local_candidate[local_valid]
                oracle[selection] = local_oracle
                local_accepted = accepted[selection]
                local_accepted[local_valid] = True
                accepted[selection] = local_accepted
    cells = np.asarray(cell_values, dtype=np.float64)
    details = {
        "scored_cell_count": int(cells.size),
        "beneficial_cells_percent": float(100 * np.mean(cells > 0)),
        "harmful_cells_percent": float(100 * np.mean(cells < 0)),
        "neutral_cells_percent": float(100 * np.mean(cells == 0)),
        "oracle_coverage_percent": float(100 * accepted[valid].mean()),
    }
    return oracle, details


def predict_tiled(
    model: torch.nn.Module,
    features: np.ndarray,
    *,
    patch_size: int,
    stride: int,
    device: torch.device,
) -> np.ndarray:
    height, width = features.shape[1:]
    total = np.zeros((height, width), dtype=np.float64)
    count = np.zeros((height, width), dtype=np.uint16)
    model.eval()
    with torch.inference_mode():
        for row in patch_starts(height, patch_size, stride):
            for column in patch_starts(width, patch_size, stride):
                patch = torch.from_numpy(
                    features[:, row : row + patch_size, column : column + patch_size][None]
                ).to(device)
                prediction = model(patch)[0, 0].cpu().numpy()
                total[row : row + patch_size, column : column + patch_size] += prediction
                count[row : row + patch_size, column : column + patch_size] += 1
    if np.any(count == 0):
        raise RuntimeError("tiled prediction left uncovered pixels")
    return (total / count).astype(np.float32)


def _write_raster(path: Path, values: np.ndarray, valid: np.ndarray, profile: dict, units: str) -> None:
    output = np.full(values.shape, NODATA, dtype=np.float32)
    output[valid] = values[valid].astype(np.float32)
    local = profile.copy()
    local.pop("blockxsize", None)
    local.pop("blockysize", None)
    local.update(count=1, dtype="float32", nodata=NODATA, compress="deflate")
    with rasterio.open(path, "w", **local) as dataset:
        dataset.write(output, 1)
        dataset.set_band_unit(1, units)
        dataset.update_tags(1, units=units)


def affine_candidate(scene: SceneArrays, config: TrainingConfig) -> tuple[np.ndarray, dict]:
    affine = _load_affine_module()
    depth = scene.features[4]  # normalized relative depth; affine fit is invariant to linear normalization
    support_pixels = int(round(config.support_size_m))
    support_depth, support_reference = affine.aggregate_support_pairs(
        depth, scene.reference_m, scene.valid, support_pixels, config.support_minimum_coverage
    )
    a, b, iterations = affine.fit_affine_huber(support_depth, support_reference)
    return (a * depth + b).astype(np.float32), {"a": a, "b": b, "iterations": iterations}


def evaluate_fold(
    held_out: str,
    model: ResidualUNet,
    scene: SceneArrays,
    device: torch.device,
    config: TrainingConfig = CONFIG,
) -> dict[str, Any]:
    output_dir = OUTPUT_ROOT / f"holdout_{held_out}"
    output_dir.mkdir(parents=True, exist_ok=True)
    residual = predict_tiled(
        model,
        scene.features,
        patch_size=config.patch_size,
        stride=config.patch_stride,
        device=device,
    )
    candidate = scene.reference_m + residual
    affine, affine_fit = affine_candidate(scene, config)
    valid = scene.valid
    reference_metrics = elevation_metrics(scene.reference_m[valid], scene.truth_m[valid])
    affine_metrics = elevation_metrics(affine[valid], scene.truth_m[valid])
    residual_metrics = elevation_metrics(candidate[valid], scene.truth_m[valid])
    benefit = compute_pixel_benefit(scene.reference_m, candidate, scene.truth_m, valid)
    benefit_metrics = summarize_pixel_benefit(benefit, valid)
    support_pixels = max(1, int(round(config.support_size_m)))
    oracle, support = support_oracle(
        scene.reference_m,
        candidate,
        scene.truth_m,
        valid,
        support_pixels=support_pixels,
        minimum_coverage=config.support_minimum_coverage,
    )
    oracle_metrics = elevation_metrics(oracle[valid], scene.truth_m[valid])
    affine_benefit = compute_pixel_benefit(scene.reference_m, affine, scene.truth_m, valid)
    affine_benefit_metrics = summarize_pixel_benefit(affine_benefit, valid)
    affine_oracle, affine_support = support_oracle(
        scene.reference_m,
        affine,
        scene.truth_m,
        valid,
        support_pixels=support_pixels,
        minimum_coverage=config.support_minimum_coverage,
    )
    affine_oracle_metrics = elevation_metrics(affine_oracle[valid], scene.truth_m[valid])
    changes = {
        "mae_percent_change_vs_reference": float(
            100 * (residual_metrics["mae"] - reference_metrics["mae"]) / reference_metrics["mae"]
        ),
        "rmse_percent_change_vs_reference": float(
            100 * (residual_metrics["rmse"] - reference_metrics["rmse"]) / reference_metrics["rmse"]
        ),
        "oracle_mae_improvement_percent": float(
            100 * (reference_metrics["mae"] - oracle_metrics["mae"]) / reference_metrics["mae"]
        ),
        "oracle_rmse_improvement_percent": float(
            100 * (reference_metrics["rmse"] - oracle_metrics["rmse"]) / reference_metrics["rmse"]
        ),
        "affine_oracle_mae_improvement_percent": float(
            100 * (reference_metrics["mae"] - affine_oracle_metrics["mae"]) / reference_metrics["mae"]
        ),
    }
    record = {
        "held_out_region": held_out,
        "reference": reference_metrics,
        "affine_dav2": affine_metrics,
        "affine_fit_without_truth": affine_fit,
        "affine_pixel_benefit": affine_benefit_metrics,
        "affine_support_cells": affine_support,
        "affine_truth_aware_oracle": affine_oracle_metrics,
        "residual_refiner_v1": residual_metrics,
        "pixel_benefit": benefit_metrics,
        "support_cells": support,
        "truth_aware_oracle": oracle_metrics,
        "changes": changes,
    }
    _write_raster(output_dir / "residual_m.tif", residual, valid, scene.profile, "metre")
    _write_raster(output_dir / "candidate_dsm.tif", candidate, valid, scene.profile, "metre")
    _write_raster(output_dir / "affine_dav2_candidate.tif", affine, valid, scene.profile, "metre")
    _write_raster(output_dir / "benefit_m.tif", benefit, valid, scene.profile, "metre")
    _write_raster(output_dir / "oracle_dsm.tif", oracle, valid, scene.profile, "metre")
    _write_raster(
        output_dir / "affine_oracle_dsm.tif", affine_oracle, valid, scene.profile, "metre"
    )
    (output_dir / "metrics.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def region_equal_summary(records: list[dict[str, Any]]) -> dict[str, float]:
    keys = {
        "reference_mae": ("reference", "mae"),
        "residual_mae": ("residual_refiner_v1", "mae"),
        "reference_rmse": ("reference", "rmse"),
        "residual_rmse": ("residual_refiner_v1", "rmse"),
        "mae_percent_change": ("changes", "mae_percent_change_vs_reference"),
        "rmse_percent_change": ("changes", "rmse_percent_change_vs_reference"),
        "beneficial_cells_percent": ("support_cells", "beneficial_cells_percent"),
        "harmful_cells_percent": ("support_cells", "harmful_cells_percent"),
        "oracle_mae": ("truth_aware_oracle", "mae"),
        "oracle_improvement_percent": ("changes", "oracle_mae_improvement_percent"),
        "affine_oracle_improvement_percent": (
            "changes",
            "affine_oracle_mae_improvement_percent",
        ),
    }
    return {
        name: float(np.mean([record[group][metric] for record in records]))
        for name, (group, metric) in keys.items()
    }
