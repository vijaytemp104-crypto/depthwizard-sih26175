#!/usr/bin/env python3
"""Train and evaluate fixed leave-one-region-out GeoInverse V0 folds."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

from config import CONFIG, FOLDS, OUTPUT, ROOT
from dataset import fold, load_scene
from evaluate import evaluate
from model import GeoInverseNet, reconstruct


def seed_all(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.use_deterministic_algorithms(True)


def losses(model, batch, device):
    x = batch["features"].to(device); reference = batch["reference"].to(device)
    truth = batch["truth"].to(device); valid = batch["valid"].to(device).bool()
    target_low = batch["low"].to(device); target_high = batch["high"].to(device)
    low, high, weight = model(x); candidate = reconstruct(reference, low, high, weight)
    final = F.smooth_l1_loss(candidate[valid], truth[valid], beta=CONFIG.huber_beta_m)
    low_loss = F.l1_loss(low[valid], target_low[valid]); high_loss = F.l1_loss(high[valid], target_high[valid])
    preserve = torch.abs(low[valid]).mean() + CONFIG.preserve_detail_lambda * (weight[valid] * torch.abs(high[valid])).mean()
    horizontal = valid[..., :, 1:] & valid[..., :, :-1]; vertical = valid[..., 1:, :] & valid[..., :-1, :]
    edge_x = torch.abs((candidate[..., :, 1:] - candidate[..., :, :-1])[horizontal] - (truth[..., :, 1:] - truth[..., :, :-1])[horizontal]).mean()
    edge_y = torch.abs((candidate[..., 1:, :] - candidate[..., :-1, :])[vertical] - (truth[..., 1:, :] - truth[..., :-1, :])[vertical]).mean()
    edge = (edge_x + edge_y) / 2
    total = final + CONFIG.low_loss_weight*low_loss + CONFIG.high_loss_weight*high_loss + CONFIG.preserve_loss_weight*preserve + CONFIG.edge_loss_weight*edge
    return total, (final, low_loss, high_loss, preserve, edge)


def validate(model, loader, device):
    model.eval(); values=[]
    with torch.inference_mode():
        for batch in loader: values.append(float(losses(model, batch, device)[0]))
    return float(np.mean(values))


def train_region(region: str, device: torch.device):
    seed_all(CONFIG.seed)
    train_data, validation_data, scenes = fold(region)
    generator = torch.Generator().manual_seed(CONFIG.seed)
    train_loader = DataLoader(train_data, batch_size=CONFIG.batch_size, shuffle=True, generator=generator, num_workers=0)
    validation_loader = DataLoader(validation_data, batch_size=CONFIG.batch_size, shuffle=False, num_workers=0)
    model = GeoInverseNet(CONFIG.input_channels, CONFIG.base_channels, CONFIG.initial_detail_weight).to(device)
    count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG.learning_rate, weight_decay=CONFIG.weight_decay)
    output = OUTPUT / f"holdout_{region}"; output.mkdir(parents=True, exist_ok=True)
    best=float("inf"); best_epoch=0; stale=0; history=[]; started=time.perf_counter()
    for epoch in range(1, CONFIG.maximum_epochs+1):
        model.train(); epoch_values=[]
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True); total, components=losses(model,batch,device); total.backward(); optimizer.step()
            epoch_values.append([float(total.detach()), *[float(item.detach()) for item in components]])
        held=validate(model,validation_loader,device); means=np.mean(epoch_values,axis=0)
        row={"epoch":epoch,"train_total":float(means[0]),"final":float(means[1]),"low":float(means[2]),"high":float(means[3]),"preserve":float(means[4]),"edge":float(means[5]),"held_out":held}
        history.append(row); print(json.dumps({"fold":region,**row}),flush=True)
        if held < best-1e-6:
            best=held; best_epoch=epoch; stale=0; torch.save(model.state_dict(),output/"best.pt")
        else:
            stale+=1
            if stale>=CONFIG.patience: break
    runtime=time.perf_counter()-started
    model.load_state_dict(torch.load(output/"best.pt",map_location=device,weights_only=True))
    record={"held_out_region":region,"training_regions":list(FOLDS[region]),"device":str(device),"runtime_seconds":runtime,"trainable_parameters":count,"train_patches":len(train_data),"held_out_patches":len(validation_data),"best_epoch":best_epoch,"epochs_run":len(history),"best_loss":best,"config":CONFIG.to_dict(),"loss_equation":"L_final + 0.25 L_low + 0.25 L_high + 0.02 L_preserve + 0.02 L_edge","semantic_representation":"optional architecture channel group disabled: no local lightweight semantic checkpoint","history":history}
    (output/"training.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    return record,evaluate(region,model,scenes[region],device)


def summary(training, results):
    equal={}
    for name,path in {
        "reference_mae":("reference","mae"),
        "affine_mae":("affine_dav2","mae"),
        "v1_mae":("residual_v1","mae"),
        "geoinverse_mae":("geoinverse_v0","mae"),
        "reference_rmse":("reference","rmse"),
        "geoinverse_rmse":("geoinverse_v0","rmse"),
        "geoinverse_bias":("geoinverse_v0","bias"),
        "geoinverse_pearson":("geoinverse_v0","pearson"),
        "geoinverse_spearman":("geoinverse_v0","spearman"),
        "mae_change":("changes","mae_percent_vs_reference"),
        "rmse_change":("changes","rmse_percent_vs_reference"),
        "beneficial_cells":("support_cells","beneficial_cells_percent"),
        "harmful_cells":("support_cells","harmful_cells_percent"),
        "weight_mean":("weight_detail","mean"),
        "weight_benefit_correlation":("weight_detail","pearson_with_actual_benefit"),
        "oracle_improvement":("oracle_mae_improvement_percent",None),
    }.items():
        equal[name]=float(np.mean([r[path[0]] if path[1] is None else r[path[0]][path[1]] for r in results]))
    equal["mae_percent_change_from_region_equal"] = float(
        100 * (equal["geoinverse_mae"] - equal["reference_mae"]) / equal["reference_mae"]
    )
    equal["rmse_percent_change_from_region_equal"] = float(
        100 * (equal["geoinverse_rmse"] - equal["reference_rmse"]) / equal["reference_rmse"]
    )
    v1_results=json.loads((ROOT/"outputs"/"residual_v1"/"results.json").read_text(encoding="utf-8"))
    v1_oracle=float(v1_results["region_equal"]["oracle_improvement_percent"])
    oracle_difference=equal["oracle_improvement"]-v1_oracle
    oracle_ratio=equal["oracle_improvement"]/v1_oracle if v1_oracle else math.inf
    improved_regions=sum(r["geoinverse_v0"]["mae"] < r["reference"]["mae"] for r in results)
    polk_safe=next(r for r in results if r["held_out_region"] == "polk")["geoinverse_v0"]["mae"] <= next(r for r in results if r["held_out_region"] == "polk")["reference"]["mae"]
    success={
        "region_equal_mae_improved": equal["geoinverse_mae"] < equal["reference_mae"],
        "polk_not_damaged": polk_safe,
        "at_least_two_regions_improved": improved_regions >= 2,
        "regions_improved": improved_regions,
        "oracle_headroom_materially_greater_than_v1": oracle_difference >= 1.0 and oracle_ratio >= 2.0,
        "oracle_v1_improvement_percent": v1_oracle,
        "oracle_improvement_difference_percentage_points": oracle_difference,
        "oracle_improvement_ratio": oracle_ratio,
    }
    success["overall"] = success["region_equal_mae_improved"] and success["polk_not_damaged"] and success["at_least_two_regions_improved"] and success["oracle_headroom_materially_greater_than_v1"]
    combined={"training":training,"folds":results,"region_equal":equal,"success_criteria":success}
    (OUTPUT/"results.json").write_text(json.dumps(combined,indent=2)+"\n",encoding="utf-8")
    lines=["# GeoInverse V0 results","","Negative change denotes improvement. All oracle values are truth-aware and non-deployable.","","| Region | Reference MAE | Affine MAE | V1 MAE | GeoInverse MAE | MAE change | Reference RMSE | GeoInverse RMSE | Beneficial cells | Harmful cells | Oracle MAE | Oracle improvement |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append("| {held_out_region} | {reference[mae]:.6f} | {affine_dav2[mae]:.6f} | {residual_v1[mae]:.6f} | {geoinverse_v0[mae]:.6f} | {changes[mae_percent_vs_reference]:.3f}% | {reference[rmse]:.6f} | {geoinverse_v0[rmse]:.6f} | {support_cells[beneficial_cells_percent]:.3f}% | {support_cells[harmful_cells_percent]:.3f}% | {truth_aware_oracle[mae]:.6f} | {oracle_mae_improvement_percent:.3f}% |".format(**r))
    lines += [
        "",
        "## Region-equal aggregate",
        "",
        f"- Reference MAE: {equal['reference_mae']:.6f} m",
        f"- Affine DAV2 MAE: {equal['affine_mae']:.6f} m",
        f"- Residual V1 MAE: {equal['v1_mae']:.6f} m",
        f"- GeoInverse V0 MAE: {equal['geoinverse_mae']:.6f} m ({equal['mae_percent_change_from_region_equal']:+.3f}% from region-equal reference; {equal['mae_change']:+.3f}% mean fold change)",
        f"- Reference RMSE: {equal['reference_rmse']:.6f} m",
        f"- GeoInverse V0 RMSE: {equal['geoinverse_rmse']:.6f} m ({equal['rmse_percent_change_from_region_equal']:+.3f}% from region-equal reference; {equal['rmse_change']:+.3f}% mean fold change)",
        f"- GeoInverse V0 bias / Pearson / Spearman: {equal['geoinverse_bias']:.6f} m / {equal['geoinverse_pearson']:.6f} / {equal['geoinverse_spearman']:.6f}",
        f"- Beneficial / harmful support cells: {equal['beneficial_cells']:.3f}% / {equal['harmful_cells']:.3f}%",
        f"- Detail-weight mean / correlation with actual benefit: {equal['weight_mean']:.6f} / {equal['weight_benefit_correlation']:.6f}",
        f"- Truth-aware oracle MAE improvement: {equal['oracle_improvement']:.3f}%",
        f"- Residual V1 truth-aware oracle improvement: {v1_oracle:.3f}%",
        f"- GeoInverse oracle headroom increase over V1: {oracle_difference:+.3f} percentage points ({oracle_ratio:.2f}x)",
        "",
        "## Success criteria",
        "",
        f"- Region-equal MAE improves: {'PASS' if success['region_equal_mae_improved'] else 'FAIL'}",
        f"- Polk is not damaged: {'PASS' if success['polk_not_damaged'] else 'FAIL'}",
        f"- At least two regions improve: {'PASS' if success['at_least_two_regions_improved'] else 'FAIL'} ({improved_regions}/4)",
        f"- Oracle headroom materially exceeds V1: {'PASS' if success['oracle_headroom_materially_greater_than_v1'] else 'FAIL'} (reporting rule: at least +1 percentage point and 2x; not predeclared before training)",
        f"- Overall decision: {'GO' if success['overall'] else 'NO-GO'}",
    ]
    lines += ["","## Method","",f"- Gaussian decomposition: 30 m FWHM, sigma {CONFIG.gaussian_sigma_m:.6f} m, masked normalized convolution.","- Reconstruction: `reference + delta_low + weight_detail * delta_high`.","- Semantic inputs are optional but disabled in V0 because no local lightweight semantic checkpoint was available.","- Proxy strata are deployment-available diagnostics, not semantic ground truth or calibrated confidence.",""]
    (ROOT/"GEOINVERSE_V0_RESULTS.md").write_text("\n".join(lines),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--evaluate-only",action="store_true"); args=parser.parse_args()
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu"); torch.set_num_threads(max(1,min(8,os.cpu_count() or 1)))
    training=[]; results=[]
    for region in FOLDS:
        if args.evaluate_only:
            output=OUTPUT/f"holdout_{region}"; model=GeoInverseNet(CONFIG.input_channels,CONFIG.base_channels,CONFIG.initial_detail_weight).to(device); model.load_state_dict(torch.load(output/"best.pt",map_location=device,weights_only=True)); training.append(json.loads((output/"training.json").read_text())); results.append(evaluate(region,model,load_scene(region),device))
        else:
            t,r=train_region(region,device); training.append(t); results.append(r)
    summary(training,results); return 0


if __name__ == "__main__": raise SystemExit(main())
