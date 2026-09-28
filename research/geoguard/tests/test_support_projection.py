import sys,inspect
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
sys.path.insert(0,str(Path(__file__).parents[1]/'geoinverse'))
from support_projection_diagnostic import gaussian_project,cell_project,cell_max,filter_operator,cells,write
from frequency import masked_low_pass
from geoinverse_v1 import SIGMA_M

def test_constant():
    a=np.ones((96,96))*3; v=np.ones(a.shape,bool)
    out,status=gaussian_project(a,v,1)
    assert status['converged'] and np.max(np.abs(out))<1e-8

def test_ramp():
    a=np.broadcast_to(np.linspace(-1,1,96),(96,96));v=np.ones(a.shape,bool)
    out,status=gaussian_project(a,v,1)
    assert np.mean(np.abs(out))<.1*np.mean(np.abs(a))

def test_high_frequency():
    a=((np.indices((96,96)).sum(axis=0)%2)*2-1).astype(float);v=np.ones(a.shape,bool)
    out,_=gaussian_project(a,v,1)
    assert np.std(out)>.95*np.std(a)

def test_nodata():
    a=np.ones((96,96));v=np.ones(a.shape,bool);v[25:40,20:50]=False;a[~v]=np.nan
    out,_=gaussian_project(a,v,1)
    assert np.isfinite(out).all() and np.max(np.abs(out[v]))<1e-8

def test_partial_cell_means():
    a=np.random.default_rng(1).normal(size=(97,103));v=np.ones(a.shape,bool);v[:4,:4]=False
    out=cell_project(a,v,1)
    assert cell_max(out,v,1)<1e-14

def test_physical_scale_and_equivalence():
    a=np.random.default_rng(2).normal(size=(96,96)).astype('float32');v=np.ones(a.shape,bool)
    for p in (1.,2.):
        np.testing.assert_allclose(filter_operator(v,p)(a),masked_low_pass(a,v,sigma_m=SIGMA_M,pixel_size_m=p),atol=1e-6)
    assert list(cells(a.shape,2))[0][0].stop==15

def test_no_truth_parameters():
    for f in (gaussian_project,cell_project):
        assert not any('truth' in k or 'score' in k for k in inspect.signature(f).parameters)

def test_raster_alignment(tmp_path):
    a=np.ones((20,20));v=np.ones(a.shape,bool);p=dict(driver='GTiff',width=20,height=20,count=1,dtype='float32',crs='EPSG:6344',transform=from_origin(458000,4616000,2,2))
    dest=tmp_path/'a.tif';write(dest,a,v,p)
    with rasterio.open(dest) as d:
        assert d.transform==p['transform'] and d.crs.to_epsg()==6344
        assert np.isfinite(d.read(1)).all()
