# GeoGuard-SC benefit contract

This document defines future labels and operational states. It does not describe a trained model or measured result.

## Surfaces

- Reference surface: `r`
- AI candidate: `q`
- Independent truth: `y`

All three surfaces must use a scientifically comparable target type, horizontal alignment, vertical datum, units, and valid-support mask. A DTM, DSM, AGL/nDSM, or camera-depth map must not be compared as if those quantities were interchangeable.

## Pixel benefit

For every valid truth pixel `i`, absolute-error benefit is:

`b_i = |r_i - y_i| - |q_i - y_i|`

- `b_i > 0`: the AI candidate improved the reference at that pixel.
- `b_i < 0`: the AI candidate harmed the result at that pixel.
- `b_i = 0`: equal absolute error at the recorded precision.

Pixels without valid comparable truth are excluded from the label denominator, not assigned zero benefit.

## Reference-support-cell benefit

For reference support cell `C` with valid set `V_C`:

`B_C = (1 / |V_C|) * sum(i in V_C) b_i`

If pixels have unequal ground area, use documented area weights instead of an unweighted mean. Record valid coverage in every cell and reject labels below a preregistered truth-coverage threshold. The future gate must be trained on the finalized, support-consistent candidate rather than a raw candidate that changes after gating.

## Future operational states

**REFINE** — the candidate is expected to improve the reference by more than the chosen evidence/risk margin.

**RETAIN** — AI improvement is not sufficiently supported, so the correction is not applied.

**FLAG** — the reference, candidate, alignment, metadata, or domain support is insufficiently trustworthy for authoritative use.

**RETAIN DOES NOT MEAN THE REFERENCE IS CORRECT.**

**FLAG DOES NOT REMOVE THE AREA FROM WHOLE-MAP EVALUATION.**

Whole-map accuracy uses every valid truth location with the delivered fallback policy. Selective accuracy and coverage are additional diagnostics and must not replace whole-map reporting.
