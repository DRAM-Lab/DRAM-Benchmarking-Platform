"""Extract minimum Ccell from sweep surfaces."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ccell.config import CcellConfig
from ccell.metrics import CcellMinRow
from ccell.read_signal import model_uses_sense_amp, read_pass_threshold_v


def _interp_threshold_ccell(
    ccell: np.ndarray,
    metric: np.ndarray,
    threshold: float,
    *,
    increasing: bool,
    allow_extrapolate: bool = True,
) -> float | None:
    """Find minimum Ccell where metric crosses threshold via linear interpolation."""
    mask = np.isfinite(ccell) & np.isfinite(metric)
    if mask.sum() < 2:
        return None
    x = ccell[mask]
    y = metric[mask]
    order = np.argsort(x)
    x = x[order]
    y = y[order]

    if increasing:
        ok = y >= threshold
        if not ok.any():
            if allow_extrapolate and y[-1] < threshold and y[-1] > y[-2]:
                x0, x1 = float(x[-2]), float(x[-1])
                y0, y1 = float(y[-2]), float(y[-1])
                if y1 != y0:
                    frac = (threshold - y0) / (y1 - y0)
                    extrap = x0 + frac * (x1 - x0)
                    max_ccell = float(x[-1]) * 4.0
                    if extrap <= max_ccell:
                        return extrap
            return None
        idx = int(np.argmax(ok))
        if idx == 0:
            return float(x[0])
        x0, x1 = float(x[idx - 1]), float(x[idx])
        y0, y1 = float(y[idx - 1]), float(y[idx])
    else:
        ok = y <= threshold
        if not ok.any():
            return None
        idx = int(np.argmax(ok))
        if idx == 0:
            return float(x[0])
        x0, x1 = float(x[idx - 1]), float(x[idx])
        y0, y1 = float(y[idx - 1]), float(y[idx])

    if y1 == y0:
        return float(x1)
    frac = (threshold - y0) / (y1 - y0)
    return x0 + frac * (x1 - x0)


def classify_binding(ccell_min_ret: float | None, ccell_min_read: float | None) -> str:
    """Label whether retention or read signal is the binding constraint."""
    if ccell_min_ret is None and ccell_min_read is None:
        return "unknown"
    if ccell_min_ret is None:
        return "read-limited"
    if ccell_min_read is None:
        return "retention-limited"
    if abs(ccell_min_ret - ccell_min_read) < 0.5:
        return "co-limited"
    if ccell_min_ret > ccell_min_read:
        return "retention-limited"
    return "read-limited"


_LOW_QUALITY_RETENTION_SOURCES = {"scaled_from_leakage", "interpolated_ccell"}
_TRUSTED_RETENTION_SOURCES = {
    "simulation",
    "derived_from_pareto",
    "derived_from_device_bench",
    "derived_from_golden_bench",
}


def _retention_sweep_df(sweep_df: pd.DataFrame, model_id: str, cfg: CcellConfig) -> pd.DataFrame:
    """Prefer simulated retention rows when mixed with derived duplicates."""
    ret_df = sweep_df[
        (sweep_df["model_id"] == model_id) & (sweep_df["corner"] == cfg.retention_corner)
    ].copy()
    if "source" in ret_df.columns:
        has_sim = (ret_df["source"] == "simulation").any()
        if has_sim:
            ret_df = ret_df[ret_df["source"].isin(_TRUSTED_RETENTION_SOURCES)]
        else:
            ret_df = ret_df[~ret_df["source"].isin(_LOW_QUALITY_RETENTION_SOURCES)]
    return ret_df.sort_values("ccell_ff")


def extract_ccell_min_for_model(
    sweep_df: pd.DataFrame,
    model_id: str,
    cfg: CcellConfig,
) -> CcellMinRow:
    """Compute dual-constraint Ccell_min for one model."""
    ret_df = _retention_sweep_df(sweep_df, model_id, cfg)
    read_df = sweep_df[
        (sweep_df["model_id"] == model_id) & (sweep_df["corner"] == cfg.read_corner)
    ].sort_values("ccell_ff")

    meta = ret_df.iloc[0] if not ret_df.empty else read_df.iloc[0]

    ccell_min_ret = None
    if not ret_df.empty and ret_df["t_ret_s"].notna().any():
        ccell_min_ret = _interp_threshold_ccell(
            ret_df["ccell_ff"].to_numpy(dtype=float),
            ret_df["t_ret_s"].to_numpy(dtype=float),
            cfg.constraints.min_t_ret_s,
            increasing=True,
        )

    ccell_min_read = None
    if not read_df.empty and read_df["dv_read_v"].notna().any():
        uses_sense = model_uses_sense_amp(sweep_df, model_id, cfg.read_corner)
        threshold = read_pass_threshold_v(cfg, model_id, uses_sense_amp=uses_sense)
        dv_values = read_df["dv_read_v"].astype(float).abs().to_numpy()
        ccell_min_read = _interp_threshold_ccell(
            read_df["ccell_ff"].to_numpy(dtype=float),
            dv_values,
            threshold,
            increasing=True,
        )

    ccell_min = None
    if ccell_min_ret is not None or ccell_min_read is not None:
        values = [v for v in (ccell_min_ret, ccell_min_read) if v is not None]
        ccell_min = max(values)

    return CcellMinRow(
        model_id=model_id,
        architecture=str(meta["architecture"]),
        fpitch_m=float(meta["fpitch_m"]),
        ccell_min_ret_ff=ccell_min_ret,
        ccell_min_read_ff=ccell_min_read,
        ccell_min_ff=ccell_min,
        binding=classify_binding(ccell_min_ret, ccell_min_read),
    )


def build_ccell_min_table(sweep_df: pd.DataFrame, cfg: CcellConfig) -> pd.DataFrame:
    """Build Ccell_min table for all models in the sweep database."""
    if sweep_df.empty:
        return pd.DataFrame()
    rows = [
        extract_ccell_min_for_model(sweep_df, model_id, cfg).as_dict()
        for model_id in sorted(sweep_df["model_id"].unique())
    ]
    return pd.DataFrame(rows)
