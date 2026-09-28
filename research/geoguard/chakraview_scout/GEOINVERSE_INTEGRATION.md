# GeoInverse / Response Intelligence integration contract

No existing GeoInverse, Manish audit or Ayush module is modified. Caller supplies aligned arrays plus grid, CRS, verified units, validity, source/version/hash and timestamps. Reject grid mismatch, missing units and unavailable evidence rather than infer metre accuracy from a projected CRS.

Evidence registry mappings, only when genuinely supplied:

- low evidence coverage -> 1 - normalized coverage;
- missing/remote anchors -> normalized distance to valid anchors (caller defines distance saturation in metres);
- shadow disagreement -> documented normalized residual, NOT raw signed residual;
- foundation/reference disagreement -> normalized absolute disagreement, explicitly a proxy, not posterior model uncertainty;
- supplied predictive uncertainty -> documented calibration/scale and source, never fabricated.

Pass those named [0,1] arrays to `evidence_map`. Preserve unavailable sources as absent, not zero confidence claims. Response Intelligence can supply relevance arrays, reachable/allowed masks and accumulated fixed-base access cost. It owns slope, roughness, routes, staging and attention; Scout consumes rather than recreates these. A ground candidate with no known reachability/cost must be rejected.

Registry -> U -> ranked observation -> human acceptance -> actual measured observation with footprint/quality -> GeoInverse evidence registry -> a separately authorized GeoInverse update -> refreshed geometry/evidence -> rerank. Marking a point observed alone does not recover metric gauge or authorize model updates. In simulation only, visible cells use an assumed retention multiplier. Real field observations default to no uncertainty reduction unless quality/footprint is supplied and verified.

Anchor measurements need unit, datum, CRS, uncertainty, instrument and coordinate metadata. Photos need optional opaque photo_reference and consent/privacy handling; no victim/facial identification. New evidence is not calibration truth automatically. Retain evaluation splits; do not use withheld truth for ranking.
