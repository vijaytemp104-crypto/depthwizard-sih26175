# ChakraVIEW: innovation-first, template-aligned revision

Prepared 28 September 2026. This replaces the narrative/order recommendations in the three 27 September content drafts. It is revised slide copy and assembly guidance, not a newly edited PPTX. Neither supplied presentation was overwritten.

## What the source files actually require

Inspected every slide of the official template and the supplied `FINAL_SIH_PRESENTATION.pptx`, both structurally and as rendered images. Read the supplied 64-page guidelines PDF, including its slide-specific guidance; visually checked the title, main-innovation and architecture guidance pages. Readable Downloads copies of the template and PDF are SHA-256-identical to the exact WhatsApp files supplied by the user.

The template's seventh slide is instructions, not a permitted seventh content slide. It requires at most six slides INCLUDING the title, the provided template and unchanged idea-details pointers, concise points/diagrams/images, and PDF submission. Preserve these six section headings:

1. TITLE PAGE
2. IDEA TITLE
3. TECHNICAL APPROACH
4. FEASIBILITY AND VIABILITY
5. IMPACT AND BENEFITS
6. RESEARCH AND REFERENCES

Custom research headlines are subtitles INSIDE these sections, not replacement section titles. Keep the official SIH artwork, blue footer, page numbering, original dimensions and team-name position. Preserve the registered metadata. The existing deck says Team_Chakravyuh, Software and Disaster Management; Disaster Management remains the supplied THEME field, not a replacement problem statement. Its Team ID is a dash and must be replaced manually with the actual registered ID before submission. Do not invent it.

Guidelines pages 26 and 28-34 support a meaningful title, concrete problem/gap and early differentiation. Pages 37 and 40 prohibit directly using AI-generated architecture pictures and ask the team to draw/explain its engineering diagram. Pages 44-47 require feasibility evidence, risks and mitigation. Pages 50-56 require beneficiary-specific value and credible research. These are not a mandate to add every example technology, mobile app, chatbot, notification or cloud service.

## What changes from the previous deck

The previous slide 2 primarily pitches unit safeguards, validation separation and provenance. Those are important IMPLEMENTED guardrails, but do not explain the new physical/geodetic research mechanism. Keep them as support, not the innovation headline.

The first three slides now establish this sequence:

- Slide 1: name the original task and immediately seed the research distinction.
- Slide 2: show the three mechanisms and the gap they address, within the official proposed-solution pointers.
- Slide 3: show how the shadow/anchor objective sits beside the actual deployed pipeline, with explicit inputs and limitations.

No algorithm is invented for the presentation. The innovation pitch is a research integration: test model geometry against shadow evidence, treat relative shape and Earth-height placement separately, and make missing constraints explicit. It is not a world-first or verified accuracy improvement.

## Exact visible copy

Each fenced block includes the section heading and all proposed visible wording. Word caps include diagram labels and status captions. Metadata placeholders require manual verification. Notes below each block are not extra slide paragraphs.

### Slide 1: TITLE PAGE

Maximum: 100 words, including required metadata. Retain the official cover layout, not a new custom cover.

```text
SMART INDIA HACKATHON 2026
TITLE PAGE

Problem Statement ID: SIH26175
Problem Statement Title: DepthWizard - Single-View Height Estimation and 3D Flythrough
Theme: Disaster Management
PS Category: Software
Team ID: [actual registered ID]
Team Name: Team_Chakravyuh

CHAKRAVIEW
Single-View 3D with Shadow and Elevation Constraints

AI proposes. Shadows test. Elevations anchor.

Working height/DSM-to-flythrough pipeline.
Physical/geodetic constraints: SYNTHETICALLY PROTOTYPED.
Real-satellite improvement: IN RESEARCH.
```

Replace the bottom-right generic disaster-management tagline in the previous deck with the specific solution subtitle and three-part explanation. Keep the required identity panel untouched except for verified missing metadata. Do not crowd the cover with diagrams, papers or benchmark numbers. The scientific novelty is visible immediately, but the status stays attached.

### Slide 2: IDEA TITLE

Maximum: 165 words. This is the main innovation slide. Preserve the official proposed-solution pointers, with innovation carrying the visual emphasis.

