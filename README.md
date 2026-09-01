# DepthWizard

## Problem

Single overhead images do not directly provide defensible metric terrain. Monocular models infer relative structure, while geospatial alignment, metric calibration, and independent accuracy evidence require additional data.

## What the system does

DepthWizard accepts PNG/JPG imagery or an RGB GeoTIFF, runs Depth Anything V2 Small, and preserves relative output as explicitly non-metric. For a georeferenced GeoTIFF, a compatible elevation reference can fit a metric DSM. A different withheld raster can then independently validate that DSM. The application exposes artifacts, provenance, and an interactive Three.js MissionView.

## Architecture

React/Vite frontend → FastAPI API → relative depth → optional calibration → optional independent validation → terrain/evidence artifacts. See `docs/ARCHITECTURE.md`.

## Features

- Cache-only Depth Anything V2 Small inference during application runs
- PNG/JPG relative depth and RGB GeoTIFF geospatial ingest
- Linear metric calibration with fit diagnostics
- Independent RMSE, MAE, correlation, valid-pixel count, and error map
- GeoTIFF DSM export with source CRS, transform, dimensions, and nodata
- MissionView orbit/fly navigation plus height and slope measurements
- Evidence Passport, explicit stage states, failure recovery, and downloads
- Synthetic ProofBench software-integration harness

## Input modes

- **PNG/JPG:** relative, arbitrary-unit monocular depth only; never metres or elevation.
- **RGB GeoTIFF:** relative depth with source grid metadata. Metric output additionally needs a co-registered calibration reference.
- **Independent validation:** a separate reference raster not reused for calibration.

## Scientific guardrails

Calibration-fit RMSE/R² describe fitted anchors and are not independent accuracy. Validation references must be separate from calibration references. Nodata is preserved in authoritative rasters; MissionView fills isolated gaps only for visual continuity and prevents measuring those samples. Synthetic scenes prove software behavior, not field accuracy.

## Requirements

- Windows with Python 3.12 (tested: 3.12)
- Node.js 20.19+ (Node 22.12+ or newer also satisfies Vite)
- Sufficient RAM/disk for PyTorch and cached model weights; CUDA is optional
- Tested model: `depth-anything/Depth-Anything-V2-Small-hf`

## Installation

From the repository root:

```bat
py -3.12 -m venv .venv312
.venv312\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

## Backend setup

Check the environment without downloading a model:

```bat
python backend\tools\check_environment.py
```

## Frontend setup

The frontend reads `VITE_API_BASE_URL` when set and otherwise uses `http://127.0.0.1:8000`.

## Running the application

Terminal 1, from the repository root:

```bat
python -m uvicorn backend.main:app --reload
```

Terminal 2:

```bat
cd frontend
npm run dev
```

Open `http://localhost:5173/`.

## Offline model setup

Application inference deliberately uses `local_files_only=True`; once cached, it has no model-download requirement. The first cache population may require internet access and acceptance of upstream terms. Populate the Hugging Face cache before the final demo, then run `python backend\tools\check_environment.py`. Model weights and caches are not committed. The application defaults `HF_HOME` to `outputs/.hf_cache`; set `HF_HOME` before startup if using another pre-populated cache.

## Testing

```bat
python -m pytest backend\tests -v
cd frontend
npm run test:analysis
npm run build
```

Cache-only real-model tests skip rather than download when the checkpoint is absent.

## Demo workflow

Use appropriately licensed files named as described in `sample_data/README.md`. Start with `demo_rgb.png`, then demonstrate `demo_geotiff.tif` with `demo_calibration_dem.tif`, and finally add the distinct `demo_validation_reference.tif`. See `docs/DEMO_SCRIPT.md` and `docs/JUDGE_QA.md`.

## Generated artifacts

Job-scoped files are written below ignored `outputs/<job-id>/`, including `depth.npy`, `depth_preview.png`, `model_metadata.json`, optional `calibrated_dsm.tif`, `terrain.json`, `calibration.json`, `metrics.json`, `error_map.tif`, and `evidence_passport.json`.

## Validation

Validation resamples a distinct reference onto the prediction grid and reports metrics only over mutually valid pixels. It never substitutes calibration residuals for held-out accuracy.

## Known limitations

- No licensed real demo or multi-scene benchmark dataset is included.
- Monocular relative depth is ambiguous in scale and offset.
- Calibration is a global linear fit; complex domain/terrain bias may remain.
- GCP workflows, uncertainty/TrustMap, AnchorFusion, GeoRepair, and SceneRouter are not implemented.
- MissionView measurement uses the displayed decimated terrain grid, not sub-pixel samples.
- Three.js currently contributes a large frontend bundle and is not lazy-loaded.

## Repository structure

- `backend/` — API, inference, calibration, validation, evidence, evaluation, and tests
- `frontend/` — React/Vite UI and MissionView
- `contracts/` — canonical pipeline contracts
- `evaluation/` — synthetic ProofBench manifest and summary
- `sample_data/` — naming convention/placeholders; no real data bundled
- `docs/` — architecture, coverage, demo, Q&A, and recovery guidance

## Team/module ownership

Ownership follows repository modules: frontend/MissionView, backend/API and orchestration, depth/model integration, geospatial calibration/export, independent validation, and evaluation/documentation. Record named owners in the team tracker rather than inventing attribution here.

## License and data note

This repository does not grant rights to external imagery, DEMs, or model weights. Depth Anything V2 Small provenance is recorded from its upstream Hugging Face checkpoint (Apache-2.0 metadata). Every real demo/benchmark scene must record source, license/permission, acquisition date, and separation of calibration and validation references. Do not treat SRTM, third-party DEMs, or imagery as project-owned data.
