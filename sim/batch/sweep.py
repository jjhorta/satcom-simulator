"""
Parametric sweep — generate Walker constellation parameter grids.

Supports:
- Range: (start, stop, step) using numpy.linspace semantics
- Values: explicit list of values
- Cartesian product of all parameter dimensions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Literal

import numpy as np


@dataclass
class SweepParam:
    """Definition of one swept parameter dimension."""
    param: str  # one of: 'sats', 'planes', 'inclination', 'altitude', 'phasing'
    values: list[float | str]  # explicit list of values (str for weather, float for geometry)

    @classmethod
    def from_range(cls, param: str, start: float, stop: float, step: float | int) -> "SweepParam":
        """Generate values from start to stop (inclusive)."""
        if param in ("sats", "planes", "phasing"):
            values = list(range(int(start), int(stop) + 1, int(step)))
        else:
            num = max(2, int(round((stop - start) / step)) + 1)
            values = list(np.linspace(start, stop, num))
            values = [round(v, 1) for v in values]
        return cls(param=param, values=values)


@dataclass
class SweepDefinition:
    """Complete sweep definition — generates all configurations."""
    mode: Literal["heatmap", "heatmap-rf", "coverage"]
    comms: str = "vdes"
    weather: str = "clear"
    min_elev: float = 10.0
    res: float = 5.0
    duration: int = 3600
    fixed_params: dict[str, Any] = field(default_factory=dict)
    sweep_params: list[SweepParam] = field(default_factory=list)

    def generate_configs(self) -> list[dict[str, Any]]:
        """Generate all parameter combinations (Cartesian product)."""
        if not self.sweep_params:
            return [self.fixed_params.copy()]
        dim_values = [sp.values for sp in self.sweep_params]
        dim_names = [sp.param for sp in self.sweep_params]
        configs = []
        for combo in product(*dim_values):
            config = self.fixed_params.copy()
            for name, val in zip(dim_names, combo):
                config[name] = val
            configs.append(config)
        return configs

    @property
    def num_configs(self) -> int:
        """Total number of configurations in the sweep."""
        if not self.sweep_params:
            return 1
        return int(np.prod([len(sp.values) for sp in self.sweep_params]))

    def label_for(self, config: dict[str, Any]) -> str:
        """Human-readable label e.g. 's48_p6_i53_a600'."""
        parts = []
        for sp in self.sweep_params:
            val = config.get(sp.param)
            if sp.param == "sats":
                parts.append(f"s{int(val)}")
            elif sp.param == "planes":
                parts.append(f"p{int(val)}")
            elif sp.param == "inclination":
                parts.append(f"i{val:.0f}")
            elif sp.param == "altitude":
                parts.append(f"a{int(val)}")
            elif sp.param == "phasing":
                parts.append(f"f{int(val)}")
        return "_".join(parts) if parts else "default"
