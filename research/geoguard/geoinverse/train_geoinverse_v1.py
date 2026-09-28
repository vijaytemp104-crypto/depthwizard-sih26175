"""Fixed six-epoch V1 experiment. Never select models using test data."""
import json, random, time, sys
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
from config import ROOT,FOLDS
from dataset import starts
from dataset_v1 import load,Patches
from geoinverse_v1 import GeoInverseV1,loss,constrain,lowpass,SIGMA_M
from evaluate import metrics,oracle,_write

OUT=ROOT/'outputs'/'geoinverse_v1'
PROTOCOL={'seed':20260924,'epochs':6,'patch':256,'stride':192,'batch':4,'lr':.001,'weight_decay':1e-5,
 'criteria':{'region_equal_mae_tolerance_m':.0001,'polk_max_relative_mae_degradation':.05,'wake_or_humboldt_min_relative_gain':.005,'all_regions_low_mae_max_increase_m':.01,'detail_improvement_regions':2,'support_oracle_mean_gain_percent':1.0}}

def lp(a,v,pixel):
    with torch.no_grad(): return lowpass(torch.from_numpy(a.astype('float32'))[None,None],torch.from_numpy(v)[None,None],pixel)[0,0].numpy()

def errors(a,b):
    e=a.astype('float64')-b.astype('float64'); return {'mae':float(np.abs(e).mean()),'rmse':float(np.sqrt(np.mean(e*e)))}

def scale_metrics(a,t,v,pixel):
    al=lp(a,v,pixel); tl=lp(t,v,pixel)
    gradients=[]
    for axis in (0,1):
        m=np.take(v,range(1,v.shape[axis]),axis=axis)&np.take(v,range(v.shape[axis]-1),axis=axis)
        gradients.append(((np.diff(a,axis=axis)-np.diff(t,axis=axis))/pixel)[m])
    g=np.concatenate(gradients).astype('float64')
    return {'low':errors(al[v],tl[v]),'detail':errors((a-al)[v],(t-tl)[v]),'gradient_m_per_m':{'mae':float(np.abs(g).mean()),'rmse':float(np.sqrt(np.mean(g*g)))}}

def evaluate_fold(name,model):
    s=load(name)  # first test-region load is after epoch 6
    sums=[np.zeros(s.valid.shape,'float64') for _ in range(2)]; count=np.zeros(s.valid.shape)
    model.eval()
    with torch.no_grad():
        for y in starts(s.valid.shape[0],256,192):
            for x in starts(s.valid.shape[1],256,192):
                outputs=model(torch.from_numpy(s.features[:,y:y+256,x:x+256][None]))
                for total,o in zip(sums,outputs): total[y:y+256,x:x+256]+=o[0,0].numpy()
                count[y:y+256,x:x+256]+=1
        raw,w=[(a/count).astype('float32') for a in sums]
        detail,applied=constrain(torch.from_numpy(raw)[None,None],torch.from_numpy(w)[None,None],torch.from_numpy(s.input_valid)[None,None],s.pixel)
    correction=applied[0,0].numpy(); candidate=s.reference+correction; v=s.valid
    ref=metrics(s.reference[v],s.truth[v]); pred=metrics(candidate[v],s.truth[v])
    benefit=np.abs(s.reference[v]-s.truth[v])-np.abs(candidate[v]-s.truth[v])
    oracle_surface,cells=oracle(s.reference,candidate,s.truth,v,support_pixels=round(30/s.pixel))
    om=metrics(oracle_surface[v],s.truth[v]); pixel_oracle=np.where(np.abs(candidate-s.truth)<np.abs(s.reference-s.truth),candidate,s.reference)
    c=correction[v].astype('float64'); lc=lp(correction,s.input_valid,s.pixel)[v]; weights=w[v]
    result={'region':name,'reference':ref,'v1':pred,'score_mask_changed_pixels':s.mask_difference,'valid_pixels':int(v.sum()),
      'scale_reference':scale_metrics(s.reference,s.truth,v,s.pixel),'scale_v1':scale_metrics(candidate,s.truth,v,s.pixel),
      'correction':{'mean':float(c.mean()),'median':float(np.median(c)),'std':float(c.std()),'mean_abs':float(np.abs(c).mean()),'p95_abs':float(np.percentile(np.abs(c),95)),'max_abs':float(np.abs(c).max()),'lpf_mean':float(lc.mean()),'lpf_mae':float(np.abs(lc).mean()),'lpf_rmse':float(np.sqrt(np.mean(lc*lc)))},
      'weight':{'mean':float(weights.mean()),'median':float(np.median(weights)),'std':float(weights.std()),'p05':float(np.percentile(weights,5)),'p95':float(np.percentile(weights,95)),'benefit_correlation':float(np.corrcoef(weights,benefit)[0,1])},
      'oracle_support':{**om,**cells,'improvement_percent':100*(ref['mae']-om['mae'])/ref['mae']},
      'oracle_pixel':{**metrics(pixel_oracle[v],s.truth[v]),'accepted_fraction':float((benefit>0).mean())}}
    d=OUT/f'holdout_{name}'
    for filename,a,units in [('candidate_dsm.tif',candidate,'metre'),('applied_correction.tif',correction,'metre'),('raw_detail.tif',raw,'metre'),('weight_detail.tif',w,'dimensionless')]: _write(d/filename,a,s.input_valid,s.profile,units)
    (d/'metrics.json').write_text(json.dumps(result,indent=2))
    return result

