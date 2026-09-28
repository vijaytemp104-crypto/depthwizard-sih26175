"""Reference-preserving multi-head GeoInverse V0 network."""

from __future__ import annotations

import math

import torch
from torch import nn


class Block(nn.Module):
    def __init__(self, input_channels: int, output_channels: int) -> None:
        super().__init__()
        groups = min(8, output_channels)
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


class GeoInverseNet(nn.Module):
    def __init__(self, input_channels: int = 8, base_channels: int = 24, initial_weight: float = 0.05) -> None:
        super().__init__()
        b = base_channels
        self.e1 = Block(input_channels, b)
        self.e2 = Block(b, 2 * b)
        self.e3 = Block(2 * b, 4 * b)
        self.middle = Block(4 * b, 8 * b)
        self.pool = nn.MaxPool2d(2)
        self.u3 = nn.ConvTranspose2d(8 * b, 4 * b, 2, 2)
        self.d3 = Block(8 * b, 4 * b)
        self.u2 = nn.ConvTranspose2d(4 * b, 2 * b, 2, 2)
        self.d2 = Block(4 * b, 2 * b)
        self.u1 = nn.ConvTranspose2d(2 * b, b, 2, 2)
        self.d1 = Block(2 * b, b)
        self.low_head = nn.Conv2d(8 * b, 1, 1)
        self.high_head = nn.Conv2d(b, 1, 1)
        self.weight_head = nn.Conv2d(b, 1, 1)
        nn.init.zeros_(self.low_head.weight)
        nn.init.zeros_(self.low_head.bias)
        nn.init.zeros_(self.high_head.weight)
        nn.init.zeros_(self.high_head.bias)
        nn.init.zeros_(self.weight_head.weight)
        nn.init.constant_(self.weight_head.bias, math.log(initial_weight / (1 - initial_weight)))

    def forward(self, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        e1 = self.e1(values)
        e2 = self.e2(self.pool(e1))
        e3 = self.e3(self.pool(e2))
        middle = self.middle(self.pool(e3))
        d3 = self.d3(torch.cat((self.u3(middle), e3), 1))
        d2 = self.d2(torch.cat((self.u2(d3), e2), 1))
        detail = self.d1(torch.cat((self.u1(d2), e1), 1))
        low = torch.nn.functional.interpolate(
            self.low_head(middle), size=values.shape[-2:], mode="bilinear", align_corners=False
        )
        high = self.high_head(detail)
        weight = torch.sigmoid(self.weight_head(detail))
        return low, high, weight


def reconstruct(
    reference_m: torch.Tensor,
    delta_low_m: torch.Tensor,
    delta_high_m: torch.Tensor,
    weight_detail: torch.Tensor,
) -> torch.Tensor:
    return reference_m + delta_low_m + weight_detail * delta_high_m
