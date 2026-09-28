# ChakraVIEW: final SIH six-slide copy

**Superseded narrative:** Use `FINAL_SIH_TEMPLATE_ALIGNED_REVISION.md` for the 28 September innovation-first revision aligned to the inspected official template and previous final presentation. Keep this file as the earlier draft and full-reference source.

Prepared 27 September 2026 on `research/geoguard-sprint`. Content draft only, not a rendered PowerPoint. The latest preference is to emphasize research innovation while keeping SIH26175's single-image height/DSM and flythrough task central.

Use the six `text` blocks verbatim as visible copy. Arrows specify editable diagram connections, not prose bullets. Notes below each block are presenter guidance, not additional slide text. Word caps include titles, diagram labels, captions and disclosures. Do not shrink disclosures to fit. Required official identity fields can occupy the template's existing placeholders once supplied, without adding a seventh slide.

## Slide 1: CHAKRAVIEW

Maximum visible words: **45**. Current copy: **42** whitespace-delimited tokens, including diagram connectors. Main message: one overhead image becomes an inspectable terrain surface.

```text
CHAKRAVIEW
Single-View Height Estimation and Interactive 3D Flythrough
FROM ORBIT TO 3D
SIH26175

SATELLITE RGB → HEIGHT / DSM → TEXTURED 3D TERRAIN

One optical image supplies the initial geometry.
Compatible elevation references enable metric calibration.
Explore the reconstructed terrain in 3D.
```

Layout: title group above one wide RGB-to-height-to-textured-terrain visual. Three supporting lines maximum. Use an actual project input and its actual output, not a generative city. The height/DSM middle image must say relative or calibrated in its retained legend. Detailed constraints/status distinctions belong on slides 2 and 3.

Screenshot/render: an existing input crop and the corresponding current MissionView oblique view, with the same geographic orientation. Include the intermediate output as the central panel only if its identity/units are clear.

Exclude: disaster-response identity, all research ideas at once, paper metrics, accuracy promises, a full 3D-city claim, invented team metadata.

Speaker clarification: one optical image is the image input. Elevation references and acquisition metadata are additional evidence. The current geometry model is DAV2 Small, not a satellite-native replacement.

## Slide 2: ONE IMAGE. MORE THAN ONE GEOMETRIC CLUE

Maximum visible words: **120**. Current copy: **109** whitespace-delimited tokens, including diagram connectors. Main message: research checks the proposed shape against shadows and anchors its height with trusted elevations. This is the main wow slide.

```text
ONE IMAGE. MORE THAN ONE GEOMETRIC CLUE

NORMAL APPROACH
Satellite image → Generic monocular depth → Relative depth

CHAKRAVIEW RESEARCH DIRECTION
Satellite image → Initial geometry → Shadow consistency → Sparse elevation anchors
→ Evidence-constrained height surface → 3D flythrough

AI proposes the shape.
We check whether that shape would cast the observed shadow.
Trusted elevation points place the shape at the correct height on Earth.

SATELLITE-AWARE GEOMETRY
IN RESEARCH
Respect orbital imaging geometry.

SHADOW-BASED SURFACE CHECKING
SYNTHETICALLY PROTOTYPED
Compare predicted and observed shadows.

HEIGHT ANCHORED TO EARTH
Compatible DEM calibration: IMPLEMENTED
Sparse anchors: SYNTHETICALLY PROTOTYPED

Sun metadata and trusted elevations are additional inputs.
Real-satellite accuracy improvement remains unvalidated.
```

Layout: one dominant research diagram, with the ordinary pipeline as a thin comparison row. Under it, a large three-line hero explanation and three plain innovation columns. Treat the hero and diagram as one connected composition. No extra fourth innovation card.

The research chain expresses dependencies, not a deployed sequential workflow: shadow and anchor constraints feed the same candidate surface. Sun azimuth/elevation feeds the shadow comparison; external controls feed the elevation constraint. The large on-slide label RESEARCH DIRECTION must span that chain. The known surface casts a predicted mask that can be compared to an observed mask. In the existing fixture, the observed mask is synthetic and shares the renderer.

Speaker clarification: this is a separate physical constraint, not automatically statistically independent of the AI. Both the AI and observed-shadow extraction can respond to the same RGB cues. Shadows cannot establish absolute elevation by themselves. One trusted point fixes only offset if scale is already known; unknown scale and offset need adequate distinct controls. No real-image shadow extractor or full-surface optimizer is claimed.

