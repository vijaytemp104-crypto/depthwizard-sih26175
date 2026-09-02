"""Tests for the relative monocular-depth adapter.

The real-model smoke test is intentionally cache-only so normal test runs do
not download model weights unexpectedly.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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
    LoadedDepthAnythingV2Small,
    ModelLoadError,
    RelativeDepthInferenceError,
    RelativeDepthMetadata,
    RelativeDepthOutputError,
    _get_cached_default_adapter,
    _load_rgb_image,
    load_default_adapter,
    predict_depth,
    write_depth_artifacts,
)
import backend.services.relative_depth_adapter as relative_depth_adapter


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


def _fake_loaded_components(predicted_depth: torch.Tensor | None = None) -> LoadedDepthAnythingV2Small:
    if predicted_depth is None:
        predicted_depth = torch.ones((4, 5), dtype=torch.float32)
    return LoadedDepthAnythingV2Small(
        processor=_FakeProcessor(predicted_depth),
        model=_FakeModel(),
        metadata=RelativeDepthMetadata(
            model_name="fake",
            checkpoint_id=DEFAULT_MODEL_ID,
            device="cpu",
            output_units="relative_arbitrary",
            metric_depth=False,
            extra={"local_files_only": True, "depth_estimation_type": "relative"},
        ),
    )


def _path_stats(path: Path) -> tuple[bool, int, int]:
    if not path.exists():
        return (False, 0, 0)
    files = [item for item in path.rglob("*") if item.is_file()]
    return (True, len(files), sum(item.stat().st_size for item in files))


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

    def test_empty_offline_cache_fails_without_touching_real_cache(self) -> None:
        import json

        real_cache = (
            Path.home()
            / ".cache"
            / "huggingface"
            / "hub"
            / "models--depth-anything--Depth-Anything-V2-Small-hf"
        )
        before = _path_stats(real_cache)
        code = """
import json
from backend.services.relative_depth_adapter import DepthAnythingV2SmallAdapter

try:
    DepthAnythingV2SmallAdapter(device='cpu', local_files_only=True)
    payload = {'error_type': None, 'message': 'load unexpectedly succeeded'}
except Exception as exc:
    payload = {'error_type': type(exc).__name__, 'message': str(exc)}
