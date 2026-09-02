import json
from io import BytesIO

import numpy as np
import pytest
import rasterio
from affine import Affine
from fastapi.testclient import TestClient
from PIL import Image
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from backend.main import app
from backend.routes.process import depth_pipeline
from backend.services.ayush.calibration import apply_calibration, fit_calibration
from backend.services.ayush.export import write_dsm, write_terrain_json
from backend.services.relative_depth_adapter import RelativeDepthMetadata


class GridDepthAdapter:
    metadata = RelativeDepthMetadata(model_name="integration fake", checkpoint_id="test/grid", device="cpu")

    def predict_depth(self, image):
        with Image.open(image) as source:
            width, height = source.size
        depth = np.arange(width * height, dtype=np.float32).reshape(height, width)
        return depth, RelativeDepthMetadata(
            model_name="integration fake", checkpoint_id="test/grid", device="cpu",
            extra={"original_input_shape": (height, width, 3), "final_output_shape": (height, width)},
        )


def raster_bytes(array: np.ndarray, *, count: int, crs="EPSG:32643",
                 transform=from_origin(500000, 2200000, 10, 10), nodata=None,
                 vertical_units="metres", vertical_datum="NAVD88 / GEOID18",
                 vertical_crs="EPSG:5703") -> bytes:
    height, width = array.shape[-2:]
    with MemoryFile() as memory:
        with memory.open(driver="GTiff", width=width, height=height, count=count,
                         dtype=str(array.dtype), crs=crs, transform=transform, nodata=nodata) as dataset:
            dataset.write(array if count > 1 else array.reshape(1, height, width))
            if count == 1 and vertical_units:
                dataset.set_band_unit(1, vertical_units)
                dataset.update_tags(
                    VERTICAL_UNITS=vertical_units,
                    VERTICAL_DATUM=vertical_datum,
                    VERTICAL_CRS=vertical_crs,
                )
        return memory.read()


def test_known_linear_calibration_recovers_two_and_ten() -> None:
    depth = np.linspace(0, 12, 20, dtype=np.float32).reshape(4, 5)
    elevation = 2 * depth + 10
    fit = fit_calibration(depth, elevation)
    assert fit.slope == pytest.approx(2.0, rel=1e-6)
    assert fit.intercept == pytest.approx(10.0, rel=1e-6)
    assert np.allclose(apply_calibration(depth, fit), elevation)


def test_geotiff_and_terrain_exports_preserve_grid(tmp_path) -> None:
    elevation = np.array([[10, 11, 12], [13, np.nan, 15]], dtype=np.float32)
    transform = from_origin(500000, 2200000, 5, 5)
    dsm_path = write_dsm(
        tmp_path / "calibrated_dsm.tif", elevation,
        rasterio.crs.CRS.from_epsg(32643), transform,
        vertical_units="metres", vertical_datum="NAVD88 / GEOID18",
        vertical_crs="EPSG:5703",
    )
    terrain_path = write_terrain_json(
        tmp_path / "terrain.json", elevation,
        rasterio.crs.CRS.from_epsg(32643), transform,
        vertical_units="metres", vertical_datum="NAVD88 / GEOID18",
        vertical_crs="EPSG:5703",
    )
    with rasterio.open(dsm_path) as dsm:
        assert dsm.shape == elevation.shape
        assert dsm.crs.to_epsg() == 32643
        assert dsm.transform == transform
        assert dsm.dtypes[0] == "float32"
        assert dsm.nodata == -9999.0
        assert dsm.units[0] == "metres"
        assert dsm.tags()["VERTICAL_DATUM"] == "NAVD88 / GEOID18"
        assert dsm.tags()["VERTICAL_CRS"] == "EPSG:5703"
    terrain = json.loads(terrain_path.read_text(encoding="utf-8"))
    assert terrain["elevation"][0] == [10.0, 11.0, 12.0]
    assert terrain["elevation"][1][1] is None
    assert terrain["transform_order"] == "GDAL(c, a, b, f, d, e)"
    assert terrain["vertical_units"] == "metres"
    assert terrain["vertical_datum"] == "NAVD88 / GEOID18"