def main():
    if '--summary-only' in sys.argv:
        summarize([json.loads((OUT/f'holdout_{n}'/'training.json').read_text()) for n in FOLDS], [json.loads((OUT/f'holdout_{n}'/'metrics.json').read_text()) for n in FOLDS])
        return
    torch.set_num_threads(8); torch.use_deterministic_algorithms(True)
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'protocol.json').exists(): raise RuntimeError('Existing V1 run; refusing overwrite')
    (OUT/'protocol.json').write_text(json.dumps(PROTOCOL,indent=2))
    rows=[]; training=[]
    for name,regions in FOLDS.items():
        random.seed(PROTOCOL['seed']); np.random.seed(PROTOCOL['seed']); torch.manual_seed(PROTOCOL['seed'])
        ds=Patches([load(n) for n in regions]); loader=DataLoader(ds,batch_size=4,shuffle=True,generator=torch.Generator().manual_seed(PROTOCOL['seed']))
        model=GeoInverseV1(); opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=1e-5)
        history=[]; start=time.perf_counter()
        for epoch in range(1,7):
            model.train(); vals=[]
            for batch in loader:
                opt.zero_grad(); total,components=loss(model,batch)
                if not torch.isfinite(total): raise RuntimeError('Nonfinite training loss')
                total.backward(); opt.step(); vals.append([float(total.detach()),*components.detach().tolist()])
            row={'epoch':epoch,'losses':np.mean(vals,axis=0).tolist()}; history.append(row); print(name,json.dumps(row),flush=True)
        d=OUT/f'holdout_{name}'; d.mkdir(); torch.save(model.state_dict(),d/'epoch6.pt')
        tr={'region':name,'train_regions':regions,'patches':len(ds),'parameters':sum(p.numel() for p in model.parameters()),'runtime_seconds':time.perf_counter()-start,'history':history,'checkpoint_epoch':6}
        (d/'training.json').write_text(json.dumps(tr,indent=2)); training.append(tr)
        rows.append(evaluate_fold(name,model))
    summarize(training,rows)

def summarize(training,rows):
    equal={method:{metric:float(np.mean([r[method][metric] for r in rows])) for metric in ('mae','rmse','bias','pearson','spearman')} for method in ('reference','v1')}
    polk=next(r for r in rows if r['region']=='polk'); criteria=PROTOCOL['criteria']
    passes={'region_equal_mae':equal['v1']['mae']<=equal['reference']['mae']+.0001,
     'polk':polk['v1']['mae']<=polk['reference']['mae']*1.05,
     'wake_or_humboldt':any(r['v1']['mae']<=r['reference']['mae']*.995 for r in rows if r['region'] in ('wake','humboldt')),
     'low_frequency':all(r['scale_v1']['low']['mae']<=r['scale_reference']['low']['mae']+.01 for r in rows),
     'detail_two_regions':sum(r['scale_v1']['detail']['mae']<r['scale_reference']['detail']['mae']-.0001 for r in rows)>=2,
     'oracle':bool(np.mean([r['oracle_support']['improvement_percent'] for r in rows])>=1)}
    decision='GO' if all(passes.values()) else ('MARGINAL' if passes['region_equal_mae'] and passes['polk'] and passes['low_frequency'] else 'NO-GO')
    result={'protocol':PROTOCOL,'training':training,'folds':rows,'region_equal':equal,'criteria':passes,'decision':decision}
    (OUT/'results.json').write_text(json.dumps(result,indent=2)); print('COMPLETE',decision,flush=True)

if __name__=='__main__': main()
