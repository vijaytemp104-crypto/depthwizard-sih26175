# DepthWizard Phase 2 real-scene calibration report

## Scene 1

- NAME: Great Salt Lake Desert
- TYPE: Sparse/open terrain
- LOCATION: Utah, USA; 40.7500 N, 113.0000 W
- RGB SOURCE: USDA NAIP through USGS `USGSNAIPImagery`, locked catalog records listed in `sparse/SOURCE_REPORT.md`
- RGB DATE: 2021-09-25
- CALIBRATION SOURCE: USGS 3DEP bare-earth DEM, `UT_WestEast_B22`
- CALIBRATION DATE: source interval 2022-06-04 to 2023-10-04; catalog acquisition date 2023-04-10
- CRS: EPSG:32612
- RGB RESOLUTION: 1 m export; 0.6 m native catalog imagery
- DEM RESOLUTION: 10 m export from 1 m product
- BOUNDS: 330657.859, 4512429.302, 331657.859, 4513429.302 metres
- OVERLAP: 100.00%
- VERTICAL DATUM: NAVD88, metres; catalog-confirmed but not embedded in exported horizontal-only CRS
- CALIBRATION RMSE: 3.054286 m
- CALIBRATION MAE: 2.368567 m
- CALIBRATION R2: 0.699648
- NATIVE REFERENCE CELLS: 10,000
- REPROJECTION/RESAMPLING: bilinear 10 m to 1 m resampling; no CRS change
- QGIS: NO; QGIS unavailable. Programmatic and contact-sheet checks passed.
- KNOWN LIMITATIONS: in-sample fit only; bare-earth reference is not a DSM; RGB/DEM dates differ; road and drainage appearance influence monocular depth.

## Scene 2

- NAME: Badlands
- TYPE: Hilly/mountainous
- LOCATION: South Dakota, USA; 43.7500 N, 102.5000 W
- RGB SOURCE: USDA NAIP through USGS `USGSNAIPImagery`, locked catalog records listed in `hilly/SOURCE_REPORT.md`
- RGB DATE: 2022-07-13
- CALIBRATION SOURCE: USGS 3DEP bare-earth DEM, `SD_Southwest_NRCS_SD_2018_D18`
- CALIBRATION DATE: source interval 2018-04-22 to 2020-06-12; catalog acquisition date 2020-12-06
- CRS: EPSG:32613
- RGB RESOLUTION: 1 m export; 0.6 m native catalog imagery
- DEM RESOLUTION: 10 m export from 1 m product
- BOUNDS: 700777.861, 4846644.066, 701777.861, 4847644.066 metres
- OVERLAP: 100.00%
- VERTICAL DATUM: NAVD88, metres; catalog-confirmed but not embedded in exported horizontal-only CRS
- CALIBRATION RMSE: 14.173216 m
- CALIBRATION MAE: 9.404299 m
- CALIBRATION R2: 0.423857
- NATIVE REFERENCE CELLS: 10,000
- REPROJECTION/RESAMPLING: bilinear 10 m to 1 m resampling; no CRS change
- QGIS: NO; QGIS unavailable. Programmatic and contact-sheet checks passed.
- KNOWN LIMITATIONS: in-sample fit only; bare-earth reference is not a DSM; RGB/DEM dates differ; strong relief and shadows challenge a single affine fit.

## Scene 3

- NAME: Olympic Peninsula
- TYPE: Forested
- LOCATION: Washington, USA; 47.7500 N, 123.2500 W
- RGB SOURCE: USDA NAIP through USGS `USGSNAIPImagery`, locked catalog records listed in `forest/SOURCE_REPORT.md`
- RGB DATE: 2017-08-22
- CALIBRATION SOURCE: USGS 3DEP 1/3 arc-second bare-earth DEM `n48w124`
- CALIBRATION DATE: composite interval reported as 1943-01-01 to 2021-04-03; catalog acquisition date 2021-03-04
- CRS: EPSG:32610
- RGB RESOLUTION: 1 m native/export
- DEM RESOLUTION: 10 m export from 1/3 arc-second product
- BOUNDS: 480761.209, 5288044.632, 481761.209, 5289044.632 metres
- OVERLAP: 100.00%
- VERTICAL DATUM: NAVD88, metres; catalog-confirmed but not embedded in exported horizontal-only CRS
- CALIBRATION RMSE: 121.107972 m
- CALIBRATION MAE: 97.929283 m
- CALIBRATION R2: 0.091771
- NATIVE REFERENCE CELLS: 10,000
- REPROJECTION/RESAMPLING: bilinear 10 m to 1 m resampling; no CRS change
- QGIS: NO; QGIS unavailable. Programmatic and contact-sheet checks passed.
- KNOWN LIMITATIONS: very weak in-sample fit; dense canopy/image texture differs fundamentally from bare-earth elevation; calibration DEM is temporally composite.

All reported RMSE, MAE, and R2 values are calibration-fit diagnostics, not independent accuracy metrics.

## Coverage and readiness

- REAL SCENE COVERAGE — URBAN: Boulder development scene (already used diagnostically; excluded from withheld validation)
- REAL SCENE COVERAGE — SPARSE: Great Salt Lake Desert
- REAL SCENE COVERAGE — HILLY: Badlands
- REAL SCENE COVERAGE — FOREST: Olympic Peninsula
- DATA PROVENANCE COMPLETE: YES, with the forest composite-date limitation and exported vertical-CRS caveat explicitly recorded
- READY FOR HARINANDANA WITHHELD VALIDATION: Great Salt Lake Desert, Badlands, Olympic Peninsula
- PRODUCTION CODE CHANGED: NO

Large GeoTIFF, NumPy, DSM, preview, and terrain artifacts remain local and are not staged. No files were pushed.
