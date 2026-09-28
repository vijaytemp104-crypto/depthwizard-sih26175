#!/usr/bin/env python3
"""Generate tiny deterministic GeoTIFF triplets for GeoGuard raster QA tests."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import transform_bounds


PROJECTED_CRS = "EPSG:32617"
GEOGRAPHIC_CRS = "EPSG:4326"
LEFT = 500_000.0
TOP = 4_000_000.0
EXTENT_M = 64.0
NODATA = -9999.0


def _rgb() -> np.ndarray:
    rows, cols = np.indices((64, 64), dtype=np.uint16)
    red = 40 + (3 * cols) % 180
    green = 35 + (2 * rows) % 180
    blue = 55 + ((rows + cols) % 150)
    return np.stack((red, green, blue)).astype(np.uint8)


def _elevation(height: int, width: int, bias_m: float = 0.0) -> np.ndarray:
    row, col = np.indices((height, width), dtype=np.float64)
    x_m = (col + 0.5) * EXTENT_M / width
    y_m = (row + 0.5) * EXTENT_M / height
    plane = 102.0 + 0.025 * x_m + 0.015 * y_m
    hill = 6.0 * np.exp(-((x_m - 38.0) ** 2 + (y_m - 27.0) ** 2) / (2 * 9.0**2))
    return (plane + hill + bias_m).astype(np.float32)


def _write_rgb(path: Path) -> None:
    data = _rgb()
    transform = from_origin(LEFT, TOP, 1.0, 1.0)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=64,
        height=64,
        count=3,
        dtype="uint8",
        crs=PROJECTED_CRS,
        transform=transform,
        compress="deflate",
    ) as dataset:
        dataset.write(data)
        dataset.update_tags(SYNTHETIC="true", PURPOSE="GeoGuard QA fixture")


def _write_elevation(
    path: Path,
    *,
    size: int,
    pixel_size_m: float,
    bias_m: float,
    include_units: bool = True,
    include_vertical_datum: bool = True,
    crs: str = PROJECTED_CRS,
    transform=None,
) -> None:
    data = _elevation(size, size, bias_m=bias_m)
    if transform is None:
        transform = from_origin(LEFT, TOP, pixel_size_m, pixel_size_m)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=size,
        height=size,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=NODATA,
        compress="deflate",
    ) as dataset:
        dataset.write(data, 1)
        tags = {
            "ELEVATION_TYPE": "DSM",
            "SYNTHETIC": "true",
            "PURPOSE": "GeoGuard QA fixture",
        }
        if include_units:
            tags["UNITTYPE"] = "metre"
        if include_vertical_datum:
            tags["VERTICAL_DATUM"] = "NAVD88"
        dataset.update_tags(**tags)


def _make_case(
    root: Path,
    name: str,
    *,
    reference_units: bool = True,
    reference_datum: bool = True,
    nonoverlap: bool = False,
    geographic_truth: bool = False,
) -> None:
    case_dir = root / name
    case_dir.mkdir(parents=True, exist_ok=True)
    _write_rgb(case_dir / "rgb.tif")
    _write_elevation(
        case_dir / "reference.tif",
        size=16,
        pixel_size_m=4.0,
        bias_m=1.25,
        include_units=reference_units,
        include_vertical_datum=reference_datum,
    )

    truth_transform = from_origin(LEFT, TOP, 0.5, 0.5)
    truth_crs = PROJECTED_CRS
    if nonoverlap:
        truth_transform = from_origin(LEFT + 10_000.0, TOP + 10_000.0, 0.5, 0.5)
    elif geographic_truth:
        projected_bounds = (LEFT, TOP - EXTENT_M, LEFT + EXTENT_M, TOP)
        geographic_bounds = transform_bounds(
            PROJECTED_CRS, GEOGRAPHIC_CRS, *projected_bounds, densify_pts=21
        )
        truth_transform = from_bounds(*geographic_bounds, width=128, height=128)
        truth_crs = GEOGRAPHIC_CRS

    _write_elevation(
        case_dir / "truth.tif",
        size=128,
        pixel_size_m=0.5,
        bias_m=0.0,
        crs=truth_crs,
        transform=truth_transform,
    )


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    _make_case(output, "valid")
    _make_case(output, "missing_vertical_datum", reference_datum=False)
    _make_case(output, "missing_units", reference_units=False)
    _make_case(output, "nonoverlap", nonoverlap=True)
    _make_case(output, "crs_transformable", geographic_truth=True)


def _parse_args() -> argparse.Namespace:
    default_output = Path(__file__).resolve().parent / "fixtures"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    generate(args.output)
    print(f"Generated five deterministic synthetic QA cases in {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
