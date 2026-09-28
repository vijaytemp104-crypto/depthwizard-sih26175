# GeoInverse V1A support-projection diagnostic

Answer: **NO**

## Method

No training. Existing V1 applied-correction rasters only. Both controls are constructed before opening truth/scoring masks. Gaussian kernel, truncation and reflect boundaries match V1; NumPy FFT linear convolution with explicit reflect padding is the float64 equivalent, tested against V1. No dependency installed.
Gaussian: C(k+1)=C(k)-masked_LPF(C(k)), sigma=12.738853503184714 m. Stop when inference-valid mean absolute LPF <0.001 m (1 mm, small versus metre-scale errors), maximum 200 iterations. A cap hit is NOT convergence or exact support conservation. Iterated high-pass filtering attenuates signal; it is not an orthogonal projection.
Cells: fixed upper-left raster origin, round(30 m/pixel size) pixels per cell. Subtract each inference-valid cell mean; retain partial boundary cells. This is exact cell-mean conservation, not zero Gaussian LPF. Truth validity can differ, so zero mean over inference support need not imply zero mean over scored pixels.
Scoring uses unchanged V1 support, definitions and approximately 30 m truth-aware support oracle. Float64 projected outputs preserve alignment. Scale metrics retain V1 float32 LPF implementation. Physical gradient errors are m/m.
Decision rule frozen before scoring: YES if either control improves detail MAE >=0.5% in >=3 regions, region-equal total MAE <=reference+0.0001m and mean support oracle gain >=1%; WEAK if not YES but >=2 regions have detail improvement >=0.1% and mean support oracle gain >=0.5%; otherwise NO. Nonconverged Gaussian control cannot qualify.

## Standard metrics

| Region | Variant | mae | rmse | bias | pearson | spearman |
|---|---|---|---|---|---|---|
| wake | reference | 6.799877 | 8.935212 | -1.421412 | 0.836373 | 0.844576 |
| wake | v1 | 6.832012 | 8.980973 | -1.449523 | 0.834877 | 0.842993 |
| wake | gaussian | 6.822402 | 8.967054 | -1.421843 | 0.835201 | 0.843331 |
| wake | cell | 6.828668 | 8.977493 | -1.421944 | 0.834818 | 0.842931 |
| polk | reference | 0.487771 | 1.387274 | -0.029263 | 0.810057 | 0.924748 |
| polk | v1 | 0.702978 | 1.687236 | -0.303437 | 0.750405 | 0.868191 |
| polk | gaussian | 0.605285 | 1.459583 | -0.028818 | 0.792551 | 0.896327 |
| polk | cell | 0.713627 | 1.547876 | -0.029137 | 0.773106 | 0.872597 |
| larimer | reference | 2.556609 | 3.432679 | 0.902446 | 0.999090 | 0.999094 |
| larimer | v1 | 2.545540 | 3.449276 | 0.779976 | 0.999063 | 0.999066 |
| larimer | gaussian | 2.584138 | 3.460788 | 0.902594 | 0.999074 | 0.999078 |
| larimer | cell | 2.601004 | 3.480054 | 0.902262 | 0.999062 | 0.999067 |
| humboldt | reference | 7.685916 | 9.850414 | -3.760334 | 0.967542 | 0.963540 |
| humboldt | v1 | 7.800670 | 9.987722 | -3.744405 | 0.966402 | 0.962168 |
| humboldt | gaussian | 7.749974 | 9.926227 | -3.760632 | 0.966939 | 0.962796 |
| humboldt | cell | 7.787191 | 9.974481 | -3.760509 | 0.966552 | 0.962337 |

## Region-equal

| Variant | mae | rmse | bias | pearson | spearman |
|---|---|---|---|---|---|
| reference | 4.382543 | 5.901395 | -1.077141 | 0.903265 | 0.932989 |
| v1 | 4.470300 | 6.026302 | -1.179347 | 0.887687 | 0.918105 |
| gaussian | 4.440450 | 5.953413 | -1.077175 | 0.898441 | 0.925383 |
| cell | 4.482622 | 5.994976 | -1.077332 | 0.893385 | 0.919233 |

