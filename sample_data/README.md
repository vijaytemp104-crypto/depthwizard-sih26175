# Demo data convention

No real demo dataset is bundled. **REAL DEMO DATA REQUIRED.** Keep large/private data out of Git and record provenance and permission for every file.

Use this layout:

- `input/demo_rgb.png` — ordinary overhead RGB image for relative-depth demonstration
- `input/demo_geotiff.tif` — legitimate three-band overhead RGB GeoTIFF with CRS and affine transform
- `reference/demo_calibration_dem.tif` — elevation raster used only to fit metric scale/offset
- `validation/demo_validation_reference.tif` — separately sourced or withheld elevation raster used only for independent validation
- `demo/` — optional local copies/shortcuts assembled for rehearsal; do not commit restricted data

The GeoTIFF and references must overlap, use compatible vertical units/datums, and carry provenance. Calibration and validation must not be the same file or identical content. Synthetic fixtures and `mock_outputs/` are not real evidence.
