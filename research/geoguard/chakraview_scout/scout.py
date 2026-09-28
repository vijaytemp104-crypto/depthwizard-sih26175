"""Offline next-observation research prototype; not autonomous command."""
from dataclasses import dataclass
import numpy as np

def unit_layer(a, shape):
    a=np.asarray(a,float)
    if a.shape!=shape or not np.isfinite(a).all() or np.any((a<0)|(a>1)):
        raise ValueError('Require aligned finite [0,1] layer')
    return a

def evidence_map(layers,shape,weights=None):
    if not layers: raise ValueError('Named evidence required; no fabricated uncertainty')
    weights=weights or {}; total=np.zeros(shape); denominator=0.; sources=[]
    for name,a in layers.items():
        w=float(weights.get(name,1.))
        if not np.isfinite(w) or w<0: raise ValueError('Invalid evidence weight')
        total+=w*unit_layer(a,shape); denominator+=w; sources.append({'source':name,'weight':w})
    if denominator<=0: raise ValueError('Positive weight required')
    return total/denominator,sources

def relevance_map(layers,shape,change_score=None,change_weight=0.):
    r,sources=evidence_map(layers,shape)
    if not np.isfinite(change_weight) or change_weight<0: raise ValueError('Invalid change weight')
    if change_score is not None:
        r=np.clip(r+change_weight*unit_layer(change_score,shape),0,1)
        sources.append({'source':'supplied_change_score','weight':change_weight})
    return r,sources

@dataclass(frozen=True)
class Terrain:
    z: np.ndarray
    valid: np.ndarray
    pixel: float=1.
    origin: tuple=(0.,0.)
    metric: bool=True
    crs: str='LOCAL_METRIC_SYNTHETIC'
    def __post_init__(self):
        z=np.asarray(self.z,float).copy(); v=np.asarray(self.valid,bool).copy()
        if z.ndim!=2 or v.shape!=z.shape or not np.isfinite(self.pixel) or self.pixel<=0 or not np.isfinite(self.origin).all():
            raise ValueError('Invalid terrain grid')
        if np.any(v&~np.isfinite(z)): raise ValueError('Nonfinite valid terrain')
        z.setflags(write=False);v.setflags(write=False)
        object.__setattr__(self,'z',z);object.__setattr__(self,'valid',v)
    def xy(self,r,c): return (self.origin[0]+(c+.5)*self.pixel,self.origin[1]-(r+.5)*self.pixel)

@dataclass(frozen=True)
class Point:
    row: int
    col: int
    mode: str
    height: float

def candidates(t,mode,stride=6,height=1.7,reachable=None,allowed=None,slope=None,max_slope=None):
    if mode not in ('GROUND','AERIAL') or stride<1 or not np.isfinite(height) or height<=0: raise ValueError('Invalid candidate settings')
    if mode=='GROUND' and reachable is None: raise ValueError('Ground mode requires supplied reachability')
    valid=t.valid.copy()
    for m in (reachable if mode=='GROUND' else None,allowed):
        if m is not None:
            if np.asarray(m).shape!=valid.shape: raise ValueError('Constraint grid mismatch')
            valid&=np.asarray(m,bool)
    if slope is not None:
        if not t.metric or max_slope is None: raise ValueError('Slope requires metric terrain and threshold')
        s=np.asarray(slope,float)
        if s.shape!=valid.shape: raise ValueError('Slope grid mismatch')
        valid&=np.isfinite(s)&(s<=max_slope)
    return [Point(r,c,mode,height) for r in range(0,valid.shape[0],stride) for c in range(0,valid.shape[1],stride) if valid[r,c]]

