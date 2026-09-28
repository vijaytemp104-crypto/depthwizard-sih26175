"""Evidence registry and explicitly weighted, optional physical objectives."""
from dataclasses import dataclass
import numpy as np
if __package__:
    from .anchors import anchor_loss,huber
    from .shadows import render_shadow,shadow_loss
else:
    from anchors import anchor_loss,huber
    from shadows import render_shadow,shadow_loss

@dataclass
class Constraint:
    name:str
    weight:float=1.
    evidence:object=None
    options:dict|None=None

    def evaluate(self,z,valid):
        opt=self.options or {};units='dimensionless' if self.name=='shadow' else 'm²' if self.name in ('anchor','reference','foundation') else '(m/m)²'
        row={'name':self.name,'available_evidence':self.evidence is not None,'units':units,'weight':self.weight,'loss':None,'status':'missing','limitations':[]}
        if self.weight<0 or not np.isfinite(self.weight):raise ValueError('Constraint weight must be finite nonnegative')
        if self.weight==0:row['status']='disabled';return row
        if self.evidence is None:return row
        if self.name in ('reference','foundation','shadow') and np.shape(self.evidence)!=z.shape:
            raise ValueError('Evidence raster must be aligned to candidate shape')
        if self.name=='anchor':
            value=anchor_loss(z,valid,self.evidence,opt.get('transform'));row['limitations']=['Anchor datum/units must be harmonized externally; no provider truth assumed.','Normalized inverse-variance weights preserve m² loss units.']
        elif self.name=='shadow':
            required=('azimuth','elevation','pixel_size')
            if not all(k in opt for k in required):row['status']='missing_sun_geometry';return row
            rendered=render_shadow(z,valid,opt['azimuth'],opt['elevation'],opt['pixel_size'])
            support=rendered['known']&np.isfinite(self.evidence)
            if not support.any():row['status']='no_valid_evidence';return row
            value=shadow_loss(rendered['shadow'],self.evidence,support)
            row['limitations']=['Finite-domain blockers only; external occlusion unobserved.','Geometric mask is not RGB radiance; requires independent observed shadow mask and sun metadata.','Global vertical offset is unidentifiable from shadows.']
        elif self.name in ('reference','foundation'):
            support=valid&np.isfinite(self.evidence)
            if not support.any():row['status']='no_valid_evidence';return row
            value=float(huber(z[support]-self.evidence[support]).mean());row['limitations']=['Reference uncertainty/datum must be supplied externally.','Foundation disagreement is a prior, not independent measured accuracy.']
        elif self.name=='smoothness':
            pixel=opt.get('pixel_size',1.);values=[]
            if not np.isfinite(pixel) or pixel<=0:raise ValueError('Positive metre spacing required')
            for axis in (0,1):
                a=np.take(valid,range(1,valid.shape[axis]),axis=axis)&np.take(valid,range(valid.shape[axis]-1),axis=axis)
                values.extend(((np.diff(z,axis=axis)/pixel)[a]**2).tolist())
            if not values:row['status']='no_valid_neighbours';return row
            value=float(np.mean(values));row['limitations']=['Smoothness can suppress real ridges/buildings; optional regularizer only.']
        else:raise ValueError('Unknown constraint')
        if not np.isfinite(value):raise ValueError('Nonfinite constraint loss')
        row.update(loss=value,status='active');return row

class ConstraintRegistry:
    def __init__(self,constraints):
        if len({c.name for c in constraints})!=len(constraints):raise ValueError('Duplicate constraint names')
        self.constraints=constraints
    def objective(self,z,valid):
        if not np.isfinite(z[valid]).all():raise ValueError('Nonfinite valid elevation')
        rows=[c.evaluate(z,valid) for c in self.constraints]
        total=sum(r['weight']*r['loss'] for r in rows if r['status']=='active')
        active=[r['name'] for r in rows if r['status']=='active']
        return {'total':float(total),'constraints':rows,'active':active,'certainty':'not calibrated','status':'constrained' if any(n in active for n in ('anchor','shadow','reference')) else 'prior_only' if active else 'unconstrained','weight_note':'Losses have different units; coefficients carry reciprocal units or deliberate normalization. No universal weights or confidence inferred.'}
