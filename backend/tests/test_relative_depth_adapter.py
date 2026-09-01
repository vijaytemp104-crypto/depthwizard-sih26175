"""Tests for the relative monocular-depth adapter.

The real-model smoke test is intentionally cache-only so normal test runs do
not download model weights unexpectedly.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from huggingface_hub import try_to_load_from_cache
from PIL import Image

from backend.services.relative_depth_adapter import (
    DEFAULT_MODEL_ID,
    DepthAnythingV2SmallAdapter,
    DepthArtifactResult,
    ImageInputError,
    ModelLoadError,
    RelativeDepthInferenceError,
    RelativeDepthMetadata,
    RelativeDepthOutputError,
    _load_rgb_image,
    write_depth_artifacts,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_IMAGE = REPO_ROOT / "sample_data" / "input" / "test_urban.jpg"


class _FakeProcessor:
    def __init__(self, predicted_depth: torch.Tensor) -> None:
        self.predicted_depth = predicted_depth

    def __call__(self, images: Image.Image, return_tensors: str) -> dict[str, torch.Tensor]:
        return {"pixel_values": torch.zeros((1, 3, 2, 2), dtype=torch.float32)}

    def post_process_depth_estimation(
        self,
        outputs: SimpleNamespace,
        target_sizes: list[tuple[int, int]],
    ) -> list[dict[str, torch.Tensor]]:
        return [{"predicted_depth": self.predicted_depth}]


class _FakeModel:
    def __init__(self, fail_forward: bool = False) -> None:
        self.fail_forward = fail_forward

    def eval(self) -> None:
        return None

    def __call__(self, **inputs: torch.Tensor) -> SimpleNamespace:
        if self.fail_forward:
            raise RuntimeError("forced forward failure")
        return SimpleNamespace(predicted_depth=torch.ones((1, 2, 2), dtype=torch.float32))


def _fake_adapter(predicted_depth: torch.Tensor, fail_forward: bool = False) -> DepthAnythingV2SmallAdapter:
    adapter = DepthAnythingV2SmallAdapter.__new__(DepthAnythingV2SmallAdapter)
    adapter.model_id = DEFAULT_MODEL_ID
    adapter.device = "cpu"
    adapter.processor = _FakeProcessor(predicted_depth)
    adapter.model = _FakeModel(fail_forward=fail_forward)
    adapter.metadata = RelativeDepthMetadata(
        model_name="fake",
        checkpoint_id=DEFAULT_MODEL_ID,
        device="cpu",
        output_units="relative_arbitrary",
        metric_depth=False,
    )
    return adapter


class RelativeDepthInputErrorTests(unittest.TestCase):
    def test_missing_file_raises_file_not_found(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "Input image not found"):
            _load_rgb_image(REPO_ROOT / "sample_data" / "input" / "missing.jpg")

    def test_corrupt_image_raises_image_input_error(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jpg") as corrupt:
            corrupt.write(b"not a real image")
            corrupt.flush()
            with self.assertRaisesRegex(ImageInputError, "Unsupported or unreadable"):
                _load_rgb_image(corrupt.name)

    def test_invalid_array_shape_raises_image_input_error(self) -> None:
        invalid = np.zeros((8, 8), dtype=np.uint8)
        with self.assertRaisesRegex(ImageInputError, "H x W x 3"):
            _load_rgb_image(invalid)

    def test_invalid_array_dtype_raises_image_input_error(self) -> None:
        invalid = np.zeros((8, 8, 3), dtype=np.float32)
        with self.assertRaisesRegex(ImageInputError, "uint8"):
            _load_rgb_image(invalid)


class RelativeDepthModelErrorTests(unittest.TestCase):
    def test_missing_cache_with_local_files_only_raises_model_load_error(self) -> None:
        missing_model_path = REPO_ROOT / "sample_data" / "input" / "missing_model_cache"
        with self.assertRaises(ModelLoadError):
            DepthAnythingV2SmallAdapter(
                device="cpu",
                model_id=str(missing_model_path),
                local_files_only=True,
            )

    def test_inference_failure_is_classified(self) -> None:
        adapter = _fake_adapter(torch.ones((4, 5), dtype=torch.float32), fail_forward=True)
        image = Image.new("RGB", (5, 4))
        with self.assertRaisesRegex(RelativeDepthInferenceError, "forward pass"):
            adapter.predict_depth(image)

    def test_nonfinite_output_is_rejected(self) -> None:
        adapter = _fake_adapter(torch.full((4, 5), float("nan"), dtype=torch.float32))
        image = Image.new("RGB", (5, 4))
        with self.assertRaisesRegex(RelativeDepthOutputError, "NaN or Inf"):
            adapter.predict_depth(image)

    def test_unexpected_output_dimensionality_is_rejected(self) -> None:
        adapter = _fake_adapter(torch.zeros((1, 4, 5), dtype=torch.float32))
        image = Image.new("RGB", (5, 4))
        with self.assertRaisesRegex(RelativeDepthOutputError, "Expected 2D"):
            adapter.predict_depth(image)

    def test_shape_mismatch_is_rejected(self) -> None:
        adapter = _fake_adapter(torch.zeros((5, 5), dtype=torch.float32))
        image = Image.new("RGB", (5, 4))
        with self.assertRaisesRegex(RelativeDepthOutputError, "shape mismatch"):
            adapter.predict_depth(image)


class RelativeDepthCachedSmokeTest(unittest.TestCase):
    def test_cached_depth_anything_v2_small_inference(self) -> None:
        if not SMOKE_IMAGE.exists():
            self.skipTest(f"smoke image is unavailable: {SMOKE_IMAGE}")
        if try_to_load_from_cache(DEFAULT_MODEL_ID, "config.json") is None:
            self.skipTest(
                f"{DEFAULT_MODEL_ID} is not cached locally; refusing to download in tests"
            )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        adapter = DepthAnythingV2SmallAdapter(device=device, local_files_only=True)
        with Image.open(SMOKE_IMAGE) as opened:
            image = opened.convert("RGB")

        depth, metadata = adapter.predict_depth(image)

        self.assertEqual(depth.ndim, 2)
        self.assertEqual(depth.shape, (image.height, image.width))
        self.assertEqual(depth.dtype, np.float32)
        self.assertTrue(np.isfinite(depth).all())
        self.assertGreater(float(np.std(depth)), 1e-6)
        self.assertEqual(metadata.output_units, "relative_arbitrary")
        self.assertFalse(metadata.metric_depth)
        self.assertEqual(metadata.extra["depth_estimation_type"], "relative")
        self.assertEqual(metadata.extra["final_output_shape"], depth.shape)


class RelativeDepthArtifactTests(unittest.TestCase):
    def test_constant_depth_preview_is_safe(self) -> None:
        constant_depth = torch.full((4, 5), 7.0, dtype=torch.float32)
        adapter = _fake_adapter(constant_depth)
        image = Image.new("RGB", (5, 4))

        with tempfile.TemporaryDirectory() as output_dir:
            result = write_depth_artifacts(image, output_dir, adapter=adapter)
            self.assertIsInstance(result, DepthArtifactResult)

            saved_depth = np.load(result.depth_npy_path)
            with Image.open(result.depth_png_path) as preview:
                preview_array = np.asarray(preview)
                preview_size = preview.size

            self.assertEqual(saved_depth.dtype, np.float32)
            self.assertTrue(np.array_equal(saved_depth, np.full((4, 5), 7.0, dtype=np.float32)))
            self.assertEqual(preview_size, (5, 4))
            self.assertTrue(np.array_equal(preview_array, np.zeros((4, 5), dtype=np.uint8)))
            self.assertEqual(result.metadata["visualization"]["role"], "preview_only")
            self.assertFalse(result.metadata["metric"])

    def test_cached_model_writes_reloadable_artifacts(self) -> None:
        if not SMOKE_IMAGE.exists():
            self.skipTest(f"smoke image is unavailable: {SMOKE_IMAGE}")
        if try_to_load_from_cache(DEFAULT_MODEL_ID, "config.json") is None:
            self.skipTest(
                f"{DEFAULT_MODEL_ID} is not cached locally; refusing to download in tests"
            )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        adapter = DepthAnythingV2SmallAdapter(device=device, local_files_only=True)
        with Image.open(SMOKE_IMAGE) as opened:
            image = opened.convert("RGB")

        with tempfile.TemporaryDirectory() as output_dir:
            result = write_depth_artifacts(image, output_dir, adapter=adapter)

            self.assertTrue(result.depth_npy_path.exists())
            self.assertTrue(result.depth_png_path.exists())
            self.assertTrue(result.metadata_json_path.exists())

            saved_depth = np.load(result.depth_npy_path)
            self.assertTrue(np.array_equal(saved_depth, result.depth))
            self.assertEqual(saved_depth.ndim, 2)
            self.assertEqual(saved_depth.shape, (image.height, image.width))
            self.assertEqual(saved_depth.dtype, np.float32)
            self.assertTrue(np.isfinite(saved_depth).all())
            self.assertGreater(float(np.std(saved_depth)), 1e-6)

            with Image.open(result.depth_png_path) as preview:
                self.assertEqual(preview.size, (image.width, image.height))
                self.assertEqual(preview.mode, "L")
            unchanged_depth = np.load(result.depth_npy_path)
            self.assertTrue(np.array_equal(saved_depth, unchanged_depth))

            import json

            metadata = json.loads(result.metadata_json_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["checkpoint"], DEFAULT_MODEL_ID)
            self.assertEqual(metadata["units"], "relative_arbitrary")
            self.assertFalse(metadata["metric"])
            self.assertEqual(metadata["final_output_shape"], [image.height, image.width])
            self.assertEqual(metadata["output_dtype"], "float32")
            self.assertEqual(metadata["visualization"]["role"], "preview_only")
            self.assertIn("not absolute elevation", metadata["warning"])


if __name__ == "__main__":
    unittest.main()
