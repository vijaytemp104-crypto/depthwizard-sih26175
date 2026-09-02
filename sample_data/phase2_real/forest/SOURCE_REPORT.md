# Olympic Peninsula forest-scene source report

## Scene identity

- Class: forested
- Location: Olympic Peninsula, Washington, USA; center approximately 47.7500 N, 123.2500 W
- Area: 1.00 km2
- Analysis CRS: EPSG:32610, WGS 84 / UTM zone 10N
- Projected bounds: 480761.209, 5288044.632, 481761.209, 5289044.632 metres
- Geographic bounds: 123.2566927 W, 47.7454865 N, 123.2433084 W, 47.7545131 N

## RGB source and audit

- File: `rgb.tif`
- Source: USGS The National Map `USGSNAIPImagery` ImageServer; USDA NAIP, public domain
- Locked catalog records: `m_4712314_se_10_1_20170822`, `m_4712315_sw_10_1_20170822`, `m_4712322_ne_10_1_20170822`, and `m_4712323_nw_10_1_20170822`
- Acquisition date: 2017-08-22
- Native catalog and exported analysis resolution: 1.0 m
- CRS: EPSG:32610
- Affine transform: `[1.0, 0.0, 480761.209, 0.0, -1.0, 5289044.632]`
- Dimensions: 1000 x 1000 pixels, three UInt8 RGB bands
- Nodata: not declared
- Horizontal units: metres
- Service: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
- License/provenance: USGS/USDA public-domain orthoimagery

## Calibration elevation source and audit

- File: `calibration_dem.tif`
- Product: USGS 3DEP 1/3 arc-second bare-earth DEM; locked catalog object 4343, title `USGS 1/3 Arc Second n48w124 20240327`
- Source interval reported by catalog: 1943-01-01 through 2021-04-03; catalog acquisition date 2021-03-04; publication 2024-03-27. The broad start date indicates a composite seamless product, not a single acquisition flight.
- Native product resolution: 1/3 arc-second, approximately 10 m; exported calibration grid: 10 m
- CRS: EPSG:32610
- Affine transform: `[10.0, 0.0, 480761.209, 0.0, -10.0, 5289044.632]`
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
- Global affine OLS: `elevation = -138.3768679387 * depth + 1623.4904678890`
- Calibration-fit RMSE: 121.107972 m
- Calibration-fit MAE: 97.929283 m
- Calibration-fit R2: 0.091771
- Fit sample count after DEM alignment: 1,000,000 pixels
- QGIS available: NO
- Alternative visual check: YES; programmatic bounds/orientation audit and RGB/DEM/DSM contact-sheet inspection passed

These are in-sample calibration-fit metrics, not independent accuracy metrics. The extremely weak fit is retained honestly. Dense canopy and the mismatch between image appearance and bare-earth elevation are major limitations. The elevation source is a temporally composite DEM, and its exported GeoTIFF does not encode the vertical CRS internally.
