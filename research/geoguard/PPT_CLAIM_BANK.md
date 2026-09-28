# ChakraVIEW PPT claim bank

Checked 27 September 2026 against local project reports and linked primary research in PPT_INNOVATION_RESEARCH.md. Copy each line WITH its status caption. These are project/design claims, not external-paper accuracy results. “Prototype” below always means isolated research with synthetic tests, not the production app or real-world accuracy validation.

## Ten technical statements

1. **“ChakraVIEW keeps relative geometry separate from verified metric elevation.”**
   - Caption: IMPLEMENTED NOW. Relative and compatible-reference metric paths. Metric calibration does not establish survey accuracy.
2. **“Our current pipeline records the reference units and preserves geospatial metadata through metric DSM generation.”**
   - Caption: IMPLEMENTED NOW. Use a valid, compatible reference. CRS alone cannot establish vertical units or datum agreement.
3. **“Our physics prototype checks whether a proposed 3D surface casts the shadow seen in a controlled scene.”**
   - Caption: SYNTHETIC PROTOTYPE. Observed fixture masks use the same renderer. Real-image validation is pending.
4. **“Sparse anchors and shadows constrain different parts of the reconstruction problem.”**
   - Caption: SYNTHETIC PROTOTYPE. Anchors fix declared vertical gauge, shadows constrain observable relief. Neither guarantees a unique complete surface.
5. **“A trusted elevation point can fix vertical offset when the surface scale is already known.”**
   - Caption: SYNTHETIC PROTOTYPE. One point cannot identify unknown scale plus offset.
6. **“We model local shape and absolute Earth elevation as separate components.”**
   - Caption: SYNTHETIC PROTOTYPE. Explicit gauge/relief decomposition, not automatic datum identification from RGB.
7. **“Our evidence registry identifies available constraints and records where information is missing.”**
   - Caption: SYNTHETIC PROTOTYPE. Evidence bookkeeping, not calibrated uncertainty probabilities.
8. **“We are investigating satellite-native geometry while checking each model's camera and input requirements.”**
   - Caption: IN ACTIVE RESEARCH. Manish's audit owns evaluation. GeoRay's published full system is three-view with RPCs.
9. **“Our research rejects unsupported height corrections when they damage a good coarse reference.”**
   - Caption: IN ACTIVE RESEARCH. V0/V1/V1A negative results motivated rejection, not a successful production detail-refiner claim.
10. **“Calibration evidence and independent validation remain separate in the current workflow.”**
    - Caption: IMPLEMENTED NOW. Separate paths/identical-content guard and explicitly labelled fit-versus-validation metrics. This alone does not prove every data source statistically independent.

## Five application and value statements

11. **“The current application turns overhead imagery into an inspectable 3D heightfield with interactive flythrough.”**
    - Caption: IMPLEMENTED NOW. Predicted/calibrated heightfield with limitations, not a surveyed full 3D city.
12. **“Analysts can inspect height and slope with unit-aware safeguards in the current viewer.”**
    - Caption: IMPLEMENTED NOW. Engineering-grade measurements require independently validated metric geometry.
13. **“ChakraVIEW packages geometry, provenance and validation outputs for review.”**
    - Caption: IMPLEMENTED NOW. Traceability helps audit, but does not certify accuracy.
14. **“Scout's synthetic prototype recommends viewpoints that cover important unresolved terrain.”**
    - Caption: SYNTHETIC PROTOTYPE. Supplied access masks, approximate terrain LOS and simulated observation updates. No safe-navigation/rescue-performance claim.
15. **“The Scout research concept explains why each recommended observation ranks highly.”**
    - Caption: SYNTHETIC PROTOTYPE. Score decomposition and calculated coverage/cost proxies. Real operator trust/usability remains untested.

## Five future-vision statements

