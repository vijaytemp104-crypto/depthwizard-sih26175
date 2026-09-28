# GeoInverse V0 results

Negative change denotes improvement. All oracle values are truth-aware and non-deployable.

| Region | Reference MAE | Affine MAE | V1 MAE | GeoInverse MAE | MAE change | Reference RMSE | GeoInverse RMSE | Beneficial cells | Harmful cells | Oracle MAE | Oracle improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| wake | 6.799877 | 13.491140 | 6.721497 | 6.674737 | -1.840% | 8.935212 | 8.844137 | 73.053% | 26.947% | 6.628930 | 2.514% |
| polk | 0.487771 | 1.637731 | 0.576141 | 1.404591 | 187.961% | 1.387274 | 1.809021 | 5.882% | 94.118% | 0.476194 | 2.373% |
| larimer | 2.556609 | 33.276291 | 2.642752 | 2.569142 | 0.490% | 3.432679 | 3.559913 | 59.855% | 40.145% | 2.434331 | 4.783% |
| humboldt | 7.685916 | 28.564565 | 7.644476 | 7.431604 | -3.309% | 9.850414 | 9.592911 | 67.112% | 32.888% | 7.351738 | 4.348% |

## Region-equal aggregate

- Reference MAE: 4.382543 m
- Affine DAV2 MAE: 19.242432 m
- Residual V1 MAE: 4.396217 m
- GeoInverse V0 MAE: 4.520018 m (+3.137% from region-equal reference; +45.826% mean fold change)
- Reference RMSE: 5.901395 m
- GeoInverse V0 RMSE: 5.951495 m (+0.849% from region-equal reference; +7.619% mean fold change)
- GeoInverse V0 bias / Pearson / Spearman: -0.460341 m / 0.900424 / 0.925863
- Beneficial / harmful support cells: 51.476% / 48.524%
- Detail-weight mean / correlation with actual benefit: 0.076475 / 0.023245
- Truth-aware oracle MAE improvement: 3.505%
- Residual V1 truth-aware oracle improvement: 1.087%
- GeoInverse oracle headroom increase over V1: +2.417 percentage points (3.22x)

## Success criteria

- Region-equal MAE improves: FAIL
- Polk is not damaged: FAIL
- At least two regions improve: PASS (2/4)
- Oracle headroom materially exceeds V1: PASS (reporting rule: at least +1 percentage point and 2x; not predeclared before training)
- Overall decision: NO-GO

## Method

- Gaussian decomposition: 30 m FWHM, sigma 12.738854 m, masked normalized convolution.
- Reconstruction: `reference + delta_low + weight_detail * delta_high`.
- Semantic inputs are optional but disabled in V0 because no local lightweight semantic checkpoint was available.
- Proxy strata are deployment-available diagnostics, not semantic ground truth or calibrated confidence.