## Scale metrics

| Region | Variant | Low MAE | Low RMSE | Detail MAE | Detail RMSE | Gradient MAE |
|---|---|---|---|---|---|---|
| wake | reference | 3.436577 | 4.752305 | 5.104496 | 7.174856 | 3.758278 |
| wake | v1 | 3.449874 | 4.759944 | 5.135701 | 7.225175 | 3.766352 |
| wake | gaussian | 3.436935 | 4.752633 | 5.129874 | 7.213815 | 3.765872 |
| wake | cell | 3.437057 | 4.752737 | 5.136029 | 7.224258 | 3.766596 |
| polk | reference | 0.354746 | 0.588656 | 0.327145 | 1.168975 | 0.110507 |
| polk | v1 | 0.494163 | 0.831456 | 0.566963 | 1.338519 | 0.159323 |
| polk | gaussian | 0.354753 | 0.588483 | 0.478636 | 1.254023 | 0.162006 |
| polk | cell | 0.374116 | 0.602345 | 0.559477 | 1.329189 | 0.166803 |
| larimer | reference | 1.239303 | 1.569588 | 1.722464 | 2.921835 | 0.994448 |
| larimer | v1 | 1.171239 | 1.494725 | 1.797917 | 2.976349 | 1.019992 |
| larimer | gaussian | 1.239216 | 1.569499 | 1.774700 | 2.954687 | 1.019427 |
| larimer | cell | 1.237389 | 1.566849 | 1.797426 | 2.975754 | 1.022033 |
| humboldt | reference | 4.280572 | 5.171875 | 5.611930 | 7.640062 | 1.782285 |
| humboldt | v1 | 4.279777 | 5.183795 | 5.723650 | 7.787903 | 1.815164 |
| humboldt | gaussian | 4.280623 | 5.171943 | 5.684027 | 7.736828 | 1.813159 |
| humboldt | cell | 4.282125 | 5.175902 | 5.719729 | 7.783094 | 1.815746 |

## Drift (scoring pixels unless explicitly input-cell)

| Region | Variant | mean | median | std | mean_abs | p95_abs | max_abs | lpf_mean | lpf_mae | lpf_rmse | max_abs_input_cell_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| wake | v1 | -0.028111 | -0.005764 | 0.343412 | 0.113634 | 0.387381 | 9.748328 | -0.027611 | 0.054478 | 0.095509 | 1.664901 |
| wake | gaussian | -0.000431 | 0.000033 | 0.275791 | 0.107361 | 0.367994 | 6.503743 | -0.000002 | 0.001011 | 0.001912 | 0.472007 |
| wake | cell | -0.000533 | 0.001952 | 0.322091 | 0.123299 | 0.402970 | 8.418844 | -0.000045 | 0.019332 | 0.033988 | 0.000000 |
| polk | v1 | -0.274174 | 0.007448 | 0.934892 | 0.326030 | 2.260600 | 12.728831 | -0.274641 | 0.274858 | 0.467280 | 3.610496 |
| polk | gaussian | 0.000445 | 0.002157 | 0.510030 | 0.253661 | 1.164719 | 9.367507 | 0.000000 | 0.000988 | 0.001478 | 0.235203 |
| polk | cell | 0.000126 | 0.016973 | 0.803060 | 0.372001 | 1.816462 | 10.937730 | -0.000443 | 0.083903 | 0.140473 | 0.000000 |
| larimer | v1 | -0.122470 | 0.009815 | 0.647516 | 0.230133 | 1.079489 | 10.887594 | -0.122669 | 0.134508 | 0.209885 | 1.573278 |
| larimer | gaussian | 0.000148 | 0.016200 | 0.503481 | 0.236815 | 0.899598 | 9.214297 | -0.000001 | 0.000990 | 0.001446 | 0.322632 |
| larimer | cell | -0.000184 | 0.045855 | 0.610733 | 0.273980 | 0.996689 | 10.227106 | -0.000294 | 0.045822 | 0.071266 | 0.000000 |
| humboldt | v1 | 0.015929 | -0.007928 | 0.654467 | 0.240368 | 1.301296 | 8.373240 | 0.018101 | 0.095018 | 0.134493 | 0.978654 |
| humboldt | gaussian | -0.000298 | -0.013658 | 0.556450 | 0.261622 | 0.998378 | 7.815195 | -0.000002 | 0.000991 | 0.001461 | 0.277122 |
| humboldt | cell | -0.000175 | -0.029329 | 0.631844 | 0.279447 | 1.194918 | 8.316809 | 0.001649 | 0.037674 | 0.056495 | 0.000000 |