def viewshed(t,p,radius=None):
    """Half-cell sampled centre-to-centre 2.5D LOS; unknown cells block rays."""
    h,w=t.z.shape
    if not(0<=p.row<h and 0<=p.col<w) or not t.valid[p.row,p.col]: raise ValueError('Invalid observer')
    if not np.isfinite(p.height) or p.height<=0: raise ValueError('Invalid observer height')
    if radius is not None and (not np.isfinite(radius) or radius<=0): raise ValueError('Invalid radius')
    rr,cc=np.indices((h,w));dr=rr-p.row;dc=cc-p.col
    v=t.valid.copy()
    if radius is not None: v&=np.hypot(dr,dc)*t.pixel<=radius
    steps=np.maximum(1,np.ceil(2*np.maximum(abs(dr),abs(dc))).astype(int))
    observer=t.z[p.row,p.col]+p.height; target=np.where(t.valid,t.z,observer)
    for k in range(1,int(steps.max())):
        active=(k<steps)&v
        if not active.any(): break
        fraction=np.minimum(k/steps,1.)
        rows=np.rint(p.row+fraction*dr).astype(int);cols=np.rint(p.col+fraction*dc).astype(int)
        interior=active&~((rows==p.row)&(cols==p.col))&~((rows==rr)&(cols==cc))
        blocked=~t.valid[rows,cols]|(t.z[rows,cols]>observer+fraction*(target-observer)+1e-8)
        v[interior&blocked]=False
    return v

WEIGHTS=dict(information_gain=1.,relevance_gain=.15,occlusion_gain=.3,uncertainty_reduction_potential=.2,observation_cost=.15)

