"""Deterministic synthetic-only benchmark and standalone offline mobile concept."""
import json
from pathlib import Path
import time
import numpy as np
from scout import Terrain,Point,Planner,candidates,evidence_map,relevance_map,viewshed

ROOT=Path(__file__).resolve().parent

def scenario(name,n=40):
    y,x=np.indices((n,n));xx=x/(n-1);yy=y/(n-1)
    if name=='mountain':z=35*np.exp(-((xx-.47)/.1)**2)+15*np.sin(yy*5)**2+8*xx
    elif name=='urban':
        z=np.zeros((n,n))
        for r,c,height in [(6,7,16),(6,24,22),(22,7,20),(23,24,12)]:z[r:r+9,c:c+8]=height
    else:z=10*np.sin(xx*5)*np.cos(yy*4)+20*np.exp(-((xx-.62)**2+(yy-.5)**2)/.025)
    valid=np.ones((n,n),bool);valid[17:20,17:20]=False
    z[~valid]=np.nan;t=Terrain(z,valid,pixel=5.,origin=(500000.,4500000.))
    anchor_distance=np.clip(np.hypot(x-3,y-3)/35,0,1)
    disagreement=np.clip(np.exp(-((xx-.72)**2+(yy-.62)**2)/.04),0,1)
    u,sources=evidence_map({'synthetic_anchor_distance':anchor_distance,'synthetic_geometry_disagreement':disagreement,'terrain_nodata':(~valid).astype(float)},z.shape,{'synthetic_anchor_distance':1.,'synthetic_geometry_disagreement':1.,'terrain_nodata':.25})
    u[~valid]=1.
    corridor=np.exp(-((yy-.65)/.12)**2)
    target=np.exp(-((xx-.75)**2+(yy-.6)**2)/.025)
    r,rs=relevance_map({'synthetic_response_corridor':corridor,'synthetic_mission_target':target},z.shape)
    # These are fixture layers, NOT an implemented traversability/route engine.
    reachable=valid.copy()
    if name=='urban':reachable&=np.nan_to_num(z,nan=100)<2
    ground_cost=np.hypot(y-3,x-3)/np.hypot(n,n)
    return t,u,r,sources,rs,reachable,ground_cost

