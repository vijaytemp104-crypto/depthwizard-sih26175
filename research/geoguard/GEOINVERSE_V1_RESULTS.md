# GeoInverse V1 — support-conserving detail injection

Decision: **NO-GO**

## PROTOCOL CORRECTIONS

GeoInverse V0 used the geographically held-out region for checkpoint selection/early stopping and therefore its previously reported fold results are development-validation results rather than untouched geographic test results.
V0 preprocessing allowed truth availability to influence input-validity preprocessing, although truth elevation values were not supplied as model features.
Residual Refiner V1 audit: both issues also occur in residual/train.py and residual/dataset.py. Its numbers are HISTORICAL DEVELOPMENT-VALIDATION RESULTS. Neither historical experiment was retrained or modified.
V0 seed was 20260926. Corrected V1 uses authorized seed 20260924, fixed six epochs, final epoch-6 checkpoint, no validation-based selection, and no held-out scene loading until training completes. The four pilots were already explored in earlier research, so these are corrected per-fold geographic tests, not a newly sealed independent blind benchmark.
Input validity depends only on RGB/reference/DAV2 masks and finite values. Filling, normalization, gradients and inference filtering use input validity. Truth masks control only supervision/scoring. Existing evaluation masks are compared explicitly below.

## Architecture and exact loss

Eight V0 evidence channels; three-level U-Net with GroupNorm/SiLU, base width 24; decoder raw-detail and sigmoid weight heads. No delta_low head. Zero raw-head initialization; initial weight 0.05. DAV2 frozen; no semantic model.
d = raw - LPF(raw); c = weight*d; prediction = reference+c. LPF is differentiable normalized masked Gaussian with 30 m FWHM, sigma 12.738853503184714 m, truncation at ceil(3 sigma_pixels), separable reflect padding. This attenuates low frequencies; it is not an exact zero-coarse-content projection.
L = L_final + 0.50 L_detail + 0.05 L_support + 0.02 L_preserve + 0.01 L_edge.
L_final = masked SmoothL1(prediction,truth,beta=2 m). L_detail = masked SmoothL1(d, residual-LPF(residual),beta=2 m). L_support = mean(abs(LPF(c))) at supervised valid locations, with input-valid filtering support. L_preserve = mean(abs(c)/(1+abs(truth-reference)/1 m)); truth weighting exists only in the training loss. L_edge = mean absolute finite-difference gradient error across valid neighbour pairs, divided by physical pixel spacing (m/m), averaged over X/Y.
Training applies the filter within 256-pixel patches with reflected boundaries. Inference first averages overlapping raw/weight predictions, then filters the full scene using only input validity. This avoids patchwise correction seams but is a documented boundary/context difference.
V0 feature-gradient scaling is retained (per grid step); new reported physical gradient metrics explicitly divide by raster spacing. Low/detail evaluation uses the same scoring support for prediction and truth.

## Fixed configuration and operational criteria

CPU float32; deterministic PyTorch algorithms enabled; Python/NumPy/Torch seeds fixed. Batch 4; patch 256; stride 192; minimum valid patch fraction 0.8; AdamW lr 0.001, weight decay 1e-5; six epochs. Determinism is intended for this software/hardware, not guaranteed bitwise across platforms.
Numerical interpretations were frozen in protocol.json before training: region-equal MAE tolerance 0.0001 m; Polk maximum MAE degradation 5%; Wake/Humboldt minimum gain 0.5%; each region low-frequency MAE increase <=0.01 m; at least two detail-MAE gains >0.0001 m; mean 30 m support oracle gain >=1%. GO requires all six; MARGINAL requires the aggregate/Polk/low-frequency safety criteria but misses usefulness criteria; otherwise NO-GO.

## Per-region standard metrics

| Region | Method | mae | rmse | bias | pearson | spearman |
|---|---|---|---|---|---|---|
| wake | reference | 6.799877 | 8.935212 | -1.421412 | 0.836373 | 0.844576 |
| wake | v1 | 6.832012 | 8.980973 | -1.449523 | 0.834877 | 0.842993 |
| polk | reference | 0.487771 | 1.387274 | -0.029263 | 0.810057 | 0.924748 |
| polk | v1 | 0.702978 | 1.687236 | -0.303437 | 0.750405 | 0.868191 |
| larimer | reference | 2.556609 | 3.432679 | 0.902446 | 0.999090 | 0.999094 |
| larimer | v1 | 2.545540 | 3.449276 | 0.779976 | 0.999063 | 0.999066 |
| humboldt | reference | 7.685916 | 9.850414 | -3.760334 | 0.967542 | 0.963540 |
| humboldt | v1 | 7.800670 | 9.987722 | -3.744405 | 0.966402 | 0.962168 |

