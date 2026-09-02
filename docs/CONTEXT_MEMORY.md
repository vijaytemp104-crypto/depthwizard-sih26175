# DepthWizard Context Memory

Last updated: 2026-09-02
Working repository: `depthwizard-sih26175`
Experimental branch: `ayuTest`

## Continuity note

Some intermediate conversation and implementation history between the original
prototype/Boulder work and the Phase 2 multi-scene pack is missing from this
context record. The sections below preserve the artifacts and results that can
be verified in the workspace, but they should not be read as a complete
turn-by-turn history. Where older notes conflict with newer verified artifacts,
the dated Phase 2 record takes precedence.

## Project objective

DepthWizard converts a single RGB satellite image into relative monocular
depth, calibrates that relative depth against a metric elevation reference,
creates a georeferenced DSM, and exports terrain data for a 3D viewer.

The team responsibilities relevant to this work are:

- Manish: relative monocular-depth inference.
- Ayush: geospatial processing, reference alignment, metric calibration, DSM
  generation, and terrain export.
- Harinandana: validation of calibration and DSM results.
- Shawn: downstream integration and 3D visualization.

## Work completed on `ayuTest`

The complete experimental Ayush pipeline was implemented and pushed to GitHub.

- Commit: `3f122c7`
- Commit message: `Build Ayush depth calibration pipeline prototype`
- Remote branch: `origin/ayuTest`
- Branch was clean and synchronized immediately after the push.

Implemented flow:

```text
relative depth.npy + reference DEM GeoTIFF
                -> validate depth
                -> inspect DEM metadata
                -> align/reproject DEM to depth grid
                -> fit Elevation = a * Depth + b
                -> calibrated DSM GeoTIFF
                -> calibration diagnostics JSON
                -> Three.js-oriented terrain JSON
```

### Ayush implementation files

- `backend/services/ayush/depth.py`
  - Loads a non-pickled `.npy` array.
  - Requires a non-empty, numeric, two-dimensional array.
  - Converts to `float32`.
  - Allows NaN/Inf in the source so they can be masked consistently.
  - Requires at least two finite values.
- `backend/services/ayush/geospatial.py`
  - Reads DEM CRS, affine transform, dimensions, bounds, resolution, and nodata.
  - Requires the DEM to have a declared CRS and at least one band.
  - Converts DEM masks/nodata to NaN internally.
  - Uses Rasterio reprojection with bilinear resampling when CRS, transform,
    dimensions, or resolution differ.
  - Reports whether resampling/reprojection occurred; mismatches are not silently
    ignored.
- `backend/services/ayush/calibration.py`
  - Collects finite depth/elevation pairs.
  - Fits ordinary least squares using `numpy.polyfit`.
  - Uses `Elevation = a * Depth + b`.
  - Reports coefficients, valid-pixel count, RMSE in metres, and R-squared.
  - Rejects mismatched shapes, insufficient pairs, and constant depth.
- `backend/services/ayush/export.py`
  - Writes a compressed Float32 GeoTIFF with nodata `-9999.0`.
  - Preserves the target CRS and affine transform.
  - Reopens and verifies the DSM after writing.
  - Writes strict JSON without NaN; invalid elevations become JSON `null`.
- `backend/services/ayush/pipeline.py`
  - Provides `run_pipeline(depth_path, dem_path, output_dir)`.
  - Provides the command-line entry point.
  - Writes `calibration.json`, `calibrated_dsm.tif`, and `terrain.json`.
- `backend/services/ayush/sample_data.py`
  - Generates deterministic synthetic depth and reference DEM fixtures.
  - Deliberately uses a coarser DEM than the depth grid to test alignment.
- `tests/test_ayush_pipeline.py`
  - Tests linear coefficient recovery.
  - Tests DEM loading and metadata.
  - Tests dimension/resolution and CRS alignment paths.
  - Tests reopenable DSM and valid JSON creation.
  - Tests invalid values and invalid shapes.
- `contracts/README.md`
  - Documents Manish-to-Ayush, Ayush-to-Harinandana, and Ayush-to-Shawn
    artifact boundaries.
- `README.md`
  - Contains installation, execution, input contracts, and limitations.
- `pytest.ini`
  - Adds the repository root to the pytest import path.

Runtime dependencies are recorded in `requirements.txt`:

```text
numpy>=1.24,<3
rasterio>=1.3,<2
pytest>=7,<9
```

## Synthetic data and sample results

Real Manish inference and real SRTM data were not available while building the
prototype. Reproducible synthetic files were therefore generated locally:

- `sample_data/input/sample_depth.npy`
  - Placeholder for Manish's relative-depth output.
- `sample_data/reference/sample_dem.tif`
  - Placeholder for a real SRTM/DEM elevation reference.
- `sample_data/mock_outputs/calibration.json`
- `sample_data/mock_outputs/calibrated_dsm.tif`
- `sample_data/mock_outputs/terrain.json`

Generated binary/sample output files are intentionally ignored by Git. They can
always be recreated from the committed generator.

Observed sample calibration result:

```text
a = 115.60893612056064
b = 429.6305272009052
valid pixels = 12,282
RMSE = 0.2405 m
R-squared = 0.999793
```

Observed DSM properties:

```text
width = 128
height = 96
CRS = EPSG:32643
resolution = 10 m x 10 m
nodata = -9999.0
```

The final test run passed:

```text
5 passed
```

Rasterio emitted only internal pending-deprecation warnings about Affine
multiplication. These warnings did not indicate pipeline failures.

## Phase 2 real-data geospatial benchmarking

Phase 2 added a clean real multi-scene calibration pack without changing the
production calibration method or contracts. Boulder remains useful as an
urban/mixed development scene, but it is excluded from final withheld
validation because it was already used for calibration diagnostics.

The Phase 2 pack is under `sample_data/phase2_real/` and contains three new
1 km2 scenes:

| Scene | Class | RGB | Calibration elevation | Fit RMSE | Fit MAE | Fit R2 |
|---|---|---|---|---:|---:|---:|
| Great Salt Lake Desert, Utah | Sparse/open | USDA NAIP, 2021-09-25 | USGS 3DEP `UT_WestEast_B22` | 3.054286 m | 2.368567 m | 0.699648 |
| Badlands, South Dakota | Hilly | USDA NAIP, 2022-07-13 | USGS 3DEP `SD_Southwest_NRCS_SD_2018_D18` | 14.173216 m | 9.404299 m | 0.423857 |
| Olympic Peninsula, Washington | Forested | USDA NAIP, 2017-08-22 | USGS 3DEP 1/3 arc-second `n48w124` | 121.107972 m | 97.929283 m | 0.091771 |

All three RGB/DEM pairs have 100% shared-bounds overlap. RGB was analyzed on a
1 m grid. Each calibration DEM was exported on a 10 m grid with 10,000 finite
reference cells, then bilinearly resampled to the 1 m relative-depth grid by the
existing pipeline. No horizontal CRS change was required within a scene.

The relative-depth inputs are real Depth Anything V2 Small outputs generated
from the real RGB imagery with cached model revision
`5426e4f0f36572d16453bbda7a8389317b1bef99`. The unchanged global affine OLS
baseline was run as `elevation = a * depth + b`:

```text
Sparse: a = 24.3547251803, b = 1340.6152629421
Hilly:  a = 44.4615742899, b = 723.3093218457
Forest: a = -138.3768679387, b = 1623.4904678890
```

These RMSE, MAE, and R2 values are in-sample calibration-fit diagnostics, not
independent accuracy metrics. The particularly weak forest result is retained
honestly. A bare-earth DEM is not a surface DSM, and dense canopy/image texture
does not directly represent bare-earth elevation.

### Phase 2 datum and provenance safety

- NAIP and 3DEP inputs were acquired from public USGS services and locked to
  explicit catalog records/products for reproducibility.
- The 3DEP catalog reports elevation in metres relative to NAVD88.
- The exported GeoTIFFs contain horizontal EPSG CRSs only; their vertical datum
  is not embedded in the raster CRS and must remain attached as provenance.
- RGB and elevation acquisition dates differ for every scene.
- The Olympic `n48w124` elevation source is a temporally composite seamless
  product, with a broad catalog source interval rather than one flight date.
- No calibration source may be reused as Harinandana's withheld validation
  reference.

### Phase 2 visual and software checks

QGIS was unavailable, so no QGIS screenshots were claimed. Programmatic checks
confirmed north-up transforms, identical scene bounds, matching projected CRSs,
finite DEM cells, and reopenable DSM outputs. RGB/DEM/DSM contact sheets were
also inspected for orientation and category suitability.

The final regression test run after creating the pack was:

```text
5 passed, 6 Rasterio pending-deprecation warnings
```

### Phase 2 handoff files

- `sample_data/phase2_real/FINAL_REPORT_TO_SHAWN.md`
- `sample_data/phase2_real/HANDOFF_TO_HARINANDANA.md`
- `sample_data/phase2_real/sparse/SOURCE_REPORT.md`
- `sample_data/phase2_real/hilly/SOURCE_REPORT.md`
- `sample_data/phase2_real/forest/SOURCE_REPORT.md`

Large GeoTIFFs, NumPy arrays, calibrated DSMs, previews, and terrain JSON files
remain local and ignored. No production code or contracts were changed, and no
Phase 2 files were committed or pushed while this record was updated.

## How to reproduce the Ayush prototype

From the repository root:

```bash
source .venv/bin/activate
python -m backend.services.ayush.sample_data
python -m backend.services.ayush.pipeline \
  --depth sample_data/input/sample_depth.npy \
  --dem sample_data/reference/sample_dem.tif \
  --output sample_data/mock_outputs
pytest -q
```

To use real artifacts later:

```bash
python -m backend.services.ayush.pipeline \
  --depth /path/to/manish_depth.npy \
  --dem /path/to/real_srtm_dem.tif \
  --output /path/to/output_directory
```

## Depth georeferencing contract