def test_geotiff_reference_produces_metric_result_but_not_validation(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: GridDepthAdapter())
    height, width = 4, 5
    rgb = np.stack([np.full((height, width), value, dtype=np.uint8) for value in (40, 80, 120)])
    depth = np.arange(width * height, dtype=np.float32).reshape(height, width)
    dem = 2 * depth + 10
    client = TestClient(app)
    response = client.post("/process", files={
        "file": ("source.tif", raster_bytes(rgb, count=3), "image/tiff"),
        "reference_dem": ("reference.tif", raster_bytes(dem, count=1), "image/tiff"),
    })
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    result = client.get(f"/jobs/{job_id}/result").json()
    assert result["depth"]["status"] == "succeeded"
    assert result["calibration"]["calibrated"] is True
    assert result["calibration"]["scale_a"] == pytest.approx(2.0, rel=1e-6)
    assert result["calibration"]["offset_b"] == pytest.approx(10.0, rel=1e-6)
    assert result["terrain"]["height_units"] == "metres"
    assert result["terrain"]["heights"] == dem.tolist()
    assert result["validation"]["status"] == "skipped"
    assert result["validation"]["rmse"] is None
    assert result["calibration"]["fit_rmse_metres"] is not None
    assert result["calibration"]["fit_scope"] == "calibration_fit"
    assert result["calibration"]["fit_is_independent_validation"] is False
    assert result["calibration"]["reference_units_verified"] is True
    assert result["calibration"]["reference_vertical_units"] == "metres"
    assert result["calibration"]["reference_vertical_datum"] == "NAVD88 / GEOID18"
    assert result["calibration"]["transform_order"] == "Affine(a, b, c, d, e, f)"
    assert result["evidence"]["summary"]["calibration"]["fit_scope"] == "calibration_fit"
    assert result["evidence"]["summary"]["vertical_datum"] == "NAVD88 / GEOID18"
    for name in ("calibrated_dsm.tif", "terrain.json", "calibration.json"):
        assert client.get(f"/jobs/{job_id}/artifacts/{name}").status_code == 200


def test_calibration_failure_preserves_real_relative_depth(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: GridDepthAdapter())
    image = BytesIO()
    Image.new("RGB", (5, 4), (20, 30, 40)).save(image, format="PNG")
    dem = np.arange(20, dtype=np.float32).reshape(4, 5)
    client = TestClient(app)
    response = client.post("/process", files={
        "file": ("source.png", image.getvalue(), "image/png"),
        "reference_dem": ("reference.tif", raster_bytes(dem, count=1), "image/tiff"),
    })
    job_id = response.json()["job_id"]
    result = client.get(f"/jobs/{job_id}/result").json()
    assert result["job_status"] == "succeeded"
    assert result["depth"]["status"] == "succeeded"
    assert result["calibration"]["status"] == "failed"
    assert result["calibration"]["calibrated"] is False
    assert result["calibration"]["units"] == "relative"
    assert result["terrain"]["mock"] is True
    assert client.get(f"/jobs/{job_id}/artifacts/depth.npy").status_code == 200
    assert client.get(f"/jobs/{job_id}/artifacts/calibrated_dsm.tif").status_code == 404


@pytest.mark.parametrize("vertical_units", [None, "US survey foot"])
def test_missing_or_non_metric_reference_units_fall_back_to_relative(
    monkeypatch, vertical_units
) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: GridDepthAdapter())
    height, width = 4, 5
    rgb = np.stack([np.full((height, width), value, dtype=np.uint8) for value in (40, 80, 120)])
    dem = 2 * np.arange(width * height, dtype=np.float32).reshape(height, width) + 10
    client = TestClient(app)
    response = client.post("/process", files={
        "file": ("source.tif", raster_bytes(rgb, count=3), "image/tiff"),
        "reference_dem": (
            "reference.tif",
            raster_bytes(dem, count=1, vertical_units=vertical_units),
            "image/tiff",
        ),
    })
    result = client.get(f"/jobs/{response.json()['job_id']}/result").json()

    assert result["depth"]["status"] == "succeeded"
    assert result["calibration"]["status"] == "failed"
    assert result["calibration"]["calibrated"] is False
    assert result["calibration"]["units"] == "relative"
    assert result["calibration"]["reference_units_verified"] is False
    assert result["terrain"]["mock"] is True


