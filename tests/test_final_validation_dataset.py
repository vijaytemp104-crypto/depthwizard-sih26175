import json

import pytest

from backend.dataset_registry import REQUIRED_EXCLUDED_FROM
from backend.final_validation_dataset import load_final_withheld_dataset_manifest


def final_withheld_manifest():
    return {
        "dataset_id": "final-withheld-example",
        "dataset_role": "final_withheld_validation",
        "geographic_identity": {
            "geographic_identity_id": "us-nm-santa-fe-example",
            "canonical_name": "Santa Fe, New Mexico, United States",
        },
        "provenance": {
            "provider": "Example independent provider",
            "source_dataset_id": "source-example-001",
        },
        "independence": {
            "attestation": "Excluded from all listed development and calibration activities.",
            "excluded_from": sorted(REQUIRED_EXCLUDED_FROM),
            "used_for_development": False,
            "used_for_calibration": False,
            "eligible_for_final_withheld_validation": True,
        },
        "artifact_uri_or_path": "https://example.invalid/final-withheld-reference.tif",
    }


def write_registry(tmp_path, datasets):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "protected_final_withheld_geographies": [
                    {"geographic_identity_id": "us-co-boulder"}
                ],
                "datasets": datasets,
            }
        ),
        encoding="utf-8",
    )
    return registry_path


def test_loads_a_valid_registered_final_withheld_manifest(tmp_path):
    manifest = final_withheld_manifest()
    registry_path = write_registry(tmp_path, [manifest])

    result = load_final_withheld_dataset_manifest(
        manifest["dataset_id"], registry_path
    )

    assert result == manifest


def test_missing_dataset_id_raises_registry_error(tmp_path):
    registry_path = write_registry(tmp_path, [])

    with pytest.raises(ValueError, match="not registered"):
        load_final_withheld_dataset_manifest("missing-dataset", registry_path)


@pytest.mark.parametrize("dataset_role", ["development", "calibration"])
def test_development_and_calibration_datasets_cannot_be_loaded(tmp_path, dataset_role):
    registry_path = write_registry(
        tmp_path,
        [{"dataset_id": f"{dataset_role}-dataset", "dataset_role": dataset_role}],
    )

    with pytest.raises(ValueError, match="only final_withheld_validation"):
        load_final_withheld_dataset_manifest(f"{dataset_role}-dataset", registry_path)


def test_preserves_artifact_uri_or_path_exactly(tmp_path):
    manifest = final_withheld_manifest()
    manifest["artifact_uri_or_path"] = "references/final/withheld-dem.tif"
    registry_path = write_registry(tmp_path, [manifest])

    result = load_final_withheld_dataset_manifest(
        manifest["dataset_id"], registry_path
    )

    assert result["artifact_uri_or_path"] == "references/final/withheld-dem.tif"


def test_does_not_create_or_resolve_the_manifest_artifact(tmp_path):
    manifest = final_withheld_manifest()
    artifact_path = tmp_path / "not-downloaded.tif"
    manifest["artifact_uri_or_path"] = str(artifact_path)
    registry_path = write_registry(tmp_path, [manifest])

    result = load_final_withheld_dataset_manifest(
        manifest["dataset_id"], registry_path
    )

    assert result["artifact_uri_or_path"] == str(artifact_path)
    assert not artifact_path.exists()
    assert list(tmp_path.iterdir()) == [registry_path]
