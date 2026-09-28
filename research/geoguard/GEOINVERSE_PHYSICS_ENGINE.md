# GeoInverse Physics Engine — first research prototype

Implemented under `research/geoguard/geoinverse_physics/`. This is physical constraint machinery, not a neural refiner. No foundation-model selection or download took place.

## Motivation and formulation

Foundation AI proposes. Physics constrains. Geodesy anchors.

An elevation hypothesis can be assessed against independent observations rather than assuming plausible-looking geometry is correct:

`Z* = argmin_Z [λF LF + λA LA + λS LS + λG LG + λR LR]`.

Z is a surface in metres on a known projected coordinate grid. F is a foundation prior, A sparse geodetic anchors, S observed shadows, G a geodetic reference, and R optional regularization. The registry computes this objective; the prototype optimizes only simple synthetic scale/offset parameters, not an arbitrary full raster.

Loss terms have different units. Weights must carry reciprocal units or explicit normalizations. Demo weights (anchor 1, shadow 10; other terms disabled) are synthetic illustrative choices, not tuned or validated operational settings. A low objective is not calibrated confidence.

## Sparse anchors

`Anchor` accepts either floating row/column centre coordinates or projected x/y with an affine raster transform, elevation, positive uncertainty (default 1 m), and source text. The coordinate conversion subtracts half a pixel because affine coordinates index raster corners. Bilinear interpolation is used; all nonzero interpolation contributors must be finite and inference-valid. Outside/nodata anchors are skipped and usable counts are reported by fitting. Unknown datum/unit compatibility must be resolved by the caller.

Residual `ri = sample(Z,xi,yi) − hi`. Weights `wi = 1/σi²`. The implemented normalized weighted Huber objective is `LA = Σ wi ρδ(ri) / Σ wi`, δ=1 m. Huber is quadratic for |r|<=δ and linear outside. Normalization makes the reported loss have m² units and avoids an arbitrary dependence on anchor count. Higher-uncertainty anchors contribute less. No specific provider is required.

## Gauge and relief

`Z = G + R`; `decompose_gauge` accepts an explicit caller-supplied masked low-pass operator to define G, then R=Z−G. No new low-frequency information is invented.

`fit_gauge` uses inverse-variance weighted Huber IRLS, up to 50 iterations with parameter tolerance 1e-10. Modes:

- Offset: fit h−Z=b. Corrected Z=Z+b, preserving every elevation difference exactly.
- Affine: fit h=aZ+b. This intentionally changes relief amplitude while retaining its spatial pattern; it does not preserve high-frequency amplitudes unchanged.
- Plane: only with `allow_spatial=True`; fit additive b0+brow*row/height+bcol*col/width. This is a normalized spatial plane, not a high-order learned field. Insufficient/rank-deficient anchor designs are rejected.

Deployable fitting uses only declared anchors/reference evidence. The synthetic fixture provides known controls for testing; no real pilot/test truth was fitted.

## Geometric sun occlusion

Sun azimuth is clockwise from grid north: 0 north, 90 east. Sun elevation is above the horizon in (0,90] degrees. A north-up, projected metre grid is required. Sun metadata measured relative to true north must be converted to grid azimuth externally (meridian convergence); the engine does not silently perform this conversion.

For each receiving cell, march toward the sun. A sampled terrain cell blocks the ray if `Zblocker > Zreceiver + distance*tan(sun_elevation)`. Coordinates advance in half-minimum-pixel physical steps; repeated nearest-grid offsets are skipped. Actual offset distance uses both pixel spacings. At zenith no terrain shadow is returned.

This nearest-cell discrete horizon approximation is resolution-limited, not an exact continuous triangular-surface ray tracer. The algorithm costs roughly O(number of pixels × ray offsets); demonstrated on 48×48, not benchmarked for kilometre-scale grids. Rotated/geographic grids must be reprojected first. The supplied transform has no CRS, so the caller must certify metre units.

The renderer returns `shadow`, `known`, and `domain_edge_assumption`. A nodata sample makes an otherwise visible ray unknown; a known occluder proves shadow even if another sample is missing. Outside the domain, no additional blocker is assumed. Real imagery requires a surrounding terrain halo to assess that assumption. The geometry omits atmospheres, radiative transfer, penumbra, diffuse light, clouds, albedo, vegetation translucency, and building overhangs.

## Observed shadow consistency

`LS = mean(|rendered_binary_shadow − observed_probability|)` over known/observed support. Binary and [0,1] probabilities are accepted. Synthetic metrics include IoU, precision, recall, F1 and disagreement. Empty valid support raises a clear error; the registry reports absent evidence gracefully. Empty union has IoU=1, with explicit no-positive conventions in the implementation.

Observed masks are separate evidence. Sun metadata alone does not create an observed shadow mask. Uniform elevation offsets leave geometric shadows unchanged: absolute gauge is not identifiable from shadows alone.

## Constraint registry and degradation

`ConstraintRegistry.objective(Z,valid)` returns total objective and entries with name, evidence availability, units, weight, loss, status and limitations. Available kinds: anchor, shadow, reference, foundation and smoothness. Zero weight disables a constraint. Missing evidence is omitted; no fabricated certainty score is generated. Raster evidence must match candidate shape; geospatial alignment must also be checked by the caller.

