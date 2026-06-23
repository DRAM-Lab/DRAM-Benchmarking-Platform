"""Dielectric k scenario → achievable Ccell model."""

from __future__ import annotations

import pandas as pd
from bench.models import load_access_model

from ccell.config import CcellConfig, DielectricScenario
from ccell.metrics import CcellMinRow


def area_alpha_for_architecture(architecture: str, cfg: CcellConfig) -> float:
    """Return plate-area multiplier for an architecture family."""
    return float(cfg.capacitor_geometry.area_alpha.get(architecture, 1.0))


def structure_factor_for_architecture(architecture: str, cfg: CcellConfig) -> float:
    """Return cylinder/MIM effective-area multiplier for an architecture family."""
    return float(cfg.capacitor_geometry.structure_factor.get(architecture, 1.0))


def achievable_ccell_ff(
    *,
    fpitch_m: float,
    k: float,
    cfg: CcellConfig,
    architecture: str,
    beta: float = 1.0,
) -> float:
    """Compute achievable Ccell from geometric capacitor model."""
    alpha = area_alpha_for_architecture(architecture, cfg)
    structure = structure_factor_for_architecture(architecture, cfg)
    area_m2 = alpha * fpitch_m**2
    t_m = cfg.capacitor_geometry.t_dielectric_nm * 1e-9
    ccell_f = k * cfg.capacitor_geometry.epsilon0_f_per_m * area_m2 * structure / t_m
    return ccell_f * 1e15 * beta


def k_for_model(scenario: DielectricScenario, model_id: str) -> float | None:
    """Look up dielectric k for a model under a scenario."""
    model = load_access_model(model_id)
    label = model.roadmap_label
    return scenario.k_by_node.get(label)


def build_feasibility_table(
    ccell_min_df: pd.DataFrame,
    cfg: CcellConfig,
    scenario_name: str,
    *,
    beta: float = 1.0,
) -> pd.DataFrame:
    """Compare achievable Ccell vs Ccell_min under one k scenario."""
    scenario = cfg.dielectric_scenarios[scenario_name]
    rows: list[dict[str, object]] = []
    for _, row in ccell_min_df.iterrows():
        model_id = str(row["model_id"])
        model = load_access_model(model_id)
        k = k_for_model(scenario, model_id)
        if k is None:
            continue
        achievable = achievable_ccell_ff(
            fpitch_m=float(row["fpitch_m"]),
            k=k,
            cfg=cfg,
            architecture=model.architecture,
            beta=beta,
        )
        required = row.get("ccell_min_ff")
        cap_limited = None
        if required is not None and not pd.isna(required):
            cap_limited = achievable < float(required)
        rows.append(
            {
                "model_id": model_id,
                "architecture": model.architecture,
                "scenario": scenario_name,
                "k": k,
                "beta": beta,
                "achievable_ccell_ff": achievable,
                "ccell_min_ff": required,
                "cap_limited": cap_limited,
                "margin_ff": achievable - float(required) if required is not None else None,
            }
        )
    return pd.DataFrame(rows)


def annotate_ccell_min_with_feasibility(
    ccell_min_rows: list[CcellMinRow],
    cfg: CcellConfig,
    scenario_name: str = "S-base",
    *,
    beta: float = 1.0,
) -> list[CcellMinRow]:
    """Attach cap-limited flags and achievable Ccell to min rows."""
    scenario = cfg.dielectric_scenarios[scenario_name]
    updated: list[CcellMinRow] = []
    for row in ccell_min_rows:
        model = load_access_model(row.model_id)
        k = k_for_model(scenario, row.model_id)
        achievable = None
        cap_limited = None
        if k is not None:
            achievable = achievable_ccell_ff(
                fpitch_m=row.fpitch_m,
                k=k,
                cfg=cfg,
                architecture=model.architecture,
                beta=beta,
            )
            if row.ccell_min_ff is not None:
                cap_limited = achievable < row.ccell_min_ff
        updated.append(
            CcellMinRow(
                model_id=row.model_id,
                architecture=row.architecture,
                fpitch_m=row.fpitch_m,
                ccell_min_ret_ff=row.ccell_min_ret_ff,
                ccell_min_read_ff=row.ccell_min_read_ff,
                ccell_min_ff=row.ccell_min_ff,
                binding=row.binding,
                cap_limited=cap_limited,
                achievable_ccell_ff=achievable,
                scenario=scenario_name,
                beta=beta,
            )
        )
    return updated
