# Phase 2 handoff to Harinandana

These scenes are ready for independent withheld validation. Do not reuse the listed calibration products, service exports, or overlapping derivatives as validation truth. Independently source a different elevation reference and preserve its vertical datum.

## Great Salt Lake Desert

- Type: sparse/open terrain
- Location: Utah, USA; center 40.7500 N, 113.0000 W
- Bounds in EPSG:32612: 330657.859, 4512429.302, 331657.859, 4513429.302
- Geographic bounds: 113.0060546 W, 40.7453957 N, 112.9939462 W, 40.7546040 N
- RGB: USDA NAIP, acquired 2021-09-25
- Calibration dataset: USGS 3DEP `UT_WestEast_B22`, tile `USGS 1 Meter 12 x33y452 UT_WestEast_B22`, NAVD88 metres; source interval 2022-06-04 to 2023-10-04

## Badlands

- Type: hilly/mountainous
- Location: South Dakota, USA; center 43.7500 N, 102.5000 W
- Bounds in EPSG:32613: 700777.861, 4846644.066, 701777.861, 4847644.066
- Geographic bounds: 102.5063913 W, 43.7453664 N, 102.4936077 W, 43.7546333 N
- RGB: USDA NAIP, acquired 2022-07-13
- Calibration dataset: USGS 3DEP `SD_Southwest_NRCS_SD_2018_D18`, tile `USGS 1 Meter 13 x70y485 SD_Southwest_NRCS_SD_2018_D18`, NAVD88 metres; source interval 2018-04-22 to 2020-06-12

## Olympic Peninsula

- Type: forested
- Location: Washington, USA; center 47.7500 N, 123.2500 W
- Bounds in EPSG:32610: 480761.209, 5288044.632, 481761.209, 5289044.632
- Geographic bounds: 123.2566927 W, 47.7454865 N, 123.2433084 W, 47.7545131 N
- RGB: USDA NAIP, acquired 2017-08-22
- Calibration dataset: USGS 3DEP 1/3 arc-second `n48w124`, publication 2024-03-27, NAVD88 metres; composite source interval reported as 1943-01-01 to 2021-04-03

The calibration-fit RMSE/R2 values in the scene reports are not validation results. A withheld reference must be independent of these 3DEP calibration identities and should ideally include independently surveyed points or a separately governed elevation product with a documented vertical transformation.
