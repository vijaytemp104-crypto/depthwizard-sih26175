# DepthWizard real calibration dataset report

## Shawn handoff

SCENE NAME: Boulder Downtown–University 2 km crop

LOCATION: Boulder, Colorado, USA; centre approximately 40.015 N, 105.2705 W

SCENE TYPE: mixed urban / vegetated / foothill-influenced

RGB SOURCE: USGS The National Map `USGSNAIPImagery` ImageServer; source catalog item `m_4010562_se_13_060_20190919`, USDA NAIP, acquired 2019-09-19, native catalog resolution 0.6 m, exported as a 1 m RGB GeoTIFF.

RGB LICENSE/PROVENANCE: USGS/USDA NAIP, public domain. Service credit: `USGS, USDA, The National Map: Orthoimagery. January 09, 2025.`

RGB FILE: `sample_data/real_demo/real_rgb_geotiff.tif`

CALIBRATION DEM SOURCE: USGS The National Map 3D Elevation Program (3DEP) Bare Earth DEM Dynamic ImageServer; service data published through 2026-08-24; exported at 10 m for this calibration experiment.

CALIBRATION DEM LICENSE/PROVENANCE: USGS 3DEP, public domain and available without use restrictions. Service credit: `USGS National Map 3D Elevation Program (3DEP). August 25, 2026.` This is a calibration reference, not independent validation.

CALIBRATION FILE: `sample_data/real_demo/real_calibration_dem.tif`

RGB CRS: EPSG:32613 (WGS 84 / UTM zone 13N)

DEM CRS: EPSG:32613 (WGS 84 / UTM zone 13N)

RGB RESOLUTION: 1 m x 1 m; 2000 x 2000 pixels; three UInt8 RGB bands

DEM RESOLUTION: 10 m x 10 m; 200 x 200 pixels; one Float32 elevation band

RGB BOUNDS: left 475915.239344975, bottom 4428457.112618952, right 477915.239344975, top 4430457.112618952

DEM BOUNDS: left 475915.239344975, bottom 4428457.112618952, right 477915.239344975, top 4430457.112618952

OVERLAP: PASS — exact common bounds; 4,000,000 m²; 100% of RGB footprint

CALIBRATION PIPELINE: PASS — real Depth Anything V2 Small relative depth generated from the NAIP RGB and Ayush pipeline completed against the real 3DEP calibration DEM.

CALIBRATED_DSM: PASS — `calibrated_dsm.tif` reopened as a single-band Float32 GeoTIFF with EPSG:32613, the exact RGB transform/bounds, 1 m resolution, 2000 x 2000 pixels, and nodata -9999.0.

QGIS CHECK: NO — QGIS is not installed in the test environment.

KNOWN LIMITATIONS:

- The global ordinary-least-squares fit is weak: RMSE 13.8644 m and R-squared 0.09227 across 4,000,000 pixels. Pipeline execution passed, but this output is not accurate enough for a defensible metric-elevation claim.
- The 3DEP product is a bare-earth DEM, whereas an urban monocular-depth image can respond to roofs, trees, shadows, and image appearance. It is not a building-surface truth DSM.
- The NAIP acquisition is from 2019, while the seamless 3DEP service contains elevation sources published through 2026-08-24; source acquisition times may differ.
- The ImageServer RGB export was resampled from the catalog item's 0.6 m native resolution to a 1 m analysis grid. The 3DEP service was exported at 10 m and bilinearly aligned to the 1 m depth grid.
- No independent validation was performed. Harinandana must use a distinct withheld elevation reference.
- QGIS visual inspection remains outstanding.

CALIBRATION RESULT:

- Model: elevation = a * depth + b
- a: -20.09222787124832
- b: 1654.4049154429756
- valid pixels: 4,000,000
- fit RMSE: 13.864442820901756 m
- fit R-squared: 0.09227471626482786

DOWNLOAD LINKS / SOURCE LINKS:

- NAIP service: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
- NAIP catalog download record: https://earthexplorer.usgs.gov/download/options/naip/3029705
- 3DEP service: https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer
- USGS NAIP provenance: https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip
- USGS 3DEP provenance: https://www.usgs.gov/3d-elevation-program/about-3dep-products-services

The local GeoTIFFs, model cache, depth artifacts, and calibration outputs are intentionally uncommitted. Repository `.gitignore` excludes `*.tif` and `*.npy`; Shawn approval is required before any large-data publication decision.
