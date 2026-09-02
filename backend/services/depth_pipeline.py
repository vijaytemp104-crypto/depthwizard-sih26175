"""Real relative-depth orchestration with optional geospatial calibration."""

from __future__ import annotations

import json
import hashlib
import math
import os
from pathlib import Path
from typing import Callable

from PIL import Image

os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parents[2] / "outputs" / ".hf_cache"))

from backend.schemas.job import JobStatus, PipelineStage, StageStatus, StandardError
from backend.services.ayush.export import DEFAULT_NODATA
from backend.services.ayush.geospatial import horizontal_units
from backend.services.ayush.pipeline import run_pipeline as run_ayush_pipeline
from backend.services.job_store import InMemoryJobStore
from backend.services.relative_depth_adapter import RelativeDepthAdapter, load_default_adapter, write_depth_artifacts
from backend.services.validation import skipped_validation, validate_rasters


class DepthPipeline:
    def __init__(self, store: InMemoryJobStore, output_root: Path | None = None,
                 adapter_factory: Callable[[], RelativeDepthAdapter] | None = None) -> None:
        self.store = store
        self.output_root = output_root or Path(__file__).resolve().parents[2] / "outputs"
        self.adapter_factory = adapter_factory or (lambda: load_default_adapter(device="auto", local_files_only=True))

    def run(self, job_id: str, original_filename: str, input_path: Path,
            reference_path: Path | None = None,
            validation_reference_path: Path | None = None) -> None:
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
        validation, validation_names = self._validate(
            job_id, job_dir, calibration, reference_path, validation_reference_path)
        extra_names.extend(validation_names)
        self.store.update_stage_status(job_id, PipelineStage.EVIDENCE, StageStatus.RUNNING)
        evidence = {
            "input": {"filename": original_filename, "file_type": input_path.suffix.lower().lstrip("."),
                      "georeferenced": input_meta["georeferenced"]},
            "depth": {"status": "succeeded", "mode": "relative", "model": model_meta.get("model_name"),
                      "checkpoint": model_meta.get("checkpoint"), "artifact": "depth.npy"},
            "calibration": {"status": calibration["status"], "method": calibration["method"],
                            "reference_source": calibration["reference_source"],
                            "scale_a": calibration["scale_a"], "offset_b": calibration["offset_b"],
                            "fit_scope": calibration.get("fit_scope"),
                            "fit_rmse_metres": calibration.get("fit_rmse_metres"),
                            "fit_r_squared": calibration.get("fit_r_squared"),
                            "fit_is_independent_validation": False,
                            "reference_vertical_units": calibration.get("reference_vertical_units"),
                            "reference_vertical_datum": calibration.get("reference_vertical_datum"),
                            "reference_vertical_crs": calibration.get("reference_vertical_crs"),
                            "reference_units_verified": calibration.get("reference_units_verified"),
                            "artifact": "calibrated_dsm.tif" if calibration["calibrated"] else None},
            "validation": {key: validation.get(key) for key in (
                "status", "reference_source", "rmse", "mae", "correlation", "valid_pixel_count", "reason")},
            "error_map_artifact": "error_map.tif" if validation["status"] == "succeeded" else None,
            "crs": calibration.get("crs"), "horizontal_units": calibration.get("horizontal_units"),
            "vertical_units": calibration.get("units"),
            "vertical_datum": calibration.get("vertical_datum"),
            "vertical_crs": calibration.get("vertical_crs"),
            "transform": calibration.get("transform"),
            "transform_order": calibration.get("transform_order"),
            "confidence": None, "confidence_reason": "Confidence map is not implemented.",
            "calibration_fit_is_independent_validation": False,
            "warnings": calibration.get("warnings", []) + validation.get("warnings", []),
        }
        (job_dir / "evidence_passport.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        self.store.update_stage_status(job_id, PipelineStage.EVIDENCE, StageStatus.SUCCEEDED,
            message="Factual pipeline provenance recorded; confidence remains unimplemented.")

        job = self.store.update_job_status(job_id, JobStatus.SUCCEEDED)
        if job is None:
            return
        names = ["depth.npy", "depth.png", "model_metadata.json", *extra_names, "evidence_passport.json"]
        relative = {name: f"outputs/{job_id}/{name}" for name in names}
        calibration["artifacts"] = {
            "calibrated_dsm": relative.get("calibrated_dsm.tif"),
            "calibration_metadata": relative.get("calibration.json"),
        }
        terrain["artifact_path"] = relative.get("terrain.json") or relative.get("mock_terrain.json")
        result = {
            "mock": False,
            "pipeline_mode": ("real_depth_metric_independent_validation" if validation["status"] == "succeeded"
                              else "real_depth_metric_calibration" if calibration["calibrated"]
                              else "real_depth_synthetic_terrain"),
            "notice": ("The metric DSM was evaluated against a separately uploaded independent reference."
                       if validation["status"] == "succeeded" else
                       "Depth is real and the DSM is calibrated in metres; independent validation was not performed."
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
            "validation": validation,
            "terrain": terrain,
            "evidence": {
                "mock": False, "status": "succeeded", "confidence_map": None,
                "evidence_passport": relative["evidence_passport.json"], "summary": evidence,
                "independent_validation_substitute": False, "reason": None,
            },
            "artifacts": list(relative.values()),
            "errors": [error.model_dump(mode="json") for error in job.errors],
        }
        self.store.set_artifacts(job_id, {name: str(job_dir / name) for name in names})
        self.store.set_result(job_id, result)

    def _validate(self, job_id: str, job_dir: Path, calibration: dict,
                  calibration_reference: Path | None,
                  validation_reference: Path | None) -> tuple[dict, list[str]]:
        if validation_reference is None:
            result = skipped_validation()
            self.store.update_stage_status(job_id, PipelineStage.VALIDATION, StageStatus.SKIPPED,
                                           reason=result["reason"])
            return result, []
        if calibration_reference is not None and (
                calibration_reference.resolve() == validation_reference.resolve()
                or _sha256(calibration_reference) == _sha256(validation_reference)):
            result = skipped_validation(
                "Independent validation rejected: calibration and validation references are the same artifact.")
            self.store.update_stage_status(job_id, PipelineStage.VALIDATION, StageStatus.SKIPPED,
                                           reason=result["reason"])
            return result, []
        if not calibration["calibrated"]:
            result = skipped_validation("Independent validation requires a successfully calibrated metric DSM.")
            self.store.update_stage_status(job_id, PipelineStage.VALIDATION, StageStatus.SKIPPED,
                                           reason=result["reason"])
            return result, []
        self.store.update_stage_status(job_id, PipelineStage.VALIDATION, StageStatus.RUNNING)
        try:
            result = validate_rasters(
                job_dir / "calibrated_dsm.tif", validation_reference, job_dir,
                reference_source=f"Uploaded independent validation reference: {validation_reference.name}")
            result["artifacts"] = {
                "metrics": f"outputs/{job_id}/metrics.json",
                "error_map": f"outputs/{job_id}/error_map.tif",
            }
            (job_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            self.store.update_stage_status(job_id, PipelineStage.VALIDATION, StageStatus.SUCCEEDED,
                                           message="Independent DSM validation completed.")
            return result, ["metrics.json", "error_map.tif"]
        except Exception as exc:
            reason = f"Independent validation failed: {str(exc)}"
            result = skipped_validation(reason)
            result["status"] = "failed"
            result["reference_source"] = f"Uploaded independent validation reference: {validation_reference.name}"
            self.store.update_stage_status(job_id, PipelineStage.VALIDATION, StageStatus.FAILED, reason=reason)
            self.store.add_error(job_id, StandardError(
                code="VALIDATION_FAILED", stage=PipelineStage.VALIDATION,
                message="Independent validation could not complete; calibrated DSM remains available.",
                detail={"error_type": type(exc).__name__}, recoverable=True))
            return result, []

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
            reference_metadata = fit["reference"]["metadata"]
            output_metadata = fit["output"]
            warnings = ["RMSE and R² below are calibration-fit diagnostics, not independent validation."]
            if not reference_metadata.get("vertical_datum"):
                warnings.append("Reference vertical datum is not encoded; only metre units were verified.")
            calibration = {
                "status": "succeeded", "calibrated": True, "units": "metres",
                "method": "linear E = aD + b (ordinary least squares)",
                "reference_source": f"Uploaded reference DEM: {reference_path.name}",
                "scale_a": fit["coefficients"]["a"], "offset_b": fit["coefficients"]["b"],
                "valid_anchor_count": fit["valid_pixels"], "crs": dsm["crs"],
                "transform": dsm["transform"],
                "transform_order": "Affine(a, b, c, d, e, f)",
                "horizontal_units": output_metadata["horizontal_units"],
                "vertical_datum": output_metadata.get("vertical_datum"),
                "vertical_crs": output_metadata.get("vertical_crs"),
                "reference_units_verified": fit["reference"]["vertical_units_verified"],
                "reference_vertical_units": reference_metadata["vertical_units"],
                "reference_vertical_datum": reference_metadata.get("vertical_datum"),
                "reference_vertical_crs": reference_metadata.get("vertical_crs"),
                "fit_scope": fit["fit_scope"],
                "fit_is_independent_validation": fit["fit_is_independent_validation"],
                "warnings": warnings,
                "fit_rmse_metres": fit["rmse_metres"], "fit_r_squared": fit["r_squared"],
                "reason": None,
            }
            terrain = {
                "mock": False, "status": "succeeded", **viewer, "height_units": "metres",
                "texture_artifact": None, "coordinate_mode": "geospatial", "crs": dsm["crs"],
                "horizontal_units": output_metadata["horizontal_units"],
                "vertical_datum": output_metadata.get("vertical_datum"),
                "vertical_crs": output_metadata.get("vertical_crs"),
                "transform_order": "Affine(a, b, c, d, e, f)",
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
            "transform_order": None, "horizontal_units": None,
            "vertical_datum": None, "vertical_crs": None,
            "reference_units_verified": False, "reference_vertical_units": None,
            "reference_vertical_datum": None, "reference_vertical_crs": None,
            "fit_scope": None, "fit_is_independent_validation": False,
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
                "transform_order": "Affine(a, b, c, d, e, f)" if georeferenced else None,
                "transform_gdal": list(source.transform.to_gdal()) if georeferenced else None,
                "bounds": {"left": bounds.left, "bottom": bounds.bottom,
                           "right": bounds.right, "top": bounds.top},
                "pixel_size": {"x": abs(source.res[0]), "y": abs(source.res[1]),
                               "units": horizontal_units(source.crs)},
                "nodata": source.nodata,
            }
    with Image.open(path) as source:
        width, height, channels = source.width, source.height, len(source.getbands())
        source.verify()
    return {"width": width, "height": height, "channels": channels, "georeferenced": False,
            "crs": None, "transform": None, "transform_gdal": None,
            "transform_order": None, "bounds": None,
            "pixel_size": None, "nodata": None}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        if dsm.nodata != DEFAULT_NODATA:
            raise ValueError("Calibrated DSM nodata metadata is invalid.")
        if dsm.descriptions[0] != "calibrated_elevation_metres":
            raise ValueError("Calibrated DSM band description is invalid.")
        if str(dsm.units[0] or "").lower() not in {"m", "meter", "metre", "meters", "metres"}:
            raise ValueError("Calibrated DSM must explicitly declare metre vertical units.")
        tags = dsm.tags()
        return {"shape": list(data.shape), "crs": dsm.crs.to_string(),
                "transform": list(dsm.transform)[:6], "nodata": dsm.nodata,
                "vertical_units": dsm.units[0], "vertical_datum": tags.get("VERTICAL_DATUM"),
                "vertical_crs": tags.get("VERTICAL_CRS")}


def _viewer_terrain(payload: dict, maximum: int = 128) -> dict:
    from affine import Affine
    step = max(1, math.ceil(payload["height"] / maximum), math.ceil(payload["width"] / maximum))
    heights = [row[::step] for row in payload["elevation"][::step]]
    transform = Affine.from_gdal(*payload["transform"]) * Affine.scale(step, step)
    return {"width": len(heights[0]), "height": len(heights), "heights": heights,
            "transform": list(transform)[:6],
            "viewer_decimation": {"method": "regular stride", "step": step}}