## Region-equal metrics

| Method | mae | rmse | bias | pearson | spearman |
|---|---|---|---|---|---|
| reference | 4.382543 | 5.901395 | -1.077141 | 0.903265 | 0.932989 |
| v1 | 4.470300 | 6.026302 | -1.179347 | 0.887687 | 0.918105 |

## Scale-separated metrics

Elevation errors are metres; gradient errors are m/m, not slope-angle errors.
| Region | Method | Low MAE | Low RMSE | Detail MAE | Detail RMSE | Gradient MAE | Gradient RMSE |
|---|---|---|---|---|---|---|---|
| wake | scale_reference | 3.436577 | 4.752305 | 5.104496 | 7.174856 | 3.758278 | 7.409134 |
| wake | scale_v1 | 3.449874 | 4.759944 | 5.135701 | 7.225175 | 3.766352 | 7.412702 |
| polk | scale_reference | 0.354746 | 0.588656 | 0.327145 | 1.168975 | 0.110507 | 0.840520 |
| polk | scale_v1 | 0.494163 | 0.831456 | 0.566963 | 1.338519 | 0.159323 | 0.862738 |
| larimer | scale_reference | 1.239303 | 1.569588 | 1.722464 | 2.921835 | 0.994448 | 2.567134 |
| larimer | scale_v1 | 1.171239 | 1.494725 | 1.797917 | 2.976349 | 1.019992 | 2.572472 |
| humboldt | scale_reference | 4.280572 | 5.171875 | 5.611930 | 7.640062 | 1.782285 | 3.708645 |
| humboldt | scale_v1 | 4.279777 | 5.183795 | 5.723650 | 7.787903 | 1.815164 | 3.729157 |

| Region-equal method | Low MAE | Low RMSE | Detail MAE | Detail RMSE | Gradient MAE | Gradient RMSE |
|---|---|---|---|---|---|---|
| scale_reference | 2.327799 | 3.020606 | 3.191509 | 4.726432 | 1.661380 | 3.631358 |
| scale_v1 | 2.348763 | 3.067480 | 3.306058 | 4.831987 | 1.690208 | 3.644267 |

## Correction drift

| Region | mean | median | std | mean_abs | p95_abs | max_abs | lpf_mean | lpf_mae | lpf_rmse |
|---|---|---|---|---|---|---|---|---|---|
| wake | -0.028111 | -0.005764 | 0.343412 | 0.113634 | 0.387381 | 9.748328 | -0.027611 | 0.054478 | 0.095509 |
| polk | -0.274174 | 0.007448 | 0.934892 | 0.326030 | 2.260600 | 12.728831 | -0.274641 | 0.274858 | 0.467280 |
| larimer | -0.122470 | 0.009815 | 0.647516 | 0.230133 | 1.079489 | 10.887594 | -0.122669 | 0.134508 | 0.209885 |
| humboldt | 0.015929 | -0.007928 | 0.654467 | 0.240368 | 1.301296 | 8.373240 | 0.018101 | 0.095018 | 0.134493 |

V0 Polk mean delta_low was approximately +1.116 m. Compare directly with V1 mean correction and LPF correction above. Weight modulation can still introduce drift; the support penalty does not guarantee exactly zero drift.

## Learned detail injection weight

| Region | mean | median | std | p05 | p95 | benefit_correlation |
|---|---|---|---|---|---|---|
| wake | 0.141360 | 0.105648 | 0.113494 | 0.039665 | 0.355983 | -0.284388 |
| polk | 0.172615 | 0.053160 | 0.250379 | 0.033285 | 0.873202 | -0.755453 |
| larimer | 0.136142 | 0.077714 | 0.144894 | 0.048134 | 0.453206 | 0.065327 |
| humboldt | 0.152403 | 0.075454 | 0.174510 | 0.040965 | 0.563210 | -0.520715 |

These weights are not calibrated confidence.

## NON-DEPLOYABLE TRUTH-AWARE ORACLE

