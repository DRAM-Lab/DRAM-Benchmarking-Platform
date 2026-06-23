"""3D vertical capacitor boost comparison (Phase D)."""

from __future__ import annotations

import pandas as pd
from bench.models import load_access_model

from ccell.config import CcellConfig
from ccell.dielectric import achievable_ccell_ff, k_for_model


def build_three_d_comparison(
    ccell_min_df: pd.DataFrame,
    cfg: CcellConfig,
    scenario_name: str = "S-base",
) -> pd.DataFrame:
    """Compare 3D GAA effective Ccell vs planar VCT reference."""
    scenario = cfg.dielectric_scenarios[scenario_name]
    ref_model = cfg.three_d_boost.reference_planar_model
    ref_row = ccell_min_df[ccell_min_df["model_id"] == ref_model]
    ref_min = float(ref_row.iloc[0]["ccell_min_ff"]) if not ref_row.empty else None

    rows: list[dict[str, object]] = []
    for model_id in cfg.three_d_boost.compare_models:
        model = load_access_model(model_id)
        min_row = ccell_min_df[ccell_min_df["model_id"] == model_id]
        required = float(min_row.iloc[0]["ccell_min_ff"]) if not min_row.empty else None
        k = k_for_model(scenario, model_id)
        if k is None:
            continue
        planar_achievable = achievable_ccell_ff(
            fpitch_m=model.fpitch_m,
            k=k,
            cfg=cfg,
            architecture=model.architecture,
            beta=1.0,
        )
        for beta in cfg.three_d_boost.beta_values:
            effective = achievable_ccell_ff(
                fpitch_m=model.fpitch_m,
                k=k,
                cfg=cfg,
                architecture=model.architecture,
                beta=beta,
            )
            gap_reduction_pct = None
            if (
                ref_min is not None
                and required is not None
                and ref_min > 0
                and beta > 0
            ):
                effective_required = required / beta
                gap_reduction_pct = 100.0 * (ref_min - effective_required) / ref_min
            rows.append(
                {
                    "model_id": model_id,
                    "scenario": scenario_name,
                    "beta": beta,
                    "planar_achievable_ff": planar_achievable,
                    "effective_achievable_ff": effective,
                    "ccell_min_ff": required,
                    "reference_planar_model": ref_model,
                    "reference_ccell_min_ff": ref_min,
                    "cap_feasible": required is None or effective >= required,
                    "gap_reduction_pct_vs_ref": gap_reduction_pct,
                }
            )
    return pd.DataFrame(rows)
