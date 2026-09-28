import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import numpy as np
from anchors import Anchor,samples,anchor_loss,fit_gauge
from shadows import render_shadow,shadow_metrics
from constraints import Constraint,ConstraintRegistry
from synthetic_experiment import terrain,run
from anchors import decompose_gauge

def controls(z):return [Anchor(float(z[y,x]),row=y,col=x) for y,x in [(2,2),(3,7),(8,4),(9,9)]]

def test_anchor_residual():
    z=np.ones((12,12))*10;v=np.ones(z.shape,bool)
    assert anchor_loss(z,v,[Anchor(8,row=2,col=3)])==1.5

def test_uncertainty():
    z=np.zeros((12,12));v=np.ones(z.shape,bool)
    high=anchor_loss(z,v,[Anchor(0,row=2,col=2),Anchor(10,row=3,col=3,uncertainty=10)])
    equal=anchor_loss(z,v,[Anchor(0,row=2,col=2),Anchor(10,row=3,col=3)])
    assert high<equal/10

def test_offset():
    z=np.arange(144.).reshape(12,12);v=np.ones(z.shape,bool);a=controls(z)
    recovered,fit=fit_gauge(z+5,v,a);np.testing.assert_allclose(recovered,z,atol=1e-10)
    assert abs(fit['parameters'][0]+5)<1e-10

def test_affine():
    z=np.arange(144.).reshape(12,12);v=np.ones(z.shape,bool)
    out,_=fit_gauge(2*z+7,v,controls(z),'affine');np.testing.assert_allclose(out,z,atol=1e-9)

def test_high_frequency_preservation():
    z=(np.indices((12,12)).sum(0)%2)*3.;v=np.ones(z.shape,bool)
    out,_=fit_gauge(z+5,v,controls(z));np.testing.assert_allclose(np.diff(out),np.diff(z))

def test_shadow_direction():
    z=np.zeros((15,15));z[7,7]=6;v=np.ones(z.shape,bool)
    out=render_shadow(z,v,90,20,1)['shadow']
    assert out[7,4] and not out[7,10]

def test_sun_elevation():
    z=np.zeros((15,15));z[7,7]=6;v=np.ones(z.shape,bool)
    assert render_shadow(z,v,90,10,1)['shadow'].sum()>render_shadow(z,v,90,60,1)['shadow'].sum()

def test_terrain_obstruction():
    z=np.zeros((15,15));z[:,7]=10;v=np.ones(z.shape,bool)
    assert render_shadow(z,v,90,30,1)['shadow'][7,4]

def test_no_shadow():
    z=np.zeros((15,15));v=np.ones(z.shape,bool)
    assert not render_shadow(z,v,180,30,1)['shadow'].any()

def test_metrics():
    p=np.array([[True,False],[True,False]]);o=np.array([[True,True],[False,False]])
    m=shadow_metrics(p,o,np.ones(p.shape,bool));assert m['iou']==1/3 and m['f1']==.5

def test_combined():
    z=np.zeros((12,12));v=np.ones(z.shape,bool)
    r=ConstraintRegistry([Constraint('anchor',2,[Anchor(2,row=2,col=2)]),Constraint('reference',3,np.ones(z.shape))]).objective(z,v)
    assert r['total']==4.5

def test_missing():
    z=np.zeros((12,12));v=np.ones(z.shape,bool)
    r=ConstraintRegistry([Constraint('anchor'),Constraint('shadow'),Constraint('foundation',1,z)]).objective(z,v)
    assert r['status']=='prior_only' and r['total']==0

def test_finite_and_nodata():
    z=np.zeros((15,15));z[7,8]=np.nan;v=np.isfinite(z)
    r=render_shadow(z,v,90,30,1);assert not r['known'][7,4]

def test_deterministic_ordering():
    a=run();b=run();a.pop('runtime_seconds');b.pop('runtime_seconds');assert a==b
    for name,r in a['candidates'].items():
        if name!='truth':assert r['objective']['total']>a['candidates']['truth']['objective']['total']
    assert a['combined_grid_recovery']['mae_m']<1e-9

def test_georeferenced_anchor_and_sun():
    from rasterio.transform import from_origin
    t=from_origin(100,200,2,2);z=np.zeros((15,15));z[7,7]=6;v=np.ones(z.shape,bool)
    x,y=t*(7.5,7.5)
    value,_,_,_=samples(z,v,[Anchor(6,x=x,y=y)],t)
    np.testing.assert_allclose(value,[6])
    a=render_shadow(z,v,90,20,transform=t)['shadow'];b=render_shadow(z,v,90,20,2)['shadow']
    np.testing.assert_array_equal(a,b)

def test_explicit_plane():
    y,x=np.indices((12,12));truth=(x+y)%2*3.;z=truth+2+y/12+x/12;v=np.ones(z.shape,bool)
    out,_=fit_gauge(z,v,controls(truth),'plane',allow_spatial=True)
    np.testing.assert_allclose(out,truth,atol=1e-9)

def test_gauge_decomposition():
    z=np.arange(144.).reshape(12,12);v=np.ones(z.shape,bool)
    g,r=decompose_gauge(z,v,lambda a,m:np.full(a.shape,a[m].mean()))
    np.testing.assert_allclose(g+r,z)

def test_missing_sun_metadata():
    z=np.zeros((12,12));v=np.ones(z.shape,bool)
    r=ConstraintRegistry([Constraint('shadow',1,z)]).objective(z,v)
    assert r['constraints'][0]['status']=='missing_sun_geometry' and r['status']=='unconstrained'
