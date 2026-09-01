"""Mock upload and process endpoint."""

import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from backend.schemas.job import Job, JobStatus, StandardError
from backend.services.job_store import job_store
from backend.services.depth_pipeline import DepthPipeline
from backend.services.mock_pipeline import MockPipeline

router = APIRouter(tags=["process"])
mock_pipeline = MockPipeline(job_store)
depth_pipeline = DepthPipeline(job_store)
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def safe_error(status_code: int, code: str, message: str, detail: dict | None = None) -> HTTPException:
    error = StandardError(code=code, stage=None, message=message, detail=detail, recoverable=True)
    return HTTPException(status_code=status_code, detail=error.model_dump())


@router.post("/process", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def process_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    reference_dem: UploadFile | None = File(None),
    validation_reference: UploadFile | None = File(None),
    mode: str = Form("real"),
) -> Job:
    supplied_name = file.filename or ""
    filename = Path(supplied_name).name
    extension = Path(filename).suffix.lower()
    if not filename or filename != supplied_name or extension not in SUPPORTED_EXTENSIONS:
        raise safe_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "UNSUPPORTED_FILE_TYPE",
            "Select a PNG, JPG/JPEG, or TIF/TIFF image.",
            {"filename": supplied_name},
        )
    if mode not in {"real", "fallback_mock"}:
        raise safe_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "UNSUPPORTED_PROCESSING_MODE",
            "Processing mode must be 'real' or 'fallback_mock'.",
        )

    job = job_store.create_job()
    pipeline = depth_pipeline if mode == "real" else mock_pipeline
    input_dir = pipeline.output_root / job.job_id / "input"
    input_path = input_dir / filename
    reference_path = None
    validation_reference_path = None
    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        with input_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)
        if reference_dem is not None:
            supplied_reference = reference_dem.filename or ""
            reference_name = Path(supplied_reference).name
            if (
                not reference_name
                or reference_name != supplied_reference
                or Path(reference_name).suffix.lower() not in {".tif", ".tiff"}
            ):
                raise safe_error(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    "UNSUPPORTED_REFERENCE_TYPE",
                    "Reference DEM must be a TIF/TIFF GeoTIFF.",
                    {"filename": supplied_reference},
                )
            reference_path = input_dir / f"reference_{reference_name}"
            with reference_path.open("wb") as destination:
                shutil.copyfileobj(reference_dem.file, destination)
        if validation_reference is not None:
            supplied_validation = validation_reference.filename or ""
            validation_name = Path(supplied_validation).name
            if (
                not validation_name
                or validation_name != supplied_validation
                or Path(validation_name).suffix.lower() not in {".tif", ".tiff"}
            ):
                raise safe_error(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    "UNSUPPORTED_VALIDATION_REFERENCE_TYPE",
                    "Independent validation reference must be a TIF/TIFF GeoTIFF.",
                    {"filename": supplied_validation},
                )
            validation_reference_path = input_dir / f"validation_{validation_name}"
            with validation_reference_path.open("wb") as destination:
                shutil.copyfileobj(validation_reference.file, destination)
    except OSError:
        job_store.update_job_status(job.job_id, JobStatus.FAILED)
        raise safe_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "UPLOAD_STORE_FAILED",
            "The uploaded file could not be stored for demo processing.",
        )
    finally:
        await file.close()
        if reference_dem is not None:
            await reference_dem.close()
        if validation_reference is not None:
            await validation_reference.close()

    if mode == "real":
        background_tasks.add_task(
            pipeline.run, job.job_id, filename, input_path, reference_path, validation_reference_path)
    else:
        background_tasks.add_task(pipeline.run, job.job_id, filename, input_path)
    return job