```text
IDEA TITLE
ChakraVIEW: Single-View 3D with Shadow and Elevation Constraints

Proposed Solution (Describe your Idea/Solution/Prototype)
Detailed explanation of the proposed solution
AI proposes the shape.
Sun geometry predicts its shadow for comparison with observed shadows.
Trusted elevations anchor the shape to Earth's height reference.

How it addresses the problem
For geospatial analysts, plausible relative depth is insufficient for measured elevation.
Our working pipeline produces calibrated DSM artifacts and textured flythroughs when valid references exist.

Innovation and uniqueness of the solution
SHADOW CONSISTENCY
Check a candidate surface against geometric shadow evidence.
SEPARATE SHAPE FROM ABSOLUTE HEIGHT
Fit identifiable offset/scale using trusted controls.
MISSING-EVIDENCE-AWARE CONSTRAINTS
Record available checks and explicitly report absent evidence.
All three mechanisms: SYNTHETICALLY PROTOTYPED.

Generic relative-depth baseline → Geometry proposal
ChakraVIEW research → Proposal + Shadow checks + Elevation controls

Sun metadata and controls are additional inputs.
Real-scene accuracy benefit remains unvalidated.
```

Retain the previous deck's recognizable white/teal/orange treatment and a real current MissionView screenshot, but reduce that screenshot to about one-third of the useful area. It proves a working output; it must not displace the new technical idea.

Use three short horizontal innovation rows, not five superficial new-feature cards. The comparison is to the project's generic relative-depth baseline, not every published reconstruction system. Do not claim nobody else uses shadows or geodetic control. The proposed benefit is observable evidence checking, not proven higher accuracy.

Judge explanation, approximately 20 seconds: "Our current app already turns one overhead image into an inspectable surface. The research contribution is to test that proposed shape against the shadow it should cast, then fit trusted elevation controls for Earth-height placement. We also report which evidence is missing. We have a controlled synthetic prototype, not a claimed real-satellite accuracy win."

### Slide 3: TECHNICAL APPROACH

Maximum: 155 words. Show real engineering and the synthetic objective without blending them.

```text
TECHNICAL APPROACH

Technologies to be used
Python/PyTorch: model and constraints
Rasterio/GDAL: geospatial grids and metadata
FastAPI: processing/artifact API
React/Three.js: textured terrain and flythrough
Local computer; cached model supports offline inference.

Methodology and process for implementation
IMPLEMENTED PIPELINE
RGB upload → POST /process → DAV2 Small → Relative depth
GeoTIFF + Compatible DEM → Affine calibration → Metric DSM
Artifacts + Evidence → React/Three.js → Height/Slope/Flythrough
PNG/JPG without valid reference → Relative terrain, not metres

RESEARCH CONSTRAINT LOOP: SYNTHETICALLY PROTOTYPED
Candidate surface + Sun angles → Predicted shadow
Predicted ↔ Observed shadow → Shadow mismatch
Candidate surface + Sparse controls → Anchor mismatch
Available constraints → Combined objective
Missing evidence → Explicit unavailable status
Controlled scale/offset search, not full-surface optimization.

Satellite-native geometry integration: IN RESEARCH.
Unknown units/datum cannot establish verified absolute elevation.
```

The main engineering visual is one team-drawn, native editable architecture with two explicitly labelled lanes. Solid links describe the implemented path. Dashed links describe the research prototype. Do not paste a generated architecture bitmap from an AI tool. This document specifies the engineering connections for the team to draw/review, as requested by guideline page 40.

Required external inputs are visible side inputs: compatible calibration DEM; image-date sun azimuth/elevation; observed-shadow mask with unknown/cloud support; sparse controls with compatible coordinates, units/datum and uncertainty. Sun metadata alone is not an observed mask. Stored scientific arrays/rasters and JSON artifacts leave FastAPI for the viewer and evidence outputs. No fictitious database, cloud, notifications, mobile client or sensor is added.

Speaker-only formulation: `Z* = argmin [lambda_F L_prior + lambda_S L_shadow + lambda_A L_anchor + lambda_G L_reference + lambda_R L_regularization]`. The registry implements objective bookkeeping; the existing demonstration searches simple synthetic scale/offset, not every raster height. Do not imply all five terms were active in the recorded experiment. Weights are not confidence probabilities.