print(json.dumps(payload))
"""

        with tempfile.TemporaryDirectory(prefix="empty_hf_cache_") as cache_dir:
            cache_path = Path(cache_dir)
            env = {
                **os.environ,
                "HF_HOME": str(cache_path / "hf_home"),
                "HF_HUB_CACHE": str(cache_path / "hf_hub"),
                "TRANSFORMERS_CACHE": str(cache_path / "transformers"),
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
            completed = subprocess.run(
                [sys.executable, "-B", "-c", code],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

        after = _path_stats(real_cache)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["error_type"], "ModelLoadError")
        self.assertIn("local_files_only=True", payload["message"])
        self.assertEqual(before, after)

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


class RelativeDepthAdapterCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        relative_depth_adapter._DEFAULT_ADAPTER_CACHE.clear()

    def tearDown(self) -> None:
        relative_depth_adapter._DEFAULT_ADAPTER_CACHE.clear()

    def test_predict_depth_reuses_one_cached_adapter(self) -> None:
        calls: list[bool] = []

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            calls.append(local_files_only)
            return _fake_loaded_components()

        image = Image.new("RGB", (5, 4))
        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            depth_one, _ = predict_depth(image)
            depth_two, _ = predict_depth(image)
            adapter_one = _get_cached_default_adapter()
            adapter_two = _get_cached_default_adapter()

        self.assertEqual(calls, [True])
        self.assertIs(adapter_one, adapter_two)
        self.assertIs(adapter_one.model, adapter_two.model)
        self.assertIs(adapter_one.processor, adapter_two.processor)
        self.assertEqual(depth_one.shape, (4, 5))
        self.assertEqual(depth_two.shape, (4, 5))

    def test_different_cache_keys_create_separate_adapters(self) -> None:
        calls: list[tuple[str, bool, str]] = []

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            calls.append((self.device, local_files_only, self.model_id))
            return _fake_loaded_components()

        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            cpu_local = _get_cached_default_adapter(device="cpu", local_files_only=True)
            cpu_download_opt_in = _get_cached_default_adapter(
                device="cpu",
                local_files_only=False,
            )
            alternate_model = _get_cached_default_adapter(
                device="cpu",
                local_files_only=True,
                model_id="alternate/model",
            )

        self.assertIsNot(cpu_local, cpu_download_opt_in)
        self.assertIsNot(cpu_local, alternate_model)
        self.assertEqual(
            calls,
            [
                ("cpu", True, DEFAULT_MODEL_ID),
                ("cpu", False, DEFAULT_MODEL_ID),
                ("cpu", True, "alternate/model"),
            ],
        )

    def test_load_default_adapter_reuses_same_cache_key(self) -> None:
        calls: list[bool] = []

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            calls.append(local_files_only)
            return _fake_loaded_components()

        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            first = load_default_adapter(device="cpu", local_files_only=True)
            second = load_default_adapter(device="cpu", local_files_only=True)

        self.assertIs(first, second)
        self.assertIs(first.model, second.model)
        self.assertIs(first.processor, second.processor)
        self.assertEqual(calls, [True])

    def test_load_default_adapter_separates_relevant_cache_keys(self) -> None:
        calls: list[tuple[str, bool, str]] = []

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            calls.append((self.device, local_files_only, self.model_id))
            return _fake_loaded_components()

        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            cpu_local = load_default_adapter(device="cpu", local_files_only=True)
            cpu_download_opt_in = load_default_adapter(device="cpu", local_files_only=False)
            alternate_model = load_default_adapter(
                device="cpu",
                local_files_only=True,
                model_id="alternate/model",
            )

        self.assertIsNot(cpu_local, cpu_download_opt_in)
        self.assertIsNot(cpu_local, alternate_model)
        self.assertEqual(
            calls,
            [
                ("cpu", True, DEFAULT_MODEL_ID),
                ("cpu", False, DEFAULT_MODEL_ID),
                ("cpu", True, "alternate/model"),
            ],
        )

    def test_failed_load_is_not_cached_and_retry_can_succeed(self) -> None:
        calls = 0

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ModelLoadError("forced missing-cache failure")
            return _fake_loaded_components()

        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            with self.assertRaisesRegex(ModelLoadError, "forced missing-cache"):
                _get_cached_default_adapter(device="cpu", local_files_only=True)
            self.assertEqual(relative_depth_adapter._DEFAULT_ADAPTER_CACHE, {})
            adapter = _get_cached_default_adapter(device="cpu", local_files_only=True)

        self.assertIsInstance(adapter, DepthAnythingV2SmallAdapter)
        self.assertEqual(calls, 2)

    def test_load_default_adapter_failed_load_is_not_cached_and_retry_can_succeed(self) -> None:
        calls = 0

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ModelLoadError("forced missing-cache failure")
            return _fake_loaded_components()

        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            with self.assertRaisesRegex(ModelLoadError, "forced missing-cache"):
                load_default_adapter(device="cpu", local_files_only=True)
            self.assertEqual(relative_depth_adapter._DEFAULT_ADAPTER_CACHE, {})
            adapter = load_default_adapter(device="cpu", local_files_only=True)

        self.assertIsInstance(adapter, DepthAnythingV2SmallAdapter)
        self.assertEqual(calls, 2)

    def test_direct_adapter_construction_remains_fresh(self) -> None:
        calls: list[int] = []

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            calls.append(id(self))
            return _fake_loaded_components()

        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            first = DepthAnythingV2SmallAdapter(device="cpu")
            second = DepthAnythingV2SmallAdapter(device="cpu")

        self.assertIsNot(first, second)
        self.assertEqual(len(calls), 2)
        self.assertEqual(relative_depth_adapter._DEFAULT_ADAPTER_CACHE, {})

    def test_adapter_and_loader_default_to_local_files_only(self) -> None:
        calls: list[bool] = []

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            calls.append(local_files_only)
            return _fake_loaded_components()

        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            DepthAnythingV2SmallAdapter(device="cpu")
            load_default_adapter(device="cpu")
            DepthAnythingV2SmallAdapter(device="cpu", local_files_only=False)
            load_default_adapter(device="cpu", local_files_only=False)

        self.assertEqual(calls, [True, True, False, False])

    def test_injected_adapter_bypasses_default_cache(self) -> None:
        adapter = _fake_adapter(torch.full((4, 5), 3.0, dtype=torch.float32))
        image = Image.new("RGB", (5, 4))

        with tempfile.TemporaryDirectory() as output_dir:
            with patch.object(
                DepthAnythingV2SmallAdapter,
                "_load_model",
                side_effect=AssertionError("default cache should not load"),
            ):
                result = write_depth_artifacts(image, output_dir, adapter=adapter)

        self.assertTrue(np.array_equal(result.depth, np.full((4, 5), 3.0, dtype=np.float32)))
        self.assertEqual(relative_depth_adapter._DEFAULT_ADAPTER_CACHE, {})

    def test_write_depth_artifacts_uses_cached_adapter_when_none_supplied(self) -> None:
        calls: list[bool] = []

        def fake_load(self: DepthAnythingV2SmallAdapter, local_files_only: bool) -> LoadedDepthAnythingV2Small:
            calls.append(local_files_only)
            return _fake_loaded_components(torch.full((4, 5), 2.0, dtype=torch.float32))

        image = Image.new("RGB", (5, 4))
        with patch.object(DepthAnythingV2SmallAdapter, "_load_model", fake_load):
            with tempfile.TemporaryDirectory() as output_one:
                result_one = write_depth_artifacts(image, output_one)
            with tempfile.TemporaryDirectory() as output_two:
                result_two = write_depth_artifacts(image, output_two)

        self.assertEqual(calls, [True])
        self.assertTrue(np.array_equal(result_one.depth, result_two.depth))


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

    def test_cached_offline_inference_uses_no_network_sockets(self) -> None:
        if not SMOKE_IMAGE.exists():
            self.skipTest(f"smoke image is unavailable: {SMOKE_IMAGE}")
        if try_to_load_from_cache(DEFAULT_MODEL_ID, "config.json") is None:
            self.skipTest(
                f"{DEFAULT_MODEL_ID} is not cached locally; refusing to download in tests"
            )

        old_env = {
            "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
            "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE"),
        }
        attempts = {"count": 0}
        original_socket = socket.socket

        class GuardedSocket(original_socket):
            def __new__(cls, *args, **kwargs):
                attempts["count"] += 1
                raise RuntimeError("network socket blocked during offline test")

        try:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            with Image.open(SMOKE_IMAGE) as opened:
                image = opened.convert("RGB")
            socket.socket = GuardedSocket
            adapter = DepthAnythingV2SmallAdapter(device="auto", local_files_only=True)
            depth, _ = adapter.predict_depth(image)
        finally:
            socket.socket = original_socket
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.assertEqual(attempts["count"], 0)
        self.assertEqual(depth.shape, (image.height, image.width))
        self.assertEqual(depth.dtype, np.float32)
        self.assertTrue(np.isfinite(depth).all())

    def test_cpu_cached_inference_contract(self) -> None:
        if not SMOKE_IMAGE.exists():
            self.skipTest(f"smoke image is unavailable: {SMOKE_IMAGE}")
        if try_to_load_from_cache(DEFAULT_MODEL_ID, "config.json") is None:
            self.skipTest(
                f"{DEFAULT_MODEL_ID} is not cached locally; refusing to download in tests"
            )

        adapter = DepthAnythingV2SmallAdapter(device="cpu", local_files_only=True)
        with Image.open(SMOKE_IMAGE) as opened:
            image = opened.convert("RGB")
        depth, _ = adapter.predict_depth(image)

        self.assertEqual(depth.shape, (image.height, image.width))
        self.assertEqual(depth.dtype, np.float32)
        self.assertTrue(np.isfinite(depth).all())

    def test_gpu_cached_inference_contract_if_available(self) -> None:
        if not torch.cuda.is_available():
            self.skipTest("CUDA is unavailable")
        if not SMOKE_IMAGE.exists():
            self.skipTest(f"smoke image is unavailable: {SMOKE_IMAGE}")
        if try_to_load_from_cache(DEFAULT_MODEL_ID, "config.json") is None:
            self.skipTest(
                f"{DEFAULT_MODEL_ID} is not cached locally; refusing to download in tests"
            )

        adapter = DepthAnythingV2SmallAdapter(device="cuda", local_files_only=True)
        with Image.open(SMOKE_IMAGE) as opened:
            image = opened.convert("RGB")
        depth, _ = adapter.predict_depth(image)

        self.assertEqual(depth.shape, (image.height, image.width))
        self.assertEqual(depth.dtype, np.float32)
        self.assertTrue(np.isfinite(depth).all())


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
