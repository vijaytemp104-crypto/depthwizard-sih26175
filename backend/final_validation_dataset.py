"""Selection boundary for registered final withheld validation datasets."""

from __future__ import annotations

from pathlib import Path

from backend.dataset_registry import (
    get_final_withheld_dataset,
    load_dataset_registry,
)


def load_final_withheld_dataset_manifest(
    dataset_id: str,
    registry_path: str | Path = "configs/dataset_registry.json",
) -> dict:
    """Load and return a validated final withheld dataset manifest only."""
    registry = load_dataset_registry(registry_path)
    return get_final_withheld_dataset(registry, dataset_id)
