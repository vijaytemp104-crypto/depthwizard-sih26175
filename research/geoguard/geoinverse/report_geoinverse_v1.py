"""Render existing V1 results without rerunning training or changing decisions."""
import json
import numpy as np
from config import ROOT
from train_geoinverse_v1 import OUT

def main():
    r=json.loads((OUT/'results.json').read_text()); old=json.loads((ROOT/'outputs/geoinverse_v0/results.json').read_text())
    lines=['# GeoInverse V1 — support-conserving detail injection','',f"Decision: **{r['decision']}**",'',
      '## PROTOCOL CORRECTIONS','',
      'GeoInverse V0 used the geographically held-out region for checkpoint selection/early stopping and therefore its previously reported fold results are development-validation results rather than untouched geographic test results.',
      'V0 preprocessing allowed truth availability to influence input-validity preprocessing, although truth elevation values were not supplied as model features.',
      'Residual Refiner V1 audit: both issues also occur in residual/train.py and residual/dataset.py. Its numbers are HISTORICAL DEVELOPMENT-VALIDATION RESULTS. Neither historical experiment was retrained or modified.',
      'V0 seed was 20260926. Corrected V1 uses authorized seed 20260924, fixed six epochs, final epoch-6 checkpoint, no validation-based selection, and no held-out scene loading until training completes. The four pilots were already explored in earlier research, so these are corrected per-fold geographic tests, not a newly sealed independent blind benchmark.',
      'Input validity depends only on RGB/reference/DAV2 masks and finite values. Filling, normalization, gradients and inference filtering use input validity. Truth masks control only supervision/scoring. Existing evaluation masks are compared explicitly below.',
      '', '## Architecture and exact loss','',
      'Eight V0 evidence channels; three-level U-Net with GroupNorm/SiLU, base width 24; decoder raw-detail and sigmoid weight heads. No delta_low head. Zero raw-head initialization; initial weight 0.05. DAV2 frozen; no semantic model.',
      'd = raw - LPF(raw); c = weight*d; prediction = reference+c. LPF is differentiable normalized masked Gaussian with 30 m FWHM, sigma 12.738853503184714 m, truncation at ceil(3 sigma_pixels), separable reflect padding. This attenuates low frequencies; it is not an exact zero-coarse-content projection.',
      'L = L_final + 0.50 L_detail + 0.05 L_support + 0.02 L_preserve + 0.01 L_edge.',
      'L_final = masked SmoothL1(prediction,truth,beta=2 m). L_detail = masked SmoothL1(d, residual-LPF(residual),beta=2 m). L_support = mean(abs(LPF(c))) at supervised valid locations, with input-valid filtering support. L_preserve = mean(abs(c)/(1+abs(truth-reference)/1 m)); truth weighting exists only in the training loss. L_edge = mean absolute finite-difference gradient error across valid neighbour pairs, divided by physical pixel spacing (m/m), averaged over X/Y.',
      'Training applies the filter within 256-pixel patches with reflected boundaries. Inference first averages overlapping raw/weight predictions, then filters the full scene using only input validity. This avoids patchwise correction seams but is a documented boundary/context difference.',
      'V0 feature-gradient scaling is retained (per grid step); new reported physical gradient metrics explicitly divide by raster spacing. Low/detail evaluation uses the same scoring support for prediction and truth.',
      '', '## Fixed configuration and operational criteria','',
      'CPU float32; deterministic PyTorch algorithms enabled; Python/NumPy/Torch seeds fixed. Batch 4; patch 256; stride 192; minimum valid patch fraction 0.8; AdamW lr 0.001, weight decay 1e-5; six epochs. Determinism is intended for this software/hardware, not guaranteed bitwise across platforms.',
      'Numerical interpretations were frozen in protocol.json before training: region-equal MAE tolerance 0.0001 m; Polk maximum MAE degradation 5%; Wake/Humboldt minimum gain 0.5%; each region low-frequency MAE increase <=0.01 m; at least two detail-MAE gains >0.0001 m; mean 30 m support oracle gain >=1%. GO requires all six; MARGINAL requires the aggregate/Polk/low-frequency safety criteria but misses usefulness criteria; otherwise NO-GO.',
      '', '## Per-region standard metrics','']
    def table(headers,rows):
        lines.append('| '+' | '.join(headers)+' |');lines.append('|'+'|'.join(['---']*len(headers))+'|')
        for row in rows: lines.append('| '+' | '.join(f'{x:.6f}' if isinstance(x,float) else str(x) for x in row)+' |')
        lines.append('')
    keys=['mae','rmse','bias','pearson','spearman']
    table(['Region','Method',*keys],[[f['region'],m,*[f[m][k] for k in keys]] for f in r['folds'] for m in ('reference','v1')])
    lines+=['## Region-equal metrics',''];table(['Method',*keys],[[m,*[v[k] for k in keys]] for m,v in r['region_equal'].items()])
    lines+=['## Scale-separated metrics','', 'Elevation errors are metres; gradient errors are m/m, not slope-angle errors.']
    table(['Region','Method','Low MAE','Low RMSE','Detail MAE','Detail RMSE','Gradient MAE','Gradient RMSE'],[[f['region'],m,*[f[m][scale][k] for scale in ('low','detail','gradient_m_per_m') for k in ('mae','rmse')]] for f in r['folds'] for m in ('scale_reference','scale_v1')])
    table(['Region-equal method','Low MAE','Low RMSE','Detail MAE','Detail RMSE','Gradient MAE','Gradient RMSE'],[[m,*[float(np.mean([f[m][scale][k] for f in r['folds']])) for scale in ('low','detail','gradient_m_per_m') for k in ('mae','rmse')]] for m in ('scale_reference','scale_v1')])
    lines+=['## Correction drift',''];ck=list(r['folds'][0]['correction']);table(['Region',*ck],[[f['region'],*[f['correction'][k] for k in ck]] for f in r['folds']])
    lines+=['V0 Polk mean delta_low was approximately +1.116 m. Compare directly with V1 mean correction and LPF correction above. Weight modulation can still introduce drift; the support penalty does not guarantee exactly zero drift.','', '## Learned detail injection weight',''];wk=list(r['folds'][0]['weight']);table(['Region',*wk],[[f['region'],*[f['weight'][k] for k in wk]] for f in r['folds']])
    lines+=['These weights are not calibrated confidence.','', '## NON-DEPLOYABLE TRUTH-AWARE ORACLE','', 'Both pixel oracle and approximately 30 m support-cell oracle are reported. Historical oracle comparisons use support-cell means, not the more optimistic pixel oracle.']
    table(['Region','Support MAE','Support RMSE','Accepted %','Gain %','Pixel MAE','Pixel RMSE','Pixel accepted fraction'],[[f['region'],*[f['oracle_support'][k] for k in ('mae','rmse','oracle_coverage_percent','improvement_percent')],*[f['oracle_pixel'][k] for k in ('mae','rmse','accepted_fraction')]] for f in r['folds']])
    lines.append(f"Region-equal support-oracle gain: {np.mean([f['oracle_support']['improvement_percent'] for f in r['folds']]):.6f}%.")
    lines+=['## Historical baseline comparison','', 'Affine DAV2 is an historical calibration baseline; Residual V1 and GeoInverse V0 are HISTORICAL DEVELOPMENT-VALIDATION RESULTS, not equivalent corrected geographic test evidence.']
    table(['Region','Reference MAE','Affine DAV2 MAE','Residual V1 MAE (historical)','GeoInverse V0 MAE (historical)','GeoInverse V1 MAE'],[[f['region'],f['reference']['mae'],o['affine_dav2']['mae'],o['residual_v1']['mae'],o['geoinverse_v0']['mae'],f['v1']['mae']] for f,o in zip(r['folds'],old['folds'])])
    lines+=['## Criteria',''];table(['Criterion','Result'],[[k,'PASS' if v else 'FAIL'] for k,v in r['criteria'].items()])
    lines+=['## Masks and execution',''];table(['Region','Scored pixels','Changed scoring pixels','Training patches','Parameters','Runtime seconds'],[[f['region'],f['valid_pixels'],f['score_mask_changed_pixels'],t['patches'],t['parameters'],t['runtime_seconds']] for f,t in zip(r['folds'],r['training'])])
    lines+=['## Limitations and next experiment','',
      'A 1 m output grid does not establish 1 m effective resolution. GLO-30 is a DSM reference, not truth. LiDAR maximum-Z DSM truth has acquisition/vegetation mismatch and unquantified vertical transformation uncertainty from pilot preparation. No DTM/nDSM claims are made.',
      'This single experiment cannot distinguish inadequate DAV2 evidence, training diversity, predictability, or network capacity. Reference preservation alone is not useful reconstruction evidence.',
      'Observed result: all six criteria fail. Detail MAE and physical gradient MAE worsen in all four regions. Only Larimer total MAE improves, accompanied by improved low-frequency MAE but worse detail error; this does not demonstrate successful image-derived detail reconstruction. Polk mean correction -0.274174 m is smaller in magnitude than V0 delta_low +1.116 m, but remains damaging. The best supported failure is residual coarse drift and harmful detail from this particular soft-constrained reconstruction; model/data insufficiency hypotheses remain unresolved.',
      'Recommended next experiment, not implemented: preregister an ablation applying a differentiable exact zero-mean projection to the FINAL weighted correction in fixed physically defined 30 m support cells, with a no-projection control, fixed six-epoch training and unchanged data. Evaluate boundary artifacts, coarse drift, detail metrics and gradients. This directly tests whether enforcing support conservation after weighting resolves the demonstrated drift; do not tune this variant on the present held-out scores or claim that removing drift guarantees useful detail.',
      '', '## Repository and verification','',
      'Branch research/geoguard-sprint. Existing status: M .gitignore; ?? research/. No historical files modified. New files: geoinverse/geoinverse_v1.py, dataset_v1.py, train_geoinverse_v1.py, report_geoinverse_v1.py; tests/test_geoinverse_v1.py; this report; outputs/geoinverse_v1 protocol/results and per-fold epoch6.pt, training.json, metrics.json and four GeoTIFFs.',
      'NO COMMIT. NO PUSH. NO PRODUCTION MODIFICATIONS. No GeoGuard training, gating, foundation-model downloads, or blind-test county access.', '']
    lines += ['Tests: V1 6 passed; V0 6 passed; Residual V1 8 passed; GeoGuard 25 passed plus 3 subtests. Legacy tests initially hit Windows temporary-directory permissions, then passed using a research-local basetemp. Only existing Rasterio deprecation warnings remained. Python compilation passed.', '']
    (ROOT/'GEOINVERSE_V1_RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