Bold: the three hero lines, SHADOW-BASED SURFACE CHECKING, and its SYNTHETICALLY PROTOTYPED caption together.

## Slide 3: TECHNICAL APPROACH: TWO INPUT PATHS

Maximum visible words: **135**. Current copy: **123** whitespace-delimited tokens, including diagram connectors. Main message: relative-only input and compatible-reference metric input have distinct outputs, with a separate research checking loop.

```text
TECHNICAL APPROACH: TWO INPUT PATHS

IMPLEMENTED
PATH A
PNG / JPG → Geometry model → Relative surface (rDSM)
→ Textured 3D mesh → Flythrough
rDSM: relative display surface, arbitrary units.

PATH B
GeoTIFF → Geometry model → Relative structure
+ Compatible reference DEM → Metric calibration
→ Reference-anchored DSM → Textured 3D mesh → Flythrough
Metres require verified units. Record datum compatibility or uncertainty.

RESEARCH SIDE LOOP
SYNTHETICALLY PROTOTYPED
Proposed surface + Sun azimuth / elevation
→ Predicted shadow ↔ Observed shadow → Geometry consistency score
GCP / sparse trusted anchors: research path, not production ingestion.

PyTorch · Rasterio / GDAL · FastAPI · React · Three.js
DSM · Height · Slope · Flythrough · Validation
Physical height/slope measurements require valid metric geometry.
```

Layout: two adjacent input lanes sharing the final viewer/output row. Add one compact side loop, connected with a dashed research line rather than inserted into the implemented path. Stack names form one unobtrusive strip, not five boxes. Maximum five major groups: title, two paths, research loop, stack/output strip.

Implementation evidence: `backend/services/depth_pipeline.py` and `frontend/src/relativeTerrain.js` separate reference-calibrated terrain from relative `depth.npy` decoding; `MissionViewAnalysis.jsx` renders a textured heightfield and controls metric tools. The relative display is real model output. It is not a georeferenced metric rDSM export. The metric file is `calibrated_dsm.tif`, generated by affine OLS calibration, not the research robust anchor fitter.

Speaker clarification: GeoTIFF alone does not provide metres. Horizontal projected coordinates may use feet. Vertical units require their own check; a metre label does not establish vertical datum agreement. Where datum metadata is missing, record that uncertainty rather than claiming known absolute placement. Calibration-fit error is distinct from validation. The current geometry is a 2.5D heightfield, not complete façades or unseen structures. GCP/sparse-control ingestion and shadow refinement remain outside production.

Bold: IMPLEMENTED, the two input format labels, arbitrary units, and SYNTHETICALLY PROTOTYPED.

## Slide 4: FEASIBILITY AND VALIDATION

Maximum visible words: **120**. Current copy: **107** whitespace-delimited tokens, including diagram connectors. Main message: the application exists, negative geographic findings guide the pivot, and physics evidence is synthetic.

```text
FEASIBILITY AND VALIDATION

WHAT ALREADY WORKS
IMPLEMENTED
Input handling, depth/surface generation, calibration, DSM export,
MissionView, height/slope inspection, validation/evidence.

WHAT WE TESTED
Four development pilots: Wake, Polk, Larimer, Humboldt.
Coarse-reference MAE vs LiDAR DSM (m):
Wake 6.80   Polk 0.49   Larimer 2.56   Humboldt 7.69
Generic DAV2 refinement did not provide consistent geographic improvement.

WHAT WE ARE IMPROVING
IN RESEARCH
Rather than forcing a weak model to improve, we pivoted toward
satellite-native geometry and independent physical/geodetic constraints.

SYNTHETIC VALIDATION
SYNTHETICALLY PROTOTYPED
Sparse anchors recover offset/scale in a controlled experiment.
Shadow consistency detects tested surface-shape errors.
18 physics tests passed in the recorded run.
Shared-renderer fixture: internal consistency, not satellite-field accuracy.
```

Layout: one evidence composition with three columns WHAT ALREADY WORKS / WHAT WE TESTED / WHAT WE ARE IMPROVING. Place the synthetic evidence in the third column, not as a fourth competing panel. Keep a small four-region locator strip above the four baseline numbers. Make SYNTHETIC VALIDATION as readable as the metric labels.

Metrics on the slide: four development geographies; four coarse-reference MAEs rounded to two decimals; 18 historical focused physics tests. The four MAEs are the aligned reference raster versus LiDAR-derived DSM, NOT monocular model accuracy and NOT final withheld scores. No new experiment or test was run for this draft.

