"""Load Ccell roadmap YAML configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from bench.conditions import BenchConditions, Corner
from bench.models import AccessModel
from pareto.config import PerformanceConfig, RetentionConfig

from ccell.paths import CONFIG_PATH


@dataclass(frozen=True)
class ReadConstraintConfig:
    """Read-path pass criterion (sense-amp SA yield or pareto BL-swing)."""

    mode: str  # sa_yield | bl_swing
    target_yield: float
    default_gain: float
    sigma_os_mv: float
    m_min_mv: float
    vbl_pre_fraction: float
    use_sa_spec: bool


@dataclass(frozen=True)
class ConstraintConfig:
    """Dual retention + read-signal targets."""

    min_t_ret_s: float
    min_dv_read_v: float
    t_en_ns: float


@dataclass(frozen=True)
class CapacitorGeometry:
    """Geometric plate-capacitor model parameters."""

    epsilon0_f_per_m: float
    t_dielectric_nm: float
    area_alpha: dict[str, float]
    structure_factor: dict[str, float]


@dataclass(frozen=True)
class DielectricScenario:
    """One k-roadmap scenario."""

    name: str
    k_by_node: dict[str, float]


@dataclass(frozen=True)
class ThreeDBoostConfig:
    """3D vertical capacitor boost settings."""

    beta_values: tuple[float, ...]
    reference_planar_model: str
    compare_models: tuple[str, ...]


@dataclass(frozen=True)
class CcellConfig:
    """Full Ccell roadmap experiment configuration."""

    ccell_values_ff: tuple[float, ...]
    read_extrapolate_ccell_ff: tuple[float, ...]
    retention_corner: str
    read_corner: str
    constraints: ConstraintConfig
    read_constraint: ReadConstraintConfig
    retention: RetentionConfig
    performance: PerformanceConfig
    bitline: dict[str, float]
    capacitor_geometry: CapacitorGeometry
    dielectric_scenarios: dict[str, DielectricScenario]
    three_d_boost: ThreeDBoostConfig
    device_whatif_ioff_scale: tuple[float, ...]


def load_corners(config_path: Path | None = None) -> dict[str, Corner]:
    """Load corner definitions from ccell YAML."""
    path = config_path or CONFIG_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        name: Corner(name=name, temp_c=float(spec["temp_c"]), vdd_scale=float(spec["vdd_scale"]))
        for name, spec in raw["corners"].items()
    }


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


def load_ccell_config(config_path: Path | None = None) -> CcellConfig:
    """Load ``bench/ccell_roadmap/configs/ccell.yaml``."""
    path = config_path or CONFIG_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    ret = raw["retention"]
    perf = raw["performance"]
    cons = raw["constraints"]
    read_cons = raw.get("read_constraint", {})
    geom = raw["capacitor_geometry"]

    scenarios: dict[str, DielectricScenario] = {}
    for name, spec in raw["dielectric_scenarios"].items():
        scenarios[name] = DielectricScenario(
            name=name,
            k_by_node={str(k): float(v) for k, v in spec["k_by_node"].items()},
        )

    boost = raw["three_d_boost"]
    whatif = raw.get("device_whatif", {})

    return CcellConfig(
        ccell_values_ff=tuple(float(v) for v in raw["ccell_values_ff"]),
        read_extrapolate_ccell_ff=tuple(
            float(v) for v in raw.get("read_extrapolate_ccell_ff", [])
        ),
        retention_corner=str(raw["retention_corner"]),
        read_corner=str(raw["read_corner"]),
        constraints=ConstraintConfig(
            min_t_ret_s=float(cons["min_t_ret_s"]),
            min_dv_read_v=float(cons["min_dv_read_v"]),
            t_en_ns=float(cons["t_en_ns"]),
        ),
        read_constraint=ReadConstraintConfig(
            mode=str(read_cons.get("mode", "sa_yield")),
            target_yield=float(read_cons.get("target_yield", 0.999)),
            default_gain=float(read_cons.get("default_gain", 10.0)),
            sigma_os_mv=float(read_cons.get("sigma_os_mv", 10.0)),
            m_min_mv=float(read_cons.get("m_min_mv", 50.0)),
            vbl_pre_fraction=float(
                read_cons.get(
                    "vbl_pre_fraction",
                    raw.get("bitline", {}).get("vbl_pre_fraction", 0.50),
                )
            ),
            use_sa_spec=bool(read_cons.get("use_sa_spec", True)),
        ),
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
        bitline={k: float(v) for k, v in raw["bitline"].items()},
        capacitor_geometry=CapacitorGeometry(
            epsilon0_f_per_m=float(geom["epsilon0_f_per_m"]),
            t_dielectric_nm=float(geom["t_dielectric_nm"]),
            area_alpha={str(k): float(v) for k, v in geom["area_alpha"].items()},
            structure_factor={
                str(k): float(v) for k, v in geom.get("structure_factor", {}).items()
            },
        ),
        dielectric_scenarios=scenarios,
        three_d_boost=ThreeDBoostConfig(
            beta_values=tuple(float(v) for v in boost["beta_values"]),
            reference_planar_model=str(boost["reference_planar_model"]),
            compare_models=tuple(str(m) for m in boost["compare_models"]),
        ),
        device_whatif_ioff_scale=tuple(
            float(v) for v in whatif.get("ioff_scale_factors", [1.0])
        ),
    )
