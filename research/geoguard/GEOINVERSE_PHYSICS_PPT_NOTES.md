# GeoInverse physics — presentation notes

**Foundation AI proposes. Physics constrains. Geodesy anchors.**

**ChakraVIEW asks which 3D Earth surface best explains the satellite observation.**

## One equation

`Z* = argmin_Z [ λF L_foundation + λS L_shadow + λA L_anchor + λG L_geodetic + λR L_regularization ]`

- Z: a candidate Earth surface; Z*: the candidate with smallest chosen objective.
- argmin: search for the surface that best satisfies the available evidence.
- L_foundation: disagreement with the initial AI geometry proposal.
- L_shadow: disagreement between geometrically predicted and independently observed shadows.
- L_anchor: disagreement with trusted sparse elevation controls.
- L_geodetic: disagreement with an aligned absolute-elevation reference.
- L_regularization: optional penalty against unsupported roughness.
- λ: explicit influence/normalization coefficients for each source; not confidence probabilities.

## What is implemented

Sparse uncertainty-weighted robust anchors; offset/affine/spatial-plane gauge fitting; a geometric terrain shadow renderer; binary/probabilistic shadow mismatch; optional constraint registry; deterministic synthetic objective ordering and simple scale/offset search.

## Demonstrated claim

On a deterministic synthetic scene, the combined anchor/shadow objective prefers the known terrain to offset, scale, ridge and bump errors. Anchors identify absolute offset. Shadows add information about relative relief and localized structure. Offset/affine errors recover to numerical precision in this controlled fixture.

## Claims to avoid

No demonstrated real-satellite reconstruction improvement. No atmospheric simulator. No unique recovery guarantee. No calibrated confidence. No arbitrary full-raster optimizer. No model selection. No production integration. The synthetic ground-truth mask shares the renderer, so it verifies internal consistency only.

## Next validation

One real scene with audited shadow labels, sun geometry and calibration anchors, plus spatially separate elevation check points. Measure shadow consistency and elevation accuracy separately before claiming operational benefit.
