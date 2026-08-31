"""Deterministic demo pipeline for end-to-end plumbing only.

This module performs no scientific inference, calibration, validation, or terrain
reconstruction. It exists solely to exercise job, artifact, and frontend flows.
"""

import json
from pathlib import Path

from backend.schemas.job import JobStatus, PipelineStage, StageStatus, StandardError
from backend.services.job_store import InMemoryJobStore


class MockPipeline:
    def __init__(self, store: InMemoryJobStore, output_root: Path | None = None) -> None:
        self.store = store
        self.output_root = output_root or Path(__file__).resolve().parents[2] / "outputs"

    def run(self, job_id: str, original_filename: str, input_path: Path) -> None:
        try:
            self.store.update_job_status(job_id, JobStatus.RUNNING)
            self.store.update_stage_status(job_id, PipelineStage.INGEST, StageStatus.RUNNING)
            self.store.update_stage_status(
                job_id,
                PipelineStage.INGEST,
                StageStatus.SUCCEEDED,
                message="Demo upload stored locally; no raster parsing performed.",
            )

            self.store.update_stage_status(job_id, PipelineStage.DEPTH, StageStatus.RUNNING)
            job_dir = self.output_root / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            mock_depth = {
                "mock": True,
                "mode": "demo",
                "note": "Synthetic placeholder only; no monocular depth model was run.",
                "units": "relative_demo_units",
                "values": [[0.0, 0.25], [0.75, 1.0]],
            }
            mock_terrain = {
                "mock": True,
                "mode": "synthetic_placeholder",
                "note": "Tiny unitless demo grid; not terrain, elevation, or metres.",
                "width": 2,
                "height": 2,
                "coordinate_mode": "relative",
                "height_units": "synthetic_demo_units",
                "heights": [[0.0, 0.25], [0.75, 1.0]],
            }
            mock_evidence = {
                "mock": True,
                "mode": "demo",
                "note": "Plumbing evidence only; not scientific confidence or validation.",
                "input_filename": original_filename,
                "input_stored": input_path.is_file(),
                "independent_validation_substitute": False,
            }

            artifacts = {
                "mock_depth.json": mock_depth,
                "mock_terrain.json": mock_terrain,
                "mock_evidence.json": mock_evidence,
            }
            artifact_paths: dict[str, str] = {}
            for name, payload in artifacts.items():
                path = job_dir / name
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                artifact_paths[name] = str(path)

            self.store.update_stage_status(
                job_id,
                PipelineStage.DEPTH,
                StageStatus.SUCCEEDED,
                message="Demo placeholder — real depth module not integrated yet.",
            )
            self.store.update_stage_status(
                job_id,
                PipelineStage.CALIBRATION,
                StageStatus.SKIPPED,
                reason="Mock pipeline: no real calibration performed",
            )
            self.store.update_stage_status(
                job_id,
                PipelineStage.VALIDATION,
                StageStatus.SKIPPED,
                reason="Mock pipeline: no independent reference validation performed",
            )
            self.store.update_stage_status(job_id, PipelineStage.TERRAIN, StageStatus.RUNNING)
            self.store.update_stage_status(
                job_id,
                PipelineStage.TERRAIN,
                StageStatus.SUCCEEDED,
                message="Synthetic 2x2 placeholder only; no terrain processing performed.",
            )
            self.store.update_stage_status(job_id, PipelineStage.EVIDENCE, StageStatus.RUNNING)
            self.store.update_stage_status(
                job_id,
                PipelineStage.EVIDENCE,
                StageStatus.SUCCEEDED,
                message="Demo plumbing metadata only; not scientific evidence.",
            )

            job = self.store.update_job_status(job_id, JobStatus.SUCCEEDED)
            if job is None:
                return

            relative_artifacts = [f"outputs/{job_id}/{name}" for name in artifacts]
            result = {
                "mock": True,
                "pipeline_mode": "demo_synthetic_placeholder",
                "notice": "No real scientific processing was performed.",
                "job_id": job.job_id,
                "job_status": job.job_status.value,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
                "input": {
                    "input_id": f"INPUT-{job_id}",
                    "original_filename": original_filename,
                    "file_type": input_path.suffix.lower().lstrip("."),
                    "width": None,
                    "height": None,
                    "channels": None,
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
                    "mock": True,
                    "status": "succeeded",
                    "artifacts": {"array": None, "preview": None, "model_metadata": None},
                    "width": None,
                    "height": None,
                    "units": "relative",
                    "array_orientation": "height x width; row-major raster convention",
                    "model_metadata": None,
                    "reason": "Demo placeholder — real depth module not integrated yet",
                },
                "calibration": {
                    "status": "skipped",
                    "calibrated": False,
                    "units": "relative",
                    "method": None,
                    "reference_source": None,
                    "scale_a": None,
                    "offset_b": None,
                    "valid_anchor_count": None,
                    "crs": None,
                    "transform": None,
                    "warnings": [],
                    "artifacts": {"calibrated_dsm": None, "calibration_metadata": None},
                    "reason": "Mock pipeline: no real calibration performed",
                },
                "validation": {
                    "status": "skipped",
                    "reference_source": None,
                    "rmse": None,
                    "mae": None,
                    "correlation": None,
                    "valid_pixel_count": None,
                    "units": None,
                    "artifacts": {"metrics": None, "error_map": None},
                    "reason": "Mock pipeline: no independent reference validation performed",
                },
                "terrain": {
                    "mock": True,
                    "status": "succeeded",
                    "width": 2,
                    "height": 2,
                    "heights": [[0.0, 0.25], [0.75, 1.0]],
                    "height_units": "synthetic_demo_units",
                    "texture_artifact": None,
                    "coordinate_mode": "relative",
                    "crs": None,
                    "transform": None,
                    "artifact_path": f"outputs/{job_id}/mock_terrain.json",
                    "reason": "Synthetic placeholder only; not elevation or terrain output.",
                },
                "evidence": {
                    "mock": True,
                    "status": "succeeded",
                    "confidence_map": None,
                    "evidence_passport": None,
                    "summary": {"note": "Demo plumbing metadata only"},
                    "independent_validation_substitute": False,
                    "reason": None,
                },
                "artifacts": relative_artifacts,
                "errors": [],
            }
            self.store.set_artifacts(job_id, artifact_paths)
            self.store.set_result(job_id, result)
        except Exception:
            self.store.update_stage_status(
                job_id,
                PipelineStage.INGEST,
                StageStatus.FAILED,
                reason="Mock processing could not complete.",
            )
            self.store.update_job_status(job_id, JobStatus.FAILED)
            self.store.add_error(
                job_id,
                StandardError(
                    code="MOCK_PIPELINE_FAILED",
                    stage=PipelineStage.INGEST,
                    message="The demo pipeline could not complete.",
                    detail=None,
                    recoverable=True,
                )
            )
