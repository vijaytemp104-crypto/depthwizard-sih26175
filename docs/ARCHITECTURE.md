# DepthWizard architecture

## End-to-end flow

Input → Depth → Calibration → Validation → Terrain → Evidence → MissionView

## Components

- **Frontend:** React/Vite upload workflow, stage cards, diagnostics, downloads, error recovery, and MissionView.
- **Backend:** FastAPI creates jobs, stores uploads in job-scoped directories, executes stages, exposes results, and allowlists artifacts.
- **Depth:** Depth Anything V2 Small loads from cache with `local_files_only=True`; output is relative H×W data plus provenance.
- **Calibration:** A georeferenced RGB GeoTIFF and elevation reference fit `E = aD + b` over aligned valid samples and export a Float32 DSM.
- **Validation:** A distinct reference aligns to the DSM. Mutually valid samples produce RMSE, MAE, correlation, count, and error raster.
- **Terrain:** `terrain.json` carries a decimated row-major elevation grid, affine transform, units, CRS, and nodata as JSON null. MissionView uses nearest-valid fill only to render gaps.
- **Evidence:** `evidence_passport.json` and result metadata record checkpoint, input, stages, labels, references, diagnostics, validation, and artifacts.
- **Evaluation:** ProofBench aggregates explicitly synthetic integration scenes. Real benchmarks remain pending.

## Artifact flow

1. Uploads go to `outputs/<job-id>/input/`.
2. Depth writes `depth.npy`, `depth_preview.png`, and `model_metadata.json` at input resolution.
3. Calibration writes `calibrated_dsm.tif`, `calibration.json`, and `terrain.json`; without calibration, a clearly synthetic placeholder remains.
4. Validation writes `metrics.json` and `error_map.tif` only with a separate reference and calibrated DSM.
5. Evidence writes `evidence_passport.json`; the API links allowlisted, job-owned files.
6. The frontend consumes results and renders terrain locally with Three.js.

## Guardrails and failure boundaries

PNG/JPG remains relative. Metric calibration requires georeferencing and reference evidence. Identical calibration/validation artifacts are rejected. Raster CRS, transform, shape, dtype, and finite-pixel requirements are verified. Stage failures are explicit and surviving artifacts remain available. Canonical contracts define the API boundary and are unchanged by evaluation/documentation.
