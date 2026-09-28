"""Small convolutional residual-elevation model."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class ConvBlock(nn.Module):
    def __init__(self, input_channels: int, output_channels: int) -> None:
        super().__init__()
        groups = max(1, min(8, output_channels // 4))
        while output_channels % groups:
            groups -= 1
        self.layers = nn.Sequential(
            nn.Conv2d(input_channels, output_channels, 3, padding=1, bias=False),
            nn.GroupNorm(groups, output_channels),
            nn.SiLU(inplace=True),
            nn.Conv2d(output_channels, output_channels, 3, padding=1, bias=False),
            nn.GroupNorm(groups, output_channels),
            nn.SiLU(inplace=True),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.layers(values)


class ResidualUNet(nn.Module):
    """Three-level U-Net whose single output channel is a correction in metres."""

    def __init__(self, input_channels: int = 7, base_channels: int = 24) -> None:
        super().__init__()
        b = base_channels
        self.encoder1 = ConvBlock(input_channels, b)
        self.encoder2 = ConvBlock(b, 2 * b)
        self.encoder3 = ConvBlock(2 * b, 4 * b)
        self.bottleneck = ConvBlock(4 * b, 8 * b)
        self.down = nn.MaxPool2d(2)
        self.up3 = nn.ConvTranspose2d(8 * b, 4 * b, 2, stride=2)
        self.decoder3 = ConvBlock(8 * b, 4 * b)
        self.up2 = nn.ConvTranspose2d(4 * b, 2 * b, 2, stride=2)
        self.decoder2 = ConvBlock(4 * b, 2 * b)
        self.up1 = nn.ConvTranspose2d(2 * b, b, 2, stride=2)
        self.decoder1 = ConvBlock(2 * b, b)
        self.output = nn.Conv2d(b, 1, 1)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        e1 = self.encoder1(values)
        e2 = self.encoder2(self.down(e1))
        e3 = self.encoder3(self.down(e2))
        middle = self.bottleneck(self.down(e3))
        d3 = self.decoder3(torch.cat((self.up3(middle), e3), dim=1))
        d2 = self.decoder2(torch.cat((self.up2(d3), e2), dim=1))
        d1 = self.decoder1(torch.cat((self.up1(d2), e1), dim=1))
        return self.output(d1)


def candidate_from_residual(reference_m: torch.Tensor, residual_m: torch.Tensor) -> torch.Tensor:
    """Combine reference and correction without changing physical metre units."""

    if reference_m.shape != residual_m.shape:
        raise ValueError("reference and residual must share a shape")
    return reference_m + residual_m


def masked_huber_loss(
    residual_m: torch.Tensor,
    reference_m: torch.Tensor,
    truth_m: torch.Tensor,
    valid: torch.Tensor,
    *,
    beta_m: float,
) -> torch.Tensor:
    candidate_m = candidate_from_residual(reference_m, residual_m)
    selected = valid.bool()
    if not torch.any(selected):
        raise ValueError("masked loss requires at least one valid pixel")
    return F.smooth_l1_loss(candidate_m[selected], truth_m[selected], beta=beta_m)


def masked_gradient_l1(
    candidate_m: torch.Tensor, truth_m: torch.Tensor, valid: torch.Tensor
) -> torch.Tensor:
    horizontal = valid[..., :, 1:].bool() & valid[..., :, :-1].bool()
    vertical = valid[..., 1:, :].bool() & valid[..., :-1, :].bool()
    losses: list[torch.Tensor] = []
    if torch.any(horizontal):
        candidate_dx = candidate_m[..., :, 1:] - candidate_m[..., :, :-1]
        truth_dx = truth_m[..., :, 1:] - truth_m[..., :, :-1]
        losses.append(torch.abs(candidate_dx[horizontal] - truth_dx[horizontal]).mean())
    if torch.any(vertical):
        candidate_dy = candidate_m[..., 1:, :] - candidate_m[..., :-1, :]
        truth_dy = truth_m[..., 1:, :] - truth_m[..., :-1, :]
        losses.append(torch.abs(candidate_dy[vertical] - truth_dy[vertical]).mean())
    if not losses:
        return candidate_m.sum() * 0.0
    return torch.stack(losses).mean()
