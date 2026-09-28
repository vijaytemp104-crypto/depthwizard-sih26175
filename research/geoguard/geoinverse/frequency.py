"""Physical-scale masked Gaussian decomposition for elevation residuals."""

from __future__ import annotations

import numpy as np
import torch
from torch.nn import functional as F


def gaussian_kernel(sigma_pixels: float) -> np.ndarray:
    if sigma_pixels <= 0:
        raise ValueError("sigma must be positive")
    radius = int(np.ceil(3 * sigma_pixels))
    coordinates = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-0.5 * np.square(coordinates / sigma_pixels))
    return (kernel / kernel.sum()).astype(np.float32)


def _blur(values: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    tensor = torch.from_numpy(values.astype(np.float32))[None, None]
    radius = kernel.size // 2
    horizontal = torch.from_numpy(kernel)[None, None, None, :]
    vertical = torch.from_numpy(kernel)[None, None, :, None]
    with torch.inference_mode():
        tensor = F.pad(tensor, (radius, radius, 0, 0), mode="reflect")
        tensor = F.conv2d(tensor, horizontal)
        tensor = F.pad(tensor, (0, 0, radius, radius), mode="reflect")
        tensor = F.conv2d(tensor, vertical)
    return tensor[0, 0].numpy()


def masked_low_pass(
    values: np.ndarray, valid: np.ndarray, *, sigma_m: float, pixel_size_m: float
) -> np.ndarray:
    if values.shape != valid.shape:
        raise ValueError("values and mask must share a shape")
    kernel = gaussian_kernel(sigma_m / pixel_size_m)
    numerator = _blur(np.where(valid, values, 0.0), kernel)
    denominator = _blur(valid.astype(np.float32), kernel)
    output = np.zeros(values.shape, dtype=np.float32)
    supported = denominator > 1e-6
    output[supported] = numerator[supported] / denominator[supported]
    return output


def decompose_residual(
    truth_m: np.ndarray,
    reference_m: np.ndarray,
    valid: np.ndarray,
    *,
    sigma_m: float,
    pixel_size_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    residual = np.zeros(truth_m.shape, dtype=np.float32)
    residual[valid] = truth_m[valid] - reference_m[valid]
    low = masked_low_pass(residual, valid, sigma_m=sigma_m, pixel_size_m=pixel_size_m)
    high = np.zeros_like(low)
    high[valid] = residual[valid] - low[valid]
    return low, high
