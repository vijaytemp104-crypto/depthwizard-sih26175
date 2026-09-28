# ChakraVIEW Scout

From Passive Maps to Active Reconnaissance. Isolated offline research prototype on `research/geoguard-sprint`, not production, autonomous disaster command, a safe navigation service or a drone autopilot.

## Files and reproduction

- `scout.py`: evidence fusion, relevance, candidate constraints, 2.5D viewshed, score decomposition, sequential policies and local field evidence update.
- `demo.py`: three deterministic fixtures, two observation modes, four policies, 30 random seeds, result/report/mobile generation.
- `test_scout.py`: algorithm and safety regression tests.
- `test_mobile.cjs`: generated interface JavaScript/control tests using a DOM stub (not visual rendering).
- `mobile_template.html`: offline mobile/tablet concept template.
- `outputs/results.json`: full measured benchmark results, source attribution, top five points, scores, trajectories, maps and timings.
- `outputs/mobile_demo.html`: self-contained generated interface, no server, network or OpenAI dependency.
- `REPORT.md`: generated quantitative results at observations 1, 2, 3 and 5.
- Integration, offline, PPT and field-contract documents alongside this README.

From the repository root, using the already-installed research runtime:

```powershell
& 'research/geoguard/.venv/Scripts/python.exe' 'research/geoguard/residual/run_python.py' -m pytest research/geoguard/chakraview_scout/test_scout.py -q
& 'research/geoguard/.venv/Scripts/python.exe' 'research/geoguard/residual/run_python.py' research/geoguard/chakraview_scout/demo.py
node research/geoguard/chakraview_scout/test_mobile.cjs
```

Portable alternative: install nothing automatically; use an existing Python environment with NumPy (algorithm/demo) and pytest (tests), then run `python demo.py` from this directory. Canonical pilot inputs are not read or changed. Generated outputs are synthetic only.

## Architecture and formulations

All arrays must share one north-up, square-cell grid. Caller supplies known geospatial coordinates and verified metre units for metric use. The prototype does not reproject, infer vertical units or load ambiguous CRS data. Relative mode is explicitly labelled grid units, not metres; physical slopes cannot constrain relative terrain. Coordinates are cell centres, x increases east, y decreases with row index.

1. **Mission uncertainty U:** weighted mean of available, named, finite [0,1] evidence layers: U = sum(w_e E_e) / sum(w_e). No evidence is silently created. Caller must normalize quantities and state the scale; U is an evidence-support index, not a calibrated probability. Missing all sources fails. Optional actual nodata can be supplied as evidence; unknown terrain remains unobservable with this conservative LOS implementation. Demo explicitly sets nodata uncertainty to 1.
2. **Operational relevance R:** same named-layer fusion for supplied response attention, traversability difficulty, corridor/target/staging proximity. Optional change adds `clip(R + w_change C, 0, 1)`. R is NOT disaster severity. Demo uses synthetic corridor and target-distance functions; it does not implement Ayush's response analytics.
3. **Candidates:** deterministic lattice at configurable stride. Both modes require valid terrain. Ground requires supplied reachability and may consume allowed/traversability masks and metric slope threshold; no internal route solver. Aerial candidates have height above the local surface and an optional allowed mask (caller supplies restrictions). No obstacle-safe airspace or vehicle dynamics claims.
4. **Viewshed V_p:** for each candidate, ray from surface + observer height to every valid target cell centre. Sample at <= half-cell Chebyshev intervals, nearest-cell terrain height; sample above the ray blocks it. Unknown intermediate cells conservatively block it. Optional radius is horizontal Euclidean distance. Source/target footprints do not self-occlude endpoints. This is an approximate, finite-grid 2.5D LOS model, not GDAL's exact implementation or a supercover guarantee. No façades, overhangs, lens/FOV, refraction or Earth curvature.
5. **Information gain proxy:** `IG = sum(V U R N) / sum(U0 R)`, N = 1 for cells not yet observed in this run. This is NOT Shannon entropy or a Bayesian expected-information-gain estimate.
6. **Relevance gain:** `RG = sum(V R N) / sum(R)`.
7. **Occlusion gain:** `OG = sum(V U R N (1 - V_initial)) / sum(U0 R)`. Initial visibility is geometry visibility, not an assumed confidence update.
8. **Uncertainty-reduction potential:** `UR = (1-rho) sum(V U) / sum(U0)`. Rho is supplied observation-retention assumption, not empirically fitted sensor accuracy. Denominators stay fixed across a mission; epsilon handles empty masses safely.
9. **Observation cost:** ground = supplied accumulated cost from fixed base at candidate (caller must normalize). Aerial = distance/base-grid diagonal + height/altitude_scale. Cost is dimensionless, interpretable, not battery-optimal. Each step is an independent sortie from a fixed base; cost is summed across sorties, NOT a continuous inter-viewpoint itinerary. Height and altitude_scale use the same units in relative mode.
10. **Objective:** `Score = 1 IG + .15 RG + .30 OG + .20 UR - .15 Cost` by default. Every weight configurable. Correlated gain terms deliberately overlap; ablate and tune on development data only. All raw and weighted terms exported. Deterministic tie breaks use candidate index.
11. **Sequential loop:** score unused points using current U and novelty; choose highest score; simulate `U[V] *= rho` (demo rho=.4); mark visible cells observed; repeat, excluding used points. Repeated coverage can further reduce simulated U but does not count again as unique coverage. This update is an explicit simulation, not a real evidence assimilation claim. Production field updates must use verified evidence footprints/quality.

