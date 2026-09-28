"""GeoInverse scene features, frequency targets, and regional patches."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset

from config import CONFIG, FOLDS, PILOTS, Config
from frequency import decompose_residual, masked_low_pass


@dataclass(frozen=True)
class Scene:
    name: str
    features: np.ndarray
    reference: np.ndarray
    truth: np.ndarray
    valid: np.ndarray
    low_target: np.ndarray
    high_target: np.ndarray
    reference_gradient: np.ndarray
    rgb_gradient: np.ndarray
    vegetation_proxy: np.ndarray
    profile: dict


_CACHE: dict[str, Scene] = {}


def starts(length: int, size: int, stride: int) -> list[int]:
    values = list(range(0, length - size + 1, stride))
    if values[-1] != length - size:
        values.append(length - size)
    return values


def load_scene(name: str, config: Config = CONFIG) -> Scene:
    if name in _CACHE:
        return _CACHE[name]
    root = PILOTS[name] / "derived"
    paths = {
        "rgb": root / "rgb_aligned.tif",
        "reference": root / "reference_aligned.tif",
        "truth": root / "truth_aligned.tif",
        "mask": root / "valid_mask.tif",
        "depth": root / "ai" / "depth_relative.tif",
    }
    opened = {key: rasterio.open(path) for key, path in paths.items()}
    try:
        signature = lambda dataset: (dataset.crs, dataset.transform, dataset.width, dataset.height)
        if len({signature(dataset) for dataset in opened.values()}) != 1:
            raise ValueError(f"grid mismatch in {name}")
        rgb_ma = opened["rgb"].read([1, 2, 3], masked=True)
        reference_ma = opened["reference"].read(1, masked=True)
        truth_ma = opened["truth"].read(1, masked=True)
        mask_ma = opened["mask"].read(1, masked=True)
        depth_ma = opened["depth"].read(1, masked=True)
        profile = opened["reference"].profile.copy()
        pixel_size = float(np.mean(np.abs(opened["reference"].res)))
    finally:
        for dataset in opened.values():
            dataset.close()
    rgb = np.asarray(rgb_ma.data, dtype=np.float32) / 255.0
    reference = np.asarray(reference_ma.data, dtype=np.float32)
    truth = np.asarray(truth_ma.data, dtype=np.float32)
    depth = np.asarray(depth_ma.data, dtype=np.float32)
    valid = (
        ~np.any(np.ma.getmaskarray(rgb_ma), axis=0)
        & ~np.ma.getmaskarray(reference_ma)
        & ~np.ma.getmaskarray(truth_ma)
        & ~np.ma.getmaskarray(mask_ma)
        & ~np.ma.getmaskarray(depth_ma)
        & (np.asarray(mask_ma.data) != 0)
        & np.isfinite(reference)
        & np.isfinite(truth)
        & np.isfinite(depth)
    )
    fill = reference.copy()
    fill[~valid] = np.median(reference[valid])
    reference_low = masked_low_pass(
        fill, np.ones(valid.shape, bool), sigma_m=config.gaussian_sigma_m, pixel_size_m=pixel_size
    )
    gy, gx = np.gradient(reference_low)
    reference_gradient = np.hypot(gx, gy).astype(np.float32)
    luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    ly, lx = np.gradient(luminance)
    rgb_gradient = np.hypot(lx, ly).astype(np.float32)
    vegetation_proxy = (2 * rgb[1] - rgb[0] - rgb[2]).astype(np.float32)
    median = np.median(depth[valid])
    q25, q75 = np.percentile(depth[valid], [25, 75])
    depth_norm = np.clip((depth - median) / max(float(q75 - q25), 1e-6), -5, 5) / 5
    features = np.concatenate(
        (
            rgb,
            (fill[None] / config.reference_scale_m).astype(np.float32),
            depth_norm[None].astype(np.float32),
            np.clip(gx[None] / config.gradient_scale, -1, 1).astype(np.float32),
            np.clip(gy[None] / config.gradient_scale, -1, 1).astype(np.float32),
            np.clip(rgb_gradient[None] / 0.5, 0, 1).astype(np.float32),
        ),
        axis=0,
    )
    low, high = decompose_residual(
        truth, reference, valid, sigma_m=config.gaussian_sigma_m, pixel_size_m=pixel_size
    )
    scene = Scene(
        name, features, reference, truth, valid, low, high,
        reference_gradient, rgb_gradient, vegetation_proxy, profile,
    )
    _CACHE[name] = scene
    return scene


class Patches(Dataset):
    def __init__(self, scenes: list[Scene], config: Config = CONFIG) -> None:
        self.scenes = {scene.name: scene for scene in scenes}
        self.samples: list[tuple[str, int, int]] = []
        self.config = config
        for scene in scenes:
            for row in starts(scene.valid.shape[0], config.patch_size, config.stride):
                for column in starts(scene.valid.shape[1], config.patch_size, config.stride):
                    local = scene.valid[row:row+config.patch_size, column:column+config.patch_size]
                    if local.mean() >= config.minimum_valid_fraction:
                        self.samples.append((scene.name, row, column))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        name, row, column = self.samples[index]
        scene = self.scenes[name]
        s = np.s_[row:row+self.config.patch_size, column:column+self.config.patch_size]
        return {
            "features": torch.from_numpy(scene.features[:, s[0], s[1]].copy()),
            "reference": torch.from_numpy(scene.reference[s][None].copy()),
            "truth": torch.from_numpy(scene.truth[s][None].copy()),
            "valid": torch.from_numpy(scene.valid[s][None].copy()),
            "low": torch.from_numpy(scene.low_target[s][None].copy()),
            "high": torch.from_numpy(scene.high_target[s][None].copy()),
        }


def fold(held_out: str, config: Config = CONFIG) -> tuple[Patches, Patches, dict[str, Scene]]:
    scenes = {name: load_scene(name, config) for name in PILOTS}
    training = FOLDS[held_out]
    if held_out in training:
        raise AssertionError("geographic leakage")
    return Patches([scenes[name] for name in training], config), Patches([scenes[held_out]], config), scenes
