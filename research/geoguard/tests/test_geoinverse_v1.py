import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).parents[1]/'geoinverse'))
from geoinverse_v1 import GeoInverseV1,lowpass,constrain,support_loss,SIGMA_M
from frequency import masked_low_pass
from dataset_v1 import features_from_inputs

def test_initialization():
    m=GeoInverseV1(8); x=torch.randn(1,8,96,96); raw,w=m(x)
    d,c=constrain(raw,w,torch.ones_like(raw,dtype=torch.bool))
    assert torch.count_nonzero(c)==0
    assert torch.allclose(w,torch.full_like(w,.05))

def test_constant_and_slow_linear_removed():
    x=torch.ones(1,1,128,128)*4; v=torch.ones_like(x,dtype=torch.bool)
    d,_=constrain(x,x*.01,v); assert d.abs().max()<1e-4
    x=torch.arange(128).float()[None,None,None,:].expand(1,1,128,128)/128
    d,_=constrain(x,torch.ones_like(x),v)
    assert d[:,:,40:-40,40:-40].abs().max()<1e-5

def test_nodata_shape_finite():
    x=torch.ones(1,1,96,96); v=torch.ones_like(x,dtype=torch.bool); v[:,:,40:50,40:50]=False
    x[~v]=float('nan'); a=lowpass(x,v)
    assert a.shape==x.shape and torch.isfinite(a).all()
    assert torch.allclose(a,torch.ones_like(a),atol=1e-5)

def test_matches_v0_physical_scale():
    rng=np.random.default_rng(4); a=rng.normal(size=(96,96)).astype('float32'); v=np.ones(a.shape,bool)
    for pixel in (1.,2.):
        expected=masked_low_pass(a,v,sigma_m=SIGMA_M,pixel_size_m=pixel)
        actual=lowpass(torch.from_numpy(a)[None,None],torch.from_numpy(v)[None,None],pixel)[0,0].numpy()
        np.testing.assert_allclose(actual,expected,atol=1e-6)
    assert not torch.allclose(lowpass(torch.from_numpy(a)[None,None],torch.from_numpy(v)[None,None],1),lowpass(torch.from_numpy(a)[None,None],torch.from_numpy(v)[None,None],2))

def test_support_checks_applied_not_raw():
    applied=torch.ones(1,1,96,96,requires_grad=True); v=torch.ones_like(applied,dtype=torch.bool)
    penalty=support_loss(applied,v,v,1); assert torch.allclose(penalty,torch.tensor(1.))
    penalty.backward(); assert applied.grad.abs().sum()>0

def test_input_features_have_no_truth_argument():
    a=np.ones((96,96),dtype='float32'); v=np.ones(a.shape,bool)
    features=features_from_inputs(np.stack([a,a,a])*100,a*30,a,v,1)
    assert features.shape==(8,96,96) and np.isfinite(features).all()
