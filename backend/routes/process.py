"""Mock upload and process endpoint."""

import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from backend.schemas.job import Job, JobStatus, StandardError
from backend.services.job_store import job_store
from backend.services.mock_pipeline import MockPipeline

router = APIRouter(tags=["process"])
mock_pipeline = MockPipeline(job_store)
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def safe_error(status_code: int, code: str, message: str, detail: dict | None = None) -> HTTPException:
    error = StandardError(code=code, stage=None, message=message, detail=detail, recoverable=True)
    return HTTPException(status_code=status_code, detail=error.model_dump())


@router.post("/process", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def process_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> Job:
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

    job = job_store.create_job()
    input_dir = mock_pipeline.output_root / job.job_id / "input"
    input_path = input_dir / filename
    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        with input_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)
    except OSError:
        job_store.update_job_status(job.job_id, JobStatus.FAILED)
        raise safe_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "UPLOAD_STORE_FAILED",
            "The uploaded file could not be stored for demo processing.",
        )
    finally:
        await file.close()

    background_tasks.add_task(mock_pipeline.run, job.job_id, filename, input_path)
    return job