Speaker backup only: coarse-reference RMSE is Wake 8.935212 m, Polk 1.387274 m, Larimer 3.432679 m, Humboldt 9.850414 m. Region-equal V1 MAE is 4.470300 m versus reference 4.382543 m, so V1 was NO-GO. V0 and V1A also did not establish the required usable improvement. Previously explored pilot regions are not a sealed blind benchmark. Refer to the protocol corrections in `GEOINVERSE_V1_RESULTS.md` when asked about split discipline.

The word independent in the pivot sentence means using explicitly observed physical/geodetic evidence rather than accepting model plausibility. It does not certify statistical independence of all cues. Real-scene validation must use acquisition-date sun geometry, an audited observed shadow mask, compatible fit anchors, a terrain halo and spatially separate withheld elevation checks.

Synthetic detail for questions: the 48 x 48, 1 m fixture uses 20 known controls. A +5 m uniform shift leaves shadows unchanged and anchors recover a -5 m correction. Relief x1.4, a ridge perturbation and a local bump change shadow disagreement. The objective only searches simple controlled scale/offset parameters. The true inverse scale appears in its candidate grid. Numerical recovery is not a real-world accuracy result.

Bold: Four development pilots, the negative DAV2 conclusion, and SYNTHETIC VALIDATION. Never bold a synthetic recovery number without the qualification.

## Slide 5: INTERACTIVE 3D AND APPLICATION VALUE

Maximum visible words: **85**. Current copy: **75** whitespace-delimited tokens, including diagram connectors. Main message: interactive terrain is the core output; field tools are a smaller extension.

```text
INTERACTIVE 3D AND APPLICATION VALUE

IMPLEMENTED: MISSIONVIEW
Textured terrain
First-person navigation
Height inspection
Slope inspection
Arbitrary aerial viewpoints

The reconstructed terrain is the core output.
The same terrain can then support field-level decision tools.

ADDITIONAL APPLICATION VALUE
PROPOSED / FUTURE FIELD INTEGRATION
Terrain Accessibility
Approach Route
Candidate Staging Areas
Terrain Line-of-Sight

NEXT OBSERVATION
SYNTHETICALLY PROTOTYPED
Prioritize observations where terrain remains uncertain.

Virtual viewpoints are not autonomous flight.
Field decisions require validated terrain and operational checks.
```

Layout: one dominant current MissionView screenshot occupying approximately 70% of the useful slide area. Five short capability labels surround or sit below it. Put four small application cards in a subordinate band, with PROPOSED / FUTURE FIELD INTEGRATION spanning all four. These names are extension directions, not audited completed response-analytics features. Put the Scout label in that band only if legibility remains good.

Screenshot: current textured metric MissionView with one selected height or slope result, retaining its units/mode legend. Use a different camera view from slide 1. A separate first-person screenshot is a backup asset, not another dominant image. Do not switch on measurement overlays during pointer-lock Fly capture if the current app disables them then.

First-responder extension appears ONLY in the small application band on slide 5 and in speaker discussion. Do not label the entire solution a disaster-command system. Scout is a synthetic research prototype; actual field deployment/mobile integration remains future. Terrain-only line-of-sight is not a guarantee of radio connectivity, visibility through vegetation or safe movement.

Bold: IMPLEMENTED: MISSIONVIEW and the core-output sentence. Research/future status remains equally legible.

## Slide 6: WHY CHAKRAVIEW GOES BEYOND GENERIC MONOCULAR DEPTH

Maximum visible words: **130**. Current copy: **118** whitespace-delimited tokens, including diagram connectors. Main message: the proposed differentiation is explicit physical/geodetic checking, informed by research with different input assumptions.

```text
WHY CHAKRAVIEW GOES BEYOND GENERIC MONOCULAR DEPTH

GENERIC PIPELINE
Satellite RGB → Generic depth → Scale → Viewer

CHAKRAVIEW DIRECTION: IN RESEARCH
Satellite RGB → Satellite-aware geometry → Physical consistency
→ Geodetic anchors → Evidence-constrained DSM → Interactive 3D

The monocular model is the starting hypothesis — not the final elevation map.

RESEARCH REFERENCES, NOT INTEGRATED MODELS
GeoRay (2026): geodetic/RPC-aware reconstruction; published system uses three views.
Sat3DGen (2026): single-image 3D; generated hidden geometry is not measurement.
Zhang et al. (2026): building shadows plus acquisition geometry.
Sparse LiDAR-guided correction (2025): measured controls support height correction.
EOGS (CVPR 2025): illumination-aware reconstruction from multiple images.

Synthetic physical checks exist. Real-satellite improvement is pending.
External paper results do not establish ChakraVIEW accuracy.
```

