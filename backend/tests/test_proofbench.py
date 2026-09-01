import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from backend.evaluation.proofbench import build_summary, write_summary
from backend.services.validation import validate_rasters

SCENES = {
    "urban": np.arange(48, dtype=np.float32).reshape(6, 8),
    "sparse": np.where(np.indices((6, 8)).sum(axis=0) % 4 == 0, 12.0, 2.0).astype(np.float32),
    "hilly": (20 + 5 * np.sin(np.linspace(0, np.pi * 2, 48))).reshape(6, 8).astype(np.float32),
    "forest": (10 + (np.indices((6, 8))[0] * 3 + np.indices((6, 8))[1] * 5) % 7).astype(np.float32),
}


def write_raster(path, values):
    with rasterio.open(path, "w", driver="GTiff", width=8, height=6, count=1,
                       dtype="float32", crs="EPSG:32643",
                       transform=from_origin(500000, 2200000, 2, 2), nodata=-9999.0) as target:
        target.write(values, 1)


@pytest.mark.parametrize("scene_type", SCENES)
def test_synthetic_scene_validation_stability(scene_type, tmp_path):
    prediction = SCENES[scene_type]
    reference = prediction + 0.5
    prediction_path = tmp_path / f"{scene_type}-prediction.tif"
    reference_path = tmp_path / f"{scene_type}-reference.tif"
    write_raster(prediction_path, prediction)
    write_raster(reference_path, reference)
    scene_output = tmp_path / scene_type
    scene_output.mkdir()
    result = validate_rasters(prediction_path, reference_path, scene_output,
                              reference_source=f"SYNTHETIC {scene_type} TEST")
    assert result["status"] == "succeeded"
    assert result["rmse"] == pytest.approx(0.5)
    assert result["mae"] == pytest.approx(0.5)
    assert result["valid_pixel_count"] == 48


def test_proofbench_summary_is_explicitly_synthetic_and_machine_readable(tmp_path):
    rows = [{
        "scene_id": f"synthetic-{scene_type}-01", "scene_type": scene_type,
        "synthetic_or_real": "synthetic", "depth_status": "succeeded",
        "calibration_status": "succeeded", "validation_status": "succeeded",
        "rmse": 0.5, "mae": 0.5, "correlation": 1.0,
        "valid_pixel_count": 48, "notes": "SYNTHETIC TEST; orchestration only.",
    } for scene_type in SCENES]
    summary = build_summary(rows)
    assert summary["real_scene_count"] == 0
    assert summary["synthetic_scene_count"] == 4
    output = write_summary(rows, tmp_path / "proofbench_summary.json")
    assert json.loads(output.read_text())["scene_count"] == 4
