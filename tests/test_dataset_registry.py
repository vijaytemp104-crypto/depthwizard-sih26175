from pathlib import Path

import pytest

from backend.dataset_registry import (
    REQUIRED_EXCLUDED_FROM,
    get_final_withheld_dataset,
    load_dataset_registry,
    validate_dataset_manifest,
)


REGISTRY_PATH = Path(__file__).parents[1] / "configs" / "dataset_registry.json"


def valid_final_manifest():
    return {
        "dataset_id": "final-withheld-example",
        "dataset_role": "final_withheld_validation",
        "geographic_identity": {
            "geographic_identity_id": "us-nm-santa-fe-example",
            "canonical_name": "Santa Fe, New Mexico, United States",
            "country_code": "US",
            "admin1": "New Mexico",
            "locality": "Santa Fe",
        },
        "provenance": {
            "provider": "Example independent provider",
            "source_dataset_id": "source-example-001",
        },
        "independence": {
            "attestation": "This dataset was excluded from all listed development and calibration activities.",
            "excluded_from": sorted(REQUIRED_EXCLUDED_FROM),
            "used_for_development": False,
            "used_for_calibration": False,
            "eligible_for_final_withheld_validation": True,
        },
    }


def test_loads_the_empty_registry():
    registry = load_dataset_registry(REGISTRY_PATH)

    assert registry["schema_version"] == "1.0"
    assert registry["datasets"] == []
    assert registry["protected_final_withheld_geographies"][0]["geographic_identity_id"] == "us-co-boulder"


def test_accepts_complete_non_boulder_final_withheld_manifest():
    validate_dataset_manifest(valid_final_manifest(), load_dataset_registry(REGISTRY_PATH))


