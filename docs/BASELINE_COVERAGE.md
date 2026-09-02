# ChakraVIEW Baseline Coverage

Checkpoint 11 freezes the integrated software baseline. Synthetic tests below prove software behavior only; they are not real-world accuracy claims.

| Official requirement | Status | Evidence / limitation |
|---|---|---|
| Single RGB input | IMPLEMENTED | One overhead RGB upload per job. |
| PNG/JPG support | IMPLEMENTED | Real relative monocular depth; no metric claim. |
| GeoTIFF support | IMPLEMENTED | Reads CRS, transform, bounds, resolution and nodata. |
| Relative DSM/depth | IMPLEMENTED | `depth.npy` and preview preserve the input grid. |
| Pretrained monocular depth | IMPLEMENTED | Depth Anything V2 Small from local cache. |
| Metric calibration | IMPLEMENTED — REAL BENCHMARK PENDING | Linear `E = aD + b`; needs legitimate reference evidence. |
| Reference DEM/GCP path | PARTIAL | Reference DEM upload implemented; dedicated GCP workflow is not. |
| GeoTIFF DSM export | IMPLEMENTED | Float32 `calibrated_dsm.tif` preserves the source grid. |
| 3D textured terrain | IMPLEMENTED | MissionView with neutral fallback when texture loading fails. |
| Orbit navigation | IMPLEMENTED | Three.js OrbitControls. |
| First-person navigation | IMPLEMENTED | Pointer-lock fly mode with keyboard movement. |
| Height analysis | IMPLEMENTED | Metric only for calibrated geospatial terrain; otherwise relative units. |
| Slope analysis | IMPLEMENTED | Affine-derived metric run where supported; otherwise viewer-grid units. |
| Independent RMSE | IMPLEMENTED — REAL BENCHMARK PENDING | Requires a separately uploaded reference. |
| Independent MAE | IMPLEMENTED — REAL BENCHMARK PENDING | Synthetic tests are labeled as such. |
| Independent correlation | IMPLEMENTED — REAL BENCHMARK PENDING | Undefined constant-array correlation remains null. |
| Error map | IMPLEMENTED | Float32 absolute-error GeoTIFF on the prediction grid. |
| Unified software flow | IMPLEMENTED | Ingest → depth → calibration → validation → terrain → evidence. |
| Artifact downloads | IMPLEMENTED | Job-scoped allowlist; traversal and missing files return 404. |
| Scientific guardrails | IMPLEMENTED | Relative/metric and calibration/validation distinctions enforced. |
| Urban benchmark | NOT IMPLEMENTED | Synthetic integration scene only; legitimate real data pending. |
| Sparse benchmark | NOT IMPLEMENTED | Synthetic integration scene only; legitimate real data pending. |
| Hilly benchmark | NOT IMPLEMENTED | Synthetic integration scene only; legitimate real data pending. |
| Forest benchmark | NOT IMPLEMENTED | Synthetic integration scene only; legitimate real data pending. |
| TrustMap / confidence | NOT IMPLEMENTED | Deliberately deferred; no confidence values fabricated. |

## Baseline architecture

The canonical stages and API contracts remain unchanged. Evaluation utilities under `backend/evaluation/` and `evaluation/` are intentionally outside the per-job contract.

## Data still required

A scientifically meaningful final metric demo still needs a legitimate overhead RGB GeoTIFF, an appropriate real calibration DEM or surveyed elevation source, and a separate withheld independent validation dataset with documented provenance and compatible coverage.
