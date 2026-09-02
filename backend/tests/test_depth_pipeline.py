from io import BytesIO

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app
from backend.routes.process import depth_pipeline
from backend.services.relative_depth_adapter import RelativeDepthMetadata


class FakeDepthAdapter:
    metadata = RelativeDepthMetadata(model_name="test adapter", checkpoint_id="test/checkpoint", device="cpu")

    def predict_depth(self, image):
        with Image.open(image) as source:
            width, height = source.size
        depth = np.arange(width * height, dtype=np.float32).reshape(height, width)
        metadata = RelativeDepthMetadata(
            model_name="test adapter",
            checkpoint_id="test/checkpoint",
            device="cpu",
            extra={"original_input_shape": (height, width, 3), "final_output_shape": (height, width)},
        )
        return depth, metadata


def test_real_depth_pipeline_writes_contract_artifacts(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: FakeDepthAdapter())
    source = BytesIO()
    Image.new("RGB", (7, 5), (40, 80, 120)).save(source, format="PNG")
    response = TestClient(app).post(
        "/process",
        files={"file": ("overhead.png", source.getvalue(), "image/png")},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    result = TestClient(app).get(f"/jobs/{job_id}/result").json()

    assert result["mock"] is False
    assert result["pipeline_mode"] == "real_depth_synthetic_terrain"
    assert result["depth"]["mock"] is False
    assert (result["depth"]["height"], result["depth"]["width"]) == (5, 7)
    assert result["depth"]["units"] == "relative"
    assert result["input"]["transform_order"] is None
    assert result["calibration"]["status"] == "skipped"
    assert result["calibration"]["reference_units_verified"] is False
    assert result["calibration"]["fit_is_independent_validation"] is False
    assert result["validation"]["status"] == "skipped"
    assert result["terrain"]["mock"] is True
    for name in ("depth.npy", "depth.png", "model_metadata.json"):
        artifact = TestClient(app).get(f"/jobs/{job_id}/artifacts/{name}")
        assert artifact.status_code == 200


def test_real_depth_failure_does_not_report_fake_success(monkeypatch) -> None:
    def fail_adapter():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(depth_pipeline, "adapter_factory", fail_adapter)
    source = BytesIO()
    Image.new("RGB", (3, 2)).save(source, format="PNG")
    client = TestClient(app)
    response = client.post("/process", files={"file": ("overhead.png", source.getvalue(), "image/png")})
    job = client.get(f"/jobs/{response.json()['job_id']}").json()

    assert job["job_status"] == "failed"
    assert job["stages"]["depth"]["status"] == "failed"
    assert job["errors"][0]["code"] == "RELATIVE_DEPTH_FAILED"
