"""DSM GeoTIFF and Three.js-friendly terrain exports."""

import json
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.transform import array_bounds


DEFAULT_NODATA = -9999.0


def write_dsm(path: str | Path, elevation: np.ndarray, crs: CRS, transform: Affine) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = np.where(np.isfinite(elevation), elevation, DEFAULT_NODATA).astype(np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=elevation.shape[1],
        height=elevation.shape[0],
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=DEFAULT_NODATA,
        compress="deflate",
    ) as dst:
        dst.write(encoded, 1)
        dst.set_band_description(1, "calibrated_elevation_metres")
    # Fail immediately if a malformed artifact was written.
    with rasterio.open(path) as check:
        if check.shape != elevation.shape or check.crs != crs:
            raise IOError(f"DSM verification failed: {path}")
    return path


def write_terrain_json(path: str | Path, elevation: np.ndarray, crs: CRS, transform: Affine) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = elevation.shape
    bounds = array_bounds(height, width, transform)
    grid = [[None if not np.isfinite(v) else float(v) for v in row] for row in elevation]
    payload = {
        "schema_version": "1.0",
        "width": width,
        "height": height,
        "crs": crs.to_string(),
        "transform": list(transform.to_gdal()),
        "bounds": {"left": bounds[0], "bottom": bounds[1], "right": bounds[2], "top": bounds[3]},
        "nodata": None,
        "elevation": grid,
    }
    path.write_text(json.dumps(payload, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    return path
