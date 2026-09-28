"""Aligned regional scene loading and geographically separated patch extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset

from config import CONFIG, FOLDS, PILOTS, TrainingConfig


@dataclass(frozen=True)
class SceneArrays:
    name: str
    features: np.ndarray
    reference_m: np.ndarray
    truth_m: np.ndarray
    target_residual_m: np.ndarray
    valid: np.ndarray
    profile: dict


def construct_target_residual(
    truth_m: np.ndarray, reference_m: np.ndarray, valid: np.ndarray
) -> np.ndarray:
    if not (truth_m.shape == reference_m.shape == valid.shape):
        raise ValueError("truth, reference, and valid mask must share a shape")
    target = np.zeros(truth_m.shape, dtype=np.float32)
    target[valid] = (truth_m[valid] - reference_m[valid]).astype(np.float32)
    return target


def _read_band(path: Path) -> tuple[np.ma.MaskedArray, dict]:
    with rasterio.open(path) as dataset:
        return dataset.read(1, masked=True), dataset.profile.copy()


def _same_grid(paths: list[Path]) -> None:
    with rasterio.open(paths[0]) as first:
        signature = (first.crs, first.transform, first.width, first.height)
    for path in paths[1:]:
        with rasterio.open(path) as dataset:
            if (dataset.crs, dataset.transform, dataset.width, dataset.height) != signature:
                raise ValueError(f"grid mismatch: {path}")


def load_scene(name: str, config: TrainingConfig = CONFIG) -> SceneArrays:
    root = PILOTS[name] / "derived"
    rgb_path = root / "rgb_aligned.tif"
    reference_path = root / "reference_aligned.tif"
    truth_path = root / "truth_aligned.tif"
    mask_path = root / "valid_mask.tif"
    depth_path = root / "ai" / "depth_relative.tif"
    paths = [rgb_path, reference_path, truth_path, mask_path, depth_path]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    _same_grid(paths)

    with rasterio.open(rgb_path) as dataset:
        rgb_masked = dataset.read([1, 2, 3], masked=True)
        profile = dataset.profile.copy()
    reference, _ = _read_band(reference_path)
    truth, _ = _read_band(truth_path)
    mask, _ = _read_band(mask_path)
    depth, _ = _read_band(depth_path)

    rgb = np.asarray(rgb_masked.data, dtype=np.float32) / 255.0
    reference_data = np.asarray(reference.data, dtype=np.float32)
    truth_data = np.asarray(truth.data, dtype=np.float32)
    depth_data = np.asarray(depth.data, dtype=np.float32)
    valid = (
        ~np.any(np.ma.getmaskarray(rgb_masked), axis=0)
        & ~np.ma.getmaskarray(reference)
        & ~np.ma.getmaskarray(truth)
        & ~np.ma.getmaskarray(mask)
        & ~np.ma.getmaskarray(depth)
        & (np.asarray(mask.data) != 0)
        & np.isfinite(reference_data)
        & np.isfinite(truth_data)
        & np.isfinite(depth_data)
    )
    if not np.any(valid):
        raise ValueError(f"no valid pixels for {name}")

    reference_fill = reference_data.copy()
    reference_fill[~valid] = float(np.median(reference_data[valid]))
    gradient_y, gradient_x = np.gradient(reference_fill)
    depth_median = float(np.median(depth_data[valid]))
    q25, q75 = np.percentile(depth_data[valid], [25, 75])
    depth_scale = max(float(q75 - q25), 1e-6)
    depth_normalized = np.clip((depth_data - depth_median) / depth_scale, -5.0, 5.0) / 5.0
    features = np.concatenate(
        (
            rgb,
            (reference_fill[None] / config.reference_scale_m).astype(np.float32),
            depth_normalized[None].astype(np.float32),
            np.clip(gradient_x[None] / config.gradient_scale_m_per_m, -1, 1).astype(np.float32),
            np.clip(gradient_y[None] / config.gradient_scale_m_per_m, -1, 1).astype(np.float32),
        ),
        axis=0,
    )
    target = construct_target_residual(truth_data, reference_data, valid)
    return SceneArrays(name, features, reference_data, truth_data, target, valid, profile)


def patch_starts(length: int, size: int, stride: int) -> list[int]:
    if size > length or size < 1 or stride < 1:
        raise ValueError("invalid patch geometry")
    starts = list(range(0, length - size + 1, stride))
    if starts[-1] != length - size:
        starts.append(length - size)
    return starts


class RegionalPatchDataset(Dataset):
    def __init__(
        self,
        scenes: list[SceneArrays],
        *,
        patch_size: int,
        stride: int,
        minimum_valid_fraction: float,
    ) -> None:
        self.scenes = {scene.name: scene for scene in scenes}
        self.samples: list[tuple[str, int, int]] = []
        for scene in scenes:
            for row in patch_starts(scene.valid.shape[0], patch_size, stride):
                for column in patch_starts(scene.valid.shape[1], patch_size, stride):
                    local = scene.valid[row : row + patch_size, column : column + patch_size]
                    if float(local.mean()) >= minimum_valid_fraction:
                        self.samples.append((scene.name, row, column))
        self.patch_size = patch_size
        if not self.samples:
            raise ValueError("patch selection produced no samples")

    @property
    def scene_names(self) -> set[str]:
        return set(self.scenes)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor | str]:
        name, row, column = self.samples[index]
        scene = self.scenes[name]
        selection = np.s_[row : row + self.patch_size, column : column + self.patch_size]
        return {
            "features": torch.from_numpy(scene.features[:, selection[0], selection[1]].copy()),
            "reference_m": torch.from_numpy(scene.reference_m[selection][None].copy()),
            "truth_m": torch.from_numpy(scene.truth_m[selection][None].copy()),
            "valid": torch.from_numpy(scene.valid[selection][None].copy()),
            "scene": name,
        }


def build_fold(
    held_out: str, config: TrainingConfig = CONFIG
) -> tuple[RegionalPatchDataset, RegionalPatchDataset, dict[str, SceneArrays]]:
    if held_out not in FOLDS:
        raise KeyError(held_out)
    scenes = {name: load_scene(name, config) for name in PILOTS}
    train_names = FOLDS[held_out]
    if held_out in train_names or set(train_names) & {held_out}:
        raise AssertionError("held-out region leaked into training")
    arguments = {
        "patch_size": config.patch_size,
        "stride": config.patch_stride,
        "minimum_valid_fraction": config.minimum_valid_fraction,
    }
    train = RegionalPatchDataset([scenes[name] for name in train_names], **arguments)
    validation = RegionalPatchDataset([scenes[held_out]], **arguments)
    return train, validation, scenes
