#!/usr/bin/env python3
"""Read-only metadata and overlap QA for a GeoGuard raster triplet."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


UNIT_KEYS = {
    "unit",
    "units",
    "unittype",
    "z_unit",
    "z_units",
    "vertical_unit",
    "vertical_units",
}
DATUM_KEYS = {
    "vertical_datum",
    "verticaldatum",
    "vert_datum",
    "vdatum",
    "geoid",
}
ELEVATION_TYPE_KEYS = {
    "elevation_type",
    "elevationtype",
    "surface_type",
    "target_type",
}
ALLOWED_ELEVATION_TYPES = {"DSM", "DTM", "DEM", "AGL"}


@dataclass
class RasterReport:
    label: str
    path: Path
    shape: tuple[int, int]
    bands: int
    dtypes: tuple[str, ...]
    crs: Any
    bounds: Any
    pixel_size: tuple[float, float]
    nodata: tuple[Any, ...]
    nodata_percent: float
    finite_min: float | None
    finite_max: float | None
    units: str | None
    vertical_datum: str | None
    elevation_type: str | None
    width: int
    height: int


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rgb", required=True, type=Path, help="RGB raster path")
    parser.add_argument("--reference", required=True, type=Path, help="Coarse reference raster path")
    parser.add_argument("--truth", required=True, type=Path, help="Independent truth raster path")
    return parser.parse_args(argv)


def _normalise_tags(dataset: Any) -> dict[str, str]:
    tags: dict[str, str] = {}
    for source in (dataset.tags(), dataset.tags(1) if dataset.count else {}):
        for key, value in source.items():
            if value is not None and str(value).strip():
                tags[key.casefold()] = str(value).strip()
    return tags


def _metadata_value(tags: dict[str, str], keys: set[str]) -> str | None:
    for key in keys:
        if key in tags:
            return tags[key]
    return None


def _scan_pixels(dataset: Any, include_range: bool) -> tuple[float, float | None, float | None]:
    import numpy as np

    invalid_count = 0
    sample_count = 0
    finite_min: float | None = None
    finite_max: float | None = None

    for _, window in dataset.block_windows(1):
        block = dataset.read(window=window, masked=True)
        values = np.asarray(block.data)
        invalid = np.ma.getmaskarray(block) | ~np.isfinite(values)
        invalid_count += int(invalid.sum())
        sample_count += int(values.size)
        if include_range:
            valid_values = values[~invalid]
            if valid_values.size:
                block_min = float(valid_values.min())
                block_max = float(valid_values.max())
                finite_min = block_min if finite_min is None else min(finite_min, block_min)
                finite_max = block_max if finite_max is None else max(finite_max, block_max)

    percentage = 100.0 * invalid_count / sample_count if sample_count else 100.0
    return percentage, finite_min, finite_max


def inspect_raster(path: Path, label: str, include_range: bool) -> RasterReport:
    import rasterio

    with rasterio.open(path) as dataset:
        tags = _normalise_tags(dataset)
        property_units = tuple(unit for unit in (dataset.units or ()) if unit)
        units = property_units[0] if property_units else _metadata_value(tags, UNIT_KEYS)
        vertical_datum = _metadata_value(tags, DATUM_KEYS)
        elevation_type = _metadata_value(tags, ELEVATION_TYPE_KEYS)
        if elevation_type is not None:
            elevation_type = elevation_type.upper()
        nodata_percent, finite_min, finite_max = _scan_pixels(dataset, include_range)
        transform = dataset.transform
        pixel_x = math.hypot(transform.a, transform.d)
        pixel_y = math.hypot(transform.b, transform.e)
        return RasterReport(
            label=label,
            path=path,
            shape=(dataset.height, dataset.width),
            bands=dataset.count,
            dtypes=tuple(dataset.dtypes),
            crs=dataset.crs,
            bounds=dataset.bounds,
            pixel_size=(pixel_x, pixel_y),
            nodata=tuple(dataset.nodatavals),
            nodata_percent=nodata_percent,
            finite_min=finite_min,
            finite_max=finite_max,
            units=units,
            vertical_datum=vertical_datum,
            elevation_type=elevation_type,
            width=dataset.width,
            height=dataset.height,
        )


def _bounds_in_crs(report: RasterReport, target_crs: Any) -> tuple[float, float, float, float]:
    from rasterio.warp import transform_bounds

    if report.crs == target_crs:
        return tuple(report.bounds)
    return transform_bounds(report.crs, target_crs, *report.bounds, densify_pts=21)


def _positive_intersection(
    left: tuple[float, float, float, float], right: tuple[float, float, float, float]
) -> bool:
    return min(left[2], right[2]) > max(left[0], right[0]) and min(
        left[3], right[3]
    ) > max(left[1], right[1])


def _resolution_in_crs(report: RasterReport, target_crs: Any) -> tuple[float, float]:
    from rasterio.warp import calculate_default_transform

    if report.crs == target_crs:
        return report.pixel_size
    transform, _, _ = calculate_default_transform(
        report.crs,
        target_crs,
        report.width,
        report.height,
        *report.bounds,
    )
    return math.hypot(transform.a, transform.d), math.hypot(transform.b, transform.e)


def _format_bounds(bounds: Any) -> str:
    return f"({bounds[0]:.10g}, {bounds[1]:.10g}, {bounds[2]:.10g}, {bounds[3]:.10g})"


def _print_report(report: RasterReport) -> None:
    print(f"\n{report.label.upper()}:")
    print(f"  path: {report.path}")
    print(f"  shape: {report.shape}")
    print(f"  bands: {report.bands}")
    print(f"  dtype: {', '.join(report.dtypes)}")
    print(f"  CRS: {report.crs or 'MISSING'}")
    print(f"  bounds: {_format_bounds(report.bounds)}")
    print(f"  pixel size: ({report.pixel_size[0]:.10g}, {report.pixel_size[1]:.10g})")
    print(f"  nodata: {report.nodata}")
    print(f"  nodata/non-finite percentage: {report.nodata_percent:.6f}%")
    if report.finite_min is not None:
        print(f"  finite min/max: {report.finite_min:.10g} / {report.finite_max:.10g}")
    if report.label != "rgb":
        print(f"  units from metadata: {report.units or 'MISSING'}")
        print(f"  vertical datum from metadata: {report.vertical_datum or 'MISSING'}")
        print(f"  elevation type from metadata: {report.elevation_type or 'MISSING'}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    missing_paths = [path for path in (args.rgb, args.reference, args.truth) if not path.is_file()]
    if missing_paths:
        for path in missing_paths:
            print(f"SCIENTIFIC BLOCKER: raster path not found: {path}", file=sys.stderr)
        return 2

    try:
        import numpy  # noqa: F401
        import rasterio  # noqa: F401
    except ImportError as exc:
        print(
            f"SCIENTIFIC BLOCKER: Rasterio and NumPy are required for raster QA: {exc}",
            file=sys.stderr,
        )
        return 2

    blockers: list[str] = []
    warnings: list[str] = []
    try:
        reports = [
            inspect_raster(args.rgb, "rgb", include_range=False),
            inspect_raster(args.reference, "reference", include_range=True),
            inspect_raster(args.truth, "truth", include_range=True),
        ]
    except Exception as exc:  # Rasterio raises several format/CRS-specific exception types.
        print(f"SCIENTIFIC BLOCKER: could not inspect the raster triplet: {exc}", file=sys.stderr)
        return 2

    rgb, reference, truth = reports
    for report in reports:
        _print_report(report)
        if report.crs is None:
            blockers.append(f"{report.label} CRS is missing")
        if all(value is None for value in report.nodata):
            warnings.append(f"{report.label} has no explicit nodata metadata")

    if rgb.bands < 3:
        blockers.append(f"RGB has {rgb.bands} band(s); at least three visible bands are required")
    elif rgb.bands > 3:
        warnings.append(f"RGB has {rgb.bands} bands; confirm which three are visible RGB")

    for report in (reference, truth):
        if report.finite_min is None or report.finite_max is None:
            blockers.append(f"{report.label} has no finite elevation samples")
        if not report.units:
            blockers.append(f"{report.label} elevation units are unknown")
        if not report.vertical_datum:
            blockers.append(f"{report.label} vertical datum is unknown")
        if not report.elevation_type:
            blockers.append(f"{report.label} elevation type is unknown (DSM/DTM/DEM/AGL required)")
        elif report.elevation_type not in ALLOWED_ELEVATION_TYPES:
            blockers.append(
                f"{report.label} elevation type {report.elevation_type!r} is unsupported; "
                f"expected one of {sorted(ALLOWED_ELEVATION_TYPES)}"
            )
        if report.bands != 1:
            warnings.append(f"{report.label} has {report.bands} bands; expected one elevation band")

    print("\nALIGNMENT:")
    if any(report.crs is None for report in reports):
        print("  geographic overlap: UNAVAILABLE (missing CRS)")
        print("  CRS compatibility: FAIL")
        print("  resolution ratio: UNAVAILABLE")
    else:
        try:
            rgb_bounds = tuple(rgb.bounds)
            reference_bounds = _bounds_in_crs(reference, rgb.crs)
            truth_bounds = _bounds_in_crs(truth, rgb.crs)
            rgb_reference_overlap = _positive_intersection(rgb_bounds, reference_bounds)
            rgb_truth_overlap = _positive_intersection(rgb_bounds, truth_bounds)
            reference_truth_overlap = _positive_intersection(reference_bounds, truth_bounds)
            all_overlap = (
                rgb_reference_overlap and rgb_truth_overlap and reference_truth_overlap
            )
            print(f"  geographic overlap: {'PASS' if all_overlap else 'FAIL'}")
            print(f"  bounds plausibly intersect: {'YES' if all_overlap else 'NO'}")
            print(
                "  CRS compatibility: "
                + ("EXACT MATCH" if rgb.crs == reference.crs == truth.crs else "TRANSFORMABLE")
            )
            reference_resolution = _resolution_in_crs(reference, rgb.crs)
            truth_resolution = _resolution_in_crs(truth, rgb.crs)
            rgb_resolution = sum(rgb.pixel_size) / 2
            reference_ratio = (sum(reference_resolution) / 2) / rgb_resolution
            truth_ratio = (sum(truth_resolution) / 2) / rgb_resolution
            print(f"  reference/RGB resolution ratio: {reference_ratio:.6g}")
            print(f"  truth/RGB resolution ratio: {truth_ratio:.6g}")
            if getattr(rgb.crs, "is_geographic", False):
                warnings.append(
                    "resolution ratios were approximated in angular RGB CRS units, not metres"
                )
            if not all_overlap:
                blockers.append("the three raster bounds do not share plausible geographic overlap")
        except Exception as exc:
            print(f"  geographic overlap: FAIL ({exc})")
            print("  CRS compatibility: FAIL")
            print("  resolution ratio: UNAVAILABLE")
            blockers.append(f"CRS transformation or overlap check failed: {exc}")

    print("\nWARNINGS:")
    if warnings:
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("- none")

    print("\nSCIENTIFIC BLOCKERS:")
    if blockers:
        for blocker in blockers:
            print(f"- SCIENTIFIC BLOCKER: {blocker}")
        print("RESULT: FAIL — metadata or alignment prevents scientific comparison")
        return 1

    print("- none")
    print("RESULT: PASS — metadata supports further comparison; target-type provenance still requires manifest review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
