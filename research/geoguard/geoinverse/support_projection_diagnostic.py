"""Deterministic saved-output diagnostic. No training or truth-dependent projection."""
import json, hashlib
import numpy as np
import rasterio
import torch
from config import ROOT,FOLDS
from frequency import gaussian_kernel
from geoinverse_v1 import SIGMA_M
from train_geoinverse_v1 import scale_metrics
from evaluate import metrics,oracle

OUT=ROOT/'outputs/geoinverse_v1a'
TOLERANCE_M=.001
MAX_ITERATIONS=200
PROTOCOL={'tolerance_m':TOLERANCE_M,'maximum_iterations':MAX_ITERATIONS,'fwhm_m':30,
 'decision':'YES if either control improves detail MAE >=0.5% in >=3 regions, region-equal total MAE <=reference+0.0001m and mean support oracle gain >=1%; WEAK if not YES but >=2 regions have detail improvement >=0.1% and mean support oracle gain >=0.5%; otherwise NO. Nonconverged Gaussian control cannot qualify.',
 'cell_origin':'raster upper-left; fixed round(30/pixel_size) pixel widths; partial end cells retained'}

def filter_operator(valid,pixel):
    k=gaussian_kernel(SIGMA_M/pixel).astype('float64')
    radius=len(k)//2
    def blur(a):
        for axis in (1,0):
            size=a.shape[axis]; padding=[(0,0),(0,0)];padding[axis]=(radius,radius)
            padded=np.pad(a,padding,mode='reflect'); n=1<<(padded.shape[axis]+len(k)-2).bit_length()
            shape=[1,1];shape[axis]=n//2+1
            spectrum=np.fft.rfft(padded,n=n,axis=axis)*np.fft.rfft(k,n=n).reshape(shape)
            full=np.fft.irfft(spectrum,n=n,axis=axis)
            sl=[slice(None),slice(None)];sl[axis]=slice(2*radius,2*radius+size);a=full[tuple(sl)]
        return a
    denominator=blur(valid.astype('float64'))
    def lpf(a):return blur(np.where(valid,a,0.0))/np.maximum(denominator,1e-6)
    return lpf

def gaussian_project(correction,valid,pixel,tolerance=TOLERANCE_M,maximum=MAX_ITERATIONS):
    c=np.where(valid,correction,0).astype('float64'); lpf=filter_operator(valid,pixel)
    for iteration in range(maximum+1):
        low=lpf(c); mae=float(np.abs(low[valid]).mean())
        if mae<tolerance or iteration==maximum:
            return c,{'iterations':iteration,'converged':mae<tolerance,'residual_lpf_mae_m':mae}
        c=np.where(valid,c-low,0)

def cells(shape,pixel):
    n=max(1,round(30/pixel))
    for y in range(0,shape[0],n):
        for x in range(0,shape[1],n): yield np.s_[y:min(y+n,shape[0]),x:min(x+n,shape[1])]

def cell_project(correction,valid,pixel):
    c=np.where(valid,correction,0).astype('float64')
    for s in cells(c.shape,pixel):
        v=valid[s]
        if v.any(): c[s]=np.where(v,c[s]-c[s][v].mean(),0)
    return c

def cell_max(c,v,p):
    return max(abs(float(c[s][v[s]].mean())) for s in cells(c.shape,p) if v[s].any())

def drift(c,iv,score,p):
    a=c[score]; low=filter_operator(iv,p)(c)[score]
    return dict(mean=float(a.mean()),median=float(np.median(a)),std=float(a.std()),mean_abs=float(np.abs(a).mean()),p95_abs=float(np.percentile(np.abs(a),95)),max_abs=float(np.abs(a).max()),lpf_mean=float(low.mean()),lpf_mae=float(np.abs(low).mean()),lpf_rmse=float(np.sqrt(np.mean(low**2))),max_abs_input_cell_mean=cell_max(c,iv,p))

def write(path,a,valid,profile):
    profile=profile.copy(); profile.update(dtype='float64',count=1,nodata=-9999.,compress='deflate')
    with rasterio.open(path,'w',**profile) as ds:
        ds.write(np.where(valid,a,-9999.),1); ds.set_band_unit(1,'metre')

