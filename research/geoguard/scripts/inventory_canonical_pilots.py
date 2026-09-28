"""Read-only canonical input checks; writes only new transfer inventory artifacts."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
EXPECTED = {
    'wake': (6346, [717954,3944392,718954,3945392], .962159, 6.799877,8.935212),
    'polk': (6344, [458000,4615000,459000,4616000], .991122,.487771,1.387274),
    'larimer': (6342,[477750,4491100,478750,4492100],.960982,2.556609,3.432679),
    'humboldt': (6339,[416500,4527000,417500,4528000],.982686,7.685916,9.850414),
}

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def git(*args):
    return subprocess.run(['git',*args],cwd=REPO,capture_output=True,text=True).stdout.strip()

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def record(path, region, role):
    rel = path.relative_to(REPO).as_posix()
    tracked = bool(git('ls-files','--',rel))
    ignored = bool(git('check-ignore','--',rel))
    out = dict(region=region,role=role,absolute_source_path=str(path),repo_relative_path=rel,
               filename=path.name,sha256=digest(path),bytes=path.stat().st_size,
               CRS=None,bounds=None,shape=None,dtype=None,nodata=None,
               description=role,git_classification='tracked' if tracked else 'untracked ignored' if ignored else 'untracked',
               generated_from_source=path.suffix=='.tif')
    if path.suffix=='.tif':
        with rasterio.open(path) as ds:
            out.update(CRS=str(ds.crs),bounds=list(ds.bounds),shape=[ds.count,ds.height,ds.width],
                       dtype=list(ds.dtypes),nodata=list(ds.nodatavals),transform=list(ds.transform)[:6],
                       width=ds.width,height=ds.height,pixel_size=list(ds.res),units=list(ds.units),
                       tags=ds.tags(),band_tags=[ds.tags(i) for i in ds.indexes])
    return out

def main():
    qa = module('canonical_triplet_qa',ROOT/'qa/check_triplet.py')
    baseline = module('canonical_baseline',ROOT/'experiments/reference_baseline.py')
    entries = json.loads((ROOT/'manifests/proposed_split.json').read_text())['aois']
    files=[]; pilots=[]
    for name,(epsg,bounds,coverage,mae,rmse) in EXPECTED.items():
        entry=next(e for e in entries if f'/{name}_pilot/' in e.get('rgb_path',''))
        pilot=ROOT/'data'/f'{name}_pilot'; derived=pilot/'derived'
        paths=dict(rgb=derived/'rgb_aligned.tif',reference=derived/'reference_aligned.tif',
                   truth=derived/'truth_aligned.tif',scoring_mask=derived/'valid_mask.tif',
                   frozen_dav2=derived/'ai/depth_relative.tif')
        arrays={}; signature=None
        for role,path in paths.items():
            rec=record(path,name,role);files.append(rec)
            assert rec['CRS']==f'EPSG:{epsg}' and rec['bounds']==bounds
            assert rec['width']==rec['height']==1000 and rec['pixel_size']==[1.,1.]
            with rasterio.open(path) as ds:
                sig=(ds.crs,ds.transform,ds.width,ds.height)
                assert signature is None or sig==signature
                signature=sig
                arrays[role]=ds.read([1,2,3] if role=='rgb' else 1,masked=True)
            if role in ('rgb','reference','truth'):
                assert rec['sha256']==entry[f'{role}_checksum_sha256'],f'{name} {role} hash mismatch'
        rgb,ref,truth,mask,depth=[arrays[k] for k in ('rgb','reference','truth','scoring_mask','frozen_dav2')]
        valid=(~np.ma.getmaskarray(ref)&~np.ma.getmaskarray(truth)&~np.ma.getmaskarray(mask)
               &np.isfinite(ref.data)&np.isfinite(truth.data)&(mask.data!=0))
        iv=(~np.any(np.ma.getmaskarray(rgb),axis=0)&~np.ma.getmaskarray(ref)&~np.ma.getmaskarray(depth)
            &np.all(np.isfinite(rgb.data),axis=0)&np.isfinite(ref.data)&np.isfinite(depth.data))
        assert np.array_equal(valid,valid&iv),f'{name} V1 scoring mismatch'
        truth_fraction=float((~np.ma.getmaskarray(truth)&np.isfinite(truth.data)).mean())
        assert abs(float(valid.mean())-coverage)<1e-12, f'{name} scoring coverage mismatch: {valid.mean()}'
        metrics=baseline.compute_metrics(ref.data[valid],truth.data[valid])
        old=json.loads((derived/'baseline/reference_metrics.json').read_text())
        for key,want in [('mae',mae),('rmse',rmse)]:
            assert abs(metrics[key]-want)<1e-6 and abs(metrics[key]-old[key])<1e-9,f'{name} {key} mismatch'
        log=io.StringIO()
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            code=qa.main(['--rgb',str(paths['rgb']),'--reference',str(paths['reference']),'--truth',str(paths['truth'])])
        assert code==0,f'{name} QA failed: {log.getvalue()}'
        meta_path=pilot/'metadata/source_metadata.json'
        source=json.loads(meta_path.read_text()) if meta_path.exists() else None
        extras=list(sorted((pilot/'metadata').glob('*')))+[derived/'ai/depth_relative_metadata.json',derived/'baseline/reference_metrics.json']
        selection=pilot/'truth_raw/ept_selection.json'
        if selection.exists():extras.append(selection)
        for path in extras:
            if path.is_file():files.append(record(path,name,'provenance / historical metadata'))
        pilots.append(dict(region=name,canonical_aoi=dict(CRS=f'EPSG:{epsg}',bounds=bounds),
                           manifest_entry=entry,reference_product=entry['reference_source'],truth_product=entry['truth_source'],
                           RGB_acquisition_date=entry['rgb_date'],LiDAR_acquisition_date=entry['truth_date'],
                           vertical_datum=entry['reference_vertical_datum'],existing_source_metadata=source,
                           wake_provenance_text=(pilot/'metadata/PROVENANCE.md').read_text() if name=='wake' else None,
                           inference_mask='Not stored separately; V1 computes RGB/reference/DAV2 validity only in memory. Do not use truth/scoring mask for inference.',
                           scoring_mask=str(paths['scoring_mask']),input_valid_pixels=int(iv.sum()),scoring_pixels=int(valid.sum()),
                           truth_valid_fraction=truth_fraction,baseline_metrics=metrics,baseline_match='PASS',
                           triplet_QA='PASS',triplet_QA_output=log.getvalue(),
                           truth_construction='Existing maximum accepted LiDAR Z per 1 m cell; no interpolation. Wake accepts classes 1,2,3,4,5,6,9,10,13,14 and excludes 17/18 overlap classes and withheld. Other pilots accept 1,2,3,4,5,6,9,10,13,14,17 and exclude withheld/overlap flags; see unchanged source metadata and preparation script. Not regenerated.'))
        print(name, 'QA PASS baseline PASS', metrics['mae'],metrics['rmse'],int(valid.sum()))
    support=['manifests/schema.json','manifests/proposed_split.json','manifests/SPLIT_POLICY.md',
             'TRAINING_PILOT_SUMMARY.md','scripts/prepare_training_pilots.py','qa/check_triplet.py',
             'experiments/reference_baseline.py','geoinverse/config.py','geoinverse/dataset.py',
             'geoinverse/dataset_v1.py','residual/config.py','residual/dataset.py','scripts/inventory_canonical_pilots.py']
    for rel in support:files.append(record(ROOT/rel,'all','evaluation / provenance support'))
    outputs=['CANONICAL_PILOT_TRANSFER_MANIFEST.json','CANONICAL_PILOT_TRANSFER_README.md','CANONICAL_PILOT_FILELIST.txt']
    result=dict(schema_version='1.0',repository=str(REPO),branch=git('branch','--show-current'),HEAD=git('rev-parse','HEAD'),
                canonical_root=str(ROOT/'data'),transfer_root=str(ROOT),pilots=pilots,files=files,
                uncertainty_policy='Preserve existing NaN/unknown VDatum uncertainty; never interpret as zero.',
                trace='GeoInverse V0/V1 and Residual dataset/config modules load these same five rasters per pilot.',
                scope='No data modification, reprojection, regeneration, training, production change, commit or push.',
                generated_inventory_artifacts=outputs,total_input_bytes=sum(f['bytes'] for f in files))
    # All checks completed before creating the inventories; no historical output is overwritten.
    for out in outputs:assert not (ROOT/out).exists(),f'Existing inventory must not be overwritten: {out}'
    (ROOT/outputs[0]).write_text(json.dumps(result,indent=2,allow_nan=True)+'\n',encoding='utf-8')
    filelist=[Path(f['absolute_source_path']).relative_to(ROOT).as_posix() for f in files]+outputs
    (ROOT/outputs[2]).write_text('\n'.join(filelist)+'\n',encoding='utf-8')
    lines=['# Canonical four-pilot transfer','',f'Source/transfer root: `{ROOT}`.',
           'Copy ONLY the relative paths in CANONICAL_PILOT_FILELIST.txt, preserving their hierarchy under a new geoguard root. Do not independently reconstruct pilots. Raw LAZ/NAIP/GLO30 source tiles, checkpoints and unrelated results are unnecessary.',
           '','The JSON lists absolute/repository paths, SHA-256, bytes, Git classification, raster metadata, complete existing source metadata, manifest entries and QA logs. Generated inventory files are not self-hashed.',
           '','## Validation','']
    for p in pilots:lines.append(f"- {p['region']}: QA PASS; baseline PASS; MAE {p['baseline_metrics']['mae']:.12f}; RMSE {p['baseline_metrics']['rmse']:.12f}; scoring pixels {p['scoring_pixels']}.")
    lines += ['','## Masks and scientific provenance','',
              'valid_mask.tif is a truth/scoring intersection mask, not an inference-only mask. V1 computes input validity from RGB/reference/DAV2 alone in memory; no separate input-mask raster exists. The recomputed V1 scoring intersection equals the reference baseline mask.',
              'Maximum accepted Z per 1 m cell, no interpolation. Wake and the other three pilots have different historical accepted-class policies: Wake excludes class 17/18 overlap classes; the other preparation script accepts class 17 but rejects overlap/withheld flags. Preserve these exact policies, not an invented uniform class list.',
              'Existing provenance supports construction; this task does not re-rasterize raw point clouds to independently re-prove every exclusion.',
              'GLO30 retains effective ~30 m source resolution despite its aligned 1 m grid. Development/training counties are not blind-test data. Temporal/phenology mismatch and unquantified VDatum uncertainty remain. Wake VDatum details are in PROVENANCE.md and raster tags; there is no fabricated Wake source_metadata.json.',
              '','## Transfer and execution','',
              'Safest: make a selective archive or copy using the filelist from this transfer root; verify every received SHA-256 against the JSON before audit. Do not Git-add large raster assets. No raster duplication was performed here.',
              'Manish can copy the selected folder hierarchy and use the identical evaluation inputs. He still needs his audit code plus a compatible Python/Rasterio/NumPy environment; the data package alone is not a fully standalone audit installation.',
              'Run existing QA per pilot: python qa/check_triplet.py --rgb data/<name>_pilot/derived/rgb_aligned.tif --reference data/<name>_pilot/derived/reference_aligned.tif --truth data/<name>_pilot/derived/truth_aligned.tif',
              'Do not run preparation or baseline.run on canonical folders (the latter writes derived outputs). Baseline verification here called compute_metrics only.',
              '',f"Selected input/support bytes: {result['total_input_bytes']}; inventory files additional.",
              '','NO DATA MODIFICATION / NO REPROJECTION / NO REGENERATION / NO COMMIT / NO PUSH / NO PRODUCTION MODIFICATION.']
    (ROOT/outputs[1]).write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
