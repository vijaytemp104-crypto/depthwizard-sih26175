"""Minimal job lifecycle endpoints."""

from fastapi import APIRouter, HTTPException, status

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
