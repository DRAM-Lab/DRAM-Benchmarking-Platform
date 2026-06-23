"""Read-signal estimation for Ccell sweep (OpenDRAM-sense-amp-vct aligned)."""

from __future__ import annotations

import math
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from bench.models import AccessModel

from ccell.config import CcellConfig


def normalize_dv_bl_v(value: float | None) -> float | None:
    """Return magnitude of differential BL signal in volts."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return abs(float(value))


def resolve_bitline_rc(model_fpitch_m: float, bitline_cfg: dict[str, float]) -> tuple[float, float]:
    """Scale lumped BL R and C from 60 nm reference pitch."""
    ref_fpitch = float(bitline_cfg.get("ref_fpitch_m", 6.0e-8))
    pitch_ratio = model_fpitch_m / ref_fpitch
    rbl_ohm = float(bitline_cfg.get("rbl_ohm_at_60nm", 50.0)) / max(pitch_ratio, 1e-6)
    cbl_f = float(bitline_cfg.get("cbl_ff_at_60nm", 200.0)) * pitch_ratio * 1e-15
    return rbl_ohm, cbl_f


def analytic_dv_bl_v(
    *,
    vdd_v: float,
    ccell_ff: float,
    cbl_f: float,
    rbl_ohm: float,
    t_ns: float,
) -> float:
    """Lumped RC + charge-sharing estimate of |ΔV_BL| at ``t_ns``."""
    ccell = ccell_ff * 1e-15
    tau_s = rbl_ohm * cbl_f
    share = vdd_v * ccell / (ccell + cbl_f) * 0.5
    if tau_s <= 0:
        return share
    t_s = t_ns * 1e-9
    return share * (1.0 - math.exp(-t_s / tau_s))


def estimate_dv_read(
    model: AccessModel,
    ccell_ff: float,
    cfg: CcellConfig,
) -> float:
    """Estimate differential read signal at configured sense-enable time."""
    rbl_ohm, cbl_f = resolve_bitline_rc(model.fpitch_m, cfg.bitline)
    return analytic_dv_bl_v(
        vdd_v=model.nominal_vdd,
        ccell_ff=ccell_ff,
        cbl_f=cbl_f,
        rbl_ohm=rbl_ohm,
        t_ns=cfg.constraints.t_en_ns,
    )


def _erfinv(y: float) -> float:
    """Inverse error function (used for SA yield threshold)."""
    try:
        from scipy.special import erfinv

        return float(erfinv(y))
    except ImportError:
        try:
            from sense_amp.sa.yield_model import minimum_delta_v_for_yield  # noqa: F401

            from scipy.special import erfinv as _erfinv

            return float(_erfinv(y))
        except ImportError:
            # Winitzki approximation (sufficient for roadmap thresholds).
            a = 0.147
            ln = math.log(1.0 - y * y)
            first = 2.0 / (math.pi * a) + ln / 2.0
            return math.copysign(math.sqrt(math.sqrt(first * first - ln / a) - first), y)


def minimum_delta_v_for_yield(
    *,
    gain: float,
    sigma_os_v: float,
    m_min_v: float,
    target_yield: float = 0.999,
) -> float | None:
    """Minimum input-referred |ΔV_BL| for target SA yield (sense-amp analytic proxy)."""
    if gain <= 0 or sigma_os_v <= 0 or not 0 < target_yield < 1:
        return None
    x = _erfinv(target_yield)
    threshold = x * sigma_os_v * sqrt(2.0)
    required = (threshold + m_min_v) / gain
    return required if required > 0 else None


def _load_sa_spec_row(model_id: str) -> pd.Series | None:
    from ccell.paths import resolve_sa_spec_csv

    path = resolve_sa_spec_csv()
    if path is None:
        return None
    df = pd.read_csv(path)
    rows = df[df["model_id"] == model_id]
    if rows.empty:
        return None
    row = rows.iloc[0]
    if str(row.get("status", "")).upper() != "PASS":
        return None
    return row


def sa_tier_for_model(cfg: CcellConfig, model_id: str) -> tuple[float, float, float]:
    """Return (gain, sigma_os_v, m_min_v) for read-yield threshold."""
    rc = cfg.read_constraint
    gain = rc.default_gain
    sigma_v = rc.sigma_os_mv / 1000.0
    m_min_v = rc.m_min_mv / 1000.0
    if rc.use_sa_spec:
        row = _load_sa_spec_row(model_id)
        if row is not None:
            if pd.notna(row.get("min_gain")):
                gain = float(row["min_gain"])
            if pd.notna(row.get("max_sigma_os_mv")):
                sigma_v = float(row["max_sigma_os_mv"]) / 1000.0
    return gain, sigma_v, m_min_v


def read_pass_threshold_v(
    cfg: CcellConfig,
    model_id: str,
    *,
    uses_sense_amp: bool,
) -> float:
    """Return the |ΔV_read| pass threshold for ``Ccell_min_read`` extraction."""
    if cfg.read_constraint.mode == "bl_swing" or not uses_sense_amp:
        return cfg.constraints.min_dv_read_v
    gain, sigma_v, m_min_v = sa_tier_for_model(cfg, model_id)
    required = minimum_delta_v_for_yield(
        gain=gain,
        sigma_os_v=sigma_v,
        m_min_v=m_min_v,
        target_yield=cfg.read_constraint.target_yield,
    )
    return required if required is not None else cfg.constraints.min_dv_read_v


def read_threshold_label(cfg: CcellConfig, threshold_v: float, *, uses_sense_amp: bool) -> str:
    """Human-readable threshold label for plots and reports."""
    if cfg.read_constraint.mode == "sa_yield" and uses_sense_amp:
        pct = cfg.read_constraint.target_yield * 100.0
        return f"SA input budget @ {pct:.1f}% yield ({threshold_v * 1e3:.1f} mV)"
    return f"BL swing target ({threshold_v * 1e3:.0f} mV)"


def read_thresholds_by_model(
    cfg: CcellConfig,
    sweep_df: pd.DataFrame,
) -> dict[str, float]:
    """Return per-model read pass thresholds (volts)."""
    thresholds: dict[str, float] = {}
    for model_id in sorted(sweep_df["model_id"].unique()):
        mid = str(model_id)
        uses = model_uses_sense_amp(sweep_df, mid, cfg.read_corner)
        thresholds[mid] = read_pass_threshold_v(cfg, mid, uses_sense_amp=uses)
    return thresholds


def read_threshold_summary(cfg: CcellConfig, sweep_df: pd.DataFrame) -> str:
    """Executive-summary text for read-corner pass criteria."""
    thresholds = read_thresholds_by_model(cfg, sweep_df)
    mv = [v * 1e3 for v in thresholds.values()]
    if cfg.read_constraint.mode == "sa_yield" and any(
        model_uses_sense_amp(sweep_df, mid, cfg.read_corner) for mid in thresholds
    ):
        pct = cfg.read_constraint.target_yield * 100.0
        if min(mv) == max(mv):
            return f"SA input budget @ {pct:.1f}% yield ({min(mv):.1f} mV)"
        return f"SA input budget @ {pct:.1f}% yield ({min(mv):.1f}–{max(mv):.1f} mV per model)"
    return f"BL swing target ({cfg.constraints.min_dv_read_v * 1e3:.0f} mV)"


def model_uses_sense_amp(sweep_df: pd.DataFrame, model_id: str, read_corner: str) -> bool:
    """Return True when tt read rows for a model come from measured sense-amp CSV."""
    if "source" not in sweep_df.columns:
        return False
    rows = sweep_df[(sweep_df["model_id"] == model_id) & (sweep_df["corner"] == read_corner)]
    return bool((rows["source"] == "sense_amp_csv").any())


def load_sense_amp_dataframe(csv_path: Path | None) -> pd.DataFrame | None:
    """Load sense-amp read_signal CSV when available."""
    if csv_path is None or not csv_path.is_file():
        return None
    return pd.read_csv(csv_path)


def _dv_key(t_en_ns: float) -> str:
    return f"dv_{int(round(t_en_ns))}ns"


def _filter_sense_amp_rows(
    df: pd.DataFrame,
    model_id: str,
    *,
    vbl_pre_fraction: float | None,
) -> pd.DataFrame:
    rows = df[df["model_id"] == model_id].copy()
    if rows.empty or vbl_pre_fraction is None or "vbl_pre_fraction" not in rows.columns:
        return rows
    exact = rows[np.isclose(rows["vbl_pre_fraction"].astype(float), vbl_pre_fraction)]
    if not exact.empty:
        return exact
    rows = rows.assign(
        _vbl_dist=(rows["vbl_pre_fraction"].astype(float) - vbl_pre_fraction).abs()
    )
    best = rows["_vbl_dist"].min()
    return rows[rows["_vbl_dist"] == best].drop(columns=["_vbl_dist"])


def _dedupe_ccell_curve(rows: pd.DataFrame, key: str) -> pd.DataFrame:
    """Average duplicate Ccell samples (e.g. multiple VBL_pre decks)."""
    clean = rows.dropna(subset=[key]).copy()
    clean["_dv"] = clean[key].map(normalize_dv_bl_v)
    curve = (
        clean.dropna(subset=["_dv"])
        .groupby("ccell_ff", as_index=False)["_dv"]
        .mean()
        .rename(columns={"_dv": key})
        .sort_values("ccell_ff")
    )
    return curve


def _interp_dv_curve(ccell_ff: float, x: np.ndarray, y: np.ndarray) -> float:
    """Interpolate |ΔV_BL| with linear extrapolation outside measured Ccell range."""
    if len(x) == 1:
        return float(y[0])
    if ccell_ff <= x[0]:
        x0, x1 = float(x[0]), float(x[1])
        y0, y1 = float(y[0]), float(y[1])
        if x1 == x0:
            return y0
        slope = (y1 - y0) / (x1 - x0)
        return y0 + slope * (ccell_ff - x0)
    if ccell_ff >= x[-1]:
        x0, x1 = float(x[-2]), float(x[-1])
        y0, y1 = float(y[-2]), float(y[-1])
        if x1 == x0:
            return y1
        slope = (y1 - y0) / (x1 - x0)
        return y1 + slope * (ccell_ff - x1)
    return float(np.interp(ccell_ff, x, y))


def resolve_dv_from_sense_amp_dataframe(
    df: pd.DataFrame,
    model_id: str,
    ccell_ff: float,
    t_en_ns: float,
    *,
    vbl_pre_fraction: float | None = None,
) -> float | None:
    """Load or interpolate |ΔV_BL| from a sense-amp dataframe."""
    key = _dv_key(t_en_ns)
    if key not in df.columns:
        return None
    rows = _filter_sense_amp_rows(df, model_id, vbl_pre_fraction=vbl_pre_fraction)
    if rows.empty:
        return None

    exact = rows[np.isclose(rows["ccell_ff"].astype(float), ccell_ff)]
    if not exact.empty:
        values = [normalize_dv_bl_v(v) for v in exact[key]]
        values = [v for v in values if v is not None]
        if values:
            return float(np.mean(values))

    curve = _dedupe_ccell_curve(rows, key)
    if curve.empty:
        return None
    if len(curve) == 1:
        return normalize_dv_bl_v(curve.iloc[0][key])

    x = curve["ccell_ff"].to_numpy(dtype=float)
    y = curve[key].to_numpy(dtype=float)
    return _interp_dv_curve(ccell_ff, x, y)


def resolve_dv_read(
    model: AccessModel,
    ccell_ff: float,
    cfg: CcellConfig,
    sense_amp_df: pd.DataFrame | None,
) -> tuple[float, str]:
    """Resolve ΔV_read from sense-amp CSV (with Ccell interp) or analytic fallback."""
    if sense_amp_df is not None:
        measured = resolve_dv_from_sense_amp_dataframe(
            sense_amp_df,
            model.model_id,
            ccell_ff,
            cfg.constraints.t_en_ns,
            vbl_pre_fraction=cfg.read_constraint.vbl_pre_fraction,
        )
        if measured is not None:
            return measured, "sense_amp_csv"
    return estimate_dv_read(model, ccell_ff, cfg), "analytic_read"


def overlay_sense_amp_read(df: pd.DataFrame, cfg: CcellConfig) -> pd.DataFrame:
    """Replace analytic ΔV_read with measured sense-amp values when available."""
    from ccell.paths import load_all_sense_amp_signals

    sense_df = load_all_sense_amp_signals()
    if sense_df is None or df.empty:
        return df

    out = df.copy()
    for idx, row in out.iterrows():
        corner = str(row.get("corner", cfg.read_corner))
        corner_sense = sense_df
        if "corner" in sense_df.columns:
            corner_sense = sense_df[sense_df["corner"].astype(str) == corner]
            if corner_sense.empty:
                continue
        dv = resolve_dv_from_sense_amp_dataframe(
            corner_sense,
            str(row["model_id"]),
            float(row["ccell_ff"]),
            cfg.constraints.t_en_ns,
            vbl_pre_fraction=cfg.read_constraint.vbl_pre_fraction,
        )
        if dv is None:
            continue
        out.at[idx, "dv_read_v"] = dv
        out.at[idx, "source"] = "sense_amp_csv"
    return out


def load_dv_from_sense_amp_csv(
    csv_path: Path,
    model_id: str,
    ccell_ff: float,
    t_en_ns: float,
    *,
    vbl_pre_fraction: float | None = None,
) -> float | None:
    """Load measured ΔV_BL from sense-amp read_signal CSV when available."""
    df = load_sense_amp_dataframe(csv_path)
    if df is None:
        return None
    return resolve_dv_from_sense_amp_dataframe(
        df,
        model_id,
        ccell_ff,
        t_en_ns,
        vbl_pre_fraction=vbl_pre_fraction,
    )
