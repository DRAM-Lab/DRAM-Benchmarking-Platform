"""Device vs capacitor binding classification and what-if analysis."""

from __future__ import annotations

import pandas as pd

from ccell.ccell_min import build_ccell_min_table, classify_binding
from ccell.config import CcellConfig
from ccell.metrics import CcellMinRow


def build_binding_summary(ccell_min_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize binding labels across models."""
    if ccell_min_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for binding, group in ccell_min_df.groupby("binding", sort=False):
        rows.append(
            {
                "binding": binding,
                "model_count": len(group),
                "models": ", ".join(sorted(group["model_id"].astype(str))),
            }
        )
    return pd.DataFrame(rows)


def device_whatif_table(
    sweep_df: pd.DataFrame,
    cfg: CcellConfig,
) -> pd.DataFrame:
    """Estimate Ccell_min shift when access Ioff improves by configured factors."""
    if sweep_df.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    ret_df = sweep_df[sweep_df["corner"] == cfg.retention_corner].copy()
    for model_id in sorted(ret_df["model_id"].unique()):
        group = ret_df[ret_df["model_id"] == model_id].sort_values("ccell_ff")
        if group["t_ret_s"].notna().sum() < 2:
            continue
        base_min = build_ccell_min_table(
            sweep_df[sweep_df["model_id"] == model_id],
            cfg,
        )
        if base_min.empty:
            continue
        base_row = base_min.iloc[0]
        for scale in cfg.device_whatif_ioff_scale:
            scaled = group.copy()
            if scale <= 0:
                continue
            scaled["t_ret_s"] = scaled["t_ret_s"] / scale
            whatif_sweep = sweep_df.copy()
            whatif_sweep.loc[scaled.index, "t_ret_s"] = scaled["t_ret_s"]
            whatif_min = build_ccell_min_table(
                whatif_sweep[whatif_sweep["model_id"] == model_id],
                cfg,
            )
            if whatif_min.empty:
                continue
            row = whatif_min.iloc[0]
            base_ccell = base_row.get("ccell_min_ff")
            new_ccell = row.get("ccell_min_ff")
            reduction = None
            if base_ccell is not None and new_ccell is not None:
                reduction = float(base_ccell) - float(new_ccell)
            rows.append(
                {
                    "model_id": model_id,
                    "ioff_scale": scale,
                    "ccell_min_ff": new_ccell,
                    "ccell_min_reduction_ff": reduction,
                    "binding": row.get("binding"),
                }
            )
    return pd.DataFrame(rows)


def rows_from_min_df(ccell_min_df: pd.DataFrame) -> list[CcellMinRow]:
    """Convert a Ccell_min dataframe back to dataclass rows."""
    rows: list[CcellMinRow] = []
    for _, row in ccell_min_df.iterrows():
        rows.append(
            CcellMinRow(
                model_id=str(row["model_id"]),
                architecture=str(row["architecture"]),
                fpitch_m=float(row["fpitch_m"]),
                ccell_min_ret_ff=row.get("ccell_min_ret_ff"),
                ccell_min_read_ff=row.get("ccell_min_read_ff"),
                ccell_min_ff=row.get("ccell_min_ff"),
                binding=str(row.get("binding", classify_binding(
                    row.get("ccell_min_ret_ff"),
                    row.get("ccell_min_read_ff"),
                ))),
                cap_limited=row.get("cap_limited"),
                achievable_ccell_ff=row.get("achievable_ccell_ff"),
                scenario=row.get("scenario"),
                beta=row.get("beta"),
            )
        )
    return rows
