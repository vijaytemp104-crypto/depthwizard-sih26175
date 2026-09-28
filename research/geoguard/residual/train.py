#!/usr/bin/env python3
"""Train four deterministic leave-one-region-out Residual Refiner V1 folds."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

from config import CONFIG, FOLDS, GEOGUARD_ROOT, OUTPUT_ROOT, TrainingConfig
from dataset import build_fold, load_scene
from evaluate import evaluate_fold, region_equal_summary
from model import ResidualUNet, candidate_from_residual, masked_gradient_l1, masked_huber_loss


def set_deterministic(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)


def loss_components(
    model: torch.nn.Module, batch: dict, device: torch.device, config: TrainingConfig
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    features = batch["features"].to(device)
    reference = batch["reference_m"].to(device)
    truth = batch["truth_m"].to(device)
    valid = batch["valid"].to(device)
    residual = model(features)
    huber = masked_huber_loss(
        residual, reference, truth, valid, beta_m=config.huber_beta_m
    )
    candidate = candidate_from_residual(reference, residual)
    gradient = masked_gradient_l1(candidate, truth, valid)
    total = huber + config.gradient_loss_weight * gradient
    return total, huber, gradient


def validation_loss(
    model: torch.nn.Module, loader: DataLoader, device: torch.device, config: TrainingConfig
) -> float:
    model.eval()
    values: list[float] = []
    with torch.inference_mode():
        for batch in loader:
            total, _, _ = loss_components(model, batch, device, config)
            values.append(float(total.item()))
    return float(np.mean(values))


def train_fold(
    held_out: str, *, device: torch.device, config: TrainingConfig = CONFIG
) -> tuple[dict[str, Any], dict[str, Any]]:
    set_deterministic(config.seed)
    train_dataset, validation_dataset, scenes = build_fold(held_out, config)
    if held_out in train_dataset.scene_names or validation_dataset.scene_names != {held_out}:
        raise AssertionError("geographic fold separation failed")
    generator = torch.Generator().manual_seed(config.seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        generator=generator,
        num_workers=0,
    )
    validation_loader = DataLoader(
        validation_dataset, batch_size=config.batch_size, shuffle=False, num_workers=0
    )
    model = ResidualUNet(config.input_channels, config.base_channels).to(device)
    parameter_count = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    output_dir = OUTPUT_ROOT / f"holdout_{held_out}"
    output_dir.mkdir(parents=True, exist_ok=True)
    best_loss = math_inf = float("inf")
    best_epoch = 0
    stale = 0
    history: list[dict[str, float | int]] = []
    started = time.perf_counter()
    for epoch in range(1, config.maximum_epochs + 1):
        model.train()
        totals: list[float] = []
        hubers: list[float] = []
        gradients: list[float] = []
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                total, huber, gradient = loss_components(model, batch, device, config)
            scaler.scale(total).backward()
            scaler.step(optimizer)
            scaler.update()
            totals.append(float(total.item()))
            hubers.append(float(huber.item()))
            gradients.append(float(gradient.item()))
        held_out_loss = validation_loss(model, validation_loader, device, config)
        row = {
            "epoch": epoch,
            "train_total_loss": float(np.mean(totals)),
            "train_huber_m": float(np.mean(hubers)),
            "train_gradient_l1_m": float(np.mean(gradients)),
            "held_out_total_loss": held_out_loss,
        }
        history.append(row)
        print(json.dumps({"fold": held_out, **row}))
        if held_out_loss < best_loss - 1e-6:
            best_loss = held_out_loss
            best_epoch = epoch
            stale = 0
            torch.save(model.state_dict(), output_dir / "best.pt")
        else:
            stale += 1
            if stale >= config.early_stopping_patience:
                break
    runtime = time.perf_counter() - started
    model.load_state_dict(torch.load(output_dir / "best.pt", map_location=device, weights_only=True))
    training = {
        "held_out_region": held_out,
        "training_regions": list(FOLDS[held_out]),
        "device": str(device),
        "mixed_precision": device.type == "cuda",
        "runtime_seconds": runtime,
        "trainable_parameters": parameter_count,
        "train_patch_count": len(train_dataset),
        "held_out_patch_count": len(validation_dataset),
        "best_epoch": best_epoch,
        "epochs_run": len(history),
        "best_held_out_loss": best_loss,
        "peak_memory_mb": (
            float(torch.cuda.max_memory_allocated(device) / 1024**2)
            if device.type == "cuda"
            else None
        ),
        "peak_memory_note": None if device.type == "cuda" else "Unavailable for CPU PyTorch",
        "config": config.to_dict(),
        "loss_equation": "masked SmoothL1(reference + residual, truth; beta=2m) + 0.05 * masked L1 spatial-gradient(candidate, truth)",
        "target": "truth - reference in metres; no target normalization",
        "history": history,
    }
    (output_dir / "training.json").write_text(json.dumps(training, indent=2) + "\n", encoding="utf-8")
    evaluation = evaluate_fold(held_out, model, scenes[held_out], device, config)
    return training, evaluation


def write_summary(training: list[dict], evaluations: list[dict]) -> None:
    equal = region_equal_summary(evaluations)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    combined = {"training": training, "folds": evaluations, "region_equal": equal}
    (OUTPUT_ROOT / "results.json").write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Residual Refiner V1 results",
        "",
        "Development-only leave-one-region-out evaluation. Negative percentage change denotes improvement. The oracle uses held-out truth and is non-deployable.",
        "",
        "| Region | Reference MAE | Residual MAE | MAE % | Reference RMSE | Residual RMSE | RMSE % | Beneficial Cells % | Harmful Cells % | Oracle MAE | Oracle Improvement % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in evaluations:
        lines.append(
            "| {held_out_region} | {reference[mae]:.6f} | {residual_refiner_v1[mae]:.6f} | "
            "{changes[mae_percent_change_vs_reference]:.3f}% | {reference[rmse]:.6f} | "
            "{residual_refiner_v1[rmse]:.6f} | {changes[rmse_percent_change_vs_reference]:.3f}% | "
            "{support_cells[beneficial_cells_percent]:.3f}% | {support_cells[harmful_cells_percent]:.3f}% | "
            "{truth_aware_oracle[mae]:.6f} | {changes[oracle_mae_improvement_percent]:.3f}% |".format(**record)
        )
    lines.append(
        "| Region-equal mean | {reference_mae:.6f} | {residual_mae:.6f} | {mae_percent_change:.3f}% | "
        "{reference_rmse:.6f} | {residual_rmse:.6f} | {rmse_percent_change:.3f}% | "
        "{beneficial_cells_percent:.3f}% | {harmful_cells_percent:.3f}% | {oracle_mae:.6f} | "
        "{oracle_improvement_percent:.3f}% |".format(**equal)
    )
    lines.extend(
        [
            "",
            "## Truth-aware oracle headroom comparison",
            "",
        ]
    )
    for record in evaluations:
        lines.append(
            "- {held_out_region}: residual oracle {changes[oracle_mae_improvement_percent]:.3f}% MAE improvement; "
            "affine DAV2 oracle {changes[affine_oracle_mae_improvement_percent]:.3f}%.".format(**record)
        )
    lines.extend(
        [
            "- Region-equal mean: residual oracle {oracle_improvement_percent:.3f}%; affine DAV2 oracle "
            "{affine_oracle_improvement_percent:.3f}%.".format(**equal),
            "",
            "## Fixed method",
            "",
            "- Input channels: RGB (3), coarse reference elevation (1), frozen DAV2 relative depth (1), and coarse-reference x/y gradients (2).",
            "- Output: one metric residual channel; `candidate = reference + residual_m`.",
            "- Target: `truth - reference` in metres without target normalization.",
            "- Frozen DAV2 was not fine-tuned.",
            "- Early stopping used only the geographically held-out development region specified by each fold.",
            "- These development results do not establish generalization and do not use any blind-test county.",
            "",
        ]
    )
    (GEOGUARD_ROOT / "RESIDUAL_V1_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold", choices=tuple(FOLDS), action="append")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--evaluate-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.summary_only:
        training = [
            json.loads((OUTPUT_ROOT / f"holdout_{name}" / "training.json").read_text(encoding="utf-8"))
            for name in FOLDS
        ]
        evaluations = [
            json.loads((OUTPUT_ROOT / f"holdout_{name}" / "metrics.json").read_text(encoding="utf-8"))
            for name in FOLDS
        ]
        write_summary(training, evaluations)
        return 0
    folds = arguments.fold or list(FOLDS)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    if arguments.evaluate_only:
        training = []
        evaluations = []
        for held_out in folds:
            output_dir = OUTPUT_ROOT / f"holdout_{held_out}"
            model = ResidualUNet(CONFIG.input_channels, CONFIG.base_channels).to(device)
            model.load_state_dict(
                torch.load(output_dir / "best.pt", map_location=device, weights_only=True)
            )
            training.append(
                json.loads((output_dir / "training.json").read_text(encoding="utf-8"))
            )
            evaluations.append(evaluate_fold(held_out, model, load_scene(held_out), device))
        if set(folds) == set(FOLDS):
            write_summary(training, evaluations)
        return 0
    training: list[dict] = []
    evaluations: list[dict] = []
    for held_out in folds:
        train_record, evaluation = train_fold(held_out, device=device)
        training.append(train_record)
        evaluations.append(evaluation)
    if set(folds) == set(FOLDS):
        write_summary(training, evaluations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
