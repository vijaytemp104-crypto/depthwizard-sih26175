"""Provenance checks for final withheld validation dataset manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DATASET_ROLES = {
    "development",
    "calibration",
    "final_withheld_validation",
}
REQUIRED_EXCLUDED_FROM = {
    "model training",
    "model selection",
    "calibration-method selection",
    "hyperparameter tuning",
    "threshold tuning",
    "architecture selection",
    "smoothing-scale selection",
    "qualitative model comparison",
}


def _required_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip().lower() == "unknown":
        raise ValueError(f"{field_name} must be a non-empty, non-unknown string")
    return value.strip()


def _manifest_value(manifest: dict, key: str) -> str:
    return _required_nonempty_string(manifest.get(key), key)


def _protected_geographic_ids(registry: dict) -> set[str]:
    protected = registry.get("protected_final_withheld_geographies", [])
    if not isinstance(protected, list):
        raise ValueError("protected_final_withheld_geographies must be a list")

    protected_ids = set()
    for item in protected:
        if not isinstance(item, dict):
            raise ValueError("protected geography entries must be objects")
        protected_ids.add(
            _required_nonempty_string(
                item.get("geographic_identity_id"),
                "protected geographic_identity_id",
            )
        )
    return protected_ids


def _is_boulder_colorado_us(geographic_identity: dict) -> bool:
    """Identify the explicitly prohibited Boulder, Colorado, US geography."""
    explicit_fields_identify_boulder = (
        str(geographic_identity.get("country_code", "")).strip().upper() == "US"
        and str(geographic_identity.get("admin1", "")).strip().lower()
        in {"colorado", "co"}
        and str(geographic_identity.get("locality", "")).strip().lower() == "boulder"
    )
    canonical_name = str(geographic_identity.get("canonical_name", "")).lower()
    canonical_name_identifies_boulder = bool(
        re.search(r"\bboulder\b[^a-z0-9]+(?:colorado|co)\b", canonical_name)
    )
    return explicit_fields_identify_boulder or canonical_name_identifies_boulder


def load_dataset_registry(registry_path: str | Path) -> dict:
    """Load a JSON dataset registry without resolving or downloading artifacts."""
    with Path(registry_path).open(encoding="utf-8") as registry_file:
        registry = json.load(registry_file)

    if not isinstance(registry, dict):
        raise ValueError("dataset registry must be a JSON object")
    if registry.get("schema_version") != "1.0":
        raise ValueError("dataset registry schema_version must be '1.0'")
    if not isinstance(registry.get("datasets"), list):
        raise ValueError("dataset registry datasets must be a list")
    _protected_geographic_ids(registry)
    return registry


def validate_dataset_manifest(dataset_manifest: dict, registry: dict) -> None:
    """Confirm a candidate is explicitly eligible as final withheld validation data."""
    if not isinstance(dataset_manifest, dict):
        raise ValueError("dataset manifest must be an object")
    if not isinstance(registry, dict) or not isinstance(registry.get("datasets"), list):
        raise ValueError("registry must contain a datasets list")

    _manifest_value(dataset_manifest, "dataset_id")
    dataset_role = _manifest_value(dataset_manifest, "dataset_role")
    if dataset_role not in DATASET_ROLES:
        raise ValueError("dataset_role must be development, calibration, or final_withheld_validation")
    if dataset_role != "final_withheld_validation":
        raise ValueError("only final_withheld_validation datasets are eligible for final validation")

    geographic_identity = dataset_manifest.get("geographic_identity")
    if not isinstance(geographic_identity, dict):
        raise ValueError("geographic_identity is required")
    geographic_identity_id = _required_nonempty_string(
        geographic_identity.get("geographic_identity_id"), "geographic_identity_id"
    )
    _required_nonempty_string(geographic_identity.get("canonical_name"), "canonical_name")

    if geographic_identity_id in _protected_geographic_ids(registry):
        raise ValueError("protected geographic_identity_id is not eligible for final withheld validation")
    if _is_boulder_colorado_us(geographic_identity):
        raise ValueError("Boulder, Colorado, US is not eligible for final withheld validation")

    provenance = dataset_manifest.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("provenance is required")
    _required_nonempty_string(provenance.get("provider"), "provenance.provider")
    source_dataset_id = _required_nonempty_string(
        provenance.get("source_dataset_id"), "provenance.source_dataset_id"
    )

    independence = dataset_manifest.get("independence")
    if not isinstance(independence, dict):
        raise ValueError("independence is required")
    _required_nonempty_string(independence.get("attestation"), "independence.attestation")

    excluded_from = independence.get("excluded_from")
    if (
        not isinstance(excluded_from, list)
        or any(not isinstance(item, str) for item in excluded_from)
        or not REQUIRED_EXCLUDED_FROM.issubset(set(excluded_from))
    ):
        raise ValueError("independence.excluded_from is missing required declarations")
    if independence.get("used_for_development") is not False:
        raise ValueError("independence.used_for_development must be false")
    if independence.get("used_for_calibration") is not False:
        raise ValueError("independence.used_for_calibration must be false")
    if independence.get("eligible_for_final_withheld_validation") is not True:
        raise ValueError(
            "independence.eligible_for_final_withheld_validation must be true"
        )

    for registered_dataset in registry["datasets"]:
        if not isinstance(registered_dataset, dict):
            continue
        if registered_dataset.get("dataset_role") not in {"development", "calibration"}:
            continue

        registered_geography = registered_dataset.get("geographic_identity", {})
        if isinstance(registered_geography, dict) and (
            registered_geography.get("geographic_identity_id") == geographic_identity_id
        ):
            raise ValueError(
                "geographic_identity_id duplicates development or calibration data"
            )

        registered_provenance = registered_dataset.get("provenance", {})
        if isinstance(registered_provenance, dict) and (
            registered_provenance.get("source_dataset_id") == source_dataset_id
        ):
            raise ValueError(
                "provenance.source_dataset_id duplicates development or calibration data"
            )


def get_final_withheld_dataset(registry: dict, dataset_id: str) -> dict:
    """Return a registered, validated final withheld dataset manifest by ID."""
    requested_id = _required_nonempty_string(dataset_id, "dataset_id")
    if not isinstance(registry, dict) or not isinstance(registry.get("datasets"), list):
        raise ValueError("registry must contain a datasets list")

    for dataset_manifest in registry["datasets"]:
        if isinstance(dataset_manifest, dict) and dataset_manifest.get("dataset_id") == requested_id:
            validate_dataset_manifest(dataset_manifest, registry)
            return dataset_manifest

    raise ValueError(f"dataset_id '{requested_id}' is not registered")
