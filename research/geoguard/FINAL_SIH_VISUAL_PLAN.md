# ChakraVIEW: final six-slide visual plan

**Superseded assembly plan:** Use `FINAL_SIH_TEMPLATE_ALIGNED_REVISION.md` for the 28 September section headings, innovation-first composition and retained assets from the actual previous final deck. This earlier generic visual plan is not the template-aligned final layout.

Companion to `FINAL_SIH_6_SLIDE_COPY.md`. Content/layout specification only. No images were fabricated, no screenshots were captured, and no PPTX was produced by this task. Planned screenshot names below identify future captures, not existing evidence. Preserve the official SIH template when assembling the deck; six total slides, including the cover. Original PDF/PPTX template compliance needs a separate actual-file inspection and rendered-deck review.

## Common rules

- One main message and one dominant visual per slide. Three to five major text groups maximum, including the title. Plain aligned text, not a dashboard of badges.
- Existing template fonts/identity/footer requirements take precedence. Otherwise use ChakraVIEW teal, dark graphite and an unobtrusive warm background. Use orange sparingly for the research disclosure, not as an accuracy alarm.
- Title approximately 30-34 pt, body 20-24 pt, meaningful captions/status 18-20 pt where the template allows. References must still be readable. Cut copy before shrinking. Word caps are hard ceilings, not targets.
- Status words carry meaning independently of color. IMPLEMENTED uses solid connectors. SYNTHETICALLY PROTOTYPED uses dashed connectors. IN RESEARCH uses outlined nodes with an explicit caption. PROPOSED / FUTURE labels span future groups.
- Scientific outputs must be actual output rasters or app screenshots. Keep source identity, units and relative/metric labels. Synthetic physics views must say SYNTHETIC. Do not use generated satellite/terrain imagery as measured project results.
- Do not change scientific geometry, strengthen height exaggeration, flip a raster, crop away warnings, hide a low calibration score, or replace a current app caption with an unsupported accuracy label.
- Diagram arrows are editable evidence objects. Branching inputs must show that sun metadata, DEMs and sparse elevations come from outside the single RGB image.

## 1. CHAKRAVIEW

Main message: the original height-estimation/flythrough problem. Dominant visual: an input-to-output triptych occupying about 60% of the slide.

Exact diagram:

```text
SATELLITE RGB → HEIGHT / DSM → TEXTURED 3D TERRAIN
```

Place the logo/title/subtitle/SIH26175 above it. Supporting lines sit together, below or left. Keep the three image panels as ONE linked visual, not three unrelated story cards. Use the same scene through the entire triptych. A satellite-data thumbnail belongs here only if its actual source is satellite imagery. If using the existing Baltimore/NAIP aerial example, caption it accurately as an aerial demo and explain that the overhead pipeline targets satellite RGB too. Do not rename NAIP a satellite image.

Needed assets:

- `S1_input_rgb.png`: actual input crop, north-up as recorded in its metadata.
- `S1_geometry_output.png`: corresponding depth preview with relative legend, OR metric DSM with metre/datum qualification. Choose one and identify it accurately.
- `S1_missionview_oblique.png`: matching textured current MissionView, oblique Orbit view with mode/units retained.

No accuracy metric. Bold CHAKRAVIEW and the original-task subtitle. Exclude field-response cards and papers.

## 2. ONE IMAGE. MORE THAN ONE GEOMETRIC CLUE

Main wow factor: the surface casts a shadow that can be checked. Dominant visual: one hypothesis/check diagram, about 55% of the slide. Three innovation columns underneath, with status captions.

Exact logical diagram, with the long text chain in the copy used as its readable top spine:

```text
NORMAL: Satellite image → Generic monocular depth → Relative depth

RESEARCH: Satellite image → Initial geometry → Candidate height surface → 3D flythrough
                                               ↑                ↑
Sun azimuth/elevation → Predicted shadow ↔ Observed shadow        |
                                Shadow consistency -------------|
Sparse trusted elevations → Elevation constraint ---------------|
```

Use horizontal/vertical orthogonal connectors, not the ASCII crossing literally. The shadow/anchor links enter the candidate surface as evidence. Do not imply a full production optimizer exists. Associate the captions Satellite-aware geometry / Shadow-based surface checking / Height anchored to Earth with their corresponding parts. Hero text is the three lines in the copy.

