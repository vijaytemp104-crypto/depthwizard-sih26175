"""Real relative-depth orchestration with explicit downstream placeholders."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from PIL import Image

os.environ.setdefault(
    "HF_HOME",
    str(Path(__file__).resolve().parents[2] / "outputs" / ".hf_cache"),
)

from backend.schemas.job import JobStatus, PipelineStage, StageStatus, StandardError
from backend.services.job_store import InMemoryJobStore
from backend.services.relative_depth_adapter import (
    RelativeDepthAdapter,
    load_default_adapter,
    write_depth_artifacts,
)


class DepthPipeline:
    def __init__(
        self,
        store: InMemoryJobStore,
        output_root: Path | None = None,
        adapter_factory: Callable[[], RelativeDepthAdapter] | None = None,
    ) -> None:
        self.store = store
        self.output_root = output_root or Path(__file__).resolve().parents[2] / "outputs"
        self.adapter_factory = adapter_factory or (
            lambda: load_default_adapter(device="auto", local_files_only=True)
        )

    def run(self, job_id: str, original_filename: str, input_path: Path) -> None:
        job_dir = self.output_root / job_id
        try:
            self.store.update_job_status(job_id, JobStatus.RUNNING)
            self.store.update_stage_status(job_id, PipelineStage.INGEST, StageStatus.RUNNING)
            with Image.open(input_path) as source:
                width, height = source.size
                channels = len(source.getbands())
                source.verify()
            self.store.update_stage_status(
                job_id,
                PipelineStage.INGEST,
                StageStatus.SUCCEEDED,
                message="RGB source image verified and stored locally.",
            )

            self.store.update_stage_status(job_id, PipelineStage.DEPTH, StageStatus.RUNNING)
            artifacts = write_depth_artifacts(input_path, job_dir, self.adapter_factory())
            metadata = dict(artifacts.metadata)
            if tuple(artifacts.depth.shape) != (height, width):
                raise ValueError("Depth output does not match the source image grid.")
            self.store.update_stage_status(
                job_id,
                PipelineStage.DEPTH,
                StageStatus.SUCCEEDED,
                message="Real relative monocular depth inference completed.",
            )
            self.store.update_stage_status(
                job_id,
                PipelineStage.CALIBRATION,
                StageStatus.SKIPPED,
                reason="Awaiting calibration integration",
            )
            self.store.update_stage_status(
                job_id,
                PipelineStage.VALIDATION,
                StageStatus.SKIPPED,
                reason="Awaiting independent validation integration",
            )

            self.store.update_stage_status(job_id, PipelineStage.TERRAIN, StageStatus.RUNNING)
            mock_terrain = {
                "mock": True,
                "mode": "synthetic_placeholder",
                "note": "Synthetic unitless demo grid; not terrain, elevation, or metres.",
                "width": 2,
                "height": 2,
                "coordinate_mode": "relative",
                "height_units": "synthetic_demo_units",
                "heights": [[0.0, 0.25], [0.75, 1.0]],
            }
            terrain_path = job_dir / "mock_terrain.json"
            terrain_path.write_text(json.dumps(mock_terrain, indent=2), encoding="utf-8")
            self.store.update_stage_status(
                job_id,
                PipelineStage.TERRAIN,
                StageStatus.SUCCEEDED,
                message="Synthetic terrain placeholder retained; no terrain processing performed.",
            )

            self.store.update_stage_status(job_id, PipelineStage.EVIDENCE, StageStatus.RUNNING)
            evidence = {
                "mock": False,
                "depth_inference": "real",
                "depth_metric": False,
                "checkpoint": metadata.get("checkpoint"),
                "calibration": "not integrated",
                "independent_validation": "not integrated",
            }
            evidence_path = job_dir / "depth_evidence.json"
            evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            self.store.update_stage_status(
                job_id,
                PipelineStage.EVIDENCE,
                StageStatus.SUCCEEDED,
                message="Real model provenance recorded; this is not independent validation.",
            )

            job = self.store.update_job_status(job_id, JobStatus.SUCCEEDED)
            if job is None:
                return
            names = ["depth.npy", "depth.png", "model_metadata.json", "mock_terrain.json", "depth_evidence.json"]
            artifact_paths = {name: str(job_dir / name) for name in names}
            relative = {name: f"outputs/{job_id}/{name}" for name in names}
            model_metadata = {
                "model_name": metadata.get("model_name"),
                "model_version": metadata.get("cached_revision"),
                "checkpoint": metadata.get("checkpoint"),
                "device": metadata.get("device"),
                "runtime_seconds": metadata.get("runtime_seconds"),
                "preprocessing": metadata.get("preprocessing_summary"),
                "input_shape": metadata.get("original_input_shape"),
                "output_shape": metadata.get("final_output_shape"),
            }
            result = {
                "mock": False,
                "pipeline_mode": "real_depth_synthetic_terrain",
                "notice": "Depth is real relative monocular inference; it is not metric elevation.",
                "job_id": job.job_id,
                "job_status": job.job_status.value,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
                "input": {
                    "input_id": f"INPUT-{job_id}",
                    "original_filename": original_filename,
                    "file_type": input_path.suffix.lower().lstrip("."),
                    "width": width,
                    "height": height,
                    "channels": channels,
                    "georeferenced": None,
                    "crs": None,
                    "transform": None,
                    "bounds": None,
                    "pixel_size": None,
                    "nodata": None,
                    "artifact_path": f"outputs/{job_id}/input/{original_filename}",
                },
                "stages": {stage.value: state.model_dump(mode="json") for stage, state in job.stages.items()},
                "depth": {
                    "mock": False,
                    "status": "succeeded",
                    "artifacts": {
                        "array": relative["depth.npy"],
                        "preview": relative["depth.png"],
                        "model_metadata": relative["model_metadata.json"],
                    },
                    "width": width,
                    "height": height,
                    "units": "relative",
                    "array_orientation": "height x width; row-major raster convention",
                    "model_metadata": model_metadata,
                    "reason": None,
                },
                "calibration": {
                    "status": "skipped", "calibrated": False, "units": "relative",
                    "method": None, "reference_source": None, "scale_a": None, "offset_b": None,
                    "valid_anchor_count": None, "crs": None, "transform": None, "warnings": [],
                    "artifacts": {"calibrated_dsm": None, "calibration_metadata": None},
                    "reason": "Awaiting calibration integration",
                },
                "validation": {
                    "status": "skipped", "reference_source": None, "rmse": None, "mae": None,
                    "correlation": None, "valid_pixel_count": None, "units": None,
                    "artifacts": {"metrics": None, "error_map": None},
                    "reason": "Awaiting independent validation integration",
                },
                "terrain": {
                    **mock_terrain, "status": "succeeded", "texture_artifact": None,
                    "crs": None, "transform": None, "artifact_path": relative["mock_terrain.json"],
                    "reason": "Synthetic placeholder only; not elevation or terrain output.",
                },
                "evidence": {
                    "mock": False, "status": "succeeded", "confidence_map": None,
                    "evidence_passport": relative["depth_evidence.json"], "summary": evidence,
                    "independent_validation_substitute": False, "reason": None,
                },
                "artifacts": list(relative.values()),
                "errors": [],
            }
            self.store.set_artifacts(job_id, artifact_paths)
            self.store.set_result(job_id, result)
        except Exception as exc:
            self.store.update_stage_status(
                job_id,
                PipelineStage.DEPTH,
                StageStatus.FAILED,
                reason="Relative-depth inference could not complete.",
            )
            self.store.update_job_status(job_id, JobStatus.FAILED)
            self.store.add_error(
                job_id,
                StandardError(
                    code="RELATIVE_DEPTH_FAILED",
                    stage=PipelineStage.DEPTH,
                    message="Relative-depth inference could not complete.",
                    detail={"error_type": type(exc).__name__},
                    recoverable=True,
                ),
            )
