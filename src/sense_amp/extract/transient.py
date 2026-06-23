"""Parse transient simulation output and extract read-path signal metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_SPECTRE_SUFFIX = {
    "a": 1e-18,
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}


@dataclass(frozen=True)
class TranWaveform:
    """Parsed transient waveform columns."""

    time_s: np.ndarray
    columns: dict[str, np.ndarray]


def _parse_spectre_tokens(tokens: list[str], n_cols: int) -> list[float] | None:
    values: list[float] = []
    idx = 0
    for _ in range(n_cols):
        if idx >= len(tokens):
            return None
        try:
            val = float(tokens[idx])
        except ValueError:
            return None
        idx += 1
        if idx < len(tokens) and tokens[idx] in _SPECTRE_SUFFIX:
            val *= _SPECTRE_SUFFIX[tokens[idx]]
            idx += 1
        values.append(val)
    return values


def parse_spectre_tran_print(text: str) -> TranWaveform | None:
    """Parse Spectre ``.print tran`` multi-column table."""
    lines = text.splitlines()
    header_idx = None
    col_names: list[str] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped in {"x", "y", "******"} or stripped.startswith("*"):
            continue
        lower = stripped.lower()
        if "time" in lower.split() and ("v(" in lower or "i(" in lower):
            header_idx = idx
            for tok in stripped.split():
                tl = tok.lower()
                if tl == "time":
                    col_names.append("time")
                elif tl.startswith("v(") or tl.startswith("i("):
                    col_names.append(tl)
            break
    if header_idx is None or not col_names or col_names[0] != "time":
        return None

    rows: list[list[float]] = []
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped or stripped in {"x", "y"} or stripped.startswith("*"):
            if rows:
                break
            continue
        parsed = _parse_spectre_tokens(stripped.split(), len(col_names))
        if parsed is not None:
            rows.append(parsed)

    if not rows:
        return None

    data = np.array(rows, dtype=float)
    columns = {name: data[:, col_idx] for col_idx, name in enumerate(col_names)}
    return TranWaveform(time_s=columns["time"], columns=columns)


def differential_bl_voltage(waveform: TranWaveform) -> np.ndarray | None:
    """Return V(BL) - V(BLB) time series when both columns exist."""
    if "v(bl_sense)" in waveform.columns and "v(blb_sense)" in waveform.columns:
        return waveform.columns["v(bl_sense)"] - waveform.columns["v(blb_sense)"]
    if "v(bl)" in waveform.columns and "v(blb)" in waveform.columns:
        return waveform.columns["v(bl)"] - waveform.columns["v(blb)"]
    if "v(bl)" in waveform.columns and "v(bl_ref)" in waveform.columns:
        return waveform.columns["v(bl)"] - waveform.columns["v(bl_ref)"]
    return None


def sample_at_times(
    time_s: np.ndarray,
    values: np.ndarray,
    sample_times_s: list[float],
) -> dict[str, float]:
    """Interpolate waveform values at requested sample times.

    Args:
        time_s: Time axis in seconds.
        values: Signal values.
        sample_times_s: Sample times in seconds.

    Returns:
        Mapping ``dV_<t_ns>ns`` to interpolated voltage in volts.
    """
    result: dict[str, float] = {}
    for t_sample in sample_times_s:
        value = float(np.interp(t_sample, time_s, values))
        label = f"dv_{int(round(t_sample * 1e9))}ns"
        result[label] = value
    return result


def extract_dv_from_waveform(
    waveform: TranWaveform,
    sample_times_ns: list[float],
) -> dict[str, float]:
    """Extract differential BL voltage at configured sample times."""
    dv = differential_bl_voltage(waveform)
    if dv is None:
        return {}
    sample_times_s = [t * 1e-9 for t in sample_times_ns]
    return sample_at_times(waveform.time_s, dv, sample_times_s)


def extract_dv_from_print(print_path: Path, sample_times_ns: list[float]) -> dict[str, float]:
    """Parse a ``.print`` file and extract ΔV_BL sample points."""
    if not print_path.is_file():
        return {}
    waveform = parse_spectre_tran_print(print_path.read_text(encoding="utf-8", errors="replace"))
    if waveform is None:
        return {}
    return extract_dv_from_waveform(waveform, sample_times_ns)


def merge_signal_metrics(
    measures: dict[str, float],
    print_path: Path | None,
    sample_times_ns: list[float],
) -> dict[str, float]:
    """Merge ``.measure`` and waveform-derived ΔV_BL samples."""
    merged = dict(measures)
    if print_path is not None:
        for key, value in extract_dv_from_print(print_path, sample_times_ns).items():
            merged.setdefault(key, value)
    return merged


def dv_key_for_time_ns(t_ns: float) -> str:
    """Return canonical measure key for a sample time in nanoseconds."""
    return f"dv_{int(round(t_ns))}ns"


def parse_measure_key(key: str) -> float | None:
    """Parse ``dv_<t>ns`` keys back to nanoseconds."""
    match = re.fullmatch(r"dv_(\d+)ns", key.lower())
    if not match:
        return None
    return float(match.group(1))