def test_projected_horizontal_units_are_reported_without_assuming_metres(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: GridDepthAdapter())
    height, width = 4, 5
    rgb = np.stack([np.full((height, width), value, dtype=np.uint8) for value in (40, 80, 120)])
    depth = np.arange(width * height, dtype=np.float32).reshape(height, width)
    dem = 2 * depth + 10
    response = TestClient(app).post("/process", files={
        "file": (
            "source-feet.tif",
            raster_bytes(rgb, count=3, crs="EPSG:2230"),
            "image/tiff",
        ),
        "reference_dem": (
            "reference-feet.tif",
            raster_bytes(dem, count=1, crs="EPSG:2230"),
            "image/tiff",
        ),
    })
    result = TestClient(app).get(f"/jobs/{response.json()['job_id']}/result").json()

    assert "foot" in result["input"]["pixel_size"]["units"].lower()
    assert "foot" in result["calibration"]["horizontal_units"].lower()


def test_full_synthetic_geospatial_pipeline_with_independent_validation(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: GridDepthAdapter())
    height, width = 4, 5
    rgb = np.stack([np.full((height, width), value, dtype=np.uint8) for value in (40, 80, 120)])
    depth = np.arange(width * height, dtype=np.float32).reshape(height, width)
    calibration_dem = 2 * depth + 10
    validation_dem = calibration_dem + np.array([[0, 1, 0, -1, 0]] * height, dtype=np.float32)
    client = TestClient(app)
    response = client.post("/process", files={
        "file": ("source.tif", raster_bytes(rgb, count=3), "image/tiff"),
        "reference_dem": ("calibration.tif", raster_bytes(calibration_dem, count=1), "image/tiff"),
        "validation_reference": ("withheld.tif", raster_bytes(validation_dem, count=1), "image/tiff"),
    })
    job_id = response.json()["job_id"]
    result = client.get(f"/jobs/{job_id}/result").json()
    assert result["job_status"] == "succeeded"
    assert result["calibration"]["status"] == "succeeded"
    assert result["validation"]["status"] == "succeeded"
    assert result["validation"]["rmse"] == pytest.approx(np.sqrt(2 / 5))
    assert result["validation"]["mae"] == pytest.approx(2 / 5)
    for name in ("metrics.json", "error_map.tif", "evidence_passport.json"):
        assert client.get(f"/jobs/{job_id}/artifacts/{name}").status_code == 200


def test_same_calibration_and_validation_content_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: GridDepthAdapter())
    height, width = 4, 5
    rgb = np.stack([np.full((height, width), value, dtype=np.uint8) for value in (40, 80, 120)])
    reference = raster_bytes(2 * np.arange(width * height, dtype=np.float32).reshape(height, width) + 10, count=1)
    client = TestClient(app)
    response = client.post("/process", files={
        "file": ("source.tif", raster_bytes(rgb, count=3), "image/tiff"),
        "reference_dem": ("calibration.tif", reference, "image/tiff"),
        "validation_reference": ("same-copy.tif", reference, "image/tiff"),
    })
    result = client.get(f"/jobs/{response.json()['job_id']}/result").json()
    assert result["calibration"]["status"] == "succeeded"
    assert result["validation"]["status"] == "skipped"
    assert "same artifact" in result["validation"]["reason"]


def test_validation_failure_preserves_calibrated_dsm(monkeypatch) -> None:
    monkeypatch.setattr(depth_pipeline, "adapter_factory", lambda: GridDepthAdapter())
    height, width = 4, 5
    rgb = np.stack([np.full((height, width), value, dtype=np.uint8) for value in (40, 80, 120)])
    depth = np.arange(width * height, dtype=np.float32).reshape(height, width)
    calibration = raster_bytes(2 * depth + 10, count=1)
    far = raster_bytes(2 * depth + 11, count=1, transform=from_origin(900000, 900000, 10, 10))
    client = TestClient(app)
    response = client.post("/process", files={
        "file": ("source.tif", raster_bytes(rgb, count=3), "image/tiff"),
        "reference_dem": ("calibration.tif", calibration, "image/tiff"),
        "validation_reference": ("far.tif", far, "image/tiff"),
    })
    job_id = response.json()["job_id"]
    result = client.get(f"/jobs/{job_id}/result").json()
    assert result["job_status"] == "succeeded"
    assert result["calibration"]["status"] == "succeeded"
    assert result["validation"]["status"] == "failed"
    assert client.get(f"/jobs/{job_id}/artifacts/calibrated_dsm.tif").status_code == 200