## Convergence and masks

| Region | Iterations | Converged | Input LPF MAE m | Scored pixels | Count change |
|---|---|---|---|---|---|
| wake | 23 | True | 0.001000 | 962159 | 0 |
| polk | 75 | True | 0.000988 | 991122 | 0 |
| larimer | 53 | True | 0.000981 | 960982 | 0 |
| humboldt | 49 | True | 0.000991 | 982686 | 0 |

## NON-DEPLOYABLE TRUTH-AWARE ORACLE

| Region | Variant | MAE | RMSE | Accepted fraction | Gain % |
|---|---|---|---|---|---|
| wake | v1 | 6.788675 | 8.926631 | 0.268393 | 0.164744 |
| wake | gaussian | 6.798229 | 8.934414 | 0.182764 | 0.024242 |
| wake | cell | 6.794650 | 8.931899 | 0.253817 | 0.076866 |
| polk | v1 | 0.483387 | 1.386316 | 0.244514 | 0.898634 |
| polk | gaussian | 0.485688 | 1.382864 | 0.176799 | 0.426893 |
| polk | cell | 0.484014 | 1.375440 | 0.186685 | 0.770179 |
| larimer | v1 | 2.510522 | 3.405668 | 0.510312 | 1.802662 |
| larimer | gaussian | 2.547976 | 3.427858 | 0.372982 | 0.337677 |
| larimer | cell | 2.542903 | 3.425647 | 0.336851 | 0.536095 |
| humboldt | v1 | 7.678910 | 9.845972 | 0.202801 | 0.091156 |
| humboldt | gaussian | 7.681893 | 9.848178 | 0.184531 | 0.052351 |
| humboldt | cell | 7.679962 | 9.847688 | 0.186519 | 0.077469 |

## Decision

| Control | Answer | Mean oracle gain % |
|---|---|---|
| gaussian | NO | 0.210291 |
| cell | NO | 0.365152 |

No causal claim that DAV2 alone is inadequate: the diagnosis concerns the saved V1 learned corrections. A Gaussian convergence cap or boundary effects limit any claim of exact Gaussian drift removal. Cell means are exactly conserved on inference-valid cells.
If NO: stop further training iterations of the current frozen DAV2 plus lightweight detail-refiner family. Recommended next experiment: a preregistered foundation geometry signal audit of a stronger aerial/satellite-oriented geometry model, with untouched evaluation geography and separate calibration. Do not implement or download it here.
If YES/WEAK: only the measured detail gains and oracle headroom justify another constrained-refinement experiment; no deployment claim.

## Repository

Branch research/geoguard-sprint. Existing M .gitignore and ?? research/ preserved. New diagnostic script, focused tests, separate V1A output directory and this report. No V1 outputs overwritten. NO TRAINING. NO COMMIT. NO PUSH. NO PRODUCTION MODIFICATIONS.

## Verified outcome

Both controls answer NO. Gaussian convergence was reached in all regions. Cell means are zero to floating-point precision. Nevertheless, both controls worsen total MAE, detail MAE and physical-gradient MAE versus reference in all four regions. Coarse drift therefore does not explain all the damage in the saved V1 signal. This does not prove that every DAV2 representation is incapable of useful geometry.
STOP further training iterations of the current frozen DAV2/lightweight-refiner family. Next: foundation geometry signal audit; not implemented.
Tests: 8 projection tests, 6 V0 tests, 6 V1 tests, 8 Residual V1 tests, and 25 GeoGuard tests passed (53 total, plus 3 subtests). Existing Rasterio deprecation warnings only.
