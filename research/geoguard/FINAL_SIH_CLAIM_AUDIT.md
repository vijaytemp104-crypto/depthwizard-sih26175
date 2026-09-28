# ChakraVIEW: final SIH claim audit

**Revision note, 28 September:** Scientific exclusions here remain in force. For the latest template-aligned copy, section mapping and its claim boundaries, use `FINAL_SIH_TEMPLATE_ALIGNED_REVISION.md`. This table originally audited the 27 September draft, not a rendered revised deck.

Audited 27 September 2026 against current implementation, existing research reports, recorded outputs and primary literature. Applies to the six-slide copy in `FINAL_SIH_6_SLIDE_COPY.md`, not an unseen/rendered PPTX. The latest emphasis is research innovation, with the original height/flythrough task central.

YES authorizes the **safe wording with its attached status and qualification**, not the risky wording. NO prohibits the unqualified claim. For a desired capability without evidence, use PROPOSED / FUTURE instead. No external paper accuracy becomes ChakraVIEW accuracy.

## Evidence key

- **I1:** `README.md`, production paths and limitations; `backend/services/depth_pipeline.py`, geospatial/reference metadata and artifact generation.
- **I2:** `frontend/src/relativeTerrain.js`, actual relative depth decoding with no metric conversion; `frontend/src/components/MissionViewAnalysis.jsx`, textured heightfield, Orbit/Fly, height/slope tools.
- **I3:** `backend/services/depth_pipeline.py`, distinct calibration/validation reference guards and evidence outputs. Same-path/content rejection does not alone prove statistical independence.
- **R1:** `GEOINVERSE_PHYSICS_ENGINE.md`, `GEOINVERSE_PHYSICS_PPT_NOTES.md`, `geoinverse_physics/synthetic_results.json`, controlled constraint prototype and recorded 18 tests.
- **R2:** `GEOINVERSE_V0_RESULTS.md`, `GEOINVERSE_V1_RESULTS.md`, `GEOINVERSE_V1A_SUPPORT_PROJECTION.md`, negative research results and protocol corrections.
- **D1:** `CANONICAL_PILOT_TRANSFER_MANIFEST.json`, four developmental geographies, reference/truth provenance and baseline metrics.
- **S1:** `chakraview_scout/VALIDATION.md`, `chakraview_scout/outputs/results.json`, isolated synthetic next-observation prototype, not real field validation.
- **P1:** `PPT_INNOVATION_RESEARCH.md`, `PPT_CLAIM_BANK.md` and primary references in slide 6. Papers inform direction; no adoption/performance claim established.

## Claim audit table

