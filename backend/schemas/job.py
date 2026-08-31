"""Canonical job and stage state schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


class PipelineStage(str, Enum):
    INGEST = "ingest"
    DEPTH = "depth"
    CALIBRATION = "calibration"
    VALIDATION = "validation"
    TERRAIN = "terrain"
    EVIDENCE = "evidence"


class StageState(BaseModel):
    status: StageStatus = StageStatus.PENDING
    reason: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def require_skipped_reason(self) -> "StageState":
        if self.status is StageStatus.SKIPPED and not self.reason:
            raise ValueError("A skipped stage requires a reason.")
        return self


class StandardError(BaseModel):
    code: str
    stage: PipelineStage | None = None
    message: str
    detail: Any | None = None
    recoverable: bool


class Job(BaseModel):
    job_id: str
    job_status: JobStatus = JobStatus.PENDING
    created_at: datetime
    updated_at: datetime
    stages: dict[PipelineStage, StageState]
    errors: list[StandardError] = Field(default_factory=list)
