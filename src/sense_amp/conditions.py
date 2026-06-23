"""Benchmark corner and bias condition helpers."""

from __future__ import annotations

from dataclasses import dataclass

from sense_amp.models import AccessModel
from sense_amp.paths import load_read_path_config


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
    vbl_pre: float
    wl_boost: float
    temp_c: float


def load_corners(config: dict | None = None) -> dict[str, Corner]:
    """Load corner definitions from YAML config.

    Args:
        config: Optional pre-loaded configuration.

    Returns:
        Mapping of corner name to :class:`Corner`.
    """
    raw = config or load_read_path_config()
    return {
        name: Corner(name=name, temp_c=float(spec["temp_c"]), vdd_scale=float(spec["vdd_scale"]))
        for name, spec in raw["corners"].items()
    }


def resolve_conditions(
    model: AccessModel,
    corner: Corner,
    *,
    vbl_pre_fraction: float = 0.5,
) -> BenchConditions:
    """Combine model nominal biases with a corner definition.

    Args:
        model: Access transistor model metadata.
        corner: Temperature/Vdd corner.
        vbl_pre_fraction: BL precharge level as a fraction of Vdd.

    Returns:
        Fully resolved bench conditions.
    """
    vdd = model.nominal_vdd * corner.vdd_scale
    return BenchConditions(
        model=model,
        corner=corner,
        vdd=vdd,
        vbl_pre=vdd * vbl_pre_fraction,
        wl_boost=vdd * 1.15,
        temp_c=corner.temp_c,
    )
