# Optional change-aware relevance

“Change detection identifies where something changed. ChakraVIEW Scout decides which changed/uncertain location should be observed first.”

Input: `change_score[y,x]`, finite [0,1], same grid, with modality (pre/post optical, SAR or supplied foundation output), source/model/version, acquisition timestamps, validity and normalization metadata. Caller handles clouds, registration and known artefacts; missing/invalid pixels must not be silently labelled unchanged. No change detector is trained here.

`relevance_map(..., change_score=C, change_weight=w)` computes `clip(R_existing + w C, 0, 1)` and records the source. Prototype expects finite aligned input; caller must explicitly restrict valid mission support or reject missing values. Change is not disaster severity or proof of damage. Freeze w on development data; evaluate its usefulness independently. No production API or contracts are changed.
