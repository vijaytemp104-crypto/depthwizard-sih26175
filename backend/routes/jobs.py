"""Minimal job lifecycle endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from backend.schemas.job import Job, StandardError
from backend.services.job_store import job_store

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=Job, status_code=status.HTTP_201_CREATED)
def create_job() -> Job:
    """Create an empty pending pipeline job."""
    return job_store.create_job()


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    """Return a job or a safe contract-compatible not-found error."""
    job = job_store.get_job(job_id)
    if job is None:
        error = StandardError(
            code="JOB_NOT_FOUND",
            stage=None,
            message="The requested job was not found.",
            detail={"job_id": job_id},
            recoverable=False,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.model_dump())
    return job


@router.get("/{job_id}/result")
def get_job_result(job_id: str) -> dict:
    job = job_store.get_job(job_id)
    if job is None:
        raise _job_not_found(job_id)
    result = job_store.get_result(job_id)
    if result is None:
        error = StandardError(
            code="RESULT_NOT_READY",
            stage=None,
            message="The demo result is not available yet.",
            detail={"job_id": job_id, "job_status": job.job_status.value},
            recoverable=True,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.model_dump())
    return result


@router.get("/{job_id}/artifacts/{artifact_name}")
def download_artifact(job_id: str, artifact_name: str) -> FileResponse:
    if job_store.get_job(job_id) is None:
        raise _job_not_found(job_id)
    if Path(artifact_name).name != artifact_name or "/" in artifact_name or "\\" in artifact_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    artifact_path = job_store.get_artifact(job_id, artifact_name)
    if artifact_path is None or not Path(artifact_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    media_types = {
        ".json": "application/json",
        ".png": "image/png",
        ".npy": "application/octet-stream",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }
    return FileResponse(
        artifact_path,
        filename=artifact_name,
        media_type=media_types.get(Path(artifact_name).suffix.lower(), "application/octet-stream"),
    )


def _job_not_found(job_id: str) -> HTTPException:
    error = StandardError(
        code="JOB_NOT_FOUND",
        stage=None,
        message="The requested job was not found.",
        detail={"job_id": job_id},
        recoverable=False,
    )
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.model_dump())