def main():
    begin=time.perf_counter();results=[]
    for name in ('mountain','urban','mixed'):
        t,u,r,us,rs,reach,cost=scenario(name)
        initial_view=viewshed(t,Point(3,3,'GROUND',1.7),radius=100)
        for mode,height in [('GROUND',1.7),('AERIAL',25.)]:
            start=time.perf_counter()
            pts=candidates(t,mode,stride=6,height=height,reachable=reach)
            p=Planner(t,pts,u,r,(3,3),ground_cost=cost,current_visible=initial_view,radius=100)
            precompute=time.perf_counter()-start
            selection=time.perf_counter()
            trajectories={s:p.simulate(s,5,seed=42) for s in ('scout','random','nearest','highest')}
            trials=[p.simulate('random',5,seed=seed) for seed in range(30)]
            stats=[]
            for step in range(5):
                stats.append({metric:{'mean':float(np.mean([a[step][metric] for a in trials])),
                                      'std':float(np.std([a[step][metric] for a in trials]))}
                              for metric in ('uncertainty_covered_fraction','operational_weighted_coverage','uncertainty_reduction_fraction','cumulative_observation_cost')})
            results.append(dict(scenario=name,mode=mode,label='SYNTHETIC ACTIVE-RECONNAISSANCE DEMO',candidate_count=len(pts),
                                uncertainty_sources=us,relevance_sources=rs,top5=p.rank()[:5],trajectories=trajectories,random_30_seed_summary=stats,
                                runtime_seconds=dict(viewshed_precompute=precompute,ranking_and_all_baselines=time.perf_counter()-selection),
                                grid=dict(CRS=t.crs,pixel_m=t.pixel,shape=list(t.z.shape),origin=list(t.origin)),
                                maps=dict(terrain=np.where(t.valid,t.z,0).tolist(),valid=t.valid.tolist(),uncertainty=u.tolist(),relevance=r.tolist(),
                                          top_view=p.sheds[p.rank()[0]['index']].tolist(),
                                          scout_views=[p.sheds[s['point']['index']].tolist() for s in trajectories['scout']]+[np.zeros(t.z.shape,bool).tolist()])))
    report=dict(label='SYNTHETIC ACTIVE-RECONNAISSANCE DEMO',retention=.4,random_seeds=list(range(30)),random_display_seed=42,
                assumptions='Visible cells retain 40% uncertainty after each simulated observation. This is not a measured sensor likelihood. Independent sorties from fixed base; no path or drone flight optimization.',
                total_runtime_seconds=time.perf_counter()-begin,results=results)
    out=ROOT/'outputs';out.mkdir(exist_ok=True)
    payload=json.dumps(report,indent=2,allow_nan=False)
    (out/'results.json').write_text(payload+'\n',encoding='utf-8')
    template=(ROOT/'mobile_template.html').read_text(encoding='utf-8')
    (out/'mobile_demo.html').write_text(template.replace('__SCOUT_DATA__',json.dumps(report,allow_nan=False)).replace('r.maps.top_view[y][x]', 'r.maps.scout_views[n][y][x]'),encoding='utf-8')
    lines=['# ChakraVIEW Scout — complete implementation report','',report['label'],'',report['assumptions'],'',
           '## Quantitative results','', 'Coverage is unique initial uncertainty mass seen; reduction is simulated remaining uncertainty change. Weighted coverage uses initial U × R. Costs are dimensionless fixed-base sortie proxies. Random shown below is the 30-seed mean ± population SD, not a selected lucky seed.','']
    for row in results:
        lines.append(f"### {row['scenario']} / {row['mode']}")
        lines.append(f"Candidates: {row['candidate_count']}; precompute {row['runtime_seconds']['viewshed_precompute']:.4f}s; ranking and 34 baseline runs {row['runtime_seconds']['ranking_and_all_baselines']:.4f}s.")
        for s,steps in row['trajectories'].items():
            for n in (1,2,3,5):
                a=steps[n-1]
                lines.append(f"- {s}, observation {n}: uncertainty coverage {100*a['uncertainty_covered_fraction']:.2f}%; reduction {100*a['uncertainty_reduction_fraction']:.2f}%; remaining {100*a['uncertainty_remaining_fraction']:.2f}%; weighted coverage {100*a['operational_weighted_coverage']:.2f}%; cost {a['cumulative_observation_cost']:.3f}.")
        for n in (1,3,5):
            stat=row['random_30_seed_summary'][n-1];v=stat['operational_weighted_coverage']
            lines.append(f"- Random 30-seed weighted coverage at {n}: {100*v['mean']:.2f}% ± {100*v['std']:.2f}%.")
        best=row['top5'][0]
        lines+=['',f"Top point: {best['coordinates']}, {best['reason']}",f"Score terms: {json.dumps(best['terms'])}",f"Weighted contributions: {json.dumps(best['contributions'])}",'']
    lines += ['## Reproduction and architecture','', 'See README.md for all formulations, architecture, limitations and real-world validation protocol; integration documents for contracts; PPT notes for defensible claims. results.json contains every top-five explanation and complete baseline trajectory.',
              f"Total runtime: {report['total_runtime_seconds']:.4f}s.",
              '','No production modification. No foundation model training. No GeoInverse modification. No canonical pilot changes. No commit. No push.']
    for document in ('README.md','GEOINVERSE_INTEGRATION.md','CHANGE_DETECTION_INTEGRATION.md','OFFLINE_MOBILE_ARCHITECTURE.md','CHAKRAVIEW_SCOUT_PPT_NOTES.md','VALIDATION.md'):
        lines += ['','---','',f'## Included document: {document}','',(ROOT/document).read_text(encoding='utf-8')]
    lines += ['','## Mermaid architecture','', '```mermaid', (ROOT/'ARCHITECTURE.mmd').read_text(encoding='utf-8'), '```']
    lines += ['','## Field observation update contract','', '```json', (ROOT/'FIELD_OBSERVATION_CONTRACT.json').read_text(encoding='utf-8'), '```']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f"Six scenario/mode benchmarks completed in {report['total_runtime_seconds']:.3f}s")
    for row in results:
        a=row['trajectories']['scout'][4];rand=row['random_30_seed_summary'][4]['operational_weighted_coverage']
        print(row['scenario'],row['mode'],'Scout weighted coverage',round(100*a['operational_weighted_coverage'],2),'random mean',round(100*rand['mean'],2))

if __name__=='__main__':main()