## Quantitative evaluation

Mountain: ridge, valleys, relief and hidden cells. Urban-like: raised blocks/corridors (not building façades). Mixed: ridge, synthetic response corridor, staging/base and uncertainty patch. All 40x40 at 5 m in local synthetic metric coordinates; each contains a small nodata patch. Candidate stride 6 cells, radius 100 m; ground height 1.7 m, aerial height 25 m. Fixture reachability/cost layers are labelled synthetic, not independently computed safe access.

All strategies use identical candidates, viewsheds, uncertainty, relevance, retention and fixed-base cost. Random runs 30 seeds 0–29; an additional seed42 trajectory is explicitly labelled for display. Nearest uses planar distance to fixed base, highest uses observer elevation. Scout may lose on some metrics/settings; do not infer guaranteed dominance. Read REPORT.md/results.json for exact coverage, reduction, cost and runtime per scenario, mode and observation count. Runtime includes precomputation and ranking separately, is machine-specific, and is not a mobile-device benchmark.

Unique uncertainty coverage = sum(U0 * union visibility) / sum(U0). Operational weighted coverage = sum(U0 R * union visibility) / sum(U0 R). Remaining = sum(U_t)/sum(U0); reduction = sum(U0-U_t)/sum(U0). These are distinct metrics; they are not disaster severity, mission confidence, recovered height accuracy or calibrated posterior uncertainty. Invalid cells remain in the uncertainty denominator and cannot be claimed observed.

## Research inspiration

The innovation claim is application-level integration of established next-best-view/active perception and terrain visibility into evidence-constrained response prioritization, not invention of NBV. Primary sources:

- Bircher et al., *Receding Horizon “Next–Best–View” Planner for 3D Exploration* (2016), [author repository](https://github.com/ethz-asl/nbvplanner). Scout is a simpler greedy raster proxy, not a reproduction of their 3D planner.
- [GDAL viewshed documentation](https://gdal.org/en/stable/programs/gdal_raster_viewshed.html) for established terrain viewshed context. Scout's LOS kernel is independently implemented and approximate.

## Exact future real-world validation

Before accessing held-out measurements, preregister a protocol on at least three independent, noncanonical sites representing mountainous, built-up and mixed environments. Freeze AOIs, verified vertical/horizontal units, input terrain/response layers, access masks, sensor range/FOV/no-fly restrictions, candidate grid, weights, retention model and comparator definitions using development sites only. Keep audit truth inaccessible to planning. Have a supervised ground team/drone operator gather one observation at each nominated viewpoint using equal time/budget and safety approvals; randomize strategy/site order and compare independent campaigns to avoid sharing newly collected evidence between policies. Use a reference LiDAR/photogrammetry surface withheld from selection plus adjudicated visibility/access observations solely for evaluation. Measure actual newly verified high-relevance area, calibration of evidence reduction, terrain error before/after, visibility precision/recall, observation time, failed/inaccessible recommendations and operator agreement after 1/3/5 observations. Report paired site-level intervals and random seeds, not cell-independent confidence intervals; do not tune on withheld outcomes. First validate LOS against surveyed targets and a trusted viewshed implementation. Operational safety decisions remain human-controlled.

## Limitations and deliverable status

Prototype implemented and synthetic-tested; no field validation. Finite-grid LOS can miss thin/corner obstacles; uncertain terrain can distort viewsheds. No sensor likelihood, camera footprint, safety-route proof, semantic disaster labels, autonomous control or mobile deployment. Candidate density, scale normalization and weights influence outcomes. No production UI/API changes. GeoInverse/Response Intelligence integration is a documented array contract, not a live connection. Mobile interface is an offline concept: working scenario/step controls and local note queue, not an installed responder app; terrain view is 2D and navigation is informational only.

NO PRODUCTION MODIFICATION / NO FOUNDATION MODEL TRAINING / NO GEOINVERSE MODIFICATION / NO CANONICAL DATA MODIFICATION / NO COMMIT / NO PUSH.