Both pixel oracle and approximately 30 m support-cell oracle are reported. Historical oracle comparisons use support-cell means, not the more optimistic pixel oracle.
| Region | Support MAE | Support RMSE | Accepted % | Gain % | Pixel MAE | Pixel RMSE | Pixel accepted fraction |
|---|---|---|---|---|---|---|---|
| wake | 6.788675 | 8.926631 | 26.839327 | 0.164744 | 6.759977 | 8.903022 | 0.446946 |
| polk | 0.483387 | 1.386316 | 24.451379 | 0.898634 | 0.463581 | 1.372890 | 0.371909 |
| larimer | 2.510522 | 3.405668 | 51.031237 | 1.802662 | 2.451786 | 3.351234 | 0.451013 |
| humboldt | 7.678910 | 9.845972 | 20.280130 | 0.091156 | 7.625972 | 9.806662 | 0.413769 |

Region-equal support-oracle gain: 0.739299%.
## Historical baseline comparison

Affine DAV2 is an historical calibration baseline; Residual V1 and GeoInverse V0 are HISTORICAL DEVELOPMENT-VALIDATION RESULTS, not equivalent corrected geographic test evidence.
| Region | Reference MAE | Affine DAV2 MAE | Residual V1 MAE (historical) | GeoInverse V0 MAE (historical) | GeoInverse V1 MAE |
|---|---|---|---|---|---|
| wake | 6.799877 | 13.491140 | 6.721497 | 6.674737 | 6.832012 |
| polk | 0.487771 | 1.637731 | 0.576141 | 1.404591 | 0.702978 |
| larimer | 2.556609 | 33.276291 | 2.642752 | 2.569142 | 2.545540 |
| humboldt | 7.685916 | 28.564565 | 7.644476 | 7.431604 | 7.800670 |

## Criteria

| Criterion | Result |
|---|---|
| region_equal_mae | FAIL |
| polk | FAIL |
| wake_or_humboldt | FAIL |
| low_frequency | FAIL |
| detail_two_regions | FAIL |
| oracle | FAIL |

## Masks and execution

| Region | Scored pixels | Changed scoring pixels | Training patches | Parameters | Runtime seconds |
|---|---|---|---|---|---|
| wake | 962159 | 0 | 75 | 1085786 | 138.781637 |
| polk | 991122 | 0 | 75 | 1085786 | 141.667282 |
| larimer | 960982 | 0 | 75 | 1085786 | 144.704188 |
| humboldt | 982686 | 0 | 75 | 1085786 | 143.749882 |

## Limitations and next experiment

A 1 m output grid does not establish 1 m effective resolution. GLO-30 is a DSM reference, not truth. LiDAR maximum-Z DSM truth has acquisition/vegetation mismatch and unquantified vertical transformation uncertainty from pilot preparation. No DTM/nDSM claims are made.
This single experiment cannot distinguish inadequate DAV2 evidence, training diversity, predictability, or network capacity. Reference preservation alone is not useful reconstruction evidence.
Observed result: all six criteria fail. Detail MAE and physical gradient MAE worsen in all four regions. Only Larimer total MAE improves, accompanied by improved low-frequency MAE but worse detail error; this does not demonstrate successful image-derived detail reconstruction. Polk mean correction -0.274174 m is smaller in magnitude than V0 delta_low +1.116 m, but remains damaging. The best supported failure is residual coarse drift and harmful detail from this particular soft-constrained reconstruction; model/data insufficiency hypotheses remain unresolved.
Recommended next experiment, not implemented: preregister an ablation applying a differentiable exact zero-mean projection to the FINAL weighted correction in fixed physically defined 30 m support cells, with a no-projection control, fixed six-epoch training and unchanged data. Evaluate boundary artifacts, coarse drift, detail metrics and gradients. This directly tests whether enforcing support conservation after weighting resolves the demonstrated drift; do not tune this variant on the present held-out scores or claim that removing drift guarantees useful detail.

## Repository and verification

Branch research/geoguard-sprint. Existing status: M .gitignore; ?? research/. No historical files modified. New files: geoinverse/geoinverse_v1.py, dataset_v1.py, train_geoinverse_v1.py, report_geoinverse_v1.py; tests/test_geoinverse_v1.py; this report; outputs/geoinverse_v1 protocol/results and per-fold epoch6.pt, training.json, metrics.json and four GeoTIFFs.
NO COMMIT. NO PUSH. NO PRODUCTION MODIFICATIONS. No GeoGuard training, gating, foundation-model downloads, or blind-test county access.

Tests: V1 6 passed; V0 6 passed; Residual V1 8 passed; GeoGuard 25 passed plus 3 subtests. Legacy tests initially hit Windows temporary-directory permissions, then passed using a research-local basetemp. Only existing Rasterio deprecation warnings remained. Python compilation passed.