A plain `.npy` file does not contain a CRS or affine transform. Ayush therefore
supports an optional sidecar named by appending `.json` to the complete depth
filename. For `depth.npy`, the sidecar is `depth.npy.json`.

Example:

```json
{
  "crs": "EPSG:32643",
  "transform": [500000, 10, 0, 2200000, 0, -10]
}
```

The transform is in GDAL order:

```text
origin_x, pixel_width, x_rotation, origin_y, y_rotation, pixel_height
```

When this sidecar is present, the reference DEM is reprojected to the exact
depth grid. When it is absent, the prototype explicitly assumes the depth array
covers the complete DEM bounds and derives a target transform from those bounds.
That fallback is useful for synthetic testing but is not sufficiently reliable
for final production integration.

## Manish branch inspection

The latest remote Manish branch was fetched and inspected without modifying it.

- Remote branch: `origin/Manish`
- Latest inspected commit: `3536e40`
- Commit message: `Add relative monocular depth adapter`

Manish implemented:

- `backend/services/relative_depth_adapter.py`
- `backend/tests/test_relative_depth_adapter.py`
- Depth Anything V2 Small adapter using Hugging Face Transformers.
- RGB input validation.
- Relative-depth inference restored to original image height and width.
- Strict finite two-dimensional Float32 output validation.
- `write_depth_artifacts(...)`, which writes:
  - `depth.npy`
  - `depth.png`
  - `model_metadata.json`
- Metadata that explicitly states the output is relative, arbitrary-unit,
  non-metric depth and requires downstream calibration.
- Fake-model unit tests and a cache-only real-model smoke test.

### Manish-to-Ayush compatibility

The core contract is already compatible:

```text
Manish write_depth_artifacts(...).depth_npy_path
                         -> Ayush run_pipeline(depth_path=...)
```

Manish's `depth.npy` is a two-dimensional `float32` array, which is exactly what
Ayush loads. `depth.png` is preview-only and must never be used for calibration.
`model_metadata.json` is useful for provenance but is not currently required by
the Ayush numerical pipeline.

Illustrative combined invocation:

```python
from backend.services.relative_depth_adapter import write_depth_artifacts
from backend.services.ayush.pipeline import run_pipeline

depth_result = write_depth_artifacts(
    image="satellite_image.tif",
    output_dir="outputs/depth",
)

terrain_result = run_pipeline(
    depth_path=depth_result.depth_npy_path,
    dem_path="reference/srtm_dem.tif",
    output_dir="outputs/terrain",
)
```

### Remaining Manish/Ayush integration gaps

1. Manish does not currently propagate source-image CRS and affine transform.
   The combined pipeline should create Ayush's `depth.npy.json` sidecar from the
   georeferenced satellite input or adopt one shared metadata schema.
2. Manish's default adapter uses `local_files_only=True`. Real inference works
   only when the model checkpoint is already in the Hugging Face cache unless
   the integration layer changes this behavior deliberately.
3. Manish's tests import `torch`, but his branch does not explicitly list
   `torch` in `requirements.txt`. The merged dependency set should explicitly
   include the selected compatible PyTorch build.
4. A shared orchestration service/route still needs to call Manish first and
   pass his returned `depth_npy_path` plus a real reference DEM to Ayush.
5. The merged requirements must combine Manish's model stack
   (`transformers`, `pillow`, and explicit `torch`) with Ayush's Rasterio,
   NumPy, and pytest requirements.

## Production replacements and limitations

Replace during final integration:

- Synthetic `sample_depth.npy` with Manish's actual `depth.npy`.
- Synthetic `sample_dem.tif` with a real, validated SRTM/DEM/GCP elevation
  reference covering the satellite image footprint.
- Shared-extent fallback with explicit source-image georeferencing.
- Large nested JSON grids with tiles, quantized heightmaps, or binary terrain
  payloads if Shawn's viewer handles large scenes.

Current scientific limitation: one global ordinary-least-squares affine model
is fitted. Production evaluation may require robust regression, outlier
rejection, local/spatial calibration, land-cover-aware logic, uncertainty
reporting, and checks for inverse/disparity orientation. The reference DEM is
used only as a calibration anchor; it is not copied as the DSM result.

## Recommended next steps

This older prototype-era list is retained for history. Items related to running
real scenes have been partially superseded by the Phase 2 pack above.

1. Merge or cherry-pick Manish's adapter into an integration branch.
2. Define one shared metadata schema containing model provenance and raster
   georeferencing, then make both modules consume it.
3. Add an orchestration function and API route for RGB -> depth -> DSM ->
   terrain JSON.
4. Test against one real georeferenced satellite image and matching SRTM tile.
5. Have Harinandana validate alignment, calibration metrics, nodata handling,
   DSM reopening, and known-control-point errors.
6. Have Shawn test the terrain schema, orientation, coordinate conventions, and
   performance in the Three.js viewer.

## Git note

This context-memory file was created after commit `3f122c7`. Unless a later
commit is recorded here, it may still be an uncommitted local change on
`ayuTest`.
