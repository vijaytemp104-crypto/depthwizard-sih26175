from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
import torch


RESIDUAL = Path(__file__).parents[1] / "residual"
sys.path.insert(0, str(RESIDUAL))

from config import FOLDS  # noqa: E402
from dataset import RegionalPatchDataset, SceneArrays, construct_target_residual  # noqa: E402
from evaluate import _write_raster, compute_pixel_benefit  # noqa: E402
from model import (  # noqa: E402
    ResidualUNet,
    candidate_from_residual,
    masked_huber_loss,
)


def test_target_residual_is_truth_minus_reference_in_metres() -> None:
    truth = np.array([[12.5, 20.0]], dtype=np.float32)
    reference = np.array([[10.0, 25.0]], dtype=np.float32)
    valid = np.array([[True, False]])
    target = construct_target_residual(truth, reference, valid)
    np.testing.assert_allclose(target, [[2.5, 0.0]])


def test_candidate_is_reference_plus_metric_residual() -> None:
    reference = torch.tensor([[[[100.0, 20.0]]]])
    residual = torch.tensor([[[[2.5, -4.0]]]])
    torch.testing.assert_close(candidate_from_residual(reference, residual), torch.tensor([[[[102.5, 16.0]]]]))


def test_masked_huber_excludes_invalid_pixels_and_retains_metre_magnitude() -> None:
    reference = torch.tensor([[[[10.0, 1000.0]]]])
    truth = torch.tensor([[[[14.0, -500.0]]]])
    residual = torch.tensor([[[[1.0, 9999.0]]]])
    valid = torch.tensor([[[[True, False]]]])
    loss = masked_huber_loss(residual, reference, truth, valid, beta_m=2.0)
    assert loss.item() == pytest.approx(2.0)  # SmoothL1(|error|=3, beta=2) = 3 - 1


def test_fold_assignments_never_include_held_out_region() -> None:
    assert set(FOLDS) == {"wake", "polk", "larimer", "humboldt"}
    for held_out, training in FOLDS.items():
        assert held_out not in training
        assert set(training) == set(FOLDS) - {held_out}


def test_patch_dataset_preserves_scene_separation() -> None:
    def scene(name: str) -> SceneArrays:
        shape = (8, 8)
        return SceneArrays(
            name=name,
            features=np.zeros((7, *shape), dtype=np.float32),
            reference_m=np.zeros(shape, dtype=np.float32),
            truth_m=np.zeros(shape, dtype=np.float32),
            target_residual_m=np.zeros(shape, dtype=np.float32),
            valid=np.ones(shape, dtype=bool),
            profile={},
        )

    training = RegionalPatchDataset(
        [scene("wake"), scene("polk")], patch_size=4, stride=4, minimum_valid_fraction=1.0
    )
    validation = RegionalPatchDataset(
        [scene("larimer")], patch_size=4, stride=4, minimum_valid_fraction=1.0
    )
    assert training.scene_names.isdisjoint(validation.scene_names)


def test_deterministic_synthetic_forward_pass() -> None:
    torch.manual_seed(42)
    first = ResidualUNet(input_channels=7, base_channels=8)
    values = torch.randn(1, 7, 32, 32)
    first_output = first(values)
    torch.manual_seed(42)
    second = ResidualUNet(input_channels=7, base_channels=8)
    second_output = second(values)
    torch.testing.assert_close(first_output, second_output)
    assert first_output.shape == (1, 1, 32, 32)


def test_benefit_calculation_is_signed_and_metric() -> None:
    reference = np.array([[10.0, 10.0]])
    candidate = np.array([[11.0, 15.0]])
    truth = np.array([[12.0, 12.0]])
    valid = np.array([[True, True]])
    benefit = compute_pixel_benefit(reference, candidate, truth, valid)
    np.testing.assert_allclose(benefit, [[1.0, -1.0]])


def test_metric_output_raster_declares_metres(tmp_path: Path) -> None:
    output = tmp_path / "residual.tif"
    profile = {
        "driver": "GTiff",
        "height": 2,
        "width": 2,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32615",
        "transform": rasterio.transform.from_origin(500000, 4500000, 1, 1),
    }
    _write_raster(
        output,
        np.full((2, 2), 1.25, dtype=np.float32),
        np.ones((2, 2), dtype=bool),
        profile,
        "metre",
    )
    with rasterio.open(output) as dataset:
        assert dataset.units[0] == "metre"
        np.testing.assert_allclose(dataset.read(1), 1.25)
