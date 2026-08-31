# DepthWizard — Ayush calibration prototype

Experimental end-to-end geospatial calibration pipeline for the `ayuTest`
branch. It converts Manish's relative-depth contract (`.npy`, a 2-D floating
point array) into a georeferenced metric DSM and a terrain payload for Shawn's
Three.js integration.

## Pipeline

```text
relative depth.npy + reference DEM GeoTIFF
                -> align reference to depth grid
                -> linear fit (elevation = a * depth + b)
                -> calibrated_dsm.tif + calibration.json + terrain.json
```

The DEM is an elevation anchor used to learn a mapping; it is not copied to the
output. Invalid depth/DEM pixels are excluded. Output pixels with invalid input
depth are written as nodata.

## Install and run

Python 3.10+ and GDAL-compatible Rasterio wheels are recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate reproducible example depth and DEM data
python -m backend.services.ayush.sample_data

# Run the complete pipeline
python -m backend.services.ayush.pipeline \
  --depth sample_data/input/sample_depth.npy \
  --dem sample_data/reference/sample_dem.tif \
  --output sample_data/mock_outputs

pytest -q
```

Generated files are `calibrated_dsm.tif`, `calibration.json`, and
`terrain.json`. The terrain JSON contains row-major elevation values; invalid
pixels are JSON `null`, never non-standard `NaN`.

## Input and integration contract

- Depth input: a 2-D numeric NumPy array. NaN/Inf values are treated as
  invalid. At least two distinct, valid samples are required for calibration.
- Reference input: a single-band GeoTIFF with a CRS and affine transform.
- Optional depth sidecar: `<depth filename>.json` (for example,
  `depth.npy.json`) with `crs` and six-value GDAL `transform`. When supplied,
  the DEM is reprojected to this exact depth grid. Without a sidecar, the
  prototype explicitly assumes the depth covers the full DEM bounds and
  derives a transform for the depth dimensions.
- DSM output: Float32 GeoTIFF on the depth grid, preserving its CRS/transform.
- Terrain output: versioned JSON with dimensions, CRS, bounds, transform,
  nodata, and a nested row-major elevation grid.

Production replacement points are deliberately narrow: replace the synthetic
`.npy` with Manish's inference output and the synthetic GeoTIFF with Ayush's
downloaded/validated SRTM (or GCP-derived reference). Harinandana can validate
fit metrics in `calibration.json` and reopen/check the DSM. Shawn can consume
`terrain.json` without knowing how calibration was performed.

## Prototype limitations

- A global affine relationship is fitted; local bias, nonlinear monocular
  depth response, vegetation/building class differences, and outliers may need
  more advanced models in production.
- The synthetic sample uses a projected metre-based CRS. Geographic CRS inputs
  work, but resolution values are then angular units.
- Large rasters produce large JSON files. Production visualization should use
  tiles, quantization, or a binary mesh/height texture.
- A missing depth georeferencing sidecar invokes the documented shared-extent
  assumption; production inference should always emit the sidecar.
