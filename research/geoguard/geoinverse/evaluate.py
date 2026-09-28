"""GeoInverse held-out metrics, stratification, benefit, and oracle analysis."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import torch

from config import CONFIG, OUTPUT, ROOT, Config
from dataset import Scene, starts
from model import GeoInverseNet


NODATA = -9999.0


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    first = np.flatnonzero(np.r_[True, sorted_values[1:] != sorted_values[:-1]])
    ends = np.r_[first[1:], values.size]
    result = np.empty(values.size, np.float64)
    result[order] = np.repeat((first + ends - 1) / 2 + 1, ends - first)
    return result


def metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | int]:
    p = prediction.astype(np.float64).ravel()
    t = truth.astype(np.float64).ravel()
    error = p - t
    correlation = lambda a, b: math.nan if a.size < 2 or np.ptp(a) == 0 or np.ptp(b) == 0 else float(np.corrcoef(a, b)[0, 1])
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
        "bias": float(np.mean(error)),
        "pearson": correlation(p, t),
        "spearman": correlation(_ranks(p), _ranks(t)),
        "valid_pixel_count": int(p.size),
    }


def benefit(reference: np.ndarray, candidate: np.ndarray, truth: np.ndarray, valid: np.ndarray) -> np.ndarray:
    result = np.full(reference.shape, np.nan, np.float64)
    result[valid] = np.abs(reference[valid] - truth[valid]) - np.abs(candidate[valid] - truth[valid])
    return result


def oracle(
    reference: np.ndarray, candidate: np.ndarray, truth: np.ndarray, valid: np.ndarray,
    support_pixels: int = 30, minimum_coverage: float = 0.8,
) -> tuple[np.ndarray, dict[str, float]]:
    values = benefit(reference, candidate, truth, valid)
    output = reference.copy()
    accepted = np.zeros(valid.shape, bool)
    cells: list[float] = []
    rows = np.array_split(np.arange(valid.shape[0]), int(np.ceil(valid.shape[0] / support_pixels)))
    columns = np.array_split(np.arange(valid.shape[1]), int(np.ceil(valid.shape[1] / support_pixels)))
    for rr in rows:
        for cc in columns:
            s = np.ix_(rr, cc)
            local_valid = valid[s]
            if local_valid.mean() < minimum_coverage:
                continue
            score = float(values[s][local_valid].mean())
            cells.append(score)
            if score > 0:
                local = output[s]
                local[local_valid] = candidate[s][local_valid]
                output[s] = local
                flag = accepted[s]
                flag[local_valid] = True
                accepted[s] = flag
    cells_array = np.asarray(cells)
    return output, {
        "scored_cells": int(cells_array.size),
        "beneficial_cells_percent": float(100 * np.mean(cells_array > 0)),
        "harmful_cells_percent": float(100 * np.mean(cells_array < 0)),
        "oracle_coverage_percent": float(100 * accepted[valid].mean()),
    }


def predict(model: GeoInverseNet, features: np.ndarray, device: torch.device, config: Config = CONFIG):
    shape = features.shape[1:]
    sums = [np.zeros(shape, np.float64) for _ in range(3)]
    count = np.zeros(shape, np.uint16)
    model.eval()
    with torch.inference_mode():
        for row in starts(shape[0], config.patch_size, config.stride):
            for column in starts(shape[1], config.patch_size, config.stride):
                x = torch.from_numpy(features[:, row:row+config.patch_size, column:column+config.patch_size][None]).to(device)
                outputs = model(x)
                for total, output in zip(sums, outputs):
                    total[row:row+config.patch_size, column:column+config.patch_size] += output[0, 0].cpu().numpy()
                count[row:row+config.patch_size, column:column+config.patch_size] += 1
    return tuple((total / count).astype(np.float32) for total in sums)


def _write(path: Path, values: np.ndarray, valid: np.ndarray, profile: dict, units: str) -> None:
    data = np.full(values.shape, NODATA, np.float32)
    data[valid] = values[valid]
    local = profile.copy()
    local.pop("blockxsize", None); local.pop("blockysize", None)
    local.update(count=1, dtype="float32", nodata=NODATA, compress="deflate")
    with rasterio.open(path, "w", **local) as dataset:
        dataset.write(data, 1); dataset.set_band_unit(1, units); dataset.update_tags(1, units=units)


def _strata(scene: Scene) -> dict[str, np.ndarray]:
    valid = scene.valid
    ref = scene.reference_gradient[valid]
    rgb = scene.rgb_gradient[valid]
    vegetation = scene.vegetation_proxy[valid]
    return {
        "low_relief_open_proxy": valid & (scene.reference_gradient <= np.percentile(ref, 25)) & (scene.rgb_gradient <= np.percentile(rgb, 50)),
        "high_relief_proxy": valid & (scene.reference_gradient >= np.percentile(ref, 75)),
        "vegetation_dominant_rgb_proxy": valid & (scene.vegetation_proxy >= np.percentile(vegetation, 75)),
        "strong_structural_edge_proxy": valid & (scene.rgb_gradient >= np.percentile(rgb, 90)),
    }


def evaluate(region: str, model: GeoInverseNet, scene: Scene, device: torch.device) -> dict[str, Any]:
    output = OUTPUT / f"holdout_{region}"; output.mkdir(parents=True, exist_ok=True)
    low, high, weight = predict(model, scene.features, device)
    candidate = scene.reference + low + weight * high
    valid = scene.valid
    reference_metrics = metrics(scene.reference[valid], scene.truth[valid])
    candidate_metrics = metrics(candidate[valid], scene.truth[valid])
    values = benefit(scene.reference, candidate, scene.truth, valid)
    helped = values[valid] > 0; harmed = values[valid] < 0; harm = -values[valid][harmed]
    oracle_surface, support = oracle(scene.reference, candidate, scene.truth, valid)
    oracle_metrics = metrics(oracle_surface[valid], scene.truth[valid])
    weight_values = weight[valid].astype(np.float64)
    benefit_values = values[valid]
    weight_benefit_correlation = float(np.corrcoef(weight_values, benefit_values)[0, 1]) if np.ptp(weight_values) > 0 else math.nan
    v1 = json.loads((ROOT / "outputs" / "residual_v1" / "results.json").read_text(encoding="utf-8"))
    v1_fold = next(item for item in v1["folds"] if item["held_out_region"] == region)
    strata = {}
    for name, selection in _strata(scene).items():
        strata[name] = {
            "reference": metrics(scene.reference[selection], scene.truth[selection]),
            "geoinverse": metrics(candidate[selection], scene.truth[selection]),
            "coverage_percent": float(100 * selection[valid].mean()),
        }
    result = {
        "held_out_region": region,
        "reference": reference_metrics,
        "affine_dav2": v1_fold["affine_dav2"],
        "residual_v1": v1_fold["residual_refiner_v1"],
        "geoinverse_v0": candidate_metrics,
        "changes": {
            "mae_percent_vs_reference": float(100 * (candidate_metrics["mae"] - reference_metrics["mae"]) / reference_metrics["mae"]),
            "rmse_percent_vs_reference": float(100 * (candidate_metrics["rmse"] - reference_metrics["rmse"]) / reference_metrics["rmse"]),
        },
        "pixel_benefit": {
            "helped_percent": float(100 * helped.mean()), "harmed_percent": float(100 * harmed.mean()),
            "mean_benefit_m": float(benefit_values.mean()), "median_benefit_m": float(np.median(benefit_values)),
            "mean_harm_m": float(harm.mean()) if harm.size else math.nan,
            "p95_harm_m": float(np.percentile(harm, 95)) if harm.size else math.nan,
        },
        "support_cells": support,
        "truth_aware_oracle": oracle_metrics,
        "oracle_mae_improvement_percent": float(100 * (reference_metrics["mae"] - oracle_metrics["mae"]) / reference_metrics["mae"]),
        "weight_detail": {
            "mean": float(weight_values.mean()), "std": float(weight_values.std()),
            "p05": float(np.percentile(weight_values, 5)), "p25": float(np.percentile(weight_values, 25)),
            "median": float(np.median(weight_values)), "p75": float(np.percentile(weight_values, 75)),
            "p95": float(np.percentile(weight_values, 95)),
            "pearson_with_actual_benefit": weight_benefit_correlation,
            "interpretation": "diagnostic reconstruction weight; not calibrated confidence",
        },
        "stratified_proxy_analysis": strata,
    }
    for name, values_out, units in (("delta_low_m.tif", low, "metre"), ("delta_high_m.tif", high, "metre"), ("weight_detail.tif", weight, "dimensionless"), ("candidate_dsm.tif", candidate, "metre"), ("oracle_dsm.tif", oracle_surface, "metre")):
        _write(output / name, values_out, valid, scene.profile, units)
    (output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