Visual evidence: a small pair of annotated synthetic shadow masks may sit INSIDE the diagram, replacing decorative surface icons. Rendered shadow vs observed mask must use the existing saved fixture, and the caption must say shared renderer / synthetic. Do not place a real satellite screenshot next to synthetic agreement and imply the real scene was tested.

Needed screenshot/render if available later: `S2_synthetic_shadow_check.png`, a faithful view of known terrain, perturbed terrain and their masks from the existing results. Not yet an existing screenshot. If generating this view would require another experiment, use the diagram alone for this task's deck.

Bold hero text and SHADOW-BASED SURFACE CHECKING with SYNTHETICALLY PROTOTYPED attached. Do not add accuracy percentages or a world's-first badge. Acquisition metadata and observed-mask availability must remain visible.

## 3. TECHNICAL APPROACH: TWO INPUT PATHS

Main message: metres depend on valid evidence. Dominant visual: two-lane architecture diagram, about 65% of the slide. Paths occupy two-thirds of the diagram width, research loop the remaining third.

Exact connections:

```text
PNG/JPG → Geometry model → Relative surface (rDSM) → Textured mesh → Flythrough

GeoTIFF → Geometry model → Relative structure → Metric calibration
Compatible reference DEM --------------------↑
Metric calibration → Reference-anchored DSM → Textured mesh → Flythrough

RESEARCH ONLY:
Proposed surface + Sun azimuth/elevation → Predicted shadow
Predicted shadow ↔ Observed shadow → Geometry consistency score
GCP / sparse anchors → Research elevation constraint
```

Do not put GCP/anchor ingestion as an implemented production node. Add the stack/output strip exactly as in the copy, with a unit note next to Path A and a reference-unit/datum note next to Path B. Relative height must not inherit the metre symbol from the second lane.

Needed screenshots: none. Use native editable diagram objects; keep actual artifacts `depth.npy` and `calibrated_dsm.tif` in notes or short presenter callouts, not a wall of filenames. No speed/accuracy metric.

Bold IMPLEMENTED, PNG/JPG, GeoTIFF, arbitrary units, and research-loop status. Avoid calling rDSM a current georeferenced export.

## 4. FEASIBILITY AND VALIDATION

Main message: working system plus bounded research evidence. Dominant visual: one three-column evidence composition, with a modest geographic locator strip. The synthetic group stays inside WHAT WE ARE IMPROVING, not an extra fourth column.

Exact evidence grouping:

```text
WHAT ALREADY WORKS       WHAT WE TESTED          WHAT WE ARE IMPROVING
Implemented functions   Four development       Research pivot
                        pilot geographies      Synthetic validation
                        Reference MAEs         18 recorded tests
                        DAV2 NO-GO finding     Offset/scale + shadows
```

The geographical strip identifies Wake NC, Polk FL, Larimer CO and Humboldt CA. A basic locator is enough; do not imply their AOIs span the entire county. Labels are development pilots. Main-slide numeric line: coarse-reference MAE vs LiDAR DSM: 6.80 / 0.49 / 2.56 / 7.69 m in that order. This is baseline reference agreement, not DAV2 accuracy.

Exact evidence sources:

- `CANONICAL_PILOT_TRANSFER_MANIFEST.json`, per-pilot `baseline_metrics`.
- `GEOINVERSE_V1_RESULTS.md`, per-region reference scores, aggregate failure and protocol qualifications.
- `GEOINVERSE_PHYSICS_ENGINE.md` and `geoinverse_physics/synthetic_results.json`, controlled physics scope.

Metrics worth showing ON SLIDE: **4 development regions**, the **four reference MAEs**, **18 recorded physics tests**. No test count represents real accuracy.

Optional SPEAKER BACKUP, not main-slide clutter:

- Reference MAE/RMSE in metres: Wake 6.799877 / 8.935212; Polk 0.487771 / 1.387274; Larimer 2.556609 / 3.432679; Humboldt 7.685916 / 9.850414.
- Valid scoring pixels respectively: 962,159 / 991,122 / 960,982 / 982,686.
- V1 region-equal MAE 4.470300 m vs reference 4.382543 m, about 2.00% worse, not a GO.
- Controlled fixture: 48 x 48 cells, 1 m grid, 20 controls, +5 m shift corrected by -5 m. Do not call this a precision guarantee.
- Shadow disagreement: known 0%, +5 m uniform shift 0%, relief x1.4 3.342%, ridge perturbation 7.248%, local bump 5.642%. These show offset non-identifiability and sensitivity to those tested shape errors, not field detection accuracy.