Speaker-only technical distinction: uniform elevation offset does not alter geometric shadows. Anchors identify vertical placement; shadows can constrain visible relief. One anchor only fixes offset when scale is known. Offset fitting preserves relief differences; affine fitting deliberately changes relief amplitude. The algorithm neither automatically preserves all detail nor proves a unique heightfield.

### Slide 4: FEASIBILITY AND VIABILITY

Maximum: 150 words. Keep the template's feasibility, risk and mitigation pointers rather than substituting a model-research results slide.

```text
FEASIBILITY AND VIABILITY

Analysis of the feasibility of the idea
IMPLEMENTED: image processing, reference calibration, DSM export,
textured MissionView, height/slope tools, validation and evidence.
Existing open-source stack and cached local inference.

PROTOTYPE EVIDENCE
18 physics tests passed in the recorded synthetic run.
Controlled +5 m offset: anchors recover -5 m.
Shape perturbations alter predicted-shadow agreement.
Shared renderer: internal consistency, not field accuracy.

Potential challenges and risks
Missing/incompatible reference; domain shift; unreliable shadow evidence.

Strategies for overcoming these challenges
Relative/not-metric fallback; unit/datum checks; separate validation.
Audit sun/shadow evidence and terrain halo before real-scene refinement.

VIABILITY
Local software workflow with reusable geospatial artifacts.
Operational deployment and costs require further validation.

REAL-DATA LIMITATION
Frozen RMSE: Acadia terrain 49.60 m; Baltimore DSM 30.78 m.
Generic DAV2 refinement did not improve consistently across four development pilots.
```

Keep the previous two-column feasibility/risk style, but reduce five risks to three useful grouped risks. Replace the tiny validation dashboard screenshot with readable, correctly named evidence. A documented test count is software evidence, not satellite accuracy.

Use the existing frozen metrics without recalculation or experiment changes. Acadia is terrain DTM; Baltimore DSM is surface validation. The high errors are not new research results, and correlations do not cancel them. Geographic pilots Wake/Polk/Larimer/Humboldt are development experiments, not final withheld regions. Numeric-exact synthetic recovery cannot be extrapolated to field precision. No latency, cost or scalability number is invented.

### Slide 5: IMPACT AND BENEFITS

Maximum: 115 words. Preserve the previous Acadia/Baltimore images and recognizable delivery story, but keep application value secondary to the original output.

```text
IMPACT AND BENEFITS

Potential impact on the target audience
Geospatial analysts and planners:
inspect a textured heightfield using Orbit/Fly and height/slope tools.
Review DSM artifacts, provenance and validation evidence.

Benefits of the solution
Inspection: connect overhead imagery to an interactive surface.
Reuse: export geospatial artifacts for downstream GIS review.
Access: cached local model inference after setup.

IMPLEMENTED: MISSIONVIEW AND EVIDENCE
Acadia terrain view
Baltimore surface view
Predicted/calibrated geometry, not surveyed ground truth.

ADDITIONAL FIELD VALUE: PROPOSED / FUTURE
Accessibility, approach routes, candidate staging, terrain line-of-sight.

NEXT-OBSERVATION SELECTION: SYNTHETICALLY PROTOTYPED
Prioritize unresolved terrain for another observation.
No proven rescue benefit or guaranteed safe route.
```

Reuse the exact existing Acadia/Baltimore screenshots from the previous deck, retaining units, mode and warnings. They are produced project outputs, not before/after research-refinement comparisons. Keep one larger scene and a smaller supporting scene, or the existing paired composition if readable. Remove the previous oversized generic Target Audience/Scalability banner to recover usable space.

Responders are potential downstream beneficiaries, not the central problem statement. The existing Scout synthetic research may be mentioned, but no autonomous flight, field safety, radio LOS, mobile deployment or actual operator benefit is asserted. Do not quantify savings/lives/users without evidence.

### Slide 6: RESEARCH AND REFERENCES

Maximum: 135 words. Keep state of the art, gap and implementation resources within the official reference section.