@pytest.mark.parametrize("dataset_role", ["development", "calibration"])
def test_rejects_development_and_calibration_roles(dataset_role):
    manifest = valid_final_manifest()
    manifest["dataset_role"] = dataset_role

    with pytest.raises(ValueError, match="only final_withheld_validation"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_boulder_by_protected_geographic_identity_id():
    manifest = valid_final_manifest()
    manifest["geographic_identity"]["geographic_identity_id"] = "us-co-boulder"

    with pytest.raises(ValueError, match="protected geographic_identity_id"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_boulder_by_explicit_geographic_fields():
    manifest = valid_final_manifest()
    manifest["geographic_identity"].update(
        {
            "geographic_identity_id": "unregistered-boulder-id",
            "canonical_name": "Boulder, Colorado, United States",
            "country_code": "US",
            "admin1": "Colorado",
            "locality": "Boulder",
        }
    )

    with pytest.raises(ValueError, match="Boulder, Colorado"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_boulder_by_canonical_name_without_explicit_location_fields():
    manifest = valid_final_manifest()
    manifest["geographic_identity"].update(
        {
            "geographic_identity_id": "unregistered-boulder-id",
            "canonical_name": "Boulder, Colorado, United States",
        }
    )
    manifest["geographic_identity"].pop("country_code")
    manifest["geographic_identity"].pop("admin1")
    manifest["geographic_identity"].pop("locality")

    with pytest.raises(ValueError, match="Boulder, Colorado"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_duplicate_development_or_calibration_geographic_identity():
    registry = load_dataset_registry(REGISTRY_PATH)
    registry["datasets"].append(
        {
            "dataset_id": "development-site",
            "dataset_role": "development",
            "geographic_identity": {"geographic_identity_id": "us-nm-santa-fe-example"},
            "provenance": {"source_dataset_id": "development-source"},
        }
    )

    with pytest.raises(ValueError, match="geographic_identity_id duplicates"):
        validate_dataset_manifest(valid_final_manifest(), registry)


def test_rejects_duplicate_development_or_calibration_source_dataset_id():
    registry = load_dataset_registry(REGISTRY_PATH)
    registry["datasets"].append(
        {
            "dataset_id": "calibration-site",
            "dataset_role": "calibration",
            "geographic_identity": {"geographic_identity_id": "different-geography"},
            "provenance": {"source_dataset_id": "source-example-001"},
        }
    )

    with pytest.raises(ValueError, match="source_dataset_id duplicates"):
        validate_dataset_manifest(valid_final_manifest(), registry)


def test_rejects_missing_provenance():
    manifest = valid_final_manifest()
    manifest.pop("provenance")

    with pytest.raises(ValueError, match="provenance"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


@pytest.mark.parametrize(
    ("field", "value"),
    [("geographic_identity_id", None), ("geographic_identity_id", "unknown")],
)
def test_rejects_missing_or_unknown_geographic_identity_id(field, value):
    manifest = valid_final_manifest()
    if value is None:
        manifest["geographic_identity"].pop(field)
    else:
        manifest["geographic_identity"][field] = value

    with pytest.raises(ValueError, match="geographic_identity_id"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


@pytest.mark.parametrize(
    ("field", "value"),
    [("canonical_name", None), ("canonical_name", "unknown")],
)
def test_rejects_missing_or_unknown_canonical_name(field, value):
    manifest = valid_final_manifest()
    if value is None:
        manifest["geographic_identity"].pop(field)
    else:
        manifest["geographic_identity"][field] = value

    with pytest.raises(ValueError, match="canonical_name"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


@pytest.mark.parametrize("source_dataset_id", [None, "unknown"])
def test_rejects_missing_or_unknown_source_dataset_id(source_dataset_id):
    manifest = valid_final_manifest()
    if source_dataset_id is None:
        manifest["provenance"].pop("source_dataset_id")
    else:
        manifest["provenance"]["source_dataset_id"] = source_dataset_id

    with pytest.raises(ValueError, match="provenance.source_dataset_id"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_missing_independence_attestation():
    manifest = valid_final_manifest()
    manifest["independence"].pop("attestation")

    with pytest.raises(ValueError, match="independence.attestation"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_incomplete_excluded_from_declarations():
    manifest = valid_final_manifest()
    manifest["independence"]["excluded_from"] = ["model training"]

    with pytest.raises(ValueError, match="excluded_from"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_missing_excluded_from_declarations():
    manifest = valid_final_manifest()
    manifest["independence"].pop("excluded_from")

    with pytest.raises(ValueError, match="excluded_from"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_malformed_excluded_from_declarations_with_value_error():
    manifest = valid_final_manifest()
    manifest["independence"]["excluded_from"] = [["model training"]]

    with pytest.raises(ValueError, match="excluded_from"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


@pytest.mark.parametrize(
    ("field", "value"),
    [("used_for_development", True), ("used_for_calibration", True)],
)
def test_rejects_prior_development_or_calibration_use(field, value):
    manifest = valid_final_manifest()
    manifest["independence"][field] = value

    with pytest.raises(ValueError, match=field):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


@pytest.mark.parametrize("eligibility", [False, "true", 1])
def test_rejects_eligibility_that_is_not_exactly_true(eligibility):
    manifest = valid_final_manifest()
    manifest["independence"]["eligible_for_final_withheld_validation"] = eligibility

    with pytest.raises(ValueError, match="eligible_for_final_withheld_validation"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_rejects_invalid_dataset_role():
    manifest = valid_final_manifest()
    manifest["dataset_role"] = "test"

    with pytest.raises(ValueError, match="dataset_role"):
        validate_dataset_manifest(manifest, load_dataset_registry(REGISTRY_PATH))


def test_empty_registry_does_not_manufacture_a_dataset():
    with pytest.raises(ValueError, match="not registered"):
        get_final_withheld_dataset(load_dataset_registry(REGISTRY_PATH), "missing-dataset")


def test_get_final_withheld_dataset_rejects_registered_development_dataset():
    registry = load_dataset_registry(REGISTRY_PATH)
    registry["datasets"].append(
        {"dataset_id": "development-site", "dataset_role": "development"}
    )

    with pytest.raises(ValueError, match="only final_withheld_validation"):
        get_final_withheld_dataset(registry, "development-site")
