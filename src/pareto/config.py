"""Load Pareto roadmap YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from bench.conditions import BenchConditions, Corner
from bench.models import AccessModel
from pareto.paths import CONFIG_PATH


@dataclass(frozen=True)
class RetentionConfig:
    """Retention metric extraction settings."""

    delta_v_v: float
    v_cell0_v: float | None
    hold_start_s: float
    hold_end_s: float
    max_hold_s: float
    tran_step_hold_s: float
    extrapolate: bool
    direct_crossing: bool


@dataclass(frozen=True)
class PerformanceConfig:
    """Performance metric extraction settings."""

    bl_signal_v: float
    write_tol_v: float
    wl_read_rise_s: float
    wl_read_fall_s: float
    write_start_s: float
    write_end_s: float


@dataclass(frozen=True)
class ApplicationProfile:
    """Market segment anchor for architecture recommendation."""

    name: str
    min_t_ret_s: float
    target_t_ret_s: float
    corner: str
    optimize: tuple[str, ...]
    weight_energy: float


@dataclass(frozen=True)
class ParetoConfig:
    """Full Pareto roadmap experiment configuration."""

    ccell_values_ff: tuple[float, ...]
    pareto_corners: tuple[str, ...]
    reference_corner: str
    reference_ccell_ff: float
    retention: RetentionConfig
    performance: PerformanceConfig
    applications: dict[str, ApplicationProfile]


def load_corners(config_path: Path | None = None) -> dict[str, Corner]:
    """Load corner definitions from pareto YAML.

    Args:
        config_path: Optional override path.

    Returns:
        Mapping of corner name to :class:`Corner`.
    """
    path = config_path or CONFIG_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        name: Corner(name=name, temp_c=float(spec["temp_c"]), vdd_scale=float(spec["vdd_scale"]))
        for name, spec in raw["corners"].items()
    }


def resolve_conditions(model: AccessModel, corner: Corner) -> BenchConditions:
    """Combine model nominal biases with a corner definition.

    Args:
        model: Access transistor model metadata.
        corner: Temperature/Vdd corner.

    Returns:
        Fully resolved bench conditions.
    """
    vdd = model.nominal_vdd * corner.vdd_scale
    return BenchConditions(
        model=model,
        corner=corner,
        vdd=vdd,
        vdd_half=vdd / 2.0,
        wl_boost=vdd * 1.15,
        temp_c=corner.temp_c,
    )


def load_pareto_config(config_path: Path | None = None) -> ParetoConfig:
    """Load ``bench/pareto_roadmap/configs/pareto.yaml``.

    Args:
        config_path: Optional override path.

    Returns:
        Parsed :class:`ParetoConfig`.
    """
    path = config_path or CONFIG_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    ret = raw["retention"]
    perf = raw["performance"]
    apps: dict[str, ApplicationProfile] = {}
    for name, spec in raw["applications"].items():
        apps[name] = ApplicationProfile(
            name=name,
            min_t_ret_s=float(spec["min_t_ret_s"]),
            target_t_ret_s=float(spec.get("target_t_ret_s", spec["min_t_ret_s"])),
            corner=str(spec["corner"]),
            optimize=tuple(str(x) for x in spec["optimize"]),
            weight_energy=float(spec.get("weight_energy", 0.0)),
        )

    return ParetoConfig(
        ccell_values_ff=tuple(float(v) for v in raw["ccell_values_ff"]),
        pareto_corners=tuple(str(c) for c in raw["pareto_corners"]),
        reference_corner=str(raw["reference_corner"]),
        reference_ccell_ff=float(raw["reference_ccell_ff"]),
        retention=RetentionConfig(
            delta_v_v=float(ret["delta_v_v"]),
            v_cell0_v=float(ret["v_cell0_v"]) if ret.get("v_cell0_v") is not None else None,
            hold_start_s=float(ret["hold_start_s"]),
            hold_end_s=float(ret["hold_end_s"]),
            max_hold_s=float(ret.get("max_hold_s", 0.08)),
            tran_step_hold_s=float(ret.get("tran_step_hold_s", 5e-9)),
            extrapolate=bool(ret.get("extrapolate", True)),
            direct_crossing=bool(ret.get("direct_crossing", True)),
        ),
        performance=PerformanceConfig(
            bl_signal_v=float(perf["bl_signal_v"]),
            write_tol_v=float(perf["write_tol_v"]),
            wl_read_rise_s=float(perf["wl_read_rise_s"]),
            wl_read_fall_s=float(perf["wl_read_fall_s"]),
            write_start_s=float(perf["write_start_s"]),
            write_end_s=float(perf["write_end_s"]),
        ),
        applications=apps,
    )