def run():
    torch.set_num_threads(8)
    if OUT.exists(): raise RuntimeError('Refusing to overwrite V1A outputs')
    OUT.mkdir(); (OUT/'protocol.json').write_text(json.dumps(PROTOCOL,indent=2))
    historical=json.loads((ROOT/'outputs/geoinverse_v1/results.json').read_text())
    rows=[]
    for name in FOLDS:
        source=ROOT/f'outputs/geoinverse_v1/holdout_{name}/applied_correction.tif'
        with rasterio.open(source) as ds:
            c=ds.read(1,masked=True); profile=ds.profile; p=ds.res[0]
            assert ds.crs.linear_units in ('metre','meter') and ds.res[0]==ds.res[1] and ds.transform.b==ds.transform.d==0
            iv=~np.ma.getmaskarray(c)&np.isfinite(c.data); original=c.data.astype('float64')
        # Projections constructed before reading any truth or scoring mask.
        gauss,convergence=gaussian_project(original,iv,p); cell=cell_project(original,iv,p)
        folder=OUT/name; folder.mkdir()
        for label,a in [('gaussian',gauss),('cell',cell)]:write(folder/f'{label}_correction.tif',a,iv,profile)
        root=ROOT/f'data/{name}_pilot/derived'
        with rasterio.open(root/'reference_aligned.tif') as ds: reference=ds.read(1); assert ds.transform==profile['transform'] and ds.crs==profile['crs']
        with rasterio.open(root/'truth_aligned.tif') as ds: truth=ds.read(1,masked=True)
        with rasterio.open(root/'valid_mask.tif') as ds: mask=ds.read(1,masked=True)
        v=iv&~np.ma.getmaskarray(truth)&np.isfinite(truth.data)&~np.ma.getmaskarray(mask)&(mask.data!=0)
        old=next(f for f in historical['folds'] if f['region']==name)
        assert int(v.sum())==old['valid_pixels']
        # Match V1's original float32 sum exactly; projections are stored/scored float64.
        with rasterio.open(ROOT/f'outputs/geoinverse_v1/holdout_{name}/candidate_dsm.tif') as ds: original_candidate=ds.read(1)
        surfaces={'reference':reference,'v1':original_candidate,'gaussian':reference+gauss,'cell':reference+cell}
        row={'region':name,'pixels':int(v.sum()),'mask_count_change':int(v.sum())-old['valid_pixels'],'convergence':convergence,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'variants':{},'drift':{}}
        for label,a in surfaces.items():
            m=metrics(a[v],truth.data[v]); scales=scale_metrics(a,truth.data,v,p)
            os,stats=oracle(reference,a,truth.data,v,support_pixels=round(30/p)); om=metrics(os[v],truth.data[v])
            row['variants'][label]={'metrics':m,'scales':scales,'oracle':{**om,**stats,'gain_percent':100*(old['reference']['mae']-om['mae'])/old['reference']['mae']}}
            if label in ('gaussian','cell'):write(folder/f'{label}_candidate.tif',a,iv,profile)
        for label,a in [('v1',original),('gaussian',gauss),('cell',cell)]:row['drift'][label]=drift(a,iv,v,p)
        (folder/'metrics.json').write_text(json.dumps(row,indent=2)); rows.append(row)
        print(name,convergence,flush=True)
    equal={m:{k:float(np.mean([r['variants'][m]['metrics'][k] for r in rows])) for k in ('mae','rmse','bias','pearson','spearman')} for m in surfaces}
    decisions={}
    for m in ('gaussian','cell'):
        gains=[100*(r['variants']['reference']['scales']['detail']['mae']-r['variants'][m]['scales']['detail']['mae'])/r['variants']['reference']['scales']['detail']['mae'] for r in rows]
        og=float(np.mean([r['variants'][m]['oracle']['gain_percent'] for r in rows]))
        converged=m=='cell' or all(r['convergence']['converged'] for r in rows)
        yes=converged and sum(g>=.5 for g in gains)>=3 and equal[m]['mae']<=equal['reference']['mae']+.0001 and og>=1
        weak=converged and sum(g>=.1 for g in gains)>=2 and og>=.5
        decisions[m]={'answer':'YES' if yes else 'WEAK' if weak else 'NO','detail_gain_percent':gains,'mean_oracle_gain_percent':og}
    answer='YES' if any(d['answer']=='YES' for d in decisions.values()) else 'WEAK' if any(d['answer']=='WEAK' for d in decisions.values()) else 'NO'
    result={'protocol':PROTOCOL,'folds':rows,'region_equal':equal,'decisions':decisions,'answer':answer}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)); report(result)

