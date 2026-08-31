"""Command-line orchestration for Ayush's complete prototype pipeline."""

import argparse
import json
from pathlib import Path

from .calibration import apply_calibration, fit_calibration
from .depth import load_depth
from .export import write_dsm, write_terrain_json
from .geospatial import align_dem, depth_grid, load_dem


def run_pipeline(depth_path: str | Path, dem_path: str | Path, output_dir: str | Path) -> dict:
    depth_path, dem_path, output_dir = Path(depth_path), Path(dem_path), Path(output_dir)
    depth = load_depth(depth_path)
    _, dem_meta = load_dem(dem_path)
    crs, transform, grid_source = depth_grid(depth_path, depth.shape, dem_meta)
    aligned_dem, reference_meta, was_aligned = align_dem(dem_path, depth.shape, crs, transform)
    calibration = fit_calibration(depth, aligned_dem)
    elevation = apply_calibration(depth, calibration)

    output_dir.mkdir(parents=True, exist_ok=True)
    dsm_path = write_dsm(output_dir / "calibrated_dsm.tif", elevation, crs, transform)
    terrain_path = write_terrain_json(output_dir / "terrain.json", elevation, crs, transform)
    calibration_path = output_dir / "calibration.json"
    payload = calibration.to_dict()
    payload["model"] = "elevation = a * depth + b"
    payload["reference"] = {
        "path": str(dem_path),
        "metadata": reference_meta.to_dict(),
        "resampled_or_reprojected": was_aligned,
        "target_grid_source": grid_source,
    }
    calibration_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return {"calibration": calibration_path, "dsm": dsm_path, "terrain": terrain_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate relative depth and generate a metric DSM")
    parser.add_argument("--depth", required=True, help="Manish-compatible 2-D .npy relative depth")
    parser.add_argument("--dem", required=True, help="Reference DEM GeoTIFF")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()
    outputs = run_pipeline(args.depth, args.dem, args.output)
    print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
