"""General sparse controls and robust geodetic gauge recovery."""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Anchor:
    elevation: float
    row: float | None = None
    col: float | None = None
    x: float | None = None
    y: float | None = None
    uncertainty: float = 1.0
    source: str = 'unspecified'

def huber(residual,delta=1.0):
    a=np.abs(residual)
    return np.where(a<=delta,.5*a*a,delta*(a-.5*delta))

def samples(z,valid,anchors,transform=None):
    """Bilinear samples require all interpolation support to be valid."""
    values=[]; heights=[]; weights=[]; positions=[]
    for a in anchors:
        if not np.isfinite(a.elevation) or not np.isfinite(a.uncertainty) or a.uncertainty<=0:
            raise ValueError('Anchor elevation must be finite and uncertainty positive')
        if a.row is not None and a.col is not None: row,col=a.row,a.col
        elif a.x is not None and a.y is not None and transform is not None:
            col,row=(~transform)*(a.x,a.y);row-=.5;col-=.5
        else: raise ValueError('Need row/col or x/y with raster transform')
        if not np.isfinite(row+col) or not(0<=row<=z.shape[0]-1 and 0<=col<=z.shape[1]-1): continue
        r0=int(np.floor(row));c0=int(np.floor(col));r1=min(r0+1,z.shape[0]-1);c1=min(c0+1,z.shape[1]-1)
        entries=[(r0,c0,(1-row+r0)*(1-col+c0)),(r1,c0,(row-r0)*(1-col+c0)),(r0,c1,(1-row+r0)*(col-c0)),(r1,c1,(row-r0)*(col-c0))]
        entries=[e for e in entries if e[2]>0]
        if not all(valid[r,c] and np.isfinite(z[r,c]) for r,c,_ in entries): continue
        values.append(sum(z[r,c]*w for r,c,w in entries));heights.append(a.elevation)
        weights.append(1/a.uncertainty**2);positions.append((row,col))
    return np.asarray(values),np.asarray(heights),np.asarray(weights),np.asarray(positions)

def anchor_loss(z,valid,anchors,transform=None,delta_m=1.0):
    value,height,weight,_=samples(z,valid,anchors,transform)
    if not len(value): raise ValueError('No usable anchors')
    return float(np.sum(weight*huber(value-height,delta_m))/weight.sum())

def fit_gauge(z,valid,anchors,mode='offset',transform=None,allow_spatial=False):
    value,height,weight,pos=samples(z,valid,anchors,transform)
    if mode=='offset': X=np.ones((len(value),1));target=height-value
    elif mode=='affine': X=np.column_stack((value,np.ones(len(value))));target=height
    elif mode=='plane' and allow_spatial:
        X=np.column_stack((np.ones(len(value)),pos[:,0]/z.shape[0],pos[:,1]/z.shape[1]));target=height-value
    else: raise ValueError('Spatial gauge requires explicit permission; mode must be offset/affine/plane')
    if len(value)<X.shape[1] or np.linalg.matrix_rank(X)<X.shape[1]:raise ValueError('Insufficient independent anchors')
    current=weight.copy();previous=None
    for _ in range(50):
        beta=np.linalg.lstsq(X*np.sqrt(current[:,None]),target*np.sqrt(current),rcond=None)[0]
        residual=X@beta-target
        current=weight*np.minimum(1,1/np.maximum(np.abs(residual),1e-12))
        if previous is not None and np.max(np.abs(beta-previous))<1e-10:break
        previous=beta
    yy,xx=np.indices(z.shape)
    if mode=='offset':corrected=z+beta[0]
    elif mode=='affine':corrected=beta[0]*z+beta[1]
    else:corrected=z+beta[0]+beta[1]*yy/z.shape[0]+beta[2]*xx/z.shape[1]
    return np.where(valid,corrected,np.nan),{'mode':mode,'parameters':beta.tolist(),'usable_anchors':len(value),'huber_delta_m':1.0,'relief_effect':'Affine deliberately rescales relief; offset preserves all elevation differences; plane preserves relief only relative to its fitted plane.'}

def decompose_gauge(z,valid,lowpass):
    gauge=lowpass(z,valid);relief=np.where(valid,z-gauge,0)
    return gauge,relief
