from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validate_manifest.py"
SPEC = importlib.util.spec_from_file_location("geoguard_validate_manifest", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load validator from {MODULE_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def valid_record() -> dict[str, object]:
    checksum = "a" * 64
    return {
        "aoi_id": "sample_aoi",
        "region": "Sample County",
        "state": "Example State",
        "country": "United States",
        "role": "train",
        "domain": "urban",
        "rgb_source": "Synthetic RGB fixture",
        "rgb_path": "fixtures/rgb.tif",
        "rgb_date": "2025-06-01",
        "rgb_crs": "EPSG:32617",
        "rgb_gsd_m": 0.6,
        "reference_source": "Synthetic coarse fixture",
        "reference_path": "fixtures/reference.tif",
        "reference_type": "DSM",
        "reference_date": "2020-01-01",
        "reference_crs": "EPSG:32617",
        "reference_vertical_datum": "NAVD88",
        "reference_units": "metre",
        "reference_resolution_m": 30.0,
        "truth_source": "Synthetic independent fixture",
        "truth_path": "fixtures/truth.tif",
        "truth_type": "DSM",
        "truth_date": "2025-05-20",
        "truth_crs": "EPSG:32617",
        "truth_vertical_datum": "NAVD88",
        "truth_units": "metre",
        "truth_resolution_m": 1.0,
        "license": "Synthetic test fixture",
        "acquisition_gap_days": 12,
        "valid_truth_fraction": 0.98,
        "status": "ready",
        "exclusion_reason": None,
        "rgb_checksum_sha256": checksum,
        "reference_checksum_sha256": checksum,
        "truth_checksum_sha256": checksum,
        "notes": "Synthetic metadata only; no external data.",
    }


def manifest(*records: dict[str, object]) -> dict[str, object]:
    return {"schema_version": "1.0", "aois": list(records)}


class ManifestValidatorTests(unittest.TestCase):
    def assert_error_contains(self, document: dict[str, object], fragment: str) -> None:
        errors = VALIDATOR.validate_manifest(document)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"Expected error containing {fragment!r}; got {errors!r}",
        )

    def test_valid_manifest(self) -> None:
        self.assertEqual(VALIDATOR.validate_manifest(manifest(valid_record())), [])

    def test_verified_pilot_status_is_valid(self) -> None:
        record = valid_record()
        record["status"] = "verified_pilot"
        self.assertEqual(VALIDATOR.validate_manifest(manifest(record)), [])

    def test_metadata_pending_allows_unresolved_scientific_fields(self) -> None:
        record = valid_record()
        record["status"] = "metadata_pending"
        for field in VALIDATOR.SCIENTIFIC_METADATA_FIELDS:
            record[field] = None
        self.assertEqual(VALIDATOR.validate_manifest(manifest(record)), [])

    def test_duplicate_aoi(self) -> None:
        first = valid_record()
        second = copy.deepcopy(first)
        second["region"] = "Different County"
        self.assert_error_contains(manifest(first, second), "duplicate aoi_id")

    def test_same_geography_in_overlapping_roles(self) -> None:
        first = valid_record()
        second = copy.deepcopy(first)
        second["aoi_id"] = "sample_aoi_blind"
        second["role"] = "blind_test"
        self.assert_error_contains(manifest(first, second), "assigned to multiple roles")
        self.assert_error_contains(manifest(first, second), "also appears in train")

    def test_missing_datum(self) -> None:
        record = valid_record()
        record["truth_vertical_datum"] = None
        self.assert_error_contains(manifest(record), "truth_vertical_datum")

    def test_missing_units(self) -> None:
        record = valid_record()
        record["reference_units"] = ""
        self.assert_error_contains(manifest(record), "reference_units")

    def test_invalid_enum(self) -> None:
        record = valid_record()
        record["role"] = "test"
        self.assert_error_contains(manifest(record), ".role must be one of")

    def test_invalid_gsd(self) -> None:
        for invalid in (0, -1, "0.6"):
            with self.subTest(invalid=invalid):
                record = valid_record()
                record["rgb_gsd_m"] = invalid
                self.assert_error_contains(manifest(record), "rgb_gsd_m must be a positive number")


if __name__ == "__main__":
    unittest.main()