Layout: two aligned pipelines as one dominant comparison diagram. Attach the central hypothesis line beneath them. Use a compact five-line bibliography beneath the diagram. Full titles and clickable URLs belong in speaker notes; short references and multi-view/generation limitations remain visible.

Speaker clarification: the generic row is a simplified baseline sketch, not a claim that all existing systems lack calibration or physics. The research direction supplements the implemented path. No adopted GeoRay or Sat3DGen weights, no winner declaration, and no copied external benchmark numbers. The pitch is an integration/research direction, not invention of monocular depth, shadow geometry or geodetic control.

Bold: the central hypothesis line and IN RESEARCH. Do not turn the title into a proven accuracy comparison.

### Slide 6: exact references for speaker notes

1. **GeoRay: Gauge-Aware Feed-Forward Satellite 3D Reconstruction in the Geodetic Frame.** 2026 arXiv v1. [Primary paper](https://arxiv.org/html/2608.29680v1). [Author repository](https://github.com/HIT-SIRS/GeoRay). Full published system: three satellite views and RPC sensor models, with declared optional elevation controls. Architectural relevance is not single-image compatibility or adoption.
2. **Sat3DGen: Comprehensive Street-Level 3D Scene Generation from Single Satellite Image.** 2026. [Primary paper](https://arxiv.org/html/2605.14984v1). [Author repository](https://github.com/qianmingduowan/Sat3DGen). Distinguish single-image scene generation/novel views from measured hidden geometry and geodetic elevation.
3. **Urban Building Footprints Extraction and Heights Estimation from High-Resolution Spaceborne Remote Sensing Imagery Using a CNN-Transformer Network.** Zhang, Deng and Yan, Remote Sensing 18(10), 1484, 2026. [Publisher](https://www.mdpi.com/2072-4292/18/10/1484). Sun/sensor geometry and extracted building/shadow regions support case-dependent height estimation. Occlusion and vegetation complicate the evidence. Publisher search text verified title and scope; full-page access was unavailable in this check. No numerical results borrowed.
4. **Enhancing Monocular Height Estimation via Sparse LiDAR-Guided Correction.** 2025 arXiv v1. [Primary paper](https://arxiv.org/html/2505.06905v1). Sparse LiDAR evidence plus learned correction, not the same method as ChakraVIEW's synthetic robust offset/scale fitter.
5. **Gaussian Splatting for Efficient Satellite Image Photogrammetry.** Aira, Facciolo and Ehret, CVPR 2025, pp. 5959-5969. [CVF proceedings](https://openaccess.thecvf.com/content/CVPR2025/html/Aira_Gaussian_Splatting_for_Efficient_Satellite_Image_Photogrammetry_CVPR_2025_paper.html). EOGS includes radiometric/shadow modelling in satellite reconstruction. Multiple observations and per-scene optimization do not prove single-image recovery. Proceedings title/abstract verified, with detailed input scope also documented in the existing research brief.

## Maturity contract: never separate the statement from its label

- **IMPLEMENTED:** image processing, real relative terrain, compatible-reference metric calibration, DSM artifacts, MissionView, unit-aware height/slope, backend/frontend, validation/evidence infrastructure.
- **SYNTHETICALLY PROTOTYPED:** forward shadows, shadow mismatch, sparse-anchor constraints, offset/scale gauge recovery, combined physical/geodetic objective and next-observation selection. Isolated research, not production.
- **IN RESEARCH:** satellite-native foundation integration, real-image shadow-constrained improvement and advanced object/semantic constraint investigation. No selected or integrated replacement model asserted.
- **PROPOSED / FUTURE:** stronger semantic capabilities, full pre/post 3D change, response-tool integration and further field/mobile delivery.

Current generic DAV2 remains the implemented geometry source. The new physical/geodetic idea carries slides 2 and 6; slide 4 supplies its bounded evidence. First-responder value remains secondary on slide 5.

## Scope and handoff

Only the three requested documentation files were created. Existing production, experiments, canonical data and final metrics were not edited. Existing `.gitignore` changes remain untouched. No training, new algorithm implementation, fresh performance benchmark, commit or push. Exact layouts/screenshots and allowed claims are in the companion visual plan and audit. This draft does not certify a completed PPTX against an official template; the later deck must retain that template's prescribed headings, identity fields and slide limits.