```text
RESEARCH AND REFERENCES

RESEARCH BASIS AND GAP
GeoRay (2026): RPC/geodetic reconstruction; full system uses three views.
Sat3DGen (2026): single-image scene generation; hidden geometry is generated.
Shadow-height research (2026): sun/sensor geometry informs building heights.
Sparse LiDAR correction (2025): measured controls support height correction.
EOGS (CVPR 2025): illumination-aware, multi-image reconstruction.

OUR RESEARCH DIRECTION
Combine shadow checks, identifiable height placement and explicit missing evidence
around a single-image geometry proposal.
Synthetic prototype exists; real-image improvement is unvalidated.
These papers are references, not integrated production models.

IMPLEMENTATION RESOURCES
Depth Anything V2 Small; Copernicus GLO-30; USGS 3DEP.

DATA ROLES
Boulder/GAMUS and four counties: development.
GLO-30: calibration. Acadia/Baltimore LiDAR: withheld validation.
Calibration fit is not independent validation.
```

Keep bibliography links readable and clickable. Full URLs may be attached to the visible reference labels and repeated in speaker notes, rather than five lines of microscopic raw URLs. Do not add a seventh bibliography slide. Use full citations from `FINAL_SIH_6_SLIDE_COPY.md`; no borrowed paper benchmark numbers. Current production remains DAV2 Small. No satellite-native model adoption is asserted.

## Visual retention and specific edits to the supplied final deck

- **Slide 1:** retain official metadata, artwork and layout. Replace only the project's generic subtitle with the innovation-specific name/status. Fill Team ID from portal before final submission.
- **Slide 2:** keep IDEA TITLE, team identifier, official header/footer and one real MissionView view. Remove the highlighted paragraph and generic guardrail-as-novelty bullet list. Put the three physical/geodetic mechanisms where WHAT MAKES US STAND OUT currently appears, with the synthetic qualifier spanning them.
- **Slide 3:** keep TECHNICAL APPROACH and the two required technology/methodology pointers. Replace the four equally weighted perception/calibration/output/delivery boxes with the connected implemented pipeline plus a dashed research-side loop. Keep the module stack, actual API and artifacts explainable.
- **Slide 4:** keep FEASIBILITY AND VIABILITY and risk/mitigation coverage. Replace adjective-heavy low-cost/scalable wording with actual existing software resources and bounded synthetic evidence. Include real-data accuracy limitations rather than cropped unreadable dashboard evidence.
- **Slide 5:** keep IMPACT AND BENEFITS and the Acadia/Baltimore project visuals. Prioritize actual terrain inspection and artifact reuse. Keep response applications and Scout small, with future/synthetic status attached.
- **Slide 6:** keep RESEARCH AND REFERENCES. Replace a resources-only bibliography with recent relevant research, its assumptions, the proposed integration gap and the existing implementation/data resources.

Use the source theme/margins/artwork rather than a redesigned deck. Inspect wrapping after assembly. Keep body/status text at least as readable as the previous deck; never hide SYNTHETICALLY PROTOTYPED to create more room for novelty. The instructions slide is excluded from the final six-slide content. Export PDF for the portal, retaining PPTX as the editable working file.

## Claim boundaries and compliance conclusion

Innovation is now visible in slide 1, explained in slide 2 and engineered in slide 3. The central novelty is explicit physical/geodetic evidence checking and missing-evidence handling, not a claim of a new pretrained foundation model or invented photogrammetry.

Allowed: a working height/DSM-to-flythrough application; synthetic forward shadows; controlled anchor/gauge fitting; a synthetic constraint registry; a future real-scene research direction. Attach each status to the corresponding mechanism.

Not allowed: real-satellite improvement, survey accuracy, satellite-native production integration, a full-surface optimizer, shadows alone fixing absolute height, automatic datum compatibility, uncertainty calibrated as probability, every detail preserved under affine scaling, field-safe routes or deployed mobile response. Existing claim-audit scientific exclusions remain in force.

The revised CONTENT maps to all six required template sections and the requested early-innovation emphasis. It is not certification of a revised PDF/PPTX layout because no revised deck has been exported. The source deck has six slides but an unfilled Team ID, so it is not ready to declare complete portal submission compliance. Source screenshots and numerical evidence must remain truthful. Team members should draw/review the final editable architecture themselves, consistent with the supplied guidelines.

Only research presentation documentation changed. No source code, production functionality, algorithms, training, canonical data, evaluation splits or final scientific results changed. No commit. No push. Both source PPTX files and the PDF remain untouched.
