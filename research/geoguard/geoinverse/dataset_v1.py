"""Input-only preprocessing; historical scoring mask and patch geometry preserved."""
from dataclasses import dataclass
import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset
from config import PILOTS
from dataset import starts
from frequency import masked_low_pass, decompose_residual
from geoinverse_v1 import SIGMA_M

def features_from_inputs(rgb, reference, depth, input_valid, pixel):
    rgb=np.where(input_valid[None],rgb,0).astype('float32')/255
    fill=np.where(input_valid,reference,np.median(reference[input_valid])).astype('float32')
    smooth=masked_low_pass(fill,np.ones(input_valid.shape,bool),sigma_m=SIGMA_M,pixel_size_m=pixel)
    gy,gx=np.gradient(smooth)  # preserve V0 feature scaling; physical metrics are separate
    median=np.median(depth[input_valid]); q25,q75=np.percentile(depth[input_valid],[25,75])
    dn=np.clip((np.where(input_valid,depth,median)-median)/max(float(q75-q25),1e-6),-5,5)/5
    ly,lx=np.gradient(.299*rgb[0]+.587*rgb[1]+.114*rgb[2])
    return np.concatenate((rgb,fill[None]/2500,dn[None],np.clip(gx[None]/20,-1,1),np.clip(gy[None]/20,-1,1),np.clip(np.hypot(lx,ly)[None]/.5,0,1))).astype('float32')

@dataclass
class Scene:
    name:str
    features:np.ndarray
    reference:np.ndarray
    truth:np.ndarray
    valid:np.ndarray
    input_valid:np.ndarray
    high:np.ndarray
    profile:dict
    pixel:float
    mask_difference:int

def load(name):
    root=PILOTS[name]/'derived'; arrays={}; signatures=[]
    for key,file in dict(rgb='rgb_aligned.tif',reference='reference_aligned.tif',depth='ai/depth_relative.tif',truth='truth_aligned.tif',mask='valid_mask.tif').items():
        with rasterio.open(root/file) as ds:
            arrays[key]=ds.read([1,2,3] if key=='rgb' else 1,masked=True)
            signatures.append((ds.crs,ds.transform,ds.width,ds.height))
            if key=='reference': profile=ds.profile.copy(); resolution=ds.res; units=ds.crs.linear_units
    if len(set(signatures))!=1: raise ValueError('Grid mismatch')
    if units not in ('metre','meter') or not np.isclose(resolution[0],resolution[1]): raise ValueError('Expected square metre grid')
    pixel=float(resolution[0]); rgb,ref,depth,truth,mask=[arrays[k] for k in ('rgb','reference','depth','truth','mask')]
    iv=(~np.any(np.ma.getmaskarray(rgb),axis=0)&~np.ma.getmaskarray(ref)&~np.ma.getmaskarray(depth)&np.all(np.isfinite(rgb.data),axis=0)&np.isfinite(ref.data)&np.isfinite(depth.data))
    valid=iv&~np.ma.getmaskarray(truth)&~np.ma.getmaskarray(mask)&(mask.data!=0)&np.isfinite(truth.data)
    historical=(~np.any(np.ma.getmaskarray(rgb),axis=0)&~np.ma.getmaskarray(ref)&~np.ma.getmaskarray(depth)&~np.ma.getmaskarray(truth)&~np.ma.getmaskarray(mask)&(mask.data!=0)&np.isfinite(ref.data)&np.isfinite(depth.data)&np.isfinite(truth.data))
    features=features_from_inputs(rgb.data,ref.data,depth.data,iv,pixel)
    _,high=decompose_residual(truth.data.astype('float32'),ref.data.astype('float32'),valid,sigma_m=SIGMA_M,pixel_size_m=pixel)
    return Scene(name,features,ref.data.astype('float32'),truth.data.astype('float32'),valid,iv,high,profile,pixel,int(np.count_nonzero(valid!=historical)))

class Patches(Dataset):
    def __init__(self,scenes):
        self.scenes=scenes; self.samples=[]
        for i,s in enumerate(scenes):
            for y in starts(s.valid.shape[0],256,192):
                for x in starts(s.valid.shape[1],256,192):
                    if s.valid[y:y+256,x:x+256].mean()>=.8: self.samples.append((i,y,x))
    def __len__(self): return len(self.samples)
    def __getitem__(self,i):
        j,y,x=self.samples[i]; s=self.scenes[j]; z=np.s_[y:y+256,x:x+256]
        b={k:torch.from_numpy(getattr(s,k)[z][None].copy()) for k in ('reference','truth','valid','input_valid','high')}
        b['features']=torch.from_numpy(s.features[:,z[0],z[1]].copy()); b['pixel_size']=s.pixel
        return b
