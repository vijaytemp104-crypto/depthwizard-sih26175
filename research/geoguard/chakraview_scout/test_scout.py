import numpy as np
import pytest
from scout import Terrain,Point,Planner,candidates,viewshed,evidence_map,relevance_map,apply_field_observation
from demo import scenario

def flat(n=9,metric=True):return Terrain(np.zeros((n,n)),np.ones((n,n),bool),metric=metric)
def planner(t=None):
    t=t or flat();p=candidates(t,'AERIAL',stride=3,height=2)
    return Planner(t,p,np.ones(t.z.shape),np.ones(t.z.shape),(0,0),radius=4)

def test_flat_viewshed():assert viewshed(flat(),Point(4,4,'GROUND',1.7)).all()
def test_ridge_occlusion():
    z=np.zeros((9,9));z[:,4]=10;t=Terrain(z,np.ones(z.shape,bool))
    v=viewshed(t,Point(4,1,'GROUND',1.7));assert not v[4,7] and v[4,3]
def test_elevated_reveals_hidden():
    z=np.zeros((9,9));z[:,4]=10;t=Terrain(z,np.ones(z.shape,bool))
    assert viewshed(t,Point(4,1,'AERIAL',40))[4,7]
def test_nodata_blocks():
    z=np.zeros((9,9));z[:,4]=np.nan;t=Terrain(z,np.isfinite(z));v=viewshed(t,Point(4,1,'GROUND',2))
    assert not v[4,4] and not v[4,7]
def test_radius():assert viewshed(flat(),Point(4,4,'AERIAL',2),radius=1).sum()==5
@pytest.mark.parametrize('pos',[(-1,0),(0,9),(9,9)])
def test_region_boundary(pos):
    with pytest.raises(ValueError):viewshed(flat(),Point(*pos,'GROUND',2))
def test_ground_requires_reachability():
    with pytest.raises(ValueError):candidates(flat(),'GROUND')
def test_candidates_respect_masks():
    t=flat();reach=np.zeros((9,9),bool);reach[0,0]=True
    assert len(candidates(t,'GROUND',stride=1,reachable=reach))==1
def test_slope_constraint():
    t=flat();s=np.ones((9,9))*40;s[0,0]=0
    assert len(candidates(t,'GROUND',1,reachable=t.valid,slope=s,max_slope=20))==1
def test_relative_no_physical_slope():
    t=flat(metric=False)
    with pytest.raises(ValueError):candidates(t,'GROUND',reachable=t.valid,slope=t.z,max_slope=20)
def test_relative_units():assert planner(flat(metric=False)).rank()[0]['area_units']=='grid_units_squared'
def test_metric_coordinates():assert Terrain(np.zeros((2,2)),np.ones((2,2),bool),5,(100,200)).xy(0,0)==(102.5,197.5)
def test_missing_evidence():
    with pytest.raises(ValueError):evidence_map({},(3,3))
def test_named_evidence():
    u,s=evidence_map({'anchor_gap':np.ones((3,3))},(3,3));assert u.mean()==1 and s[0]['source']=='anchor_gap'
@pytest.mark.parametrize('bad',[np.nan,np.inf,-.1,1.1])
def test_evidence_invalid(bad):
    with pytest.raises(ValueError):evidence_map({'bad':np.full((3,3),bad)},(3,3))
def test_change_clips():
    r,s=relevance_map({'route':np.ones((3,3))*.8},(3,3),np.ones((3,3)),.5);assert np.all(r==1)
def test_score_decomposition():
    a=planner().rank()[0];assert np.isclose(a['score'],sum(a['contributions'].values()))
def test_novelty_removes_gain():
    p=planner();a=p.rank(observed=np.ones((9,9),bool))[0];assert a['terms']['information_gain']==0 and a['terms']['occlusion_gain']==0
def test_ground_cost_handling():
    t=flat();points=candidates(t,'GROUND',reachable=t.valid);cost=np.ones((9,9))*.3
    p=Planner(t,points,cost,cost,(0,0),ground_cost=cost);assert p.costs[0]==.3
def test_unreachable_cost_rejected():
    t=flat();cost=np.full((9,9),np.inf)
    with pytest.raises(ValueError):Planner(t,candidates(t,'GROUND',reachable=t.valid),np.ones((9,9)),np.ones((9,9)),(0,0),ground_cost=cost)
def test_aerial_cost_increases():
    p=planner();assert p.cost(Point(0,0,'AERIAL',3))>p.cost(Point(0,0,'AERIAL',2))
def test_sequential_monotonic():
    s=planner().simulate();assert all(s[i]['uncertainty_remaining_fraction']<=s[i-1]['uncertainty_remaining_fraction'] for i in range(1,5))
def test_random_determinism():assert planner().simulate('random',seed=9)==planner().simulate('random',seed=9)
def test_highest_baseline():
    t=flat();z=t.z.copy();z[6,6]=20;t=Terrain(z,t.valid)
    assert planner(t).simulate('highest')[0]['point']['row']==6
def test_nearest_baseline():assert planner().simulate('nearest')[0]['point']['coordinates']==[.5,-.5]
def test_no_duplicate_observations():
    s=planner().simulate();assert len(set(x['point']['index'] for x in s))==len(s)
def test_empty_candidates():
    t=flat();p=Planner(t,[],t.z,t.z,(0,0));assert p.rank()==[] and p.simulate()==[]
def test_invalid_direct_mode():
    t=flat()
    with pytest.raises(ValueError):Planner(t,[Point(0,0,'UNKNOWN',2)],t.z,t.z,(0,0))
def test_invalid_weights():
    with pytest.raises(ValueError):Planner(flat(),[],np.zeros((9,9)),np.zeros((9,9)),(0,0),weights={'information_gain':float('nan')})
def test_scoring_deterministic():assert planner().simulate()==planner().simulate()
def test_occlusion_gain_initially_visible_zero():
    t=flat();p=Planner(t,candidates(t,'AERIAL'),np.ones((9,9)),np.ones((9,9)),(0,0),current_visible=np.ones((9,9),bool))
    assert all(x['terms']['occlusion_gain']==0 for x in p.rank())
def test_zero_information_finite():
    t=flat();p=Planner(t,candidates(t,'AERIAL'),t.z,t.z,(0,0));assert np.isfinite(p.rank()[0]['score'])
def test_input_not_mutated():
    p=planner();before=p.initial.copy();p.simulate();assert np.array_equal(before,p.initial)
@pytest.mark.parametrize('status',['OBSERVED','BLOCKED','CLEAR'])
def test_field_updates_local_only(status):
    u,o=apply_field_observation(np.ones((3,3)),np.zeros((3,3),bool),dict(row=1,col=1,status=status,quality=.5))
    assert u.sum()==8.5 and o.sum()==1
@pytest.mark.parametrize('status',['UNKNOWN','NOTE'])
def test_no_fabricated_field_update(status):
    u,o=apply_field_observation(np.ones((3,3)),np.zeros((3,3),bool),dict(row=1,col=1,status=status));assert u.sum()==9 and not o.any()
@pytest.mark.parametrize('name',['mountain','urban','mixed'])
def test_scenarios_deterministic(name):
    a=scenario(name);b=scenario(name);assert np.array_equal(a[0].z,b[0].z,equal_nan=True)
    p=Planner(a[0],candidates(a[0],'AERIAL',stride=12,height=25),a[1],a[2],(3,3),radius=100)
    assert all(np.isfinite(x['score']) for x in p.rank())
