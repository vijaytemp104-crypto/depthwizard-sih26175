"""Fixed, preregistered configuration for Residual Refiner V1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


GEOGUARD_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = GEOGUARD_ROOT.parents[1]
DATA_ROOT = GEOGUARD_ROOT / "data"
OUTPUT_ROOT = GEOGUARD_ROOT / "outputs" / "residual_v1"

PILOTS = {
    "wake": DATA_ROOT / "wake_pilot",
    "polk": DATA_ROOT / "polk_pilot",
    "larimer": DATA_ROOT / "larimer_pilot",
    "humboldt": DATA_ROOT / "humboldt_pilot",
}

FOLDS = {
    "wake": ("polk", "larimer", "humboldt"),
    "polk": ("wake", "larimer", "humboldt"),
    "larimer": ("wake", "polk", "humboldt"),
    "humboldt": ("wake", "polk", "larimer"),
}

DAV2_MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"
DAV2_CACHE = REPOSITORY_ROOT / "outputs" / ".hf_cache"
DAV2_SNAPSHOT = (
    DAV2_CACHE
    / "hub"
    / "models--depth-anything--Depth-Anything-V2-Small-hf"
    / "snapshots"
    / "5426e4f0f36572d16453bbda7a8389317b1bef99"
)


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 20260924
    patch_size: int = 256
    patch_stride: int = 192
    minimum_valid_fraction: float = 0.80
    batch_size: int = 4
    learning_rate: float = 0.001
    weight_decay: float = 0.00001
    maximum_epochs: int = 6
    early_stopping_patience: int = 2
    huber_beta_m: float = 2.0
    gradient_loss_weight: float = 0.05
    base_channels: int = 24
    input_channels: int = 7
    reference_scale_m: float = 2500.0
    gradient_scale_m_per_m: float = 20.0
    support_size_m: float = 30.0
    support_minimum_coverage: float = 0.80

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


CONFIG = TrainingConfig()
