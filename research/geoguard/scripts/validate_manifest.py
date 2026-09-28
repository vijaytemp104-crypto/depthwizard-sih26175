#!/usr/bin/env python3
"""Validate a GeoGuard-SC AOI manifest without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ALLOWED_ROLES = {"train", "model_validation", "gate_calibration", "blind_test"}
ALLOWED_DOMAINS = {"urban", "open", "hilly", "forest"}
ALLOWED_TARGET_TYPES = {"DSM", "DTM", "DEM", "AGL"}
ALLOWED_STATUSES = {"metadata_pending", "verified_pilot", "ready", "excluded"}

REQUIRED_FIELDS = {
    "aoi_id",
    "region",
    "state",
    "country",
    "role",
    "domain",
    "rgb_source",
    "rgb_path",
    "rgb_date",
    "rgb_crs",
    "rgb_gsd_m",
    "reference_source",
    "reference_path",
    "reference_type",
    "reference_date",
    "reference_crs",
    "reference_vertical_datum",
    "reference_units",
    "reference_resolution_m",
    "truth_source",
    "truth_path",
    "truth_type",
    "truth_date",
    "truth_crs",
    "truth_vertical_datum",
    "truth_units",
    "truth_resolution_m",
    "license",
    "acquisition_gap_days",
    "valid_truth_fraction",
    "status",
    "exclusion_reason",
    "rgb_checksum_sha256",
    "reference_checksum_sha256",
    "truth_checksum_sha256",
    "notes",
}

SCIENTIFIC_METADATA_FIELDS = {
    "rgb_source",
    "rgb_path",
    "rgb_date",
    "rgb_crs",
    "rgb_gsd_m",
    "reference_source",
    "reference_path",
    "reference_date",
    "reference_crs",
    "reference_vertical_datum",
    "reference_units",
    "reference_resolution_m",
    "truth_source",
    "truth_path",
    "truth_date",
    "truth_crs",
    "truth_vertical_datum",
    "truth_units",
    "truth_resolution_m",
    "license",
    "acquisition_gap_days",
    "valid_truth_fraction",
    "rgb_checksum_sha256",
    "reference_checksum_sha256",
    "truth_checksum_sha256",
}

DATE_FIELDS = {"rgb_date", "reference_date", "truth_date"}
POSITIVE_FIELDS = {"rgb_gsd_m", "reference_resolution_m", "truth_resolution_m"}
CHECKSUM_FIELDS = {
    "rgb_checksum_sha256",
    "reference_checksum_sha256",
    "truth_checksum_sha256",
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
AOI_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _location_key(record: dict[str, Any]) -> tuple[str, str, str] | None:
    parts = []
    for field in ("region", "state", "country"):
        value = record.get(field)
        if value is None:
            value = ""
        if not isinstance(value, str):
            return None
        parts.append(" ".join(value.casefold().split()))
    if not parts[0] or not parts[2]:
        return None
    return tuple(parts)  # type: ignore[return-value]


def validate_manifest(document: Any) -> list[str]:
    """Return all hard validation errors in deterministic order."""

    errors: list[str] = []
    if not isinstance(document, dict):
        return ["manifest root must be a JSON object"]

    if document.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")

    records = document.get("aois")
    if not isinstance(records, list) or not records:
        errors.append("aois must be a non-empty array")
        return errors

    id_rows: dict[str, list[int]] = defaultdict(list)
    location_roles: dict[tuple[str, str, str], list[tuple[int, str, str]]] = defaultdict(list)

    for index, record in enumerate(records):
        prefix = f"aois[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing_keys = sorted(REQUIRED_FIELDS - set(record))
        if missing_keys:
            errors.append(f"{prefix} missing required fields: {', '.join(missing_keys)}")

        aoi_id = record.get("aoi_id")
        if not isinstance(aoi_id, str) or not AOI_ID_RE.fullmatch(aoi_id):
            errors.append(f"{prefix}.aoi_id must match {AOI_ID_RE.pattern}")
            display_id = f"<row-{index}>"
        else:
            display_id = aoi_id
            id_rows[aoi_id].append(index)

        role = record.get("role")
        if role not in ALLOWED_ROLES:
            errors.append(f"{prefix}.role must be one of {sorted(ALLOWED_ROLES)}")

        domain = record.get("domain")
        if domain not in ALLOWED_DOMAINS:
            errors.append(f"{prefix}.domain must be one of {sorted(ALLOWED_DOMAINS)}")

        for field in ("reference_type", "truth_type"):
            if record.get(field) not in ALLOWED_TARGET_TYPES:
                errors.append(f"{prefix}.{field} must be one of {sorted(ALLOWED_TARGET_TYPES)}")

        status = record.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(ALLOWED_STATUSES)}")

        for field in ("region", "country"):
            if _missing(record.get(field)):
                errors.append(f"{prefix}.{field} is required")

        if status in {"verified_pilot", "ready"}:
            for field in SCIENTIFIC_METADATA_FIELDS:
                if _missing(record.get(field)):
                    errors.append(f"{prefix}.{field} is required for scientific use")

        for field in DATE_FIELDS:
            value = record.get(field)
            if _missing(value):
                continue
            if not isinstance(value, str):
                errors.append(f"{prefix}.{field} must be an ISO date (YYYY-MM-DD)")
                continue
            try:
                date.fromisoformat(value)
            except ValueError:
                errors.append(f"{prefix}.{field} is not a valid ISO date: {value!r}")

        for field in POSITIVE_FIELDS:
            value = record.get(field)
            if _missing(value):
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"{prefix}.{field} must be a positive number")

        gap = record.get("acquisition_gap_days")
        if not _missing(gap) and (
            isinstance(gap, bool) or not isinstance(gap, int) or gap < 0
        ):
            errors.append(f"{prefix}.acquisition_gap_days must be a non-negative integer")

        fraction = record.get("valid_truth_fraction")
        if not _missing(fraction) and (
            isinstance(fraction, bool)
            or not isinstance(fraction, (int, float))
            or not 0 <= fraction <= 1
        ):
            errors.append(f"{prefix}.valid_truth_fraction must be between 0 and 1")

        for field in CHECKSUM_FIELDS:
            value = record.get(field)
            if _missing(value):
                continue
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                errors.append(f"{prefix}.{field} must be a 64-character SHA-256 hex digest")

        location = _location_key(record)
        if location is not None and isinstance(role, str):
            location_roles[location].append((index, display_id, role))

    for aoi_id, rows in sorted(id_rows.items()):
        if len(rows) > 1:
            errors.append(f"duplicate aoi_id {aoi_id!r} at rows {rows}")

    for location, assignments in sorted(location_roles.items()):
        roles = {role for _, _, role in assignments}
        if len(roles) > 1:
            readable_location = ", ".join(part for part in location if part)
            details = ", ".join(f"{aoi_id}:{role}" for _, aoi_id, role in assignments)
            errors.append(
                f"same AOI geography assigned to multiple roles ({readable_location}): {details}"
            )
        if "train" in roles and "blind_test" in roles:
            readable_location = ", ".join(part for part in location if part)
            errors.append(f"blind-test AOI also appears in train: {readable_location}")

    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to a GeoGuard manifest JSON file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        with args.manifest.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except FileNotFoundError:
        print(f"FAIL: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: could not read valid JSON from {args.manifest}: {exc}", file=sys.stderr)
        return 2

    errors = validate_manifest(document)
    if errors:
        print(f"FAIL: {len(errors)} manifest validation error(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"PASS: {len(document['aois'])} AOI record(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
