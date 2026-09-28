"""Geometric sun-ray occlusion on a north-up projected metre grid."""
import numpy as np

def render_shadow(z,valid,azimuth_deg,elevation_deg,pixel_size_m=None,transform=None):
    if z.ndim!=2 or valid.shape!=z.shape:raise ValueError('Surface/mask shape mismatch')
    if not(0<elevation_deg<=90) or not np.isfinite(azimuth_deg):raise ValueError('Sun elevation must be (0,90] degrees')
    if transform is not None:
        if transform.b!=0 or transform.d!=0 or transform.a<=0 or transform.e>=0:raise ValueError('North-up raster transform required')
        dx,dy=transform.a,-transform.e
    else:dx=dy=pixel_size_m
    if dx is None or dy is None or min(dx,dy)<=0:raise ValueError('Positive physical metre spacing required')
    valid=valid&np.isfinite(z);shadow=np.zeros(z.shape,bool);known=valid.copy();outside=np.zeros(z.shape,bool)
    if elevation_deg==90:return {'shadow':shadow,'known':known,'domain_edge_assumption':valid.copy()}
    angle=np.deg2rad(azimuth_deg%360);sx=np.sin(angle);sy=-np.cos(angle)
    step=min(dx,dy)/2;rise=np.tan(np.deg2rad(elevation_deg))
    yy,xx=np.indices(z.shape);seen=set()
    for distance in np.arange(step,np.hypot(z.shape[0]*dy,z.shape[1]*dx)+step,step):
        dr=int(np.rint(distance*sy/dy));dc=int(np.rint(distance*sx/dx))
        if (dr,dc)==(0,0) or (dr,dc) in seen:continue
        seen.add((dr,dc));ry=yy+dr;cx=xx+dc;inside=(ry>=0)&(ry<z.shape[0])&(cx>=0)&(cx<z.shape[1])
        sampled=z[np.clip(ry,0,z.shape[0]-1),np.clip(cx,0,z.shape[1]-1)]
        ray_valid=valid[np.clip(ry,0,z.shape[0]-1),np.clip(cx,0,z.shape[1]-1)]
        known&=~(inside&~ray_valid)
        outside|=~inside
        physical=np.hypot(dr*dy,dc*dx)
        shadow|=inside&ray_valid&(sampled>z+physical*rise+1e-9)
    # A known blocker establishes shadow even if another ray sample is nodata.
    known=(known|shadow)&valid
    return {'shadow':shadow&valid,'known':known,'domain_edge_assumption':outside&valid}

def shadow_metrics(predicted,observed,valid):
    p=predicted[valid].astype(bool);o=observed[valid].astype(bool)
    if not len(p):raise ValueError('No observed shadow support')
    tp=int(np.sum(p&o));fp=int(np.sum(p&~o));fn=int(np.sum(~p&o));union=tp+fp+fn
    precision=tp/(tp+fp) if tp+fp else (1. if not o.any() else 0.)
    recall=tp/(tp+fn) if tp+fn else 1.
    return {'iou':tp/union if union else 1.,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0.,'disagreement':float(np.mean(p!=o)),'pixels':len(p)}

def shadow_loss(predicted,observed,valid):
    if not np.any(valid):raise ValueError('No shadow evidence')
    o=observed[valid]
    if not np.isfinite(o).all() or np.any((o<0)|(o>1)):raise ValueError('Observed probabilities must be in [0,1]')
    return float(np.mean(np.abs(predicted[valid].astype(float)-o)))
