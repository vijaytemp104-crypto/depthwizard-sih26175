# Residual Refiner V1 results

Development-only leave-one-region-out evaluation. Negative percentage change denotes improvement. The oracle uses held-out truth and is non-deployable.

| Region | Reference MAE | Residual MAE | MAE % | Reference RMSE | Residual RMSE | RMSE % | Beneficial Cells % | Harmful Cells % | Oracle MAE | Oracle Improvement % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| wake | 6.799877 | 6.721497 | -1.153% | 8.935212 | 8.891514 | -0.489% | 70.009% | 29.991% | 6.657100 | 2.100% |
| polk | 0.487771 | 0.576141 | 18.117% | 1.387274 | 1.393581 | 0.455% | 12.370% | 87.630% | 0.481364 | 1.313% |
| larimer | 2.556609 | 2.642752 | 3.369% | 3.432679 | 3.486763 | 1.576% | 13.562% | 86.438% | 2.549945 | 0.261% |
| humboldt | 7.685916 | 7.644476 | -0.539% | 9.850414 | 9.802854 | -0.483% | 73.886% | 26.114% | 7.633945 | 0.676% |
| Region-equal mean | 4.382543 | 4.396217 | 4.949% | 5.901395 | 5.893678 | 0.265% | 42.457% | 57.543% | 4.330588 | 1.087% |

## Truth-aware oracle headroom comparison

- wake: residual oracle 2.100% MAE improvement; affine DAV2 oracle 8.576%.
- polk: residual oracle 1.313% MAE improvement; affine DAV2 oracle 5.106%.
- larimer: residual oracle 0.261% MAE improvement; affine DAV2 oracle 0.420%.
- humboldt: residual oracle 0.676% MAE improvement; affine DAV2 oracle 3.684%.
- Region-equal mean: residual oracle 1.087%; affine DAV2 oracle 4.446%.

## Fixed method

- Input channels: RGB (3), coarse reference elevation (1), frozen DAV2 relative depth (1), and coarse-reference x/y gradients (2).
- Output: one metric residual channel; `candidate = reference + residual_m`.
- Target: `truth - reference` in metres without target normalization.
- Frozen DAV2 was not fine-tuned.
- Early stopping used only the geographically held-out development region specified by each fold.
- These development results do not establish generalization and do not use any blind-test county.
