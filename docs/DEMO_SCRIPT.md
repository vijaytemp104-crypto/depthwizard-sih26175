# Judge demo script (2–4 minutes)

1. **Problem (15s):** “A single overhead image gives visual structure, not defensible metric elevation. DepthWizard keeps that boundary visible.”
2. **Relative depth (25s):** Upload `demo_rgb.png`. Show the REAL Depth Anything V2 Small result and its `RELATIVE / NOT METRIC` label. Arbitrary values cannot be read as metres.
3. **Geospatial input (25s):** Upload `demo_geotiff.tif`. Point out preserved CRS, transform, resolution, dimensions, and nodata.
4. **Metric calibration (30s):** Add `demo_calibration_dem.tif`. Show the calibrated DSM and scale/offset. Describe fit RMSE/R² as calibration diagnostics—not final accuracy.
5. **Independent validation (30s):** Add the distinct `demo_validation_reference.tif`. Show RMSE, MAE, correlation, valid-pixel count, and error-map download. State why it was withheld from calibration.
6. **MissionView (35s):** Open terrain, orbit, switch to Fly, then return to Orbit. Measure height and slope. Measurements use source elevations on the displayed grid; vertical exaggeration is visual and nodata cannot be measured.
7. **Evidence (20s):** Show the Evidence Passport: checkpoint, status, source metadata, calibration/validation distinction, warnings, and artifacts. Download the DSM and evidence files.
8. **Close (15s):** “This is a traceable pipeline, not a claim that monocular inference alone is survey-grade. Real multi-scene benchmarking and stronger calibration remain future work.”

Before presenting, cache the model, run the environment check, confirm all four legitimate demo files and provenance notes, start both servers, and rehearse once without network access.
