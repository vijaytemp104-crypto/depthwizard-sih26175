"""Raster metadata inspection and reference DEM alignment."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject


@dataclass(frozen=True)
class RasterMetadata:
    crs: str
    transform: tuple[float, float, float, float, float, float]
    width: int
    height: int
    bounds: tuple[float, float, float, float]
    resolution: tuple[float, float]
    nodata: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _metadata(dataset: rasterio.io.DatasetReader) -> RasterMetadata:
    if dataset.crs is None:
        raise ValueError("Reference DEM must declare a CRS")
    if dataset.count < 1:
        raise ValueError("Reference DEM has no raster bands")
    return RasterMetadata(
        crs=dataset.crs.to_string(),
        transform=tuple(dataset.transform)[:6],
        width=dataset.width,
        height=dataset.height,
        bounds=tuple(dataset.bounds),
        resolution=tuple(abs(v) for v in dataset.res),
        nodata=dataset.nodata,
    )


def load_dem(path: str | Path) -> tuple[np.ndarray, RasterMetadata]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Reference DEM does not exist: {path}")
    try:
        with rasterio.open(path) as src:
            meta = _metadata(src)
            dem = src.read(1, masked=True).filled(np.nan).astype(np.float32)
    except rasterio.errors.RasterioIOError as exc:
        raise ValueError(f"Could not open reference DEM {path}: {exc}") from exc
    return dem, meta


def depth_grid(depth_path: str | Path, shape: tuple[int, int], dem_meta: RasterMetadata):
    """Resolve depth georeferencing from a sidecar or documented DEM extent fallback."""
    sidecar = Path(str(depth_path) + ".json")
    height, width = shape
    if sidecar.exists():
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        if "crs" not in payload or "transform" not in payload:
            raise ValueError(f"Depth sidecar must contain crs and transform: {sidecar}")
        values = payload["transform"]
        if not isinstance(values, list) or len(values) != 6:
            raise ValueError("Depth sidecar transform must be six GDAL-order numbers")
        # Sidecar is GDAL order: origin x, pixel width, rotation, origin y, rotation, pixel height.
        transform = Affine.from_gdal(*map(float, values))
        crs = CRS.from_user_input(payload["crs"])
        assumption = "depth sidecar"
    else:
        crs = CRS.from_user_input(dem_meta.crs)
        transform = from_bounds(*dem_meta.bounds, width, height)
        assumption = "shared DEM extent (no depth sidecar supplied)"
    return crs, transform, assumption


def align_dem(
    dem_path: str | Path,
    target_shape: tuple[int, int],
    target_crs: CRS,
    target_transform: Affine,
) -> tuple[np.ndarray, RasterMetadata, bool]:
    """Reproject/resample a DEM onto the depth grid, reporting whether alignment occurred."""
    with rasterio.open(dem_path) as src:
        source_meta = _metadata(src)
        already_aligned = (
            (src.height, src.width) == target_shape
            and src.crs == target_crs
            and src.transform.almost_equals(target_transform)
        )
        if already_aligned:
            return src.read(1, masked=True).filled(np.nan).astype(np.float32), source_meta, False

        destination = np.full(target_shape, np.nan, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=target_transform,
            dst_crs=target_crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    return destination, source_meta, True
