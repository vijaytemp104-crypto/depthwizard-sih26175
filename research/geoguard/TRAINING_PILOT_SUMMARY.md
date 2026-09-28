# GeoGuard training-pilot summary

These four AOIs are development/training pilots. They are not blind-test evidence. `Valid coverage` is the common valid RGB/reference/truth mask fraction used by the baseline evaluator. Copernicus GLO-30 is treated as a coarse DSM reference with an acquisition epoch of 2011–2015, not as independent validation truth.

| Pilot | Domain | RGB date | Truth date/range | Temporal gap | Reference epoch | Valid coverage | Reference MAE (m) | Reference RMSE (m) | Bias (m) | Pearson | Spearman |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Wake, NC | forest | 2014-06-18 | 2014-02-09 | 129 days | 2011–2015 | 96.2159% | 6.799877 | 8.935212 | -1.421412 | 0.836373 | 0.844576 |
| Polk, IA | open/agricultural | 2019-08-22 | 2020-04-19 to 2020-04-20 | 241–242 days | 2011–2015 | 99.1122% | 0.487771 | 1.387274 | -0.029263 | 0.810057 | 0.924748 |
| Larimer, CO | hilly/mountainous | 2021-07-26 | 2021-09-07 to 2021-09-22 | 43–58 days | 2011–2015 | 96.0982% | 2.556609 | 3.432679 | 0.902446 | 0.999090 | 0.999094 |
| Humboldt, CA | forest/high vegetation | 2022-05-31 | 2022-09-11 to 2022-11-03 | 103–156 days | 2011–2015 | 98.2686% | 7.685916 | 9.850414 | -3.760334 | 0.967542 | 0.963540 |

For Larimer and Humboldt, the public EPT transport records GPS time type 0, so a defensible per-tile acquisition day cannot be decoded. The official USGS project collection ranges and corresponding gap ranges are reported instead. Polk has an adjusted-GPS tile date range. Wake values are copied from its existing verified manifest and baseline result; they were not recomputed for this task.
