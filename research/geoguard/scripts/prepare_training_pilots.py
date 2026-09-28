#!/usr/bin/env python3
"""Prepare the three approved real GeoGuard training pilots reproducibly."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import laspy
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds


NODATA = -9999.0
METRES_PER_US_SURVEY_FOOT = 1200.0 / 3937.0
COPERNICUS_EPOCH = "2011-2015"
COPERNICUS_H_FRAME = "WGS84-G1150"
ACCEPTED_SURFACE_CLASSES = {1, 2, 3, 4, 5, 6, 9, 10, 13, 14, 17}


SITES: dict[str, dict[str, Any]] = {
    "polk": {
        "directory": "polk_pilot",
        "county": "Polk County",
        "state": "Iowa",
        "domain": "open",
        "target_crs": "EPSG:6344",
        "bounds": (458000.0, 4615000.0, 459000.0, 4616000.0),
        "naip_date": "2019-08-22",
        "naip_gsd_m": 0.6,
        "naip_crs": "EPSG:26915",
        "naip_ids": [
            "ia_m_4109321_sw_15_060_20190822_20191105",
            "ia_m_4109321_nw_15_060_20190822_20191105",
            "ia_m_4109320_se_15_060_20190822_20191105",
            "ia_m_4109320_ne_15_060_20190822_20191105",
        ],
        "naip_urls": [
            "https://naipeuwest.blob.core.windows.net/naip/v002/ia/2019/ia_60cm_2019/41093/m_4109321_sw_15_060_20190822.tif",
            "https://naipeuwest.blob.core.windows.net/naip/v002/ia/2019/ia_60cm_2019/41093/m_4109321_nw_15_060_20190822.tif",
            "https://naipeuwest.blob.core.windows.net/naip/v002/ia/2019/ia_60cm_2019/41093/m_4109320_se_15_060_20190822.tif",
            "https://naipeuwest.blob.core.windows.net/naip/v002/ia/2019/ia_60cm_2019/41093/m_4109320_ne_15_060_20190822.tif",
        ],
        "lidar_product": "USGS LPC IA_NorthCentral_2020_D20 w4580n4615",
        "lidar_url": "https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/IA_NorthCentral_2020_D20/IA_NorthCentral_2_2020/LAZ/USGS_LPC_IA_NorthCentral_2020_D20_w4580n4615.laz?download=1",
        "lidar_filename": "USGS_LPC_IA_NorthCentral_2020_D20_w4580n4615.laz",
        "ept_name": "IA_NorthCentral_2_2020",
        "use_ept": False,
        "metadata_url": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/metadata/IA_NorthCentral_2020_D20/IA_NorthCentral_2_2020/reports/vendor_provided_xml/ClassifiedPointCloud_2.1_Block_3_IA_NorthCentral.xml",
        "truth_native_crs": "EPSG:6344",
        "truth_vertical_datum": "NAVD88 (Geoid12B)",
        "truth_geoid": "geoid12b",
        "truth_native_units": "metre",
        "truth_scale_to_metres": 1.0,
        "truth_nominal_spacing_m": 0.71,
        "collection_range": "2020-04-16/2020-04-27",
        "copernicus_tile": "Copernicus_DSM_COG_10_N41_00_W094_00_DEM",
    },
    "larimer": {
        "directory": "larimer_pilot",
        "county": "Larimer County",
        "state": "Colorado",
        "domain": "hilly",
        "target_crs": "EPSG:6342",
        "bounds": (477750.0, 4491100.0, 478750.0, 4492100.0),
        "naip_date": "2021-07-26",
        "naip_gsd_m": 0.6,
        "naip_crs": "EPSG:26913",
        "naip_ids": [
            "co_m_4010531_nw_13_060_20210726",
            "co_m_4010530_ne_13_060_20210726",
        ],
        "naip_urls": [
            "https://naipeuwest.blob.core.windows.net/naip/v002/co/2021/co_060cm_2021/40105/31/m_4010531_nw_13_060_20210726.tif",
            "https://naipeuwest.blob.core.windows.net/naip/v002/co/2021/co_060cm_2021/40105/30/m_4010530_ne_13_060_20210726.tif",
        ],
        "lidar_product": "USGS LPC CO_CameronPeakWildfire_2021_D21 w3065n1450",
        "lidar_url": "https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CO_CameronPeakWildfire_2021_D21/CO_CameronPkFire_1_2021/LAZ/USGS_LPC_CO_CameronPeakWildfire_2021_D21_w3065n1450.laz?download=1",
        "lidar_filename": "USGS_LPC_CO_CameronPeakWildfire_2021_D21_w3065n1450.laz",
        "ept_name": "CO_CameronPkFire_1_2021",
        "use_ept": True,
        "metadata_url": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/metadata/CO_CameronPeakWildfire_2021_D21/CO_CameronPkFire_1_2021/reports/vendor_provided_xml/312021410_USGS_Cameron_Peak_Lidar_ClassifiedPointCloud.xml",
        "truth_native_crs": "EPSG:6430",
        "truth_vertical_datum": "NAVD88 (Geoid18)",
        "truth_geoid": "geoid18",
        "truth_native_units": "US survey foot",
        "truth_scale_to_metres": METRES_PER_US_SURVEY_FOOT,
        "truth_nominal_spacing_m": 0.43,
        "collection_range": "2021-09-07/2021-09-22",
        "copernicus_tile": "Copernicus_DSM_COG_10_N40_00_W106_00_DEM",
    },
    "humboldt": {
        "directory": "humboldt_pilot",
        "county": "Humboldt County",
        "state": "California",
        "domain": "forest",
        "target_crs": "EPSG:6339",
        "bounds": (416500.0, 4527000.0, 417500.0, 4528000.0),
        "naip_date": "2022-05-31",
        "naip_gsd_m": 0.6,
        "naip_crs": "EPSG:26910",
        "naip_ids": [
            "ca_m_4012408_se_10_060_20220531",
            "ca_m_4012301_sw_10_060_20220531",
        ],
        "naip_urls": [
            "https://naipeuwest.blob.core.windows.net/naip/v002/ca/2022/ca_060cm_2022/40124/m_4012408_se_10_060_20220531.tif",
            "https://naipeuwest.blob.core.windows.net/naip/v002/ca/2022/ca_060cm_2022/40123/m_4012301_sw_10_060_20220531.tif",
        ],
        "lidar_product": "USGS LPC CA_NorthernCA_B22 10TDL1627",
        "lidar_url": "https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_NorthernCA_B22/CA_NorthernCA_5_B22/LAZ/USGS_LPC_CA_NorthernCA_B22_10TDL1627.laz?download=1",
        "lidar_filename": "USGS_LPC_CA_NorthernCA_B22_10TDL1627.laz",
        "ept_name": "CA_NorthernCA_5_B22",
        "use_ept": True,
        "metadata_url": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/metadata/CA_NorthernCA_B22/CA_NorthernCA_5_B22/reports/vendor_provided_xml/CA_NorthernCA_B22_WU300466_ClassifiedPointCloud.xml",
        "truth_native_crs": "EPSG:6339",
        "truth_vertical_datum": "NAVD88 (Geoid18)",
        "truth_geoid": "geoid18",
        "truth_native_units": "metre",
        "truth_scale_to_metres": 1.0,
        "truth_nominal_spacing_m": 0.35,
        "collection_range": "2022-09-11/2022-11-03",
        "copernicus_tile": "Copernicus_DSM_COG_10_N40_00_W124_00_DEM",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def truth_primary_url(config: dict[str, Any]) -> str:
    if config.get("use_ept"):
        return f"https://usgs-lidar-public.s3.amazonaws.com/{config['ept_name']}/ept.json"
    return config["lidar_url"]


def download(url: str, path: Path) -> None:
    if path.is_file() and path.stat().st_size:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    headers = {"User-Agent": "GeoGuard-research/1.0", "Range": "bytes=0-0"}
    probe = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(probe, timeout=90) as response:
        content_range = response.headers.get("Content-Range", "")
        match = re.search(r"/(\d+)$", content_range)
        if not match:
            with temporary.open("wb") as target:
                target.write(response.read())
                while chunk := response.read(4 * 1024 * 1024):
                    target.write(chunk)
            temporary.replace(path)
            return
        total_size = int(match.group(1))

    # The legacy vdelivery endpoint is substantially more reliable with small ranges.
    chunk_size = 1024 * 1024
    completed = temporary.stat().st_size if temporary.exists() else 0
    if completed > total_size:
        temporary.unlink()
        completed = 0
    with temporary.open("ab") as target:
        while completed < total_size:
            end = min(completed + chunk_size - 1, total_size - 1)
            for attempt in range(5):
                try:
                    request = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "GeoGuard-research/1.0",
                            "Range": f"bytes={completed}-{end}",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=90) as response:
                        payload = response.read()
                    if len(payload) != end - completed + 1:
                        raise OSError("short ranged response")
                    target.write(payload)
                    target.flush()
                    completed += len(payload)
                    break
                except (OSError, urllib.error.URLError):
                    if attempt == 4:
                        raise
                    time.sleep(2**attempt)
    temporary.replace(path)


def copernicus_url(tile: str) -> str:
    return f"https://copernicus-dem-30m.s3.amazonaws.com/{tile}/{tile}.tif"


def download_simple(url: str, path: Path) -> None:
    if path.is_file() and path.stat().st_size:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "GeoGuard-research/1.0"})
            with urllib.request.urlopen(request, timeout=120) as source, temporary.open("wb") as target:
                while chunk := source.read(4 * 1024 * 1024):
                    target.write(chunk)
            temporary.replace(path)
            return
        except (OSError, urllib.error.URLError):
            if attempt == 4:
                raise
            time.sleep(2**attempt)


def ept_node_bounds(root_bounds: list[float], key: str) -> tuple[float, float, float, float]:
    depth, x_index, y_index, _ = map(int, key.split("-"))
    divisions = 2**depth
    x_size = (root_bounds[3] - root_bounds[0]) / divisions
    y_size = (root_bounds[4] - root_bounds[1]) / divisions
    return (
        root_bounds[0] + x_index * x_size,
        root_bounds[1] + y_index * y_size,
        root_bounds[0] + (x_index + 1) * x_size,
        root_bounds[1] + (y_index + 1) * y_size,
    )


def prepare_ept_sources(config: dict[str, Any], root: Path) -> tuple[list[Path], Path]:
    dataset = config["ept_name"]
    base_url = f"https://usgs-lidar-public.s3.amazonaws.com/{dataset}"
    ept = json.load(urllib.request.urlopen(f"{base_url}/ept.json", timeout=90))
    transformed_bounds = transform_bounds(
        config["target_crs"], "EPSG:3857", *config["bounds"], densify_pts=21
    )

    def overlaps(bounds: tuple[float, float, float, float]) -> bool:
        return min(bounds[2], transformed_bounds[2]) > max(bounds[0], transformed_bounds[0]) and min(
            bounds[3], transformed_bounds[3]
        ) > max(bounds[1], transformed_bounds[1])

    selected: dict[str, int] = {}
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visited:
            return
        visited.add(key)
        hierarchy_url = f"{base_url}/ept-hierarchy/{key}.json"
        hierarchy = json.load(urllib.request.urlopen(hierarchy_url, timeout=90))
        for node_key, count in hierarchy.items():
            if not overlaps(ept_node_bounds(ept["bounds"], node_key)):
                continue
            if count == -1:
                visit(node_key)
            elif count > 0:
                selected[node_key] = int(count)

    visit("0-0-0-0")
    chunk_root = root / "truth_raw" / "ept_chunks"
    jobs = [
        (key, f"{base_url}/ept-data/{key}.laz", chunk_root / f"{key}.laz")
        for key in sorted(selected)
    ]

    def fetch(job: tuple[str, str, Path]) -> tuple[str, Path]:
        key, url, path = job
        download_simple(url, path)
        return key, path

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        completed = dict(executor.map(fetch, jobs))
    paths = [completed[key] for key in sorted(completed)]
    selection = {
        "source": "USGS 3DEP public EPT",
        "collection": dataset,
        "ept_url": f"{base_url}/ept.json",
        "target_bounds_epsg3857": transformed_bounds,
        "selected_node_count": len(selected),
        "advertised_selected_point_count": sum(selected.values()),
        "nodes": [
            {
                "key": key,
                "point_count": selected[key],
                "url": f"{base_url}/ept-data/{key}.laz",
                "sha256": sha256(completed[key]),
            }
            for key in sorted(selected)
        ],
    }
    selection_path = root / "truth_raw" / "ept_selection.json"
    selection_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    return paths, selection_path


def wgs84_bounds(config: dict[str, Any]) -> tuple[float, float, float, float]:
    return transform_bounds(config["target_crs"], "EPSG:4326", *config["bounds"], densify_pts=21)


def vdatum_offset(longitude: float, latitude: float, geoid: str) -> dict[str, Any]:
    parameters = {
        "s_x": longitude,
        "s_y": latitude,
        "s_z": 0,
        "region": "contiguous",
        "s_h_frame": "WGS84_G1674",
        "s_coor": "geo",
        "s_h_unit": "m",
        "s_v_frame": "EGM2008",
        "s_v_unit": "m",
        "s_v_geoid": "egm2008",
        "t_h_frame": "NAD83_2011",
        "t_coor": "geo",
        "t_h_unit": "m",
        "t_v_frame": "NAVD88",
        "t_v_unit": "m",
        "t_v_geoid": geoid,
    }
    url = "https://vdatum.noaa.gov/vdatumweb/api/convert?" + urllib.parse.urlencode(parameters)
    response = json.load(urllib.request.urlopen(url, timeout=90))
    response["request_url"] = url
    return response


def prepare_rgb(config: dict[str, Any], root: Path) -> tuple[Path, list[str]]:
    source_paths = [rasterio.open(url) for url in config["naip_urls"]]
    try:
        crop_bounds = transform_bounds(
            config["target_crs"], config["naip_crs"], *config["bounds"], densify_pts=21
        )
        mosaic, mosaic_transform = merge(
            source_paths,
            bounds=crop_bounds,
            res=config["naip_gsd_m"],
            indexes=[1, 2, 3],
            nodata=0,
            method="first",
        )
    finally:
        for dataset in source_paths:
            dataset.close()

    source_crop = root / "rgb" / "naip_rgb_source_crop.tif"
    source_crop.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        source_crop,
        "w",
        driver="GTiff",
        height=mosaic.shape[1],
        width=mosaic.shape[2],
        count=3,
        dtype=mosaic.dtype,
        crs=config["naip_crs"],
        transform=mosaic_transform,
        nodata=0,
        compress="deflate",
    ) as output:
        output.write(mosaic)
        output.update_tags(source="USDA-FSA NAIP", acquisition_date=config["naip_date"])

    aligned = np.zeros((3, 1000, 1000), dtype=np.uint8)
    aligned_transform = from_bounds(*config["bounds"], 1000, 1000)
    with rasterio.open(source_crop) as source:
        for band in range(1, 4):
            reproject(
                source=rasterio.band(source, band),
                destination=aligned[band - 1],
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=0,
                dst_transform=aligned_transform,
                dst_crs=config["target_crs"],
                dst_nodata=0,
                resampling=Resampling.bilinear,
            )
    aligned_path = root / "derived" / "rgb_aligned.tif"
    aligned_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        aligned_path,
        "w",
        driver="GTiff",
        height=1000,
        width=1000,
        count=3,
        dtype="uint8",
        crs=config["target_crs"],
        transform=aligned_transform,
        nodata=0,
        compress="deflate",
    ) as output:
        output.write(aligned)
        output.update_tags(source="USDA-FSA NAIP", acquisition_date=config["naip_date"])
    return source_crop, config["naip_ids"]


def prepare_reference(config: dict[str, Any], root: Path) -> tuple[Path, list[dict[str, Any]]]:
    tile = config["copernicus_tile"]
    url = copernicus_url(tile)
    native_crop = root / "reference" / "copernicus_glo30_crop.tif"
    native_crop.parent.mkdir(parents=True, exist_ok=True)
    bounds4326 = wgs84_bounds(config)
    with rasterio.open(url) as source:
        window = source.window(*bounds4326).round_offsets().round_lengths()
        window = window.intersection(rasterio.windows.Window(0, 0, source.width, source.height))
        data = source.read(1, window=window, boundless=False)
        transform = source.window_transform(window)
        profile = source.profile.copy()
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)
        profile.update(height=data.shape[0], width=data.shape[1], transform=transform, compress="deflate")
        with rasterio.open(native_crop, "w", **profile) as output:
            output.write(data, 1)
            output.set_band_unit(1, "metre")
            output.update_tags(
                1,
                units="metre",
                vertical_datum="EGM2008",
                elevation_type="DSM",
                source_product=tile,
            )

    aligned = np.full((1000, 1000), NODATA, dtype=np.float32)
    aligned_transform = from_bounds(*config["bounds"], 1000, 1000)
    with rasterio.open(native_crop) as source:
        reproject(
            source=rasterio.band(source, 1),
            destination=aligned,
            src_transform=source.transform,
            src_crs=source.crs,
            src_nodata=source.nodata,
            dst_transform=aligned_transform,
            dst_crs=config["target_crs"],
            dst_nodata=NODATA,
            resampling=Resampling.bilinear,
        )

    west, south, east, north = bounds4326
    responses = [
        vdatum_offset(west, north, config["truth_geoid"]),
        vdatum_offset(east, north, config["truth_geoid"]),
        vdatum_offset(west, south, config["truth_geoid"]),
        vdatum_offset(east, south, config["truth_geoid"]),
    ]
    tl, tr, bl, br = [float(item["t_z"]) for item in responses]
    row_fraction = np.linspace(0.0, 1.0, 1000, dtype=np.float64)[:, None]
    column_fraction = np.linspace(0.0, 1.0, 1000, dtype=np.float64)[None, :]
    top = tl + (tr - tl) * column_fraction
    bottom = bl + (br - bl) * column_fraction
    correction = top + (bottom - top) * row_fraction
    valid = aligned != NODATA
    aligned[valid] += correction[valid].astype(np.float32)

    aligned_path = root / "derived" / "reference_aligned.tif"
    with rasterio.open(
        aligned_path,
        "w",
        driver="GTiff",
        height=1000,
        width=1000,
        count=1,
        dtype="float32",
        crs=config["target_crs"],
        transform=aligned_transform,
        nodata=NODATA,
        compress="deflate",
    ) as output:
        output.write(aligned, 1)
        output.set_band_unit(1, "metre")
        output.update_tags(
            1,
            units="metre",
            vertical_datum=config["truth_vertical_datum"],
            elevation_type="DSM",
            source_product=tile,
            vertical_conversion="NOAA VDatum EGM2008 to NAVD88",
            effective_resolution="approximately 30 metres",
        )
    return native_crop, responses


def gps_range_to_dates(minimum: float | None, maximum: float | None, adjusted: bool) -> tuple[str | None, str | None]:
    if minimum is None or maximum is None or not adjusted:
        return None, None
    epoch = datetime(1980, 1, 6, tzinfo=timezone.utc)
    convert = lambda value: (epoch + timedelta(seconds=value + 1_000_000_000 - 18)).date().isoformat()
    return convert(minimum), convert(maximum)


def prepare_truth(config: dict[str, Any], root: Path) -> tuple[Path, dict[str, Any]]:
    if config.get("use_ept"):
        source_paths, raw_descriptor = prepare_ept_sources(config, root)
    else:
        laz_path = root / "truth_raw" / config["lidar_filename"]
        download(config["lidar_url"], laz_path)
        source_paths, raw_descriptor = [laz_path], laz_path
    surface = np.full((1000, 1000), -np.inf, dtype=np.float64)
    density = np.zeros((1000, 1000), dtype=np.uint32)
    class_counts: Counter[int] = Counter()
    accepted_counts: Counter[int] = Counter()
    accepted_point_count = 0
    gps_minimum: float | None = None
    gps_maximum: float | None = None
    west, south, east, north = config["bounds"]

    source_crs_values: set[str] = set()
    gps_types: set[int] = set()
    for source_path in source_paths:
      with laspy.open(source_path) as reader:
        source_crs = reader.header.parse_crs() or config["truth_native_crs"]
        source_crs_values.add(str(source_crs))
        transformer = Transformer.from_crs(source_crs, config["target_crs"], always_xy=True)
        gps_type = int(reader.header.global_encoding.gps_time_type)
        gps_types.add(gps_type)
        z_scale = 1.0 if config.get("use_ept") else config["truth_scale_to_metres"]
        for points in reader.chunk_iterator(1_000_000):
            classes = np.asarray(points.classification)
            unique, counts = np.unique(classes, return_counts=True)
            class_counts.update({int(key): int(value) for key, value in zip(unique, counts)})
            x, y = transformer.transform(np.asarray(points.x), np.asarray(points.y))
            inside = (x >= west) & (x < east) & (y >= south) & (y < north)
            accepted = inside & np.isin(classes, list(ACCEPTED_SURFACE_CLASSES))
            if hasattr(points, "withheld"):
                accepted &= ~np.asarray(points.withheld, dtype=bool)
            if hasattr(points, "overlap"):
                accepted &= ~np.asarray(points.overlap, dtype=bool)
            if not accepted.any():
                continue
            accepted_classes, accepted_class_counts = np.unique(classes[accepted], return_counts=True)
            accepted_counts.update(
                {int(key): int(value) for key, value in zip(accepted_classes, accepted_class_counts)}
            )
            rows = np.floor((north - y[accepted]) / 1.0).astype(np.int64)
            columns = np.floor((x[accepted] - west) / 1.0).astype(np.int64)
            keep = (rows >= 0) & (rows < 1000) & (columns >= 0) & (columns < 1000)
            rows, columns = rows[keep], columns[keep]
            z = np.asarray(points.z)[accepted][keep] * z_scale
            flat = rows * 1000 + columns
            np.maximum.at(surface.ravel(), flat, z)
            np.add.at(density.ravel(), flat, 1)
            accepted_point_count += int(z.size)
            if hasattr(points, "gps_time"):
                times = np.asarray(points.gps_time)[accepted][keep]
                if times.size:
                    local_minimum, local_maximum = float(times.min()), float(times.max())
                    gps_minimum = local_minimum if gps_minimum is None else min(gps_minimum, local_minimum)
                    gps_maximum = local_maximum if gps_maximum is None else max(gps_maximum, local_maximum)

    valid = np.isfinite(surface)
    truth = np.full(surface.shape, NODATA, dtype=np.float32)
    truth[valid] = surface[valid].astype(np.float32)
    aligned_path = root / "derived" / "truth_aligned.tif"
    aligned_transform = from_bounds(*config["bounds"], 1000, 1000)
    with rasterio.open(
        aligned_path,
        "w",
        driver="GTiff",
        height=1000,
        width=1000,
        count=1,
        dtype="float32",
        crs=config["target_crs"],
        transform=aligned_transform,
        nodata=NODATA,
        compress="deflate",
    ) as output:
        output.write(truth, 1)
        output.set_band_unit(1, "metre")
        output.update_tags(
            1,
            units="metre",
            vertical_datum=config["truth_vertical_datum"],
            elevation_type="DSM",
            rasterization="maximum accepted LiDAR Z per 1 metre cell; no interpolation",
        )

    adjusted_gps = gps_types == {1}
    start_date, end_date = gps_range_to_dates(gps_minimum, gps_maximum, adjusted_gps)
    valid_density = density[valid]
    details = {
        "source_crs": sorted(source_crs_values),
        "source_transport": "USGS 3DEP public EPT subset" if config.get("use_ept") else "USGS TNM LAZ tile",
        "source_file_count": len(source_paths),
        "gps_time_types": sorted(gps_types),
        "tile_acquisition_start": start_date,
        "tile_acquisition_end": end_date,
        "project_collection_range": config["collection_range"],
        "all_class_counts": dict(sorted(class_counts.items())),
        "accepted_class_counts": dict(sorted(accepted_counts.items())),
        "accepted_surface_classes": sorted(ACCEPTED_SURFACE_CLASSES),
        "excluded_classes": [7, 11, 18, 20, 22],
        "accepted_point_count": accepted_point_count,
        "valid_cell_count": int(valid.sum()),
        "valid_fraction": float(valid.mean()),
        "density_min": int(valid_density.min()) if valid_density.size else 0,
        "density_median": float(np.median(valid_density)) if valid_density.size else 0,
        "density_max": int(valid_density.max()) if valid_density.size else 0,
        "elevation_min_m": float(truth[valid].min()) if valid.any() else None,
        "elevation_max_m": float(truth[valid].max()) if valid.any() else None,
    }
    return raw_descriptor, details


def prepare_mask(root: Path) -> float:
    paths = [
        root / "derived" / "rgb_aligned.tif",
        root / "derived" / "reference_aligned.tif",
        root / "derived" / "truth_aligned.tif",
    ]
    with rasterio.open(paths[0]) as rgb, rasterio.open(paths[1]) as reference, rasterio.open(paths[2]) as truth:
        rgb_data = rgb.read(masked=True)
        reference_data = reference.read(1, masked=True)
        truth_data = truth.read(1, masked=True)
        valid = (
            ~np.ma.getmaskarray(rgb_data).any(axis=0)
            & ~np.ma.getmaskarray(reference_data)
            & ~np.ma.getmaskarray(truth_data)
            & np.isfinite(rgb_data.data).all(axis=0)
            & np.isfinite(reference_data.data)
            & np.isfinite(truth_data.data)
        )
        profile = truth.profile.copy()
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    profile.update(count=1, dtype="uint8", nodata=0, compress="deflate")
    with rasterio.open(root / "derived" / "valid_mask.tif", "w", **profile) as output:
        output.write(valid.astype(np.uint8), 1)
        output.update_tags(1, units="dimensionless", mask_definition="RGB AND reference AND truth valid")
    return float(valid.mean())


def provenance_markdown(config: dict[str, Any], record: dict[str, Any]) -> str:
    return f"""# {config['county']} GeoGuard pilot provenance

