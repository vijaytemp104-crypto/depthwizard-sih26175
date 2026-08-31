"""Model-agnostic surface for relative monocular-depth inference.

This module intentionally exposes relative monocular depth only. Raw model
outputs are not metres, elevations, DSMs, or calibrated terrain heights.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol


ImageInput = Any
DepthArray = Any

DEFAULT_MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"
DEFAULT_MODEL_NAME = "Depth Anything V2 Small"
MODEL_SOURCE = "https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf"
MODEL_LICENSE = "apache-2.0"
OUTPUT_CONVENTION = (
    "relative disparity-like monocular depth; values are arbitrary and must not "
    "be interpreted as metric distance, elevation, or DSM height"
)


class RelativeDepthError(Exception):
    """Base exception for relative-depth adapter failures."""


class ImageInputError(RelativeDepthError, ValueError):
    """Raised when an input cannot be interpreted as a valid RGB image."""


class ModelLoadError(RelativeDepthError, RuntimeError):
    """Raised when the selected pretrained model or processor cannot load."""


class RelativeDepthInferenceError(RelativeDepthError, RuntimeError):
    """Raised when preprocessing, model forward, or postprocessing fails."""


class RelativeDepthOutputError(RelativeDepthError, RuntimeError):
    """Raised when model output violates the relative-depth array contract."""


class ArtifactWriteError(RelativeDepthError, RuntimeError):
    """Raised when relative-depth artifacts cannot be written or verified."""


@dataclass(frozen=True)
class RelativeDepthMetadata:
    """Traceability fields for an uncalibrated relative-depth prediction."""

    model_name: str | None = None
    checkpoint_id: str | None = None
    model_source: str | None = None
    license: str | None = None
    device: str | None = None
    framework: str | None = None
    output_convention: str = OUTPUT_CONVENTION
    output_units: str = "relative_arbitrary"
    metric_depth: bool = False
    extra: Mapping[str, Any] = field(default_factory=dict)


class RelativeDepthAdapter(Protocol):
    """Adapter interface implemented by a future pretrained monocular model."""

    metadata: RelativeDepthMetadata

    def predict_depth(
        self,
        image: ImageInput,
    ) -> tuple[DepthArray, RelativeDepthMetadata]:
        """Return an H x W relative-depth array and metadata."""


@dataclass(frozen=True)
class LoadedDepthAnythingV2Small:
    """Loaded model components for the selected relative-depth checkpoint."""

    processor: Any
    model: Any
    metadata: RelativeDepthMetadata


@dataclass(frozen=True)
class DepthArtifactResult:
    """Result returned after writing relative-depth handoff artifacts."""

    depth: DepthArray
    metadata: Mapping[str, Any]
    depth_npy_path: Path
    depth_png_path: Path
    metadata_json_path: Path


class DepthAnythingV2SmallAdapter:
    """Loads the selected pretrained Depth Anything V2 Small checkpoint."""

    def __init__(
        self,
        device: str = "auto",
        model_id: str = DEFAULT_MODEL_ID,
        local_files_only: bool = False,
    ) -> None:
        self.model_id = model_id
        self.device = self._resolve_device(device)
        loaded = self._load_model(local_files_only=local_files_only)
        self.processor = loaded.processor
        self.model = loaded.model
        self.metadata = loaded.metadata

    @staticmethod
    def _resolve_device(device: str) -> str:
        import torch

        requested = device.lower()
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "cpu":
            return "cpu"
        if requested.startswith("cuda"):
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA was requested but is not available.")
            return requested
        raise ValueError(f"Unsupported device request: {device!r}")

    def _load_model(self, local_files_only: bool) -> LoadedDepthAnythingV2Small:
        import torch
        import transformers
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        try:
            processor = AutoImageProcessor.from_pretrained(
                self.model_id,
                local_files_only=local_files_only,
            )
        except Exception as exc:
            raise ModelLoadError(
                "Unable to load Depth Anything V2 image processor for "
                f"{self.model_id!r} with local_files_only={local_files_only}."
            ) from exc

        try:
            model = AutoModelForDepthEstimation.from_pretrained(
                self.model_id,
                local_files_only=local_files_only,
            )
        except Exception as exc:
            raise ModelLoadError(
                "Unable to load Depth Anything V2 model weights for "
                f"{self.model_id!r} with local_files_only={local_files_only}."
            ) from exc
        model = model.to(self.device)
        model.eval()

        metadata = RelativeDepthMetadata(
            model_name=DEFAULT_MODEL_NAME,
            checkpoint_id=self.model_id,
            model_source=MODEL_SOURCE,
            license=MODEL_LICENSE,
            device=str(next(model.parameters()).device),
            framework=f"transformers {transformers.__version__}; torch {torch.__version__}",
            extra={
                "local_files_only": local_files_only,
                "depth_estimation_type": getattr(
                    getattr(model, "config", None),
                    "depth_estimation_type",
                    "relative",
                ),
            },
        )
        return LoadedDepthAnythingV2Small(
            processor=processor,
            model=model,
            metadata=metadata,
        )

    def predict_depth(
        self,
        image: ImageInput,
    ) -> tuple[DepthArray, RelativeDepthMetadata]:
        """Run one relative-depth prediction and restore it to input H x W."""

        import numpy as np
        import torch

        rgb_image = _load_rgb_image(image)
        width, height = rgb_image.size

        try:
            inputs = self.processor(images=rgb_image, return_tensors="pt")
            model_input_shape = tuple(inputs["pixel_values"].shape)
            inputs = {
                name: value.to(self.device) if hasattr(value, "to") else value
                for name, value in inputs.items()
            }
        except Exception as exc:
            raise RelativeDepthInferenceError(
                "Depth Anything V2 preprocessing failed for the input image."
            ) from exc

        self.model.eval()
        try:
            with torch.inference_mode():
                outputs = self.model(**inputs)
        except Exception as exc:
            raise RelativeDepthInferenceError(
                "Depth Anything V2 model forward pass failed."
            ) from exc

        try:
            raw_prediction = outputs.predicted_depth
            raw_output_shape = tuple(raw_prediction.shape)
            post_processed = self.processor.post_process_depth_estimation(
                outputs,
                target_sizes=[(height, width)],
            )
            depth = post_processed[0]["predicted_depth"].detach().cpu().numpy()
        except Exception as exc:
            raise RelativeDepthInferenceError(
                "Depth Anything V2 postprocessing failed."
            ) from exc
        depth = np.asarray(depth, dtype=np.float32)

        if depth.ndim != 2:
            raise RelativeDepthOutputError(
                f"Expected 2D relative depth, got shape {depth.shape}."
            )
        if depth.shape != (height, width):
            raise RelativeDepthOutputError(
                "Relative depth shape mismatch: "
                f"expected {(height, width)}, got {depth.shape}."
            )
        if not np.isfinite(depth).all():
            raise RelativeDepthOutputError(
                "Relative depth prediction contains NaN or Inf values."
            )

        metadata = RelativeDepthMetadata(
            model_name=self.metadata.model_name,
            checkpoint_id=self.metadata.checkpoint_id,
            model_source=self.metadata.model_source,
            license=self.metadata.license,
            device=self.metadata.device,
            framework=self.metadata.framework,
            output_convention=self.metadata.output_convention,
            extra={
                **dict(self.metadata.extra),
                "original_input_shape": (height, width, 3),
                "model_input_shape": model_input_shape,
                "raw_output_shape": raw_output_shape,
                "final_output_shape": tuple(depth.shape),
                "postprocessing": "processor.post_process_depth_estimation with target_sizes=(H, W)",
            },
        )
        return depth, metadata


def load_default_adapter(
    device: str = "auto",
    local_files_only: bool = False,
) -> DepthAnythingV2SmallAdapter:
    """Load the selected Depth Anything V2 Small relative-depth adapter."""

    return DepthAnythingV2SmallAdapter(
        device=device,
        local_files_only=local_files_only,
    )


def predict_depth(image: ImageInput) -> tuple[DepthArray, RelativeDepthMetadata]:
    """Load the default adapter and return relative monocular depth."""

    return load_default_adapter(device="auto", local_files_only=True).predict_depth(image)


def write_depth_artifacts(
    image: ImageInput,
    output_dir: str | Path,
    adapter: RelativeDepthAdapter | None = None,
) -> DepthArtifactResult:
    """Run one prediction and write depth.npy, depth.png, and metadata JSON."""

    import numpy as np
    from PIL import Image

    selected_adapter = adapter or load_default_adapter(
        device="auto",
        local_files_only=True,
    )
    output_path = Path(output_dir)
    depth_npy_path = output_path / "depth.npy"
    depth_png_path = output_path / "depth.png"
    metadata_json_path = output_path / "model_metadata.json"

    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ArtifactWriteError(
            f"Unable to create relative-depth output directory: {output_path}"
        ) from exc

    start = time.perf_counter()
    try:
        depth, prediction_metadata = selected_adapter.predict_depth(image)
    except Exception as exc:
        raise RelativeDepthInferenceError(
            "Relative-depth prediction failed before artifact writing."
        ) from exc
    runtime_seconds = time.perf_counter() - start

    depth = np.asarray(depth, dtype=np.float32)
    if depth.ndim != 2:
        raise RelativeDepthOutputError(
            f"Expected 2D relative depth before artifact writing, got {depth.shape}."
        )
    if not np.isfinite(depth).all():
        raise RelativeDepthOutputError(
            "Relative depth contains NaN or Inf before artifact writing."
        )

    metadata_payload = _artifact_metadata_payload(
        prediction_metadata=prediction_metadata,
        depth=depth,
        runtime_seconds=runtime_seconds,
        depth_npy_path=depth_npy_path,
        depth_png_path=depth_png_path,
    )

    try:
        np.save(depth_npy_path, depth)
        preview = _relative_depth_to_uint8_preview(depth)
        Image.fromarray(preview, mode="L").save(depth_png_path)
        metadata_json_path.write_text(
            json.dumps(metadata_payload, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        raise ArtifactWriteError(
            f"Unable to write relative-depth artifacts in {output_path}."
        ) from exc

    try:
        reloaded_depth = np.load(depth_npy_path)
        with Image.open(depth_png_path) as preview_image:
            preview_size = preview_image.size
        reloaded_metadata = json.loads(metadata_json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ArtifactWriteError(
            f"Unable to reload relative-depth artifacts from {output_path}."
        ) from exc

    if reloaded_depth.shape != depth.shape or reloaded_depth.dtype != np.float32:
        raise ArtifactWriteError("Reloaded depth.npy does not match expected shape/dtype.")
    if not np.isfinite(reloaded_depth).all():
        raise ArtifactWriteError("Reloaded depth.npy contains NaN or Inf values.")
    if preview_size != (depth.shape[1], depth.shape[0]):
        raise ArtifactWriteError("Reloaded depth.png does not match depth grid size.")
    if (
        reloaded_metadata.get("metric") is not False
        or reloaded_metadata.get("units") != "relative_arbitrary"
    ):
        raise ArtifactWriteError(
            "Reloaded model_metadata.json does not describe relative non-metric depth."
        )

    return DepthArtifactResult(
        depth=depth,
        metadata=metadata_payload,
        depth_npy_path=depth_npy_path,
        depth_png_path=depth_png_path,
        metadata_json_path=metadata_json_path,
    )


def _relative_depth_to_uint8_preview(depth: DepthArray) -> Any:
    import numpy as np

    depth = np.asarray(depth, dtype=np.float32)
    depth_min = float(np.min(depth))
    depth_max = float(np.max(depth))
    if depth_max == depth_min:
        return np.zeros(depth.shape, dtype=np.uint8)
    return np.rint((depth - depth_min) / (depth_max - depth_min) * 255.0).clip(
        0,
        255,
    ).astype(np.uint8)


def _artifact_metadata_payload(
    prediction_metadata: RelativeDepthMetadata,
    depth: DepthArray,
    runtime_seconds: float,
    depth_npy_path: Path,
    depth_png_path: Path,
) -> dict[str, Any]:
    import numpy as np

    extra = dict(prediction_metadata.extra)
    checkpoint_id = prediction_metadata.checkpoint_id
    cache_info = _model_cache_info(checkpoint_id)

    return {
        "model_name": prediction_metadata.model_name,
        "checkpoint": checkpoint_id,
        "cached_revision": cache_info["cached_revision"],
        "source": prediction_metadata.model_source,
        "licence": prediction_metadata.license,
        "device": prediction_metadata.device,
        "runtime_seconds": runtime_seconds,
        "runtime_scope": (
            "preprocessing, model forward pass, postprocessing, and artifact writing; "
            "excludes model load when a preloaded adapter is supplied"
        ),
        "original_input_shape": _json_safe(extra.get("original_input_shape")),
        "model_input_shape": _json_safe(extra.get("model_input_shape")),
        "raw_output_shape": _json_safe(extra.get("raw_output_shape")),
        "final_output_shape": list(depth.shape),
        "output_dtype": str(depth.dtype),
        "units": prediction_metadata.output_units,
        "metric": prediction_metadata.metric_depth,
        "output_convention": prediction_metadata.output_convention,
        "preprocessing_summary": (
            "Input converted to RGB; checkpoint image processor handles resize, "
            "rescale, and normalization."
        ),
        "postprocessing_summary": extra.get(
            "postprocessing",
            "Model output restored to original H x W grid before saving.",
        ),
        "visualization": {
            "file": str(depth_png_path),
            "role": "preview_only",
            "normalization": (
                "linear min-max normalization of the relative-depth array to "
                "uint8 0-255 grayscale; constant arrays become all-zero previews"
            ),
            "source_array": str(depth_npy_path),
        },
        "torch_version": _optional_version("torch"),
        "transformers_version": _optional_version("transformers"),
        "cache": cache_info,
        "warning": (
            "This output is relative monocular depth in arbitrary units. It is "
            "not absolute elevation, metres, terrain height, calibrated DSM, or "
            "independently validated elevation; downstream calibration is required "
            "for metric products."
        ),
        "array_statistics": {
            "min": float(np.min(depth)),
            "max": float(np.max(depth)),
            "mean": float(np.mean(depth)),
            "std": float(np.std(depth)),
        },
    }


def _model_cache_info(checkpoint_id: str | None) -> dict[str, Any]:
    cache_info: dict[str, Any] = {
        "local_files_only": True,
        "hf_hub_cache": None,
        "model_cache_paths": [],
        "cached_revision": None,
    }
    if not checkpoint_id:
        return cache_info
    try:
        from huggingface_hub import scan_cache_dir
        from huggingface_hub.constants import HF_HUB_CACHE

        cache_info["hf_hub_cache"] = str(HF_HUB_CACHE)
        for repo in scan_cache_dir().repos:
            if repo.repo_id == checkpoint_id:
                cache_info["model_cache_paths"].append(str(repo.repo_path))
                for revision in repo.revisions:
                    cache_info["cached_revision"] = revision.commit_hash
                    break
                break
    except Exception:
        return cache_info
    return cache_info


def _optional_version(package_name: str) -> str | None:
    try:
        import importlib.metadata as metadata

        return metadata.version(package_name)
    except Exception:
        return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _load_rgb_image(image: ImageInput) -> Any:
    from PIL import Image
    from PIL import UnidentifiedImageError

    if isinstance(image, (str, Path)):
        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")
        try:
            with Image.open(image_path) as opened:
                return opened.convert("RGB")
        except (OSError, UnidentifiedImageError) as exc:
            raise ImageInputError(
                f"Unsupported or unreadable image file: {image_path}"
            ) from exc
    if isinstance(image, Image.Image):
        if image.width <= 0 or image.height <= 0:
            raise ImageInputError("Input image must have positive dimensions.")
        try:
            return image.convert("RGB")
        except Exception as exc:
            raise ImageInputError("Unable to convert PIL image to RGB.") from exc

    try:
        import numpy as np
    except Exception:
        np = None

    if np is not None and isinstance(image, np.ndarray):
        if image.ndim != 3 or image.shape[2] != 3:
            raise ImageInputError(
                "NumPy image input must have shape H x W x 3 for RGB."
            )
        if image.shape[0] <= 0 or image.shape[1] <= 0:
            raise ImageInputError("NumPy image input must have positive dimensions.")
        if image.dtype != np.uint8:
            raise ImageInputError("NumPy RGB image input must use uint8 dtype.")
        if not np.isfinite(image).all():
            raise ImageInputError("NumPy image input contains NaN or Inf values.")
        return Image.fromarray(image, mode="RGB")

    raise ImageInputError(
        "image must be a filesystem path, PIL.Image.Image, or uint8 H x W x 3 RGB array."
    )
