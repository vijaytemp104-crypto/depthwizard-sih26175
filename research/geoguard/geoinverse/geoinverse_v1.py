"""V1 inference contains no truth inputs and no learned low-frequency head."""
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from model import Block
from frequency import gaussian_kernel

SIGMA_M = 12.738853503184714

def lowpass(x, valid, pixel_size=1.0):
    """Differentiable V0-equivalent normalized Gaussian, reflect boundary."""
    k = torch.as_tensor(gaussian_kernel(SIGMA_M / pixel_size), device=x.device, dtype=x.dtype)
    r = len(k)//2
    def blur(a):
        a = F.conv2d(F.pad(a, (r,r,0,0), mode='reflect'), k.reshape(1,1,1,-1))
        return F.conv2d(F.pad(a, (0,0,r,r), mode='reflect'), k.reshape(1,1,-1,1))
    denominator = blur(valid.to(x.dtype))
    numerator = blur(torch.where(valid, x, torch.zeros_like(x)))
    return numerator / denominator.clamp_min(1e-6)

def constrain(raw, weight, valid, pixel_size=1.0):
    detail = torch.where(valid, raw-lowpass(raw,valid,pixel_size), 0.0)
    applied = weight*detail
    return detail, applied

class GeoInverseV1(nn.Module):
    def __init__(self, b=24):
        super().__init__()
        self.e1=Block(8,b); self.e2=Block(b,2*b); self.e3=Block(2*b,4*b)
        self.middle=Block(4*b,8*b); self.pool=nn.MaxPool2d(2)
        self.u3=nn.ConvTranspose2d(8*b,4*b,2,2); self.d3=Block(8*b,4*b)
        self.u2=nn.ConvTranspose2d(4*b,2*b,2,2); self.d2=Block(4*b,2*b)
        self.u1=nn.ConvTranspose2d(2*b,b,2,2); self.d1=Block(2*b,b)
        self.raw_head=nn.Conv2d(b,1,1); self.weight_head=nn.Conv2d(b,1,1)
        nn.init.zeros_(self.raw_head.weight); nn.init.zeros_(self.raw_head.bias)
        nn.init.zeros_(self.weight_head.weight); nn.init.constant_(self.weight_head.bias,math.log(.05/.95))
    def forward(self,x):
        a=self.e1(x); b=self.e2(self.pool(a)); c=self.e3(self.pool(b)); d=self.middle(self.pool(c))
        d=self.d3(torch.cat((self.u3(d),c),1)); d=self.d2(torch.cat((self.u2(d),b),1))
        d=self.d1(torch.cat((self.u1(d),a),1))
        return self.raw_head(d), torch.sigmoid(self.weight_head(d))

def support_loss(applied, input_valid, scoring_valid, pixel_size):
    return lowpass(applied,input_valid,pixel_size)[scoring_valid].abs().mean()

def loss(model, batch):
    raw,w=model(batch['features']); valid=batch['valid']; iv=batch['input_valid']
    pixel=float(batch['pixel_size'][0])
    if not torch.all(batch['pixel_size']==pixel): raise ValueError('Mixed pixel sizes in batch')
    detail,applied=constrain(raw,w,iv,pixel)
    candidate=batch['reference']+applied; truth=batch['truth']
    final=F.smooth_l1_loss(candidate[valid],truth[valid],beta=2.0)
    detail_loss=F.smooth_l1_loss(detail[valid],batch['high'][valid],beta=2.0)
    support=support_loss(applied,iv,valid,pixel)
    preserve=(applied[valid].abs()/(1+(truth[valid]-batch['reference'][valid]).abs())).mean()
    edges=[]
    for axis in (-1,-2):
        mask=valid.narrow(axis,1,valid.shape[axis]-1)&valid.narrow(axis,0,valid.shape[axis]-1)
        error=(torch.diff(candidate,dim=axis)-torch.diff(truth,dim=axis))/pixel
        edges.append(error[mask].abs().mean())
    edge=sum(edges)/2
    total=final+.50*detail_loss+.05*support+.02*preserve+.01*edge
    return total, torch.stack((final,detail_loss,support,preserve,edge))
