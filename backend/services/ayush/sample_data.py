"""Generate deterministic, realistic synthetic fixtures for the prototype."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


def generate_sample_data(root: str | Path = "sample_data", seed: int = 26175) -> tuple[Path, Path]:
    root = Path(root)
    input_dir, reference_dir = root / "input", root / "reference"
    input_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    # Depth grid is intentionally finer than the reference to exercise resampling.
    rows, cols = 96, 128
    yy, xx = np.mgrid[0:1:complex(rows), 0:1:complex(cols)]
    depth = 0.25 + 0.45 * xx + 0.12 * yy + 0.18 * np.exp(-((xx - 0.65) ** 2 + (yy - 0.4) ** 2) / 0.025)
    depth = depth.astype(np.float32)
    depth[4, 8] = np.nan
    depth[12, 20] = np.inf
    depth_path = input_dir / "sample_depth.npy"
    np.save(depth_path, depth)

    dem_rows, dem_cols = 48, 64
    dy, dx = np.mgrid[0:1:complex(dem_rows), 0:1:complex(dem_cols)]
    relative = 0.25 + 0.45 * dx + 0.12 * dy + 0.18 * np.exp(-((dx - 0.65) ** 2 + (dy - 0.4) ** 2) / 0.025)
    rng = np.random.default_rng(seed)
    dem = (115.0 * relative + 430.0 + rng.normal(0, 0.35, relative.shape)).astype(np.float32)
    dem[0, 0] = -9999.0
    dem_path = reference_dir / "sample_dem.tif"
    with rasterio.open(
        dem_path, "w", driver="GTiff", width=dem_cols, height=dem_rows, count=1,
        dtype="float32", crs="EPSG:32643", transform=from_origin(500000, 2200000, 20, 20),
        nodata=-9999.0, compress="deflate",
    ) as dst:
        dst.write(dem, 1)
        dst.set_band_description(1, "synthetic_reference_elevation_metres")
    return depth_path, dem_path


if __name__ == "__main__":
    depth, dem = generate_sample_data()
    print(f"Created {depth}\nCreated {dem}")
