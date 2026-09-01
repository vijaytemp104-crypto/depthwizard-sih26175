from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

CANONICAL_STAGES = {"ingest", "depth", "calibration", "validation", "terrain", "evidence"}


def test_create_and_get_job() -> None:
    create_response = client.post("/jobs")

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["job_status"] == "pending"
    assert set(created["stages"]) == CANONICAL_STAGES
    assert all(stage["status"] == "pending" for stage in created["stages"].values())
    assert created["errors"] == []
    assert created["created_at"].endswith("Z")
    assert created["updated_at"].endswith("Z")
    get_response = client.get(f"/jobs/{created['job_id']}")
    assert get_response.status_code == 200
    assert get_response.json() == created


def test_stage_lifecycle_timestamps_follow_status_transitions() -> None:
    created = client.post("/jobs").json()
    from backend.schemas.job import PipelineStage, StageStatus
    from backend.services.job_store import job_store

    running = job_store.update_stage_status(
        created["job_id"], PipelineStage.INGEST, StageStatus.RUNNING)
    assert running.stages[PipelineStage.INGEST].started_at is not None
    assert running.stages[PipelineStage.INGEST].completed_at is None
    completed = job_store.update_stage_status(
        created["job_id"], PipelineStage.INGEST, StageStatus.SUCCEEDED)
    assert completed.stages[PipelineStage.INGEST].started_at is not None
    assert completed.stages[PipelineStage.INGEST].completed_at is not None


def test_unknown_job_returns_contract_compatible_404() -> None:
    response = client.get("/jobs/unknown-job-id")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "JOB_NOT_FOUND",
        "stage": None,
        "message": "The requested job was not found.",
        "detail": {"job_id": "unknown-job-id"},
        "recoverable": False,
    }
