from copy import deepcopy

import pytest

from backend.final_validation_reference import (
    get_final_validation_reference_metadata,
)


def complete_manifest():
    return {
        "dataset_id": "final-withheld-example",
        "geographic_identity": {
            "geographic_identity_id": "us-nm-santa-fe-example",
            "canonical_name": "Santa Fe, New Mexico, United States",
        },
        "provenance": {
            "provider": "Example independent provider",
            "source_dataset_id": "source-example-001",
        },
        "reference_descriptor": {
            "artifact_uri_or_path": "https://example.invalid/reference.tif",
            "format": "GeoTIFF",
            "units": "metres",
            "crs": None,
            "transform": None,
            "nodata": None,
        },
    }


def test_extracts_complete_reference_metadata_with_exact_keys():
    result = get_final_validation_reference_metadata(complete_manifest())

    assert result == {
        "dataset_id": "final-withheld-example",
        "geographic_identity_id": "us-nm-santa-fe-example",
        "canonical_name": "Santa Fe, New Mexico, United States",
        "provider": "Example independent provider",
        "source_dataset_id": "source-example-001",
        "artifact_uri_or_path": "https://example.invalid/reference.tif",
        "format": "GeoTIFF",
        "units": "metres",
        "crs": None,
        "transform": None,
        "nodata": None,
    }


def test_preserves_artifact_uri_or_path_exactly():
    manifest = complete_manifest()
    manifest["reference_descriptor"]["artifact_uri_or_path"] = "references/final/withheld dem.tif"

    result = get_final_validation_reference_metadata(manifest)

    assert result["artifact_uri_or_path"] == "references/final/withheld dem.tif"


@pytest.mark.parametrize("field_name", ["crs", "transform", "nodata"])
def test_preserves_legitimate_null_reference_metadata(field_name):
    result = get_final_validation_reference_metadata(complete_manifest())

    assert result[field_name] is None


@pytest.mark.parametrize(
    ("section", "message"),
    [
        ("geographic_identity", "geographic_identity"),
        ("provenance", "provenance"),
        ("reference_descriptor", "reference_descriptor"),
    ],
)
def test_missing_required_manifest_sections_fail(section, message):
    manifest = complete_manifest()
    manifest.pop(section)

    with pytest.raises(ValueError, match=message):
        get_final_validation_reference_metadata(manifest)


@pytest.mark.parametrize(
    ("field_name", "message"),
    [
        ("artifact_uri_or_path", "artifact_uri_or_path"),
        ("format", "format"),
        ("units", "units"),
    ],
)
def test_missing_required_reference_fields_fail(field_name, message):
    manifest = complete_manifest()
    manifest["reference_descriptor"].pop(field_name)

    with pytest.raises(ValueError, match=message):
        get_final_validation_reference_metadata(manifest)


def test_does_not_mutate_the_input_manifest():
    manifest = complete_manifest()
    original_manifest = deepcopy(manifest)

    get_final_validation_reference_metadata(manifest)

    assert manifest == original_manifest


def test_does_not_create_or_resolve_the_reference_artifact(tmp_path):
    manifest = complete_manifest()
    artifact_path = tmp_path / "not-downloaded.tif"
    manifest["reference_descriptor"]["artifact_uri_or_path"] = str(artifact_path)

    result = get_final_validation_reference_metadata(manifest)

    assert result["artifact_uri_or_path"] == str(artifact_path)
    assert not artifact_path.exists()
    assert list(tmp_path.iterdir()) == []