| Claim | Slide | Status | Evidence | Safe wording | Risky wording | Allowed in final PPT? YES/NO |
| --- | --- | --- | --- | --- | --- | --- |
| Single-image height/terrain and flythrough workflow | 1, 3, 5 | IMPLEMENTED | I1, I2 | One overhead RGB image gives relative geometry, with compatible-reference calibration when available. | One RGB image uniquely recovers the real Earth surface. | YES |
| Single image contains all evidence | 2, 3 | Unsupported | I1, R1 | One image plus available sun metadata and supporting elevation evidence. | All sun/camera/elevation evidence comes from RGB pixels. | NO |
| AI geometry | 1-3 | IMPLEMENTED | I1 | Pretrained DAV2 Small supplies an initial relative-geometry hypothesis. | Our new satellite foundation model currently supplies production heights. | YES |
| High precision | All | Unsupported | R2, D1 | Report scene-specific independently scored error where available. | High-precision, centimetre-level or survey-grade reconstruction. | NO |
| Relative rDSM | 3 | IMPLEMENTED, display meaning only | I2 | Relative display surface, arbitrary units. | Exported metric/georeferenced rDSM from PNG/JPG. | YES |
| Metric DSM export | 3, 4 | IMPLEMENTED | I1 | Reference-anchored affine-calibrated DSM, explicit verified units and recorded datum information/uncertainty. | GeoTIFF automatically yields accurate metres. | YES |
| Absolute DSM without reference/datum qualification | 3 | Unsupported as an unconditional claim | I1 | Reference-anchored DSM with compatible controls and declared vertical reference. | Absolute DSM from one unreferenced image, regardless of datum. | NO |
| Projected CRS establishes metres | 3 | Unsupported | I1 | Verify horizontal units separately from vertical units. | Any projected CRS uses metres. | NO |
| Datum compatibility always established | 3 | Unsupported | I1 | Record datum compatibility or missing metadata/uncertainty. | Verified metre units prove the height datum matches. | NO |
| Current satellite-native foundation model | 2, 6 | IN RESEARCH | P1, I1 | We are investigating satellite-aware geometry. | GeoRay/Sat3DGen is already our production geometry model. | NO |
| Satellite-aware geometry direction | 2, 6 | IN RESEARCH | P1 | Respect orbital imaging geometry; integration remains under research. | Completed satellite-native replacement with verified accuracy. | YES |
| Shadow forward rendering/check | 2-4, 6 | SYNTHETICALLY PROTOTYPED | R1 | Compare predicted and observed shadows in a controlled shared-renderer fixture. | Real satellite shadows validate our final DSM. | YES |
| Shadow validated on real imagery | 2, 4 | IN RESEARCH, not demonstrated | R1 | Real-image shadow validation is pending. | Satellite-field shadow validation PASS. | NO |
| Statistical independence of AI and shadows | 2, 4 | Not established | R1, P1 | A separate physical check, with possible shared RGB sensitivities. | Shadows are guaranteed independent of the AI prediction. | NO |
| Sparse anchors recover gauge | 2-4 | SYNTHETICALLY PROTOTYPED | R1 | Controlled anchors recover offset/scale when the design identifies those parameters. | One point always recovers both scale and offset. | YES |
| Shadows fix absolute vertical origin | 2-4 | False in the implemented geometric model | R1 | Anchors fix the vertical origin; uniform offsets leave geometric shadows unchanged. | Sun/shadow geometry alone recovers absolute elevation. | NO |
| Geodetic anchoring | 2, 3, 6 | IMPLEMENTED for compatible DEM calibration; SYNTHETICALLY PROTOTYPED for sparse anchors | I1, R1 | Compatible external elevations anchor the relative result. | Sparse GCP ingestion and geodetic recovery already work end-to-end in production. | YES |
| Combined physical/geodetic objective | 2, 4, 6 | SYNTHETICALLY PROTOTYPED | R1 | Synthetic registry and simple controlled scale/offset search. | Full real-scene differentiable surface optimizer is deployed. | YES |
| Physics-based innovation | 2, 4, 6 | SYNTHETICALLY PROTOTYPED | R1 | Geometric sun occlusion plus robust elevation constraints. | Full radiative-transfer simulator or novel laws of physics. | YES |
| Accuracy improvement | 2, 4, 6 | Real-scene improvement unproven | R2, R1 | Generic DAV2 refinement did not provide consistent geographic improvement; physical constraints are a research pivot. | Our physics engine improved real satellite elevation accuracy. | NO |
| Four geographical pilots | 4 | Completed development research | D1, R2 | Wake, Polk, Larimer, Humboldt development pilots. | Four sealed independent final-test regions prove generalization. | YES |
| Four displayed baseline MAEs | 4 | Recorded reference baseline | D1, R2 | Coarse-reference vs LiDAR DSM MAE: 6.80, 0.49, 2.56, 7.69 m. | Our AI achieves these errors, or these are final withheld results. | YES |
| 18 physics tests | 4 | Recorded synthetic software validation | R1 | 18 focused physics tests passed in the recorded run. | 18 real-satellite accuracy tests passed today. | YES |
| Numerical-exact offset/scale recovery | 4 notes | Controlled synthetic software result | R1 | Recovery in the known fixture, with true inverse scale included in the search grid. | Zero elevation error in deployment. | YES |
| Validation/evidence infrastructure | 3, 4 | IMPLEMENTED | I3 | Separate calibration and validation artifacts with explicit provenance/warnings. | All uploaded references are automatically statistically independent. | YES |
| High-resolution source information from GLO-30 | 3, 4 notes | Unsupported | D1, I1 | Approximately 30 m effective reference information even on a finer aligned grid. | A 1 m reprojected grid gives exact 1 m building heights. | NO |
| Real-time reconstruction | All | Not benchmarked for current target workload | I1, R1 | Interactive viewing of a prepared terrain surface. | Real-time satellite reconstruction or instant physics refinement. | NO |
| Standalone RGB-only metric inference | 1-3 | Unsupported | I1 | Relative RGB-only mode; metric mode requires compatible external evidence. | Standalone image yields metres without reference or metadata. | NO |
| Offline model inference | Optional notes | IMPLEMENTED with setup conditions | I1 | Cached local model inference can run offline once dependencies/weights are available. | No setup, no downloads and no computer needed. | YES |
| Textured interactive terrain | 1, 5 | IMPLEMENTED | I2 | Current Three.js textured heightfield and virtual-camera navigation. | Complete observed 3D city with accurate unseen façades. | YES |
| Physical height/slope | 3, 5 | IMPLEMENTED, unit-aware and accuracy-limited | I1, I2 | Inspect metric height/slope when valid metric geometry exists. | Engineering-grade slope/height from arbitrary relative depth. | YES |
| Arbitrary aerial viewpoints | 5 | IMPLEMENTED virtual-camera function | I2 | Explore the heightfield from virtual viewpoints. | Autonomous drone control or genuine observations from hidden viewpoints. | YES |
| First-responder application | 5 only | PROPOSED / FUTURE FIELD INTEGRATION | P1; parallel response implementation not audited here | Terrain can support future field decision tools after appropriate validation. | Disaster response is the original SIH26175 problem, or safe rescue routes are proven. | YES |
| Accessibility/routes/staging/terrain LOS operational claims | 5 | PROPOSED / FUTURE integration; not audited as deployed | P1 | Additional application directions, visibly future field integration. | Verified safe route, guaranteed staging safety or radio connectivity. | NO |
| Active next observation | 5 | SYNTHETICALLY PROTOTYPED | S1 | Prioritize simulated observations of unresolved terrain. | Field-tested autonomous drone/responder tasking. | YES |
| Mobile deployment | Optional future notes | PROPOSED / FUTURE | P1 | Further field/mobile integration is proposed. | Deployed phone-native standalone reconstruction/planning. | NO |
| Advanced semantic constraints | Optional research notes | IN RESEARCH | P1 | We are investigating object/semantic structure constraints. | Semantic classes already fix accurate roof/ground heights. | YES |
| Stronger semantics and pre/post 3D change | Optional future notes | PROPOSED / FUTURE | P1 | Future semantic capabilities and temporal change analysis. | Validated operational change-detection product. | YES |
| GeoRay relevance | 6 | External research reference, not adopted | P1, primary GeoRay paper | Geodetic/RPC-aware architecture; full published system uses three views. | GeoRay proves our single-image accuracy or is drop-in production. | YES |
| Sat3DGen relevance | 6 | External research reference, not adopted | P1, primary Sat3DGen paper | Single-image scene generation, separating generated hidden geometry from measurement. | Generated façades are observed Earth geometry. | YES |
| Shadow-height, sparse LiDAR, EOGS relevance | 6 | External research references | P1, primary references | Evidence-informed research directions with distinct inputs/methods. | These papers validate ChakraVIEW or are implemented here. | YES |
| Entirely new scientific principle | 2, 6 | Unsupported | P1 | Our research integration combines geometry hypotheses with explicit evidence checks. | World's first monocular depth, shadow geometry or geodetic control. | NO |
| Exact official-template compliance | Entire deck | Not verified by this content-only task | No rendered deck/template comparison in this task | Six-slide copy ready for template assembly and visual review. | Final PPTX fully complies with every original guideline. | NO |

