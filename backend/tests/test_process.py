from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def upload_demo(filename: str = "site.png") -> dict:
    response = client.post("/process", files={"file": (filename, b"demo-image-bytes", "image/png")})
    assert response.status_code == 202
    return response.json()


def test_supported_upload_creates_succeeded_mock_job() -> None:
    created = upload_demo()
    job_response = client.get(f"/jobs/{created['job_id']}")

    assert job_response.status_code == 200
    job = job_response.json()
    assert job["job_status"] == "succeeded"
    assert job["stages"]["ingest"]["status"] == "succeeded"
    assert job["stages"]["depth"]["status"] == "succeeded"
    assert job["stages"]["calibration"]["status"] == "skipped"
    assert job["stages"]["validation"]["status"] == "skipped"


def test_unsupported_extension_returns_safe_error() -> None:
    response = client.post("/process", files={"file": ("notes.txt", b"not-an-image", "text/plain")})

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert "traceback" not in response.text.lower()


def test_result_is_explicitly_mock_and_has_no_fake_metrics() -> None:
    created = upload_demo("source.tif")
    response = client.get(f"/jobs/{created['job_id']}/result")

    assert response.status_code == 200
    result = response.json()
    assert result["mock"] is True
    assert result["pipeline_mode"] == "demo_synthetic_placeholder"
    assert result["calibration"]["status"] == "skipped"
    assert result["calibration"]["calibrated"] is False
    assert result["validation"]["status"] == "skipped"
    assert result["validation"]["rmse"] is None
    assert result["validation"]["mae"] is None
    assert result["validation"]["correlation"] is None


def test_job_owned_artifact_download_and_traversal_rejection() -> None:
    created = upload_demo()
    job_id = created["job_id"]

    download = client.get(f"/jobs/{job_id}/artifacts/mock_evidence.json")
    assert download.status_code == 200
    assert download.json()["mock"] is True

    traversal = client.get(f"/jobs/{job_id}/artifacts/..%2Fmock_evidence.json")
    assert traversal.status_code == 404


def test_unknown_job_result_returns_404() -> None:
    response = client.get("/jobs/not-a-job/result")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "JOB_NOT_FOUND"