16. **“We propose a height surface that must satisfy available image, shadow and geodetic evidence together.”**
    - Caption: FUTURE EXTENSION. A synthetic objective registry exists, but real-scene joint surface refinement remains unvalidated.
17. **“Future structural constraints could test whether roofs, water and terrain have reasonable local shapes.”**
    - Caption: FUTURE EXTENSION. Soft, uncertainty-aware semantic constraints. Object class is not an exact height measurement.
18. **“Future sparse satellite-laser measurements could anchor image-derived geometry to a declared Earth-height reference.”**
    - Caption: FUTURE EXTENSION. ICESat-2 provider ingestion, classification, timing and datum checks still needed.
19. **“A future scientific and immersive twin could separate measured geometry from generated hidden views.”**
    - Caption: FUTURE EXTENSION. Synthetic visuals permanently labelled. All scientific measurements use the authoritative height surface.
20. **“A future field observation could return verified evidence to the reconstruction and trigger a new recommendation.”**
    - Caption: FUTURE EXTENSION. Closed-loop integration and real evidence assimilation are contracts, not a deployed autonomous system.

## Main-slide copy

**Headline:** Shadow-based surface checking

**Main line:** “AI proposes the shape. We check whether that shape would cast the shadow in the image.”

**Supporting line:** “Trusted elevation points place the shape at the right height on Earth.”

**Visible disclosure:** SYNTHETIC PHYSICS PROTOTYPE. REAL-SCENE VALIDATION PENDING.

**Original problem stays central:** Single-image height estimation and interactive 3D flythrough.

## Suggested ambitious wording that needs a qualifier

- “Shadows become physical measurements” is a PROPOSED object-height measurement pathway, not an implemented real-image extractor. Prefer “We propose using visible shadows as physical height checks.”
- “Self-checking 3D” means testing observable constraints, not proving the entire surface correct.
- “Pinned to Earth” requires declared metric scale and compatible datum/controls.
- “More reliable 3D” is the intended outcome to validate. Prefer “A surface with explicit evidence checks” until independent improvement is measured.
- “Mission confidence” should be “evidence-support indicator” unless a confidence calibration study exists.
- “One satellite image contains all clues” should be “One image provides appearance/shadow clues, augmented by available metadata and supporting measurements.”

## Prohibited or unsupported phrases

100% accurate, survey-grade, centimetre accuracy, works everywhere, NASA-level, world's first, guaranteed safe route, autonomous disaster command, exact façade recovery, exact building height from GLO30, improved real-scene accuracy from the synthetic objective, production GeoRay integration, validated injury/rescue benefit.

## Speaker answer: what is genuinely technically complex?

“The difficult part is identifying which heights a single overhead observation can constrain. The AI can propose plausible shape, but scale, vertical reference, occlusion and sensor geometry remain ambiguous. Our research combines robust geodetic controls with a forward shadow check and keeps unknown evidence explicit. We already have an inspectable application and synthetic physics tests. We still need independent real-image experiments to show an accuracy benefit.”

## Speaker answer: which new research do we use?

“Recent satellite-native and single-image scene research informs our direction. GeoRay motivates RPC-aware geometry and explicit vertical placement, but its full published setup uses three views. Sat3DGen demonstrates a direct single-image route to generated 3D scenes, while we keep generated appearance separate from height evidence. Our physics prototype uses established geometric ideas, not their released models or borrowed results.”

Primary links: [GeoRay paper](https://arxiv.org/html/2608.29680v1), [GeoRay input contract](https://github.com/HIT-SIRS/GeoRay), [Sat3DGen paper](https://arxiv.org/html/2605.14984v1). Model adoption remains under audit.

## Copy checklist

Keep maturity label attached. Keep scene/resolution/support if copying a number. Distinguish synthetic internal consistency from field accuracy. Preserve frozen final metrics. Do not tune on validation data. Credit external work. Clearly label additional observations and metadata. Keep Scout, change analysis and generated street views secondary to the original height/flythrough problem.
