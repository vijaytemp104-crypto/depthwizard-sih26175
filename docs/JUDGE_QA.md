# Judge Q&A

**Why not just use Depth Anything?** It produces useful relative structure, but not georeferenced metric elevation or independent accuracy evidence. ChakraVIEW adds guarded calibration, validation, artifacts, and inspection.

**Why is PNG/JPG not metric?** A monocular image has scale/offset ambiguity and lacks a geospatial grid. Its values are relative arbitrary units.

**Why do you need SRTM/GCP or another reference?** Known elevations anchor relative predictions to metres. The current implementation accepts a co-registered raster; a dedicated GCP workflow is not implemented.

**Calibration versus validation?** Calibration fits output to known elevations. Validation scores the DSM against different, withheld evidence.

**Why is calibration RMSE not final accuracy?** It measures residuals on data used to fit the model and is optimistic for generalization.

**How do you know output is aligned?** The DSM is checked against source CRS, affine transform, dimensions, and orientation. Independent data is resampled to that grid.

**What if nodata exists?** Authoritative DSM nodata is preserved. Validation uses mutually valid pixels. MissionView fills gaps only for rendering and rejects measurements on nodata.

**Why Three.js?** It provides local WebGL terrain, orbit controls, pointer-lock flight, ray picking, and explicit cleanup in React.

**How is height calculated?** Signed elevation difference between two displayed samples; metres only for calibrated metric terrain.

**How is slope calculated?** Vertical difference divided by affine-derived horizontal distance where metric spacing exists, then expressed as ratio, percent, and angle.

**How do you validate?** A distinct reference is aligned with the DSM; combined valid pixels produce RMSE, MAE, correlation, count, and an absolute-error GeoTIFF.

**What are the limitations?** Monocular ambiguity, global linear calibration, reference/datum sensitivity, display-grid measurement resolution, and no real multi-scene benchmark.

**What is novel?** The guarded evidence workflow refuses to relabel relative depth as metric, preserves geospatial metadata/nodata, separates calibration from validation, and links claims to artifacts.

**What is still synthetic?** Committed ProofBench scenes and fallback terrain. They test integration only. No real demo dataset is committed.

**What would you improve next?** Acquire licensed real scenes and withheld references, benchmark terrain classes, add uncertainty evidence, explore robust/spatial calibration, and optimize MissionView loading.
