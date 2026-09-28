from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch


MODULE = Path(__file__).parents[1] / "geoinverse"
sys.path.insert(0, str(MODULE))

from config import CONFIG, FOLDS  # noqa: E402
from frequency import decompose_residual, gaussian_kernel  # noqa: E402
from model import GeoInverseNet, reconstruct  # noqa: E402


def test_gaussian_kernel_is_normalized_and_uses_physical_sigma() -> None:
    kernel = gaussian_kernel(CONFIG.gaussian_sigma_m)
    assert np.isclose(kernel.sum(), 1.0)
    assert kernel.size == 2 * int(np.ceil(3 * CONFIG.gaussian_sigma_m)) + 1


def test_frequency_targets_recombine_to_metric_residual() -> None:
    reference = np.full((32, 32), 100.0, np.float32)
    truth = reference + 3.0
    truth[16, 16] += 5.0
    valid = np.ones((32, 32), bool)
    low, high = decompose_residual(
        truth, reference, valid, sigma_m=4.0, pixel_size_m=1.0
    )
    np.testing.assert_allclose((low + high)[valid], (truth - reference)[valid], atol=1e-5)


def test_reference_preserving_initialization() -> None:
    model = GeoInverseNet(CONFIG.input_channels, base_channels=8, initial_weight=0.05)
    features = torch.randn(1, CONFIG.input_channels, 32, 32)
    reference = torch.full((1, 1, 32, 32), 250.0)
    low, high, weight = model(features)
    torch.testing.assert_close(low, torch.zeros_like(low))
    torch.testing.assert_close(high, torch.zeros_like(high))
    torch.testing.assert_close(weight, torch.full_like(weight, 0.05), atol=1e-6, rtol=0)
    torch.testing.assert_close(reconstruct(reference, low, high, weight), reference)


def test_parameter_count_is_in_required_range() -> None:
    model = GeoInverseNet(CONFIG.input_channels, CONFIG.base_channels, CONFIG.initial_detail_weight)
    count = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    assert 1_000_000 <= count <= 5_000_000


def test_geographic_folds_do_not_leak() -> None:
    for held_out, training in FOLDS.items():
        assert held_out not in training
        assert set(training) == set(FOLDS) - {held_out}


def test_semantic_channels_are_optional_and_disabled_for_v0() -> None:
    assert CONFIG.semantic_channels == 0
    assert CONFIG.input_channels == 8
