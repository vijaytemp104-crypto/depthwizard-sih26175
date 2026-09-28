"""Fixed GeoInverse V0 experimental configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "outputs" / "geoinverse_v0"
PILOTS = {name: DATA / f"{name}_pilot" for name in ("wake", "polk", "larimer", "humboldt")}
FOLDS = {
    "wake": ("polk", "larimer", "humboldt"),
    "polk": ("wake", "larimer", "humboldt"),
    "larimer": ("wake", "polk", "humboldt"),
    "humboldt": ("wake", "polk", "larimer"),
}


@dataclass(frozen=True)
class Config:
    seed: int = 20260926
    patch_size: int = 256
    stride: int = 192
    minimum_valid_fraction: float = 0.80
    batch_size: int = 4
    learning_rate: float = 0.001
    weight_decay: float = 0.00001
    maximum_epochs: int = 6
    patience: int = 2
    input_channels: int = 8
    semantic_channels: int = 0
    base_channels: int = 24
    reference_scale_m: float = 2500.0
    gradient_scale: float = 20.0
    reference_support_m: float = 30.0
    gaussian_sigma_m: float = 12.738853503184714  # 30 m FWHM / 2.355
    huber_beta_m: float = 2.0
    low_loss_weight: float = 0.25
    high_loss_weight: float = 0.25
    preserve_loss_weight: float = 0.02
    preserve_detail_lambda: float = 1.0
    edge_loss_weight: float = 0.02
    initial_detail_weight: float = 0.05
    support_minimum_coverage: float = 0.80

    def to_dict(self) -> dict:
        return asdict(self)


CONFIG = Config()
