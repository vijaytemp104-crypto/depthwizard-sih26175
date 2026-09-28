from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


GEOGUARD_ROOT = Path(__file__).resolve().parents[1]
QA_SCRIPT = GEOGUARD_ROOT / "qa" / "check_triplet.py"
GENERATOR = Path(__file__).resolve().parent / "generate_synthetic_fixtures.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def generate_fixtures() -> None:
    subprocess.run(
        [sys.executable, str(GENERATOR), "--output", str(FIXTURES)],
        check=True,
        capture_output=True,
        text=True,
    )


def run_case(case_name: str) -> subprocess.CompletedProcess[str]:
    case_dir = FIXTURES / case_name
    return subprocess.run(
        [
            sys.executable,
            str(QA_SCRIPT),
            "--rgb",
            str(case_dir / "rgb.tif"),
            "--reference",
            str(case_dir / "reference.tif"),
            "--truth",
            str(case_dir / "truth.tif"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_valid_triplet_passes_metadata_qa() -> None:
    result = run_case("valid")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "geographic overlap: PASS" in result.stdout
    assert "CRS compatibility: EXACT MATCH" in result.stdout
    assert result.stdout.count("elevation type from metadata: DSM") == 2
    assert "RESULT: PASS" in result.stdout
    assert "SCIENTIFIC BLOCKER:" not in result.stdout


def test_missing_vertical_datum_is_scientific_blocker() -> None:
    result = run_case("missing_vertical_datum")
    assert result.returncode == 1
    assert "SCIENTIFIC BLOCKER: reference vertical datum is unknown" in result.stdout
    assert "RESULT: FAIL" in result.stdout


def test_missing_units_is_scientific_blocker() -> None:
    result = run_case("missing_units")
    assert result.returncode == 1
    assert "SCIENTIFIC BLOCKER: reference elevation units are unknown" in result.stdout
    assert "RESULT: FAIL" in result.stdout


def test_nonoverlapping_truth_is_rejected() -> None:
    result = run_case("nonoverlap")
    assert result.returncode == 1
    assert "geographic overlap: FAIL" in result.stdout
    assert "bounds plausibly intersect: NO" in result.stdout
    assert "SCIENTIFIC BLOCKER: the three raster bounds do not share plausible geographic overlap" in result.stdout


def test_different_transformable_crs_passes() -> None:
    result = run_case("crs_transformable")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "geographic overlap: PASS" in result.stdout
    assert "CRS compatibility: TRANSFORMABLE" in result.stdout
    assert "RESULT: PASS" in result.stdout
