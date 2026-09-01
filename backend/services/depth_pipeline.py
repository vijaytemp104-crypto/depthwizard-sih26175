"""Real relative-depth orchestration with optional geospatial calibration."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Callable

from PIL import Image

os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parents[2] / "outputs" / ".hf_cache"))

from backend.schemas.job import JobStatus, PipelineStage, StageStatus, StandardError
from backend.services.ayush.pipeline import run_pipeline as run_ayush_pipeline
from backend.services.job_store import InMemoryJobStore
from backend.services.relative_depth_adapter import RelativeDepthAdapter, load_default_adapter, write_depth_artifacts


class DepthPipeline:
    def __init__(self, store: InMemoryJobStore, output_root: Path | None = None,
                 adapter_factory: Callable[[], RelativeDepthAdapter] | None = None) -> None:
        self.store = store
        self.output_root = output_root or Path(__file__).resolve().parents[2] / "outputs"
        self.adapter_factory = adapter_factory or (lambda: load_default_adapter(device="auto", local_files_only=True))

    def run(self, job_id: str, original_filename: str, input_path: Path,
            reference_path: Path | None = None) -> None:
        job_dir = self.output_root / job_id
        try:
            self.store.update_job_status(job_id, JobStatus.RUNNING)
            self.store.update_stage_status(job_id, PipelineStage.INGEST, StageStatus.RUNNING)
            input_meta = _inspect_input(input_path)
            width, height = input_meta["width"], input_meta["height"]
            self.store.update_stage_status(job_id, PipelineStage.INGEST, StageStatus.SUCCEEDED,
                message="RGB source image and available geospatial metadata verified.")
            self.store.update_stage_status(job_id, PipelineStage.DEPTH, StageStatus.RUNNING)
            depth_result = write_depth_artifacts(input_path, job_dir, self.adapter_factory())
            model_meta = dict(depth_result.metadata)
            if tuple(depth_result.depth.shape) != (height, width):
                raise ValueError("Depth output does not match the source image grid.")
            self.store.update_stage_status(job_id, PipelineStage.DEPTH, StageStatus.SUCCEEDED,
                message="Real relative monocular depth inference completed.")
        except Exception as exc:
            self._fail_depth(job_id, exc)
            return

        calibration, terrain, extra_names = self._calibrate(
            job_id, job_dir, depth_result.depth_npy_path, input_meta, reference_path)
        self.store.update_stage_status(job_id, PipelineStage.VALIDATION, StageStatus.SKIPPED,
            reason="Independent validation module not integrated yet.")
        self.store.update_stage_status(job_id, PipelineStage.EVIDENCE, StageStatus.RUNNING)
        evidence = {
            "mock": False, "depth_inference": "real", "depth_metric": False,
            "checkpoint": model_meta.get("checkpoint"), "calibration": calibration["status"],
            "calibration_fit_is_independent_validation": False,
            "independent_validation": "not integrated",
        }
        (job_dir / "depth_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        self.store.update_stage_status(job_id, PipelineStage.EVIDENCE, StageStatus.SUCCEEDED,
            message="Depth/calibration provenance recorded; independent validation remains skipped.")

        job = self.store.update_job_status(job_id, JobStatus.SUCCEEDED)
        if job is None:
            return
        names = ["depth.npy", "depth.png", "model_metadata.json", *extra_names, "depth_evidence.json"]
        relative = {name: f"outputs/{job_id}/{name}" for name in names}
        calibration["artifacts"] = {
            "calibrated_dsm": relative.get("calibrated_dsm.tif"),
            "calibration_metadata": relative.get("calibration.json"),
        }
        terrain["artifact_path"] = relative.get("terrain.json") or relative.get("mock_terrain.json")
        result = {
            "mock": False,
            "pipeline_mode": "real_depth_metric_calibration" if calibration["calibrated"] else "real_depth_synthetic_terrain",
            "notice": ("Depth is real and the DSM is calibrated in metres; independent validation is not integrated."
                       if calibration["calibrated"] else
                       "Depth is real relative monocular inference; no metric elevation was produced."),
            "job_id": job.job_id, "job_status": job.job_status.value,
            "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat(),
            "input": {
                "input_id": f"INPUT-{job_id}", "original_filename": original_filename,
                "file_type": input_path.suffix.lower().lstrip("."),
                **{key: value for key, value in input_meta.items() if key != "transform_gdal"},
                "artifact_path": f"outputs/{job_id}/input/{original_filename}",
            },
            "stages": {stage.value: state.model_dump(mode="json") for stage, state in job.stages.items()},
            "depth": {
                "mock": False, "status": "succeeded",
                "artifacts": {"array": relative["depth.npy"], "preview": relative["depth.png"],
                              "model_metadata": relative["model_metadata.json"]},
                "width": width, "height": height, "units": "relative",
                "array_orientation": "height x width; row-major raster convention",
                "model_metadata": {
                    "model_name": model_meta.get("model_name"), "model_version": model_meta.get("cached_revision"),
                    "checkpoint": model_meta.get("checkpoint"), "device": model_meta.get("device"),
                    "runtime_seconds": model_meta.get("runtime_seconds"),
                    "preprocessing": model_meta.get("preprocessing_summary"),
                    "input_shape": model_meta.get("original_input_shape"),
                    "output_shape": model_meta.get("final_output_shape"),
                }, "reason": None,
            },
            "calibration": calibration,
            "validation": {
                "status": "skipped", "reference_source": None, "rmse": None, "mae": None,
                "correlation": None, "valid_pixel_count": None, "units": None,
                "artifacts": {"metrics": None, "error_map": None},
                "reason": "Independent validation module not integrated yet.",
            },
            "terrain": terrain,
            "evidence": {
                "mock": False, "status": "succeeded", "confidence_map": None,
                "evidence_passport": relative["depth_evidence.json"], "summary": evidence,
                "independent_validation_substitute": False, "reason": None,
            },
            "artifacts": list(relative.values()),
            "errors": [error.model_dump(mode="json") for error in job.errors],
        }
        self.store.set_artifacts(job_id, {name: str(job_dir / name) for name in names})
        self.store.set_result(job_id, result)

    def _calibrate(self, job_id: str, job_dir: Path, depth_path: Path, input_meta: dict,
                   reference_path: Path | None) -> tuple[dict, dict, list[str]]:
        if reference_path is None:
            reason = "No reference DEM supplied; relative depth remains non-metric."
            self.store.update_stage_status(job_id, PipelineStage.CALIBRATION, StageStatus.SKIPPED, reason=reason)
            return self._relative_outputs(job_id, job_dir, reason)
        self.store.update_stage_status(job_id, PipelineStage.CALIBRATION, StageStatus.RUNNING)
        try:
            if not input_meta["georeferenced"]:
                raise ValueError("Metric calibration requires a georeferenced source GeoTIFF.")
            Path(str(depth_path) + ".json").write_text(json.dumps({
                "crs": input_meta["crs"], "transform": input_meta["transform_gdal"]
            }, indent=2), encoding="utf-8")
            run_ayush_pipeline(depth_path, reference_path, job_dir)
            fit = json.loads((job_dir / "calibration.json").read_text(encoding="utf-8"))
            terrain_json = json.loads((job_dir / "terrain.json").read_text(encoding="utf-8"))
            dsm = _verify_dsm(job_dir / "calibrated_dsm.tif", input_meta)
            if (terrain_json["height"], terrain_json["width"]) != tuple(dsm["shape"]):
                raise ValueError("terrain.json grid does not match calibrated DSM orientation.")
            viewer = _viewer_terrain(terrain_json)
            calibration = {
                "status": "succeeded", "calibrated": True, "units": "metres",
                "method": "linear E = aD + b (ordinary least squares)",
                "reference_source": f"Uploaded reference DEM: {reference_path.name}",
                "scale_a": fit["coefficients"]["a"], "offset_b": fit["coefficients"]["b"],
                "valid_anchor_count": fit["valid_pixels"], "crs": dsm["crs"],
                "transform": dsm["transform"],
                "warnings": ["RMSE and R² below are calibration-fit diagnostics, not independent validation."],
                "fit_rmse_metres": fit["rmse_metres"], "fit_r_squared": fit["r_squared"],
                "reason": None,
            }
            terrain = {
                "mock": False, "status": "succeeded", **viewer, "height_units": "metres",
                "texture_artifact": None, "coordinate_mode": "geospatial", "crs": dsm["crs"],
                "reason": None, "full_raster_width": terrain_json["width"],
                "full_raster_height": terrain_json["height"],
            }
            self.store.update_stage_status(job_id, PipelineStage.CALIBRATION, StageStatus.SUCCEEDED,
                message="Metric DSM calibrated from the uploaded reference DEM.")
            self.store.update_stage_status(job_id, PipelineStage.TERRAIN, StageStatus.SUCCEEDED,
                message="Georeferenced metric terrain prepared for MissionView.")
            return calibration, terrain, ["calibrated_dsm.tif", "terrain.json", "calibration.json"]
        except Exception as exc:
            reason = f"Calibration unavailable: {type(exc).__name__}."
            self.store.update_stage_status(job_id, PipelineStage.CALIBRATION, StageStatus.FAILED, reason=reason)
            self.store.add_error(job_id, StandardError(
                code="CALIBRATION_FAILED", stage=PipelineStage.CALIBRATION,
                message="Metric calibration could not complete; relative depth remains available.",
                detail={"error_type": type(exc).__name__}, recoverable=True))
            return self._relative_outputs(job_id, job_dir, reason, "failed")

    def _relative_outputs(self, job_id: str, job_dir: Path, reason: str,
                          status: str = "skipped") -> tuple[dict, dict, list[str]]:
        terrain = {
            "mock": True, "mode": "synthetic_placeholder", "status": "succeeded",
            "note": "Synthetic unitless demo grid; not terrain, elevation, or metres.",
            "width": 2, "height": 2, "heights": [[0.0, 0.25], [0.75, 1.0]],
            "height_units": "synthetic_demo_units", "texture_artifact": None,
            "coordinate_mode": "relative", "crs": None, "transform": None,
            "reason": "Synthetic placeholder only; not elevation or terrain output.",
        }
        (job_dir / "mock_terrain.json").write_text(json.dumps(terrain, indent=2), encoding="utf-8")
        self.store.update_stage_status(job_id, PipelineStage.TERRAIN, StageStatus.SUCCEEDED,
            message="Synthetic relative placeholder retained; no metric terrain produced.")
        calibration = {
            "status": status, "calibrated": False, "units": "relative", "method": None,
            "reference_source": None, "scale_a": None, "offset_b": None,
            "valid_anchor_count": None, "crs": None, "transform": None, "warnings": [],
            "fit_rmse_metres": None, "fit_r_squared": None, "reason": reason,
        }
        return calibration, terrain, ["mock_terrain.json"]

    def _fail_depth(self, job_id: str, exc: Exception) -> None:
        self.store.update_stage_status(job_id, PipelineStage.DEPTH, StageStatus.FAILED,
            reason="Relative-depth inference could not complete.")
        self.store.update_job_status(job_id, JobStatus.FAILED)
        self.store.add_error(job_id, StandardError(
            code="RELATIVE_DEPTH_FAILED", stage=PipelineStage.DEPTH,
            message="Relative-depth inference could not complete.",
            detail={"error_type": type(exc).__name__}, recoverable=True))


def _inspect_input(path: Path) -> dict:
    if path.suffix.lower() in {".tif", ".tiff"}:
        import rasterio
        with rasterio.open(path) as source:
            if source.count < 3:
                raise ValueError("Source GeoTIFF must contain at least three RGB bands.")
            georeferenced = source.crs is not None
            bounds = source.bounds
            return {
                "width": source.width, "height": source.height, "channels": source.count,
                "georeferenced": georeferenced,
                "crs": source.crs.to_string() if georeferenced else None,
                "transform": list(source.transform)[:6] if georeferenced else None,
                "transform_gdal": list(source.transform.to_gdal()) if georeferenced else None,
                "bounds": {"left": bounds.left, "bottom": bounds.bottom,
                           "right": bounds.right, "top": bounds.top},
                "pixel_size": {"x": abs(source.res[0]), "y": abs(source.res[1]),
                               "units": "metres" if source.crs and source.crs.is_projected else "crs_units"},
                "nodata": source.nodata,
            }
    with Image.open(path) as source:
        width, height, channels = source.width, source.height, len(source.getbands())
        source.verify()
    return {"width": width, "height": height, "channels": channels, "georeferenced": False,
            "crs": None, "transform": None, "transform_gdal": None, "bounds": None,
            "pixel_size": None, "nodata": None}


def _verify_dsm(path: Path, input_meta: dict) -> dict:
    import numpy as np
    import rasterio
    from affine import Affine
    with rasterio.open(path) as dsm:
        data = dsm.read(1, masked=True).filled(np.nan)
        if dsm.dtypes[0] != "float32" or dsm.count != 1:
            raise ValueError("Calibrated DSM must be a single-band Float32 raster.")
        if dsm.crs is None or dsm.crs.to_string() != input_meta["crs"]:
            raise ValueError("Calibrated DSM CRS does not match the source grid.")
        if not dsm.transform.almost_equals(Affine(*input_meta["transform"])):
            raise ValueError("Calibrated DSM transform does not match the source grid.")
        if data.shape != (input_meta["height"], input_meta["width"]):
            raise ValueError("Calibrated DSM shape does not match the source grid.")
        if np.isfinite(data).sum() < 2:
            raise ValueError("Calibrated DSM has insufficient finite pixels.")
        return {"shape": list(data.shape), "crs": dsm.crs.to_string(),
                "transform": list(dsm.transform)[:6], "nodata": dsm.nodata}


def _viewer_terrain(payload: dict, maximum: int = 128) -> dict:
    from affine import Affine
    step = max(1, math.ceil(payload["height"] / maximum), math.ceil(payload["width"] / maximum))
    heights = [row[::step] for row in payload["elevation"][::step]]
    transform = Affine.from_gdal(*payload["transform"]) * Affine.scale(step, step)
    return {"width": len(heights[0]), "height": len(heights), "heights": heights,
            "transform": list(transform)[:6],
            "viewer_decimation": {"method": "regular stride", "step": step}}
