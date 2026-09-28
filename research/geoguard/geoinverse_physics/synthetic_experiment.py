"""Deterministic synthetic objective ordering and simple gauge recovery."""
import json,time
from pathlib import Path
import numpy as np
if __package__:
    from .anchors import Anchor,anchor_loss,fit_gauge
    from .shadows import render_shadow,shadow_metrics
    from .constraints import Constraint,ConstraintRegistry
else:
    from anchors import Anchor,anchor_loss,fit_gauge
    from shadows import render_shadow,shadow_metrics
    from constraints import Constraint,ConstraintRegistry

def terrain(size=48):
    y,x=np.indices((size,size));z=100+8*np.exp(-((x-15)**2+(y-18)**2)/60)+6*np.exp(-((x-31)**2)/7)*np.exp(-((y-27)**2)/170)
    z[10:18,30:37]+=12
    return z

def run():
    start=time.perf_counter();truth=terrain();valid=np.ones(truth.shape,bool);sun={'azimuth':110.,'elevation':20.,'pixel_size':1.}
    observation=render_shadow(truth,valid,**dict(azimuth_deg=sun['azimuth'],elevation_deg=sun['elevation'],pixel_size_m=1.))['shadow']
    anchors=[Anchor(float(truth[y,x]),row=y,col=x,uncertainty=.5,source='synthetic known control') for y in (6,14,24,35,43) for x in (6,15,31,40)]
    y,x=np.indices(truth.shape);ridge=6*np.exp(-((x-31)**2)/7)*np.exp(-((y-27)**2)/170);bump=8*np.exp(-((x-22)**2+(y-34)**2)/10)
    candidates={'truth':truth,'offset_plus_5':truth+5,'relief_scale_1_4':100+1.4*(truth-100),'ridge_plus_6':truth+ridge,'local_bump':truth+bump}
    registry=ConstraintRegistry([Constraint('anchor',1.,anchors),Constraint('shadow',10.,observation,sun)])
    records={}
    for name,z in candidates.items():
        objective=registry.objective(z,valid);pred=render_shadow(z,valid,110,20,1.)
        records[name]={'mae_m':float(np.abs(z-truth).mean()),'objective':objective,'shadow_metrics':shadow_metrics(pred['shadow'],observation,pred['known'])}
    shifted,offset_fit=fit_gauge(truth+5,valid,anchors)
    scaled,affine_fit=fit_gauge(100+1.4*(truth-100)+5,valid,anchors,'affine')
    # Finite grid-search optimizer over physically meaningful scale and offset.
    initial=100+1.4*(truth-100)+5;best=None;evaluations=0
    for scale in (1/1.4,.8,.9,1.):
        relief=100+scale*(initial-100)
        aligned,fit=fit_gauge(relief,valid,anchors)
        obj=registry.objective(aligned,valid);evaluations+=1
        if best is None or obj['total']<best['loss']:best={'scale':scale,'offset':fit['parameters'][0],'loss':obj['total'],'mae_m':float(np.abs(aligned-truth).mean())}
    return {'seed':'no randomness','sun':sun,'shape':list(truth.shape),'anchors':len(anchors),'candidates':records,'offset_recovery':{**offset_fit,'max_error_m':float(np.max(np.abs(shifted-truth)))},'affine_recovery':{**affine_fit,'max_error_m':float(np.max(np.abs(scaled-truth)))},'combined_grid_recovery':best,'evaluations':evaluations,'runtime_seconds':time.perf_counter()-start,'identifiability':'Uniform offset leaves shadows unchanged. Synthetic shared renderer is an internal consistency check, not independent physical validation.'}

if __name__=='__main__':
    result=run();path=Path(__file__).parent/'synthetic_results.json'
    path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
