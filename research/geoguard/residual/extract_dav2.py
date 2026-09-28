#!/usr/bin/env python3
"""Create missing frozen DAV2 relative-depth rasters from the offline checkpoint."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from config import DAV2_CACHE, DAV2_MODEL_ID, DAV2_SNAPSHOT, PILOTS, REPOSITORY_ROOT


def extract(site: str, *, overwrite: bool = False) -> dict:
    root = PILOTS[site] / "derived"
    output_dir = root / "ai"
    output_path = output_dir / "depth_relative.tif"
    metadata_path = output_dir / "depth_relative_metadata.json"
    if output_path.is_file() and not overwrite:
        return {"site": site, "status": "reused", "path": str(output_path)}
    if not DAV2_SNAPSHOT.is_dir():
        raise FileNotFoundError(f"offline DAV2 snapshot missing: {DAV2_SNAPSHOT}")

    os.environ.setdefault("HF_HOME", str(DAV2_CACHE))
    from backend.services.relative_depth_adapter import DepthAnythingV2SmallAdapter

    rgb_path = root / "rgb_aligned.tif"
    with rasterio.open(rgb_path) as source:
        rgb = np.moveaxis(source.read([1, 2, 3]), 0, -1).astype(np.uint8)
        profile = source.profile.copy()
        crs = str(source.crs)
        transform = tuple(source.transform)[:6]
    adapter = DepthAnythingV2SmallAdapter(
        device="cpu", model_id=str(DAV2_SNAPSHOT), local_files_only=True
    )
    started = time.perf_counter()
    depth, model_metadata = adapter.predict_depth(Image.fromarray(rgb, "RGB"))
    runtime = time.perf_counter() - started

    output_dir.mkdir(parents=True, exist_ok=True)
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    profile.update(count=1, dtype="float32", nodata=None, compress="deflate")
    with rasterio.open(output_path, "w", **profile) as output:
        output.write(depth.astype(np.float32), 1)
        output.set_band_unit(1, "relative_arbitrary")
        output.update_tags(
            1,
            units="relative_arbitrary",
            metric_depth="false",
            model=DAV2_MODEL_ID,
            frozen="true",
        )
    record = {
        "site": site,
        "model_name": "Depth Anything V2 Small",
        "checkpoint_id": DAV2_MODEL_ID,
        "checkpoint_snapshot": str(DAV2_SNAPSHOT.relative_to(REPOSITORY_ROOT)),
        "checkpoint_commit": DAV2_SNAPSHOT.name,
        "device": model_metadata.device,
        "framework": model_metadata.framework,
        "local_files_only": True,
        "frozen": True,
        "fine_tuned": False,
        "input": str(rgb_path),
        "output": str(output_path),
        "shape": list(depth.shape),
        "relative_min": float(depth.min()),
        "relative_max": float(depth.max()),
        "relative_mean": float(depth.mean()),
        "runtime_seconds": runtime,
        "crs": crs,
        "transform": transform,
    }
    metadata_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sites", nargs="*", choices=tuple(PILOTS), default=list(PILOTS))
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    for site in arguments.sites:
        print(json.dumps(extract(site, overwrite=arguments.overwrite), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
