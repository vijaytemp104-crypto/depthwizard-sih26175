"""Metadata-only boundary for final withheld validation references."""

from __future__ import annotations

from typing import Any


def _required_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _required_object(value: Any, field_name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} is required")
    return value


def get_final_validation_reference_metadata(dataset_manifest: dict) -> dict:
    """Extract declared reference metadata without resolving its artifact."""
    if not isinstance(dataset_manifest, dict):
        raise ValueError("dataset_manifest is required")

    geographic_identity = _required_object(
        dataset_manifest.get("geographic_identity"), "geographic_identity"
    )
    provenance = _required_object(dataset_manifest.get("provenance"), "provenance")
    reference_descriptor = _required_object(
        dataset_manifest.get("reference_descriptor"), "reference_descriptor"
    )

    for field_name in ("crs", "transform", "nodata"):
        if field_name not in reference_descriptor:
            raise ValueError(f"reference_descriptor.{field_name} is required and may be null")

    return {
        "dataset_id": _required_nonempty_string(
            dataset_manifest.get("dataset_id"), "dataset_id"
        ),
        "geographic_identity_id": _required_nonempty_string(
            geographic_identity.get("geographic_identity_id"), "geographic_identity_id"
        ),
        "canonical_name": _required_nonempty_string(
            geographic_identity.get("canonical_name"), "canonical_name"
        ),
        "provider": _required_nonempty_string(
            provenance.get("provider"), "provenance.provider"
        ),
        "source_dataset_id": _required_nonempty_string(
            provenance.get("source_dataset_id"), "provenance.source_dataset_id"
        ),
        "artifact_uri_or_path": _required_nonempty_string(
            reference_descriptor.get("artifact_uri_or_path"),
            "reference_descriptor.artifact_uri_or_path",
        ),
        "format": _required_nonempty_string(
            reference_descriptor.get("format"), "reference_descriptor.format"
        ),
        "units": _required_nonempty_string(
            reference_descriptor.get("units"), "reference_descriptor.units"
        ),
        "crs": reference_descriptor["crs"],
        "transform": reference_descriptor["transform"],
        "nodata": reference_descriptor["nodata"],
    }
