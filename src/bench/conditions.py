"""Benchmark corner and bias condition helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from bench.corner_registry import load_corners_from_registry
from bench.models import AccessModel
from bench.paths import CONFIG_PATH


@dataclass(frozen=True)
class Corner:
    """Simulation corner (temperature and Vdd scale)."""

    name: str
    temp_c: float
    vdd_scale: float


@dataclass(frozen=True)
class BenchConditions:
    """Resolved electrical conditions for one model and corner."""

    model: AccessModel
    corner: Corner
    vdd: float
    vdd_half: float
    wl_boost: float
    temp_c: float

    @property
    def ac_freq_hz(self) -> float:
        return 1.0e6


def _parse_corners(raw: dict) -> dict[str, Corner]:
    return {
        name: Corner(name=name, temp_c=float(spec["temp_c"]), vdd_scale=float(spec["vdd_scale"]))
        for name, spec in raw["corners"].items()
    }


def load_corners(config_path: Path | None = None) -> dict[str, Corner]:
    """Load corners from explicit path, IDEA153 registry, or local YAML (see OPEN_DRAM_CORNER_SOURCE)."""
    if config_path is not None:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        return _parse_corners(raw)
    return load_corners_from_registry(local_path=CONFIG_PATH)


def resolve_conditions(model: AccessModel, corner: Corner) -> BenchConditions:
    """Combine model nominal biases with a corner definition."""
    vdd = model.nominal_vdd * corner.vdd_scale
    return BenchConditions(
        model=model,
        corner=corner,
        vdd=vdd,
        vdd_half=vdd / 2.0,
        wl_boost=vdd * 1.15,
        temp_c=corner.temp_c,
    )