- Role/status: `train` / `verified_pilot`
- Domain: `{config['domain']}`
- AOI: exactly 1,000 m × 1,000 m
- Target CRS: `{config['target_crs']}`
- Target bounds: `{', '.join(str(value) for value in config['bounds'])}`
- WGS84 envelope: `{', '.join(f'{value:.10f}' for value in record['wgs84_bounds'])}`

## RGB

- USDA-FSA NAIP, `{config['naip_date']}`, native `{config['naip_gsd_m']} m`, four-band RGBNIR; bands 1–3 retained.
- Native CRS: `{config['naip_crs']}`.
- STAC identifiers: `{', '.join(config['naip_ids'])}`.
- URLs: {json.dumps(config['naip_urls'])}

## Coarse reference

- Copernicus DEM GLO-30 DSM `{config['copernicus_tile']}`.
- Native horizontal reference: EPSG:4326 / {COPERNICUS_H_FRAME}.
- Native vertical datum: EGM2008, metres; source epoch {COPERNICUS_EPOCH}.
- URL: {copernicus_url(config['copernicus_tile'])}
- Converted to `{config['truth_vertical_datum']}` with NOAA VDatum corner offsets recorded in `source_metadata.json`.
- VDatum reported `NaN` uncertainty; conversion uncertainty is unquantified, not zero.