States:

- RGB/foundation geometry only: foundation prior, `prior_only`.
- Foundation + sun metadata + independently observed shadow mask: shadow constraint available. Sun without a mask remains missing.
- Foundation + trusted aligned DEM: reference constraint available.
- Foundation + sparse anchors: anchor constraint available.
- All evidence: combined constraints.
- No evidence: `unconstrained`, not a crash.

Smoothness penalizes squared physical gradients (m/m)² and can flatten true structures; it is optional and disabled in the experiment. Reference and foundation losses are masked Huber disagreements, not measured accuracy claims. Registry coefficient comparison is evidence bookkeeping, not Bayesian uncertainty estimation.

## Synthetic experiment and measured results

Deterministic 48×48 terrain, 1 m grid, baseline elevation 100 m, Gaussian hill, ridge, building-like block and near-flat surroundings. Sun azimuth 110°, elevation 20°. Twenty synthetic anchors with uncertainty 0.5 m. Ground-truth observed mask uses the same renderer; this is an internal consistency validation, not independent validation of the renderer's physical fidelity.

| Candidate | Surface MAE m | Anchor loss m² | Shadow disagreement | Combined objective | Shadow IoU |
|---|---:|---:|---:|---:|---:|
| Known terrain | 0 | 0 | 0 | 0 | 1 |
| Uniform +5 m | 5.000000 | 4.500000 | 0 | 4.500000 | 1 |
| Relief ×1.4 | 0.489025 | 0.594367 | 0.033420 | 0.928568 | 0.901408 |
| Ridge-height error | 0.278138 | 0.573000 | 0.072483 | 1.297826 | 0.808266 |
| Local bump | 0.109083 | 0.000073 | 0.056424 | 0.564309 | 0.840881 |

Every perturbed candidate has larger combined loss than the known terrain. Shadows detect all three nonuniform perturbations, but not the global offset. Sparse anchors nearly miss the localized bump; shadows provide complementary information. Loss ordering is not monotonically equivalent to full-raster MAE: ridge damage has a larger objective than scale damage despite lower overall MAE. Evidence coverage determines sensitivity.

Offset recovery: −5 m, maximum error 0. Affine recovery for `1.4*(Z−100)+105`: a≈0.7142857143, b≈25 m, max error 5.68e-14 m. A four-point scale grid with robust anchor offset fitting recovers scale 1/1.4, offset −3.5714285714 m under its parameterization, MAE≈1.17e-16 m. The true inverse scale is included in the finite grid, so this demonstrates parameter search functionality, not difficult blind optimization. No ridge/bump optimizer or differentiable full-surface shadow solver is claimed.

Measured synthetic experiment runtime: approximately 0.07 s in the first run; exact run time is stored in `synthetic_results.json`. No random sampling. Runtime depends on hardware; real-scene throughput remains unmeasured.

## Integration contract for Manish's future model

1. Supply Z0 plus explicit output type (relative depth, metric DSM, DTM or nDSM); never treat arbitrary depth scores as geodetic metres.
2. Provide north-up projected metre CRS, transform, valid mask, elevation units, vertical datum and provenance. Convert model depth to a metric gauge using declared calibration evidence first when needed; document sign/scale ambiguity.
3. Supply aligned reference/anchor evidence with uncertainty and provenance. No withheld evaluation truth enters fitting.
4. Supply image-date sun geometry, grid-north conversion, independently derived observed-shadow mask, its unknown/cloud mask, and a terrain halo.
5. Registry produces constraint losses/availability/limitations for a future Evidence Passport. No production API is changed; no model winner is assumed.

The prototype does not prove a unique Earth surface can be recovered from one image. Shadow geometry has ambiguities and scene mismatch; anchors can be sparse or biased; reference DSM can differ in epoch, datum and effective resolution. A 1 m grid does not establish 1 m recoverable detail.

## Exact next experiment — not implemented

Use one independent real overhead scene with image-date sun metadata, a manually audited shadow mask, surrounding terrain, and separate sparse calibration anchors. Compare an unchanged initial metric surface, anchor-only gauge correction, shadow-only parameter search and combined objective. Fix parameters/weights before evaluating; reserve spatially disjoint LiDAR check points solely for scoring. Report occlusion accuracy and elevation error separately, including shadow-mask error and datum/epoch uncertainty. This validates observation-to-geometry consistency before any full-surface optimization.

## Verification and repository

All 18 focused tests passed in 0.48 seconds: residuals, uncertainty weights, offset/affine recovery, relief preservation, direction/elevation/obstruction/no-shadow behavior, mask metrics, combined objective, missing evidence, nodata, deterministic experiment, georeferenced anchor/transform handling, explicit plane fitting, gauge decomposition and missing sun metadata. Python compilation passed. Only affine multiplication deprecation warnings remained. Latest synthetic run took 0.0595 seconds.

Branch: research/geoguard-sprint. Existing status M .gitignore and ?? research/ preserved. All implementation changes are new files under geoinverse_physics; these two research Markdown reports are outside it as explicitly requested. Production unchanged. NO COMMIT. NO PUSH. NO GEOGUARD/DAV2 TRAINING.