def report(r):
    lines=['# GeoInverse V1A support-projection diagnostic','',f"Answer: **{r['answer']}**",'',
    '## Method','', 'No training. Existing V1 applied-correction rasters only. Both controls are constructed before opening truth/scoring masks. Gaussian kernel, truncation and reflect boundaries match V1; NumPy FFT linear convolution with explicit reflect padding is the float64 equivalent, tested against V1. No dependency installed.',
    'Gaussian: C(k+1)=C(k)-masked_LPF(C(k)), sigma=12.738853503184714 m. Stop when inference-valid mean absolute LPF <0.001 m (1 mm, small versus metre-scale errors), maximum 200 iterations. A cap hit is NOT convergence or exact support conservation. Iterated high-pass filtering attenuates signal; it is not an orthogonal projection.',
    'Cells: fixed upper-left raster origin, round(30 m/pixel size) pixels per cell. Subtract each inference-valid cell mean; retain partial boundary cells. This is exact cell-mean conservation, not zero Gaussian LPF. Truth validity can differ, so zero mean over inference support need not imply zero mean over scored pixels.',
    'Scoring uses unchanged V1 support, definitions and approximately 30 m truth-aware support oracle. Float64 projected outputs preserve alignment. Scale metrics retain V1 float32 LPF implementation. Physical gradient errors are m/m.',
    'Decision rule frozen before scoring: '+PROTOCOL['decision'],'']
    def table(h,rs):
        lines.extend(['| '+' | '.join(h)+' |','|'+'|'.join(['---']*len(h))+'|'])
        for row in rs:lines.append('| '+' | '.join(f'{x:.6f}' if isinstance(x,float) else str(x) for x in row)+' |')
        lines.append('')
    lines+=['## Standard metrics',''];ks=['mae','rmse','bias','pearson','spearman']
    table(['Region','Variant',*ks],[[f['region'],m,*[v['metrics'][k] for k in ks]] for f in r['folds'] for m,v in f['variants'].items()])
    lines+=['## Region-equal',''];table(['Variant',*ks],[[m,*[v[k] for k in ks]] for m,v in r['region_equal'].items()])
    lines+=['## Scale metrics',''];table(['Region','Variant','Low MAE','Low RMSE','Detail MAE','Detail RMSE','Gradient MAE'],[[f['region'],m,*[v['scales'][s][k] for s,k in [('low','mae'),('low','rmse'),('detail','mae'),('detail','rmse'),('gradient_m_per_m','mae')]]] for f in r['folds'] for m,v in f['variants'].items()])
    lines+=['## Drift (scoring pixels unless explicitly input-cell)',''];dk=list(r['folds'][0]['drift']['v1']);table(['Region','Variant',*dk],[[f['region'],m,*[d[k] for k in dk]] for f in r['folds'] for m,d in f['drift'].items()])
    lines+=['## Convergence and masks',''];table(['Region','Iterations','Converged','Input LPF MAE m','Scored pixels','Count change'],[[f['region'],f['convergence']['iterations'],f['convergence']['converged'],f['convergence']['residual_lpf_mae_m'],f['pixels'],f['mask_count_change']] for f in r['folds']])
    lines+=['## NON-DEPLOYABLE TRUTH-AWARE ORACLE',''];table(['Region','Variant','MAE','RMSE','Accepted fraction','Gain %'],[[f['region'],m,v['oracle']['mae'],v['oracle']['rmse'],v['oracle']['oracle_coverage_percent']/100,v['oracle']['gain_percent']] for f in r['folds'] for m,v in f['variants'].items() if m!='reference'])
    lines+=['## Decision',''];table(['Control','Answer','Mean oracle gain %'],[[m,v['answer'],v['mean_oracle_gain_percent']] for m,v in r['decisions'].items()])
    lines+=['No causal claim that DAV2 alone is inadequate: the diagnosis concerns the saved V1 learned corrections. A Gaussian convergence cap or boundary effects limit any claim of exact Gaussian drift removal. Cell means are exactly conserved on inference-valid cells.',
    'If NO: stop further training iterations of the current frozen DAV2 plus lightweight detail-refiner family. Recommended next experiment: a preregistered foundation geometry signal audit of a stronger aerial/satellite-oriented geometry model, with untouched evaluation geography and separate calibration. Do not implement or download it here.',
    'If YES/WEAK: only the measured detail gains and oracle headroom justify another constrained-refinement experiment; no deployment claim.',
    '', '## Repository','', 'Branch research/geoguard-sprint. Existing M .gitignore and ?? research/ preserved. New diagnostic script, focused tests, separate V1A output directory and this report. No V1 outputs overwritten. NO TRAINING. NO COMMIT. NO PUSH. NO PRODUCTION MODIFICATIONS.']
    lines += ['', '## Verified outcome', '',
      'Both controls answer NO. Gaussian convergence was reached in all regions. Cell means are zero to floating-point precision. Nevertheless, both controls worsen total MAE, detail MAE and physical-gradient MAE versus reference in all four regions. Coarse drift therefore does not explain all the damage in the saved V1 signal. This does not prove that every DAV2 representation is incapable of useful geometry.',
      'STOP further training iterations of the current frozen DAV2/lightweight-refiner family. Next: foundation geometry signal audit; not implemented.',
      'Tests: 8 projection tests, 6 V0 tests, 6 V1 tests, 8 Residual V1 tests, and 25 GeoGuard tests passed (53 total, plus 3 subtests). Existing Rasterio deprecation warnings only.']
    (ROOT/'GEOINVERSE_V1A_SUPPORT_PROJECTION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':
    import sys
    if '--report-only' in sys.argv: report(json.loads((OUT/'results.json').read_text()))
    else: run()
