"""Performance metric extraction from 1T1C transient measures."""

from __future__ import annotations

import math

from bench.extract.transient import (
    TranWaveform,
    extract_t_read_bl,
    extract_t_read_cell,
    parse_spectre_tran_print,
)
from pareto.config import PerformanceConfig


def extract_t_rcd_from_waveform(
    waveform: TranWaveform,
    cfg: PerformanceConfig,
    v_precharge: float,
) -> float | None:
    """Extract tRCD as WL rise to BL reaching ``bl_signal_v`` above precharge.

    Args:
        waveform: Parsed transient with ``v(bl)`` column.
        cfg: Performance configuration.
        v_precharge: BL precharge voltage (Vdd/2).

    Returns:
        Absolute time of BL threshold crossing, or None.
    """
    if "v(bl)" not in waveform.columns:
        return None
    target = v_precharge + cfg.bl_signal_v
    t = waveform.time_s
    v_bl = waveform.columns["v(bl)"]
    mask = (t >= cfg.wl_read_rise_s) & (t <= cfg.wl_read_fall_s)
    if not np_any(mask):
        return None
    t_win = t[mask]
    v_win = v_bl[mask]
    for idx in range(1, len(t_win)):
        v0, v1 = float(v_win[idx - 1]), float(v_win[idx])
        t0, t1 = float(t_win[idx - 1]), float(t_win[idx])
        if v0 <= target <= v1 or (v0 < target <= v1):
            if v1 == v0:
                return t1
            frac = (target - v0) / (v1 - v0)
            return t0 + frac * (t1 - t0)
    return None


def np_any(mask: object) -> bool:
    """Thin wrapper to avoid importing numpy at module level for type checkers."""
    import numpy as np

    return bool(np.any(mask))


def extract_t_rcd_proxy(
    measures: dict[str, float],
    cfg: PerformanceConfig,
    waveform_text: str | None = None,
    v_precharge: float | None = None,
) -> float | None:
    """Return tRCD from measures or waveform fallback.

    When ``t_rcd`` measure is present, returns absolute crossing time.
    Waveform fallback uses BL 100 mV differential definition.

    Args:
        measures: Parsed simulator measures.
        cfg: Performance configuration.
        waveform_text: Optional ``.print`` contents.
        v_precharge: BL precharge level for waveform extraction.

    Returns:
        tRCD in seconds (absolute time), or None.
    """
    if "t_rcd" in measures:
        return measures["t_rcd"]

    if waveform_text and v_precharge is not None:
        wf = parse_spectre_tran_print(waveform_text)
        if wf is not None:
            t_abs = extract_t_rcd_from_waveform(wf, cfg, v_precharge)
            if t_abs is not None:
                return t_abs - cfg.wl_read_rise_s

    return None


def extract_performance_measures(
    measures: dict[str, float],
    cfg: PerformanceConfig,
    vdd: float,
    v_precharge: float,
    waveform_text: str | None = None,
) -> dict[str, float | None]:
    """Normalize performance measures to Pareto proxy definitions.

    Args:
        measures: Raw simulator measures.
        cfg: Performance configuration.
        vdd: Supply voltage (V).
        v_precharge: BL precharge (Vdd/2).
        waveform_text: Optional waveform for fallback extraction.

    Returns:
        Dict with ``t_rcd_s``, ``t_wr_s``, ``e_read_j``, ``e_write_j``, ``i_leak_a``.
    """
    t_rcd = measures.get("t_rcd")
    if t_rcd is not None:
        t_rcd = t_rcd - cfg.wl_read_rise_s
        if t_rcd < 1e-9:
            t_rcd = None
    else:
        t_rcd = extract_t_rcd_proxy(measures, cfg, waveform_text, v_precharge)

    t_wr = measures.get("t_wr")
    if t_wr is not None and not math.isnan(t_wr):
        t_wr = t_wr - cfg.write_start_s
    else:
        t_wr = None

    wf = parse_spectre_tran_print(waveform_text) if waveform_text else None
    if t_rcd is None and wf is not None:
        t_cell = extract_t_read_cell(
            wf,
            v_sense=v_precharge,
            t_read_start_s=cfg.wl_read_rise_s,
            t_read_end_s=cfg.wl_read_fall_s,
        )
        if t_cell is not None:
            t_rcd = t_cell - cfg.wl_read_rise_s
    if t_rcd is None and wf is not None:
        t_bl = extract_t_read_bl(
            wf,
            v_precharge=v_precharge,
            t_read_start_s=cfg.wl_read_rise_s,
            t_read_end_s=cfg.wl_read_fall_s,
            fraction=cfg.bl_signal_v / max(vdd - v_precharge, 1e-6),
        )
        if t_bl is not None:
            t_rcd = t_bl - cfg.wl_read_rise_s

    return {
        "t_rcd_s": t_rcd,
        "t_wr_s": t_wr,
        "e_read_j": measures.get("e_read"),
        "e_write_j": measures.get("e_write"),
        "i_leak_a": measures.get("i_leak"),
    }
