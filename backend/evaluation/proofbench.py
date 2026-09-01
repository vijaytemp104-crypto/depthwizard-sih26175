"""Lightweight factual aggregation for completed validation scene results."""

from __future__ import annotations

import json
from pathlib import Path

FIELDS = (
    "scene_id", "scene_type", "synthetic_or_real", "depth_status",
    "calibration_status", "validation_status", "rmse", "mae", "correlation",
    "valid_pixel_count", "notes",
)


def build_summary(scene_results: list[dict]) -> dict:
    rows = [{field: result.get(field) for field in FIELDS} for result in scene_results]
    return {
        "summary_version": "1.0",
        "purpose": "Software integration evidence; synthetic rows are not real-world accuracy.",
        "scene_count": len(rows),
        "real_scene_count": sum(row["synthetic_or_real"] == "real" for row in rows),
        "synthetic_scene_count": sum(row["synthetic_or_real"] == "synthetic" for row in rows),
        "scenes": rows,
    }


def write_summary(scene_results: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_summary(scene_results), indent=2), encoding="utf-8")
    return output_path