## Audit conclusions

The six-slide **copy is cleared with its written qualifications**, not the risky alternatives. The claims of implemented processing/visualization are distinct from synthetic physical experiments and the future model direction. No unsupported accuracy, speed, field safety or mobile deployment statement appears in the visible copy.

Main wow factor: slide 2's shape-to-shadow check with external elevation anchoring. It is not a claim of already validated real-image refinement. Slide 4 carries bounded evidence, including the negative geographic result rather than suppressing it. First-responder value stays in the subordinate slide-5 application band.

Special cautions:

- The current synthetic observed mask shares the renderer. Agreement is internal consistency, not independent physical fidelity validation.
- The synthetic objective prefers tested correct candidates but does not uniquely identify a surface or guarantee monotonic full-raster MAE.
- A +5 m shift does not change shadow geometry. Anchors are essential for absolute offset.
- Metre units are necessary, not sufficient, for datum compatibility or reliable absolute height.
- NAIP examples are aerial, not satellite. A verified satellite demo must not be fabricated from an aerial screenshot.
- Four development pilots must never replace frozen final withheld Acadia/Baltimore results. No final metrics changed.
- Historical test results are labelled recorded. No new test/performance claim is implied by this documentation task.

## Evidence/access and later-deck gate

Primary GeoRay, Sat3DGen and sparse-LiDAR papers were accessible in this check. The shadow paper and CVPR EOGS title/scope were also verified through primary publisher/proceedings search results after direct page/PDF access errors. The final copy borrows no external numeric performance. Full primary links are in the slide-copy bibliography.

Review the actual assembled deck before declaring official-template or visual compliance. Check image provenance, status captions, units, metric labels and the claims above at presentation scale. Do not add more capability claims by copying the README disaster-management tagline into the problem/title slide.

No code, production or canonical-data edits. No training. No commit. No push.
