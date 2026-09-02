# Great Salt Lake Desert sparse-scene source report

## Scene identity

- Class: sparse/open terrain
- Location: Great Salt Lake Desert, Utah, USA; center approximately 40.7500 N, 113.0000 W
- Area: 1.00 km2
- Analysis CRS: EPSG:32612, WGS 84 / UTM zone 12N
- Projected bounds: 330657.859, 4512429.302, 331657.859, 4513429.302 metres
- Geographic bounds: 113.0060546 W, 40.7453957 N, 112.9939462 W, 40.7546040 N

## RGB source and audit

- File: `rgb.tif`
- Source: USGS The National Map `USGSNAIPImagery` ImageServer; USDA NAIP, public domain
- Locked catalog records: `m_4011209_sw_12_060_20210925`, `m_4011217_nw_12_060_20210925`, `m_4011316_se_12_060_20210925`, and `m_4011324_ne_12_060_20210925`
- Acquisition date: 2021-09-25
- Native catalog resolution: 0.6 m; exported analysis resolution: 1.0 m
- CRS: EPSG:32612
- Affine transform: `[1.0, 0.0, 330657.859, 0.0, -1.0, 4513429.302]`
- Dimensions: 1000 x 1000 pixels, three UInt8 RGB bands
- Nodata: not declared
- Horizontal units: metres
- Service: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
- License/provenance: USGS/USDA public-domain orthoimagery

## Calibration elevation source and audit

- File: `calibration_dem.tif`
- Product: USGS 3DEP bare-earth DEM; locked source `UT_WestEast_B22`, catalog object 37317, tile title `USGS 1 Meter 12 x33y452 UT_WestEast_B22`
- Source collection interval: 2022-06-04 through 2023-10-04; catalog acquisition date 2023-04-10; publication 2024-10-30
- Native product resolution: 1 m; exported calibration grid: 10 m
- CRS: EPSG:32612
- Affine transform: `[10.0, 0.0, 330657.859, 0.0, -10.0, 4513429.302]`
- Dimensions: 100 x 100 pixels, one Float32 band
- Nodata: not declared; all 10,000 exported cells are finite
- Horizontal units: metres
- Vertical units: metres, per 3DEP product/service convention
- Vertical datum: North American Vertical Datum of 1988 (NAVD 88), explicitly reported by the 3DEP catalog. The exported GeoTIFF carries only the horizontal EPSG code, so this datum statement must travel with the file.
- Service: https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer
- License/provenance: USGS 3DEP, public domain

## Pair audit and baseline result

- Shared-bounds overlap: 100.00%
- DEM reprojection: no CRS change; bilinear resampling from the 10 m export grid to the 1 m depth grid was required
- Native reference-cell count: 10,000
- Depth source: real Depth Anything V2 Small inference, cached revision `5426e4f0f36572d16453bbda7a8389317b1bef99`; relative arbitrary units
- Global affine OLS: `elevation = 24.3547251803 * depth + 1340.6152629421`
- Calibration-fit RMSE: 3.054286 m
- Calibration-fit MAE: 2.368567 m
- Calibration-fit R2: 0.699648
- Fit sample count after DEM alignment: 1,000,000 pixels
- QGIS available: NO
- Alternative visual check: YES; programmatic bounds/orientation audit and RGB/DEM/DSM contact-sheet inspection passed

These are in-sample calibration-fit metrics, not independent accuracy metrics. The 3DEP product is a bare-earth DEM, not a surface DSM. RGB and elevation collection dates differ, and the exported DEM does not encode its vertical CRS internally.