## Independent truth

- {config['lidar_product']}.
- Data endpoint used: {truth_primary_url(config)}
- Legacy tile download URL: {config['lidar_url']}
- Project metadata: {config['metadata_url']}
- Native CRS: `{config['truth_native_crs']}`; vertical datum `{config['truth_vertical_datum']}`; units `{config['truth_native_units']}`.
- Nominal point spacing: {config['truth_nominal_spacing_m']} m.
- Project collection range: {config['collection_range']}; tile GPS date range: {record['truth']['tile_acquisition_start']} to {record['truth']['tile_acquisition_end']}.
- Surface truth uses maximum accepted Z per 1 m cell, no interpolation. Noise, ignored-ground, temporal-exclusion, withheld, and overlap-flagged points are excluded.

## Scientific limitations

- NAIP and LiDAR acquisition dates differ; surface changes and vegetation phenology can contribute to error.
- GLO-30 remains an approximately 30 m information product after alignment to the 1 m analytical grid.
- Maximum-return rasterization can retain sparse high returns and leaves cells without accepted points as nodata.
- This is development/training data, not blind-test evidence.
"""


def prepare_site(name: str, config: dict[str, Any], data_root: Path) -> dict[str, Any]:
    root = data_root / config["directory"]
    for directory in ("rgb", "reference", "truth_raw", "derived", "metadata"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    metadata_path = root / "metadata" / "lidar_project_metadata.xml"
    download(config["metadata_url"], metadata_path)
    source_crop, _ = prepare_rgb(config, root)
    reference_crop, vdatum = prepare_reference(config, root)
    raw_truth_descriptor, truth_details = prepare_truth(config, root)
    valid_fraction = prepare_mask(root)
    record = {
        "site": name,
        "county": config["county"],
        "state": config["state"],
        "domain": config["domain"],
        "target_crs": config["target_crs"],
        "bounds": config["bounds"],
        "wgs84_bounds": wgs84_bounds(config),
        "naip_ids": config["naip_ids"],
        "naip_urls": config["naip_urls"],
        "naip_date": config["naip_date"],
        "copernicus_tile": config["copernicus_tile"],
        "copernicus_url": copernicus_url(config["copernicus_tile"]),
        "copernicus_epoch": COPERNICUS_EPOCH,
        "vdatum_responses": vdatum,
        "truth_product": config["lidar_product"],
        "truth_url": truth_primary_url(config),
        "truth_legacy_tile_url": config["lidar_url"],
        "truth": truth_details,
        "valid_fraction": valid_fraction,
        "checksums": {
            "rgb_source_crop": sha256(source_crop),
            "reference_source_crop": sha256(reference_crop),
            "truth_raw_descriptor": sha256(raw_truth_descriptor),
            "rgb_aligned": sha256(root / "derived" / "rgb_aligned.tif"),
            "reference_aligned": sha256(root / "derived" / "reference_aligned.tif"),
            "truth_aligned": sha256(root / "derived" / "truth_aligned.tif"),
        },
    }
    (root / "metadata" / "source_metadata.json").write_text(
        json.dumps(record, indent=2, allow_nan=True) + "\n", encoding="utf-8"
    )
    (root / "metadata" / "PROVENANCE.md").write_text(
        provenance_markdown(config, record), encoding="utf-8"
    )
    print(json.dumps(record, indent=2, allow_nan=True))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("research/geoguard/data"))
    parser.add_argument("sites", nargs="*", choices=sorted(SITES), default=sorted(SITES))
    args = parser.parse_args()
    for name in args.sites:
        prepare_site(name, SITES[name], args.data_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
