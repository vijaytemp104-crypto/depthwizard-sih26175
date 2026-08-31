# Ayush pipeline contracts

The executable contract is documented in the repository README and implemented
by `backend.services.ayush.pipeline.run_pipeline`. The boundary artifacts are:

1. Manish -> Ayush: 2-D numeric `depth.npy`, optionally `depth.npy.json` with
   `crs` and a six-number GDAL-order `transform`.
2. Ayush -> Harinandana: `calibration.json` fit diagnostics and a reopenable,
   georeferenced `calibrated_dsm.tif`.
3. Ayush -> Shawn: versioned `terrain.json`, with a nested row-major elevation
   grid and `null` for unavailable elevations.
