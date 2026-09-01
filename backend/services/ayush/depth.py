"""Loading and validation for Manish's relative-depth array contract."""

from pathlib import Path

import numpy as np


def load_depth(path: str | Path) -> np.ndarray:
    """Load a 2-D numeric `.npy` depth map and normalize it to float32.

    NaN and infinity are retained here so the common validity mask can exclude
    them during calibration and emit nodata at the same locations in the DSM.
    """
    path = Path(path)
    if path.suffix.lower() != ".npy":
        raise ValueError(f"Depth input must be a .npy file: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Depth input does not exist: {path}")
    try:
        depth = np.load(path, allow_pickle=False)
    except Exception as exc:
        raise ValueError(f"Could not load depth array {path}: {exc}") from exc
    if depth.ndim != 2:
        raise ValueError(f"Depth array must be 2-D, got shape {depth.shape}")
    if not np.issubdtype(depth.dtype, np.number):
        raise ValueError(f"Depth array must be numeric, got {depth.dtype}")
    if depth.size == 0:
        raise ValueError("Depth array must not be empty")
    if np.count_nonzero(np.isfinite(depth)) < 2:
        raise ValueError("Depth array needs at least two finite pixels")
    return depth.astype(np.float32, copy=False)
