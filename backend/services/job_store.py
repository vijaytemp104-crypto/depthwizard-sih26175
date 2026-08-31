"""Temporary in-memory job persistence for the prototype API."""

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from backend.schemas.job import Job, JobStatus, PipelineStage, StageState, StageStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryJobStore:
    """Thread-safe, process-local job store that can later be replaced."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = RLock()

    def create_job(self) -> Job:
        now = utc_now()
        job = Job(
            job_id=str(uuid4()),
            created_at=now,
            updated_at=now,
            stages={stage: StageState() for stage in PipelineStage},
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job.model_copy(deep=True)

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job is not None else None

    def update_job_status(self, job_id: str, job_status: JobStatus) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.job_status = job_status
            job.updated_at = utc_now()
            return job.model_copy(deep=True)

    def update_stage_status(
        self,
        job_id: str,
        stage: PipelineStage,
        stage_status: StageStatus,
        *,
        reason: str | None = None,
        message: str | None = None,
    ) -> Job | None:
        new_state = StageState(status=stage_status, reason=reason, message=message)
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.stages[stage] = new_state
            job.updated_at = utc_now()
            return job.model_copy(deep=True)


job_store = InMemoryJobStore()