Needed screenshots: none required. Optional `S4_recorded_physics_tests.png` is a capture of the documented 18-test result, labelled historical. Do not rerun tests merely for a fresher-looking screenshot in this content task.

Bold SYNTHETIC VALIDATION and negative DAV2 finding. Avoid a giant failed-model table, perfect synthetic IoU headline, numerical-zero recovery headline or final withheld benchmark substitution.

## 5. INTERACTIVE 3D AND APPLICATION VALUE

Main message: inspect the reconstructed terrain. Dominant visual: actual MissionView, approximately 70% of available slide area. Application band approximately 15-20%, subordinate to the viewer.

Exact capability labels around the screenshot: Textured terrain / First-person navigation / Height inspection / Slope inspection / Arbitrary aerial viewpoints. The five labels form one capability group, not five full cards.

Exact extension cards, with a spanning PROPOSED / FUTURE FIELD INTEGRATION caption:

```text
Terrain Accessibility   Approach Route   Candidate Staging Areas   Terrain Line-of-Sight
```

The optional Scout line below them carries SYNTHETICALLY PROTOTYPED. It is not a completed mobile or operational response deployment. Do not duplicate Ayush's implementation or claim its completion from this unreviewed interface.

Needed assets:

- `S5_missionview_metric_inspection.png`: different oblique/current metric view from slide 1, one actual height OR slope result, visible units, spatial metadata and mode. Preserve values, including any low fit statistic.
- `S5_missionview_fly_backup.png`: current first-person view or a frame from a real screen recording, demonstrating the actual terrain viewer. Backup only. It does not prove accurate elevations or flight safety.

No invented human rescue, evacuation, safe-route or time-saving metrics. Do not label virtual aerial viewpoints as drone flight control. No new field/mobile screenshot unless a working integration is independently verified.

This is the only slide hosting first-responder extension value. The heading must still name interactive 3D, not emergency command.

## 6. WHY CHAKRAVIEW GOES BEYOND GENERIC MONOCULAR DEPTH

Main message: research checks geometry rather than treating plausible model output as final elevation. Dominant visual: two aligned pipeline rows with the central hypothesis statement underneath.

Exact diagram:

```text
GENERIC PIPELINE
Satellite RGB → Generic depth → Scale → Viewer

CHAKRAVIEW DIRECTION: IN RESEARCH
Satellite RGB → Satellite-aware geometry → Physical consistency
→ Geodetic anchors → Evidence-constrained DSM → Interactive 3D
```

Five short references appear below. Keep GeoRay three-view and Sat3DGen generated-hidden-geometry caveats visible. Full bibliography/URLs are speaker notes in the copy file. No paper benchmark numbers. No screenshots needed, no author logos suggesting partnership.

Bold the central hypothesis sentence. Avoid depicting the research row as already deployed or asserting generic methods never use physical constraints.

## Exact capture checklist and exclusions

Minimum required for later PPT assembly: S1 input, S1 geometry, S1 MissionView, S5 metric inspection. Optional: S2 synthetic visualization, S4 historical tests, S5 Fly backup. These filenames are capture requests, not deliverables created here.

Use real project assets without generating new data. If no verified satellite input/output pair exists, use an accurately labelled aerial example instead of inventing a satellite demo. Do not alter final Acadia/Baltimore metrics or assets. Keep any existing scene's legal attribution in its image caption/notes.

## Claims that deserve emphasis

Main hero: the three AI/shape/shadow/anchor lines. Proof: implemented MissionView, separated relative/metric paths, four development pilots, controlled synthetic physical checks. Direction: satellite-aware geometry and evidence-constrained height, explicitly IN RESEARCH. Keep every maturity disclosure visually attached.

Avoid: high precision, survey-grade, centimetre accuracy, real-time reconstruction, standalone hardware-free metres, production satellite-native model, real-image shadow validation, guaranteed accurate DSM, autonomous safe route, deployed mobile response, world-first physics, borrowed paper improvements.

## Assembly gates

1. Match original official template headings, required team/idea/organization fields and any required section order before approving a final PPTX. This file specifies story content, not official-template compliance certification.
2. Check total slide count is six; do not append a seventh references/cover slide.
3. Paste the exact copy, within caps. Keep required caveats if shortening.
4. Replace capture requests with genuine assets and verify scene/source matching.
5. Render the actual deck and inspect all six slides at presentation scale. Check wrap/overflow, contrast, tiny references and status visibility. No rendered-deck visual QA is claimed for these Markdown outputs.
