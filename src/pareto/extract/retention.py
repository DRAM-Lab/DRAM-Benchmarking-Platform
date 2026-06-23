"""Retention time extraction from hold transient measures and waveforms."""

from __future__ import annotations

import math

import numpy as np

from bench.extract.transient import TranWaveform, parse_spectre_tran_print
from pareto.config import RetentionConfig


def t_ret_from_leakage(
    i_leak_a: float,
    ccell_ff: float,
    delta_v_v: float,
) -> float | None:
    """Estimate retention time from average hold leakage (Q = I·t = C·ΔV).

    Args:
        i_leak_a: Average leakage current during hold (A, positive magnitude).
        ccell_ff: Cell capacitance (fF).
        delta_v_v: Allowed voltage loss (V).

    Returns:
        Estimated retention time in seconds, or None if leakage is negligible.
    """
    if i_leak_a is None or i_leak_a <= 0:
        return None
    ccell_f = ccell_ff * 1e-15
    return (delta_v_v * ccell_f) / i_leak_a


def t_ret_from_decay(
    v_start: float,
    v_end: float,
    t_start_s: float,
    t_end_s: float,
    delta_v_v: float,
) -> float | None:
    """Extrapolate retention from measured Vcell decay during hold.

    Uses log-linear fit when decay exceeds 1 mV; otherwise falls back to
    linear extrapolation.

    Args:
        v_start: Cell voltage at hold start (V).
        v_end: Cell voltage at hold end (V).
        t_start_s: Hold window start (s).
        t_end_s: Hold window end (s).
        delta_v_v: Target voltage loss from initial stored level (V).

    Returns:
        Extrapolated time to threshold, or None if decay is too small.
    """
    dt = t_end_s - t_start_s
    if dt <= 0:
        return None
    dv = v_start - v_end
    if dv <= 1e-6:
        return None

    v_target = v_start - delta_v_v
    if v_end <= v_target <= v_start:
        # Linear interpolation within observed window.
        frac = (v_start - v_target) / dv
        return t_start_s + frac * dt

    if v_end > 0 and v_start > v_end:
        # Log-linear extrapolation beyond hold window.
        slope = math.log(v_end / v_start) / dt
        if slope >= 0:
            return None
        v_ratio = v_target / v_start
        if v_ratio <= 0:
            return None
        return t_start_s + math.log(v_ratio) / slope
    return t_start_s + (delta_v_v / dv) * dt


def extract_t_ret(
    measures: dict[str, float],
    ccell_ff: float,
    cfg: RetentionConfig,
    waveform_text: str | None = None,
) -> float | None:
    """Combine measure and waveform data into a single t_ret estimate.

    Priority:
    1. Log-linear / linear decay from hold-window Vcell samples.
    2. Average leakage current (``i_leak_hold`` or ``i_leak_cell``).

    Args:
        measures: Parsed simulator measures.
        ccell_ff: Cell capacitance (fF).
        cfg: Retention configuration.
        waveform_text: Optional ``.print`` file contents.

    Returns:
        Retention time in seconds.
    """
    if "t_ret" in measures and measures["t_ret"] > cfg.hold_start_s:
        return measures["t_ret"]

    v_start = measures.get("v_cell_hold_start")
    v_end = measures.get("v_cell_hold_end")
    t_ret: float | None = None

    if v_start is not None and v_end is not None:
        t_ret = t_ret_from_decay(
            v_start,
            v_end,
            cfg.hold_start_s,
            cfg.hold_end_s,
            cfg.delta_v_v,
        )

    if t_ret is None and waveform_text:
        wf = parse_spectre_tran_print(waveform_text)
        if wf is not None and "v(cell)" in wf.columns:
            mask = (wf.time_s >= cfg.hold_start_s) & (wf.time_s <= cfg.hold_end_s)
            if np.any(mask):
                t_win = wf.time_s[mask]
                v_win = wf.columns["v(cell)"][mask]
                t_ret = t_ret_from_decay(
                    float(v_win[0]),
                    float(v_win[-1]),
                    float(t_win[0]),
                    float(t_win[-1]),
                    cfg.delta_v_v,
                )

    if t_ret is None or (cfg.extrapolate and t_ret < cfg.hold_end_s):
        i_leak = measures.get("i_leak_hold") or measures.get("i_leak_cell")
        if i_leak is not None:
            t_leak = t_ret_from_leakage(abs(i_leak), ccell_ff, cfg.delta_v_v)
            if t_leak is not None:
                t_ret = t_leak

    return t_ret
