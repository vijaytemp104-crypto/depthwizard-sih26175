# Badlands hilly-scene source report

## Scene identity

- Class: hilly/mountainous
- Location: Badlands region, South Dakota, USA; center approximately 43.7500 N, 102.5000 W
- Area: 1.00 km2
- Analysis CRS: EPSG:32613, WGS 84 / UTM zone 13N
- Projected bounds: 700777.861, 4846644.066, 701777.861, 4847644.066 metres
- Geographic bounds: 102.5063913 W, 43.7453664 N, 102.4936077 W, 43.7546333 N

## RGB source and audit

- File: `rgb.tif`
- Source: USGS The National Map `USGSNAIPImagery` ImageServer; USDA NAIP, public domain
- Locked catalog records: `m_4310212_se_13_060_20220713`, `m_4310213_sw_13_060_20220713`, `m_4310220_ne_13_060_20220713`, and `m_4310221_nw_13_060_20220713`
- Acquisition date: 2022-07-13
- Native catalog resolution: 0.6 m; exported analysis resolution: 1.0 m
- CRS: EPSG:32613
- Affine transform: `[1.0, 0.0, 700777.861, 0.0, -1.0, 4847644.066]`
- Dimensions: 1000 x 1000 pixels, three UInt8 RGB bands
- Nodata: not declared
- Horizontal units: metres
- Service: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
- License/provenance: USGS/USDA public-domain orthoimagery

## Calibration elevation source and audit

- File: `calibration_dem.tif`
- Product: USGS 3DEP bare-earth DEM; locked source `SD_Southwest_NRCS_SD_2018_D18`, catalog object 76027, tile title `USGS 1 Meter 13 x70y485 SD_Southwest_NRCS_SD_2018_D18`
- Source collection interval: 2018-04-22 through 2020-06-12; catalog acquisition date 2020-12-06; publication 2022-07-26
- Native product resolution: 1 m; exported calibration grid: 10 m
- CRS: EPSG:32613
- Affine transform: `[10.0, 0.0, 700777.861, 0.0, -10.0, 4847644.066]`
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
- Global affine OLS: `elevation = 44.4615742899 * depth + 723.3093218457`
- Calibration-fit RMSE: 14.173216 m
- Calibration-fit MAE: 9.404299 m
- Calibration-fit R2: 0.423857
- Fit sample count after DEM alignment: 1,000,000 pixels
- QGIS available: NO
- Alternative visual check: YES; programmatic bounds/orientation audit and RGB/DEM/DSM contact-sheet inspection passed

These are in-sample calibration-fit metrics, not independent accuracy metrics. The 3DEP product is a bare-earth DEM, not a surface DSM. RGB and elevation collection dates differ, and the exported DEM does not encode its vertical CRS internally.
