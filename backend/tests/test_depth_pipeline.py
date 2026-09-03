from io import BytesIO

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from backend.main import app
from backend.routes.process import depth_pipeline
from backend.services import depth_pipeline as depth_pipeline_module
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


def rgb_geotiff_bytes() -> tuple[bytes, np.ndarray]:
    rgb = np.array([
        [[10, 20, 30], [40, 50, 60]],
        [[70, 80, 90], [100, 110, 120]],
        [[130, 140, 150], [160, 170, 180]],
    ], dtype=np.uint8)
    with MemoryFile() as memory:
        with memory.open(driver="GTiff", width=3, height=2, count=3, dtype="uint8",
                         crs="EPSG:32613", transform=from_origin(500000, 4400000, 1, 1)) as dataset:
            dataset.write(rgb)
        return memory.read(), rgb


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
    assert result["input"]["texture_preview"]["status"] == "not_required"
    assert result["input"]["texture_preview"]["artifact"] is None
    assert TestClient(app).get(f"/jobs/{job_id}/artifacts/input_preview.png").status_code == 404
    for name in ("depth.npy", "depth.png", "model_metadata.json"):
        artifact = TestClient(app).get(f"/jobs/{job_id}/artifacts/{name}")
        assert artifact.status_code == 200


def test_geotiff_writes_and_exposes_browser_rgb_preview(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: FakeDepthAdapter())
    source, expected = rgb_geotiff_bytes()
    client = TestClient(app)
    response = client.post("/process", files={"file": ("overhead.tif", source, "image/tiff")})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    result = client.get(f"/jobs/{job_id}/result").json()

    preview_meta = result["input"]["texture_preview"]
    assert preview_meta["status"] == "succeeded"
    assert preview_meta["artifact"] == "input_preview.png"
    assert preview_meta["role"] == "display_texture_only"
    assert preview_meta["scientific_raster"] is False
    assert preview_meta["display_conversion"]["method"] == "none"
    assert result["evidence"]["summary"]["input"]["texture_preview"] == preview_meta
    assert f"outputs/{job_id}/input_preview.png" in result["artifacts"]

    artifact = client.get(f"/jobs/{job_id}/artifacts/input_preview.png")
    assert artifact.status_code == 200
    assert artifact.headers["content-type"] == "image/png"
    with Image.open(BytesIO(artifact.content)) as preview:
        assert preview.mode == "RGB"
        assert preview.size == (3, 2)
        assert np.array_equal(np.asarray(preview), np.moveaxis(expected, 0, -1))

    depth_artifact = client.get(f"/jobs/{job_id}/artifacts/depth.npy")
    depth = np.load(BytesIO(depth_artifact.content))
    assert np.array_equal(depth, np.arange(6, dtype=np.float32).reshape(2, 3))


def test_geotiff_preview_failure_keeps_pipeline_and_neutral_fallback_safe(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: FakeDepthAdapter())
    monkeypatch.setattr(depth_pipeline_module, "_write_rgb_texture_preview", lambda *_: {
        "status": "unavailable", "artifact": None,
        "role": "display_texture_only", "scientific_raster": False,
        "reason": "A browser-compatible RGB display preview could not be generated.",
    })
    source, _ = rgb_geotiff_bytes()
    client = TestClient(app)
    response = client.post("/process", files={"file": ("overhead.tif", source, "image/tiff")})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    result = client.get(f"/jobs/{job_id}/result").json()

    assert result["job_status"] == "succeeded"
    assert result["depth"]["status"] == "succeeded"
    assert result["input"]["texture_preview"]["status"] == "unavailable"
    assert result["input"]["texture_preview"]["artifact"] is None
    assert client.get(f"/jobs/{job_id}/artifacts/input_preview.png").status_code == 404


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
