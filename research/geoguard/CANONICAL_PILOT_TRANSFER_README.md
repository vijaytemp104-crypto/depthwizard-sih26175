# Canonical four-pilot transfer

Source/transfer root: `C:\Users\shawn_d8kl69k\Documents\depthwizard-sih26175\research\geoguard`.
Copy ONLY the relative paths in CANONICAL_PILOT_FILELIST.txt, preserving their hierarchy under a new geoguard root. Do not independently reconstruct pilots. Raw LAZ/NAIP/GLO30 source tiles, checkpoints and unrelated results are unnecessary.

The JSON lists absolute/repository paths, SHA-256, bytes, Git classification, raster metadata, complete existing source metadata, manifest entries and QA logs. Generated inventory files are not self-hashed.

## Validation

- wake: QA PASS; baseline PASS; MAE 6.799877095577; RMSE 8.935211843611; scoring pixels 962159.
- polk: QA PASS; baseline PASS; MAE 0.487770734920; RMSE 1.387273885975; scoring pixels 991122.
- larimer: QA PASS; baseline PASS; MAE 2.556608823500; RMSE 3.432679150119; scoring pixels 960982.
- humboldt: QA PASS; baseline PASS; MAE 7.685916235951; RMSE 9.850414236787; scoring pixels 982686.

## Masks and scientific provenance

valid_mask.tif is a truth/scoring intersection mask, not an inference-only mask. V1 computes input validity from RGB/reference/DAV2 alone in memory; no separate input-mask raster exists. The recomputed V1 scoring intersection equals the reference baseline mask.
Maximum accepted Z per 1 m cell, no interpolation. Wake and the other three pilots have different historical accepted-class policies: Wake excludes class 17/18 overlap classes; the other preparation script accepts class 17 but rejects overlap/withheld flags. Preserve these exact policies, not an invented uniform class list.
Existing provenance supports construction; this task does not re-rasterize raw point clouds to independently re-prove every exclusion.
GLO30 retains effective ~30 m source resolution despite its aligned 1 m grid. Development/training counties are not blind-test data. Temporal/phenology mismatch and unquantified VDatum uncertainty remain. Wake VDatum details are in PROVENANCE.md and raster tags; there is no fabricated Wake source_metadata.json.

## Transfer and execution

Safest: make a selective archive or copy using the filelist from this transfer root; verify every received SHA-256 against the JSON before audit. Do not Git-add large raster assets. No raster duplication was performed here.
Manish can copy the selected folder hierarchy and use the identical evaluation inputs. He still needs his audit code plus a compatible Python/Rasterio/NumPy environment; the data package alone is not a fully standalone audit installation.
Run existing QA per pilot: python qa/check_triplet.py --rgb data/<name>_pilot/derived/rgb_aligned.tif --reference data/<name>_pilot/derived/reference_aligned.tif --truth data/<name>_pilot/derived/truth_aligned.tif
Do not run preparation or baseline.run on canonical folders (the latter writes derived outputs). Baseline verification here called compute_metrics only.

Selected input/support bytes: 43809573; inventory files additional.

NO DATA MODIFICATION / NO REPROJECTION / NO REGENERATION / NO COMMIT / NO PUSH / NO PRODUCTION MODIFICATION.
