# ProofBench scene manifest

The committed manifest is **synthetic software-integration evidence only**. Its numbers are not field accuracy or real benchmark claims.

To add a real `urban`, `sparse`, `hilly`, or `forest` scene, create a licensed scene record with:

- `scene_id`: stable unique identifier
- `scene_type`: `urban`, `sparse`, `hilly`, or `forest`
- `synthetic_or_real`: `real`
- `input_rgb_geotiff`: provenance-tracked overhead RGB GeoTIFF
- `calibration_reference`: reference used for fitting
- `validation_reference`: distinct withheld reference used for scoring
- `reference_type`: dataset/sensor/survey description
- `expected_mode`: `metric_independent_validation`
- `provenance`: source, acquisition date, permission/license, CRS, horizontal/vertical datum, resolution
- `notes`: coverage, nodata, preprocessing, and limitations

Verify calibration and validation are neither the same path nor identical content, datums are compatible, and metrics use valid overlapping pixels. Generate summaries from completed result records; never hand-author favorable values.
