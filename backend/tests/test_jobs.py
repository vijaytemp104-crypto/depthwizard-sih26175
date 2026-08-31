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