class Planner:
    def __init__(self,t,points,u,r,base,ground_cost=None,current_visible=None,weights=None,retention=.4,radius=None,altitude_scale=30.):
        self.t=t;self.points=list(points);self.base=base
        if any(p.mode not in ('GROUND','AERIAL') for p in self.points):raise ValueError('Invalid candidate mode')
        self.initial=unit_layer(u,t.z.shape).copy();self.r=unit_layer(r,t.z.shape).copy()
        if not np.isfinite(retention) or not 0<=retention<=1: raise ValueError('Invalid retention')
        if not np.isfinite(altitude_scale) or altitude_scale<=0: raise ValueError('Invalid altitude scale')
        if not(0<=base[0]<t.z.shape[0] and 0<=base[1]<t.z.shape[1]): raise ValueError('Base outside grid')
        if len(set(self.points))!=len(self.points): raise ValueError('Duplicate candidates')
        self.retention=retention;self.altitude_scale=altitude_scale;self.weights=WEIGHTS.copy()
        if weights:self.weights.update(weights)
        if set(self.weights)!=set(WEIGHTS) or any(not np.isfinite(w) or w<0 for w in self.weights.values()): raise ValueError('Invalid weights')
        self.ground_cost=None if ground_cost is None else np.asarray(ground_cost,float)
        if any(p.mode=='GROUND' for p in points):
            if self.ground_cost is None or self.ground_cost.shape!=t.z.shape: raise ValueError('Supply fixed-base accumulated ground costs')
            if any(not np.isfinite(self.ground_cost[p.row,p.col]) or self.ground_cost[p.row,p.col]<0 for p in points): raise ValueError('Unreachable ground candidate')
        self.current=np.zeros(t.z.shape,bool) if current_visible is None else np.asarray(current_visible,bool)
        if self.current.shape!=t.z.shape:raise ValueError('Visibility grid mismatch')
        self.sheds=[viewshed(t,p,radius) for p in points];self.costs=[self.cost(p) for p in points]
        self.du=max(float(self.initial.sum()),1e-12);self.dur=max(float((self.initial*self.r).sum()),1e-12);self.dr=max(float(self.r.sum()),1e-12)
    def cost(self,p):
        if p.mode=='GROUND': return float(self.ground_cost[p.row,p.col])
        return float(np.hypot(p.row-self.base[0],p.col-self.base[1])/max(np.hypot(*self.t.z.shape),1e-12)+p.height/self.altitude_scale)
    def rank(self,u=None,observed=None,excluded=()):
        u=self.initial if u is None else unit_layer(u,self.initial.shape)
        observed=np.zeros(u.shape,bool) if observed is None else np.asarray(observed,bool)
        if observed.shape!=u.shape:raise ValueError('Observed grid mismatch')
        result=[]
        for i,p in enumerate(self.points):
            if i in excluded:continue
            v=self.sheds[i];novel=v&~observed;hidden=novel&~self.current
            terms=dict(information_gain=float((u*self.r*novel).sum()/self.dur),relevance_gain=float((self.r*novel).sum()/self.dr),
                       occlusion_gain=float((u*self.r*hidden).sum()/self.dur),uncertainty_reduction_potential=float(((1-self.retention)*u*v).sum()/self.du),observation_cost=self.costs[i])
            contributions={k:(-1 if k=='observation_cost' else 1)*self.weights[k]*x for k,x in terms.items()}
            percent=100*float((u*v).sum())/max(float(u.sum()),1e-12)
            result.append(dict(index=i,row=p.row,col=p.col,coordinates=list(self.t.xy(p.row,p.col)),mode=p.mode,altitude_above_surface=p.height,
                               coordinate_units='metres' if self.t.metric else 'relative grid units',score=sum(contributions.values()),terms=terms,contributions=contributions,
                               visible_cells=int(v.sum()),visible_area=float(v.sum()*self.t.pixel**2),area_units='m2' if self.t.metric else 'grid_units_squared',
                               uncertainty_covered=float((u*v).sum()),relevance_covered=float((self.r*v).sum()),observation_cost=self.costs[i],
                               reason=f'Views {percent:.2f}% of remaining uncertainty mass and {int(hidden.sum())} newly observed cells hidden from initial view. Cost {self.costs[i]:.3f}.'))
        result.sort(key=lambda x:(-x['score'],x['index']))
        for rank,item in enumerate(result,1):item['rank']=rank
        return result
    def simulate(self,strategy='scout',n=5,seed=0):
        if strategy not in ('scout','random','nearest','highest'):raise ValueError('Unknown strategy')
        u=self.initial.copy();observed=np.zeros(u.shape,bool);used=set();steps=[];cost=0.;rng=np.random.default_rng(seed)
        for _ in range(min(n,len(self.points))):
            ranked=self.rank(u,observed,used)
            if strategy=='scout':choice=ranked[0]
            elif strategy=='random':choice=ranked[int(rng.integers(len(ranked)))]
            elif strategy=='nearest':choice=min(ranked,key=lambda x:(np.hypot(x['row']-self.base[0],x['col']-self.base[1]),x['index']))
            else:choice=max(ranked,key=lambda x:(self.t.z[x['row'],x['col']]+self.points[x['index']].height,-x['index']))
            i=choice['index'];used.add(i);v=self.sheds[i];observed|=v;u[v]*=self.retention;cost+=self.costs[i]
            steps.append(dict(observation=len(steps)+1,point=choice,uncertainty_remaining_fraction=float(u.sum()/self.du),
                              uncertainty_reduction_fraction=float((self.initial-u).sum()/self.du),uncertainty_covered_fraction=float((self.initial*observed).sum()/self.du),
                              operational_weighted_coverage=float((self.initial*self.r*observed).sum()/self.dur),cumulative_observation_cost=cost))
        return steps

def apply_field_observation(u,observed,event):
    if event.get('status') not in ('OBSERVED','BLOCKED','CLEAR','UNKNOWN','NOTE'):raise ValueError('Unknown field status')
    u=np.asarray(u,float).copy();unit_layer(u,u.shape);o=np.asarray(observed,bool).copy()
    if o.shape!=u.shape:raise ValueError('Observation grid mismatch')
    r,c=event['row'],event['col']
    if not(0<=r<u.shape[0] and 0<=c<u.shape[1]):raise ValueError('Observation outside grid')
    if event['status'] in ('OBSERVED','BLOCKED','CLEAR'):
        quality=float(event.get('quality',0.))
        if not np.isfinite(quality) or not 0<=quality<=1:raise ValueError('Invalid quality')
        u[r,c]*=1-quality;o[r,c]=quality>0 or o[r,c]
    return u,o
