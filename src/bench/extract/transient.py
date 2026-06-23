"""Parse transient simulation output and extract macro timing metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from bench.extract.dc import _SPECTRE_SUFFIX, _parse_hspice_fields


@dataclass(frozen=True)
class TranWaveform:
    """Parsed transient waveform columns."""

    time_s: np.ndarray
    columns: dict[str, np.ndarray]


def _parse_spectre_tokens(tokens: list[str], n_cols: int) -> list[float] | None:
    """Parse ``n_cols`` Spectre numeric tokens with optional SI suffixes."""
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
    """Parse Spectre ``.print tran`` multi-column table.

    Args:
        text: Contents of a ``.print`` file.

    Returns:
        Parsed waveform or None if the table is not found.
    """
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


def _crossing_time(t: np.ndarray, v: np.ndarray, target: float) -> float | None:
    """Return interpolated time of the first ``target`` crossing in ``v(t)``."""
    for idx in range(1, len(t)):
        v0, v1 = float(v[idx - 1]), float(v[idx])
        t0, t1 = float(t[idx - 1]), float(t[idx])
        if (v0 - target) * (v1 - target) > 0:
            continue
        if v1 == v0:
            return t1
        frac = (target - v0) / (v1 - v0)
        return t0 + frac * (t1 - t0)
    return None


def extract_t_read_cell(
    waveform: TranWaveform,
    *,
    v_sense: float,
    t_read_start_s: float = 12e-9,
    t_read_end_s: float = 23e-9,
) -> float | None:
    """Extract read time when Vcell crosses Vdd/2 during the read window.

    Tries the exact sense level first, then ±0.1% offsets for cards whose cell
    voltage sits slightly above or below Vdd/2 through the read pulse.

    Args:
        waveform: Parsed transient with ``v(cell)`` column.
        v_sense: Target sense voltage (typically Vdd/2).
        t_read_start_s: Read window start (WL rise).
        t_read_end_s: Read window end (WL fall).

    Returns:
        Time in seconds, or None if no crossing is found.
    """
    if "v(cell)" not in waveform.columns:
        return None
    t = waveform.time_s
    vc = waveform.columns["v(cell)"]
    mask = (t >= t_read_start_s) & (t <= t_read_end_s)
    if not np.any(mask):
        return None
    t_win = t[mask]
    v_win = vc[mask]
    for target in (v_sense, v_sense * 1.001, v_sense * 0.999):
        t_cross = _crossing_time(t_win, v_win, target)
        if t_cross is not None:
            return t_cross
    return None


def extract_t_read_bl(
    waveform: TranWaveform,
    *,
    v_precharge: float,
    t_read_start_s: float = 6e-9,
    t_read_end_s: float = 16e-9,
    fraction: float = 0.9,
) -> float | None:
    """Extract read time when BL reaches ``fraction`` of the final read level.

    Per benchmark spec: time for VBL to reach 90% of the final read level
    during the WL-high read window.

    Args:
        waveform: Parsed transient with ``v(bl)`` column.
        v_precharge: BL precharge voltage (Vdd/2).
        t_read_start_s: Read window start (WL rise).
        t_read_end_s: Read window end (WL fall).
        fraction: Target fraction of final BL delta (default 0.9).

    Returns:
        Time in seconds, or None if BL column missing or no crossing.
    """
    if "v(bl)" not in waveform.columns:
        return None
    t = waveform.time_s
    v_bl = waveform.columns["v(bl)"]
    mask = (t >= t_read_start_s) & (t <= t_read_end_s)
    if not np.any(mask):
        return None
    t_win = t[mask]
    v_win = v_bl[mask]
    v_final = float(v_win[-1])
    delta = v_final - v_precharge
    if abs(delta) < 1e-12:
        return None
    v_target = v_precharge + fraction * delta
    rising = delta > 0
    for idx in range(1, len(t_win)):
        v0, v1 = v_win[idx - 1], v_win[idx]
        t0, t1 = t_win[idx - 1], t_win[idx]
        if rising:
            crossed = v0 <= v_target <= v1 or (v0 < v_target <= v1)
        else:
            crossed = v0 >= v_target >= v1 or (v0 > v_target >= v1)
        if crossed:
            if v1 == v0:
                return float(t1)
            frac = (v_target - v0) / (v1 - v0)
            return float(t0 + frac * (t1 - t0))
    return None


def _ngspice_tran_column_name(token: str) -> str | None:
    """Map ngspice transient table header token to a normalized column name."""
    tok = token.strip().lower()
    if tok == "time":
        return "time"
    if tok.startswith("v(") and tok.endswith(")") and "=" not in tok:
        return tok
    if tok.endswith("#branch"):
        stem = tok.removesuffix("#branch")
        if stem in {"vg", "vd"}:
            return f"i({stem})"
        return f"i({stem})"
    return None


def _parse_ngspice_tran_index_block(lines: list[str], header_idx: int) -> tuple[list[str], list[list[float]]] | None:
    """Parse one ``Index``-prefixed ngspice transient table block."""
    header_tokens = lines[header_idx].split()
    if not header_tokens or header_tokens[0].lower() != "index":
        return None
    col_names = [
        name
        for tok in header_tokens[1:]
        if (name := _ngspice_tran_column_name(tok)) is not None
    ]
    if not col_names or col_names[0] != "time":
        return None

    rows: list[list[float]] = []
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            if rows:
                break
            continue
        if stripped.startswith("Index") or stripped.startswith("---"):
            if rows:
                break
            continue
        parts = re.split(r"\s+", stripped)
        if len(parts) < len(col_names) + 1:
            if rows:
                break
            continue
        try:
            int(parts[0])
            rows.append([float(parts[i + 1]) for i in range(len(col_names))])
        except ValueError:
            if rows:
                break
            continue
    if not rows:
        return None
    return col_names, rows


def parse_ngspice_tran_log(text: str) -> TranWaveform | None:
    """Parse ngspice transient table embedded in batch log."""
    lines = text.splitlines()
    col_order: list[str] | None = None
    all_rows: list[list[float]] = []
    for idx, line in enumerate(lines):
        if not line.strip().lower().startswith("index"):
            continue
        block = _parse_ngspice_tran_index_block(lines, idx)
        if block is None:
            continue
        col_names, rows = block
        if col_order is None:
            col_order = col_names
        elif col_order != col_names:
            continue
        all_rows.extend(rows)
    if col_order is None or not all_rows:
        return None

    data = np.array(all_rows, dtype=float)
    order = np.argsort(data[:, 0])
    data = data[order]
    _, unique_idx = np.unique(data[:, 0], return_index=True)
    data = data[np.sort(unique_idx)]
    columns = {name: data[:, col_idx] for col_idx, name in enumerate(col_order)}
    return TranWaveform(time_s=columns["time"], columns=columns)


def extract_t_bl_settle(
    waveform: TranWaveform,
    *,
    v_precharge: float,
    droop_frac: float = 0.99,
    t_start_s: float = 2e-9,
    t_end_s: float = 25e-9,
    sense_col: str | None = None,
) -> float | None:
    """Return time when the sense BL first crosses ``droop_frac * Vpre`` during WL turn-on.

    Args:
        waveform: Parsed transient with a ``v(bl*)`` column.
        v_precharge: BL precharge level (Vdd/2).
        droop_frac: Fraction of precharge used as settle threshold (default 0.99).
        t_start_s: Search window start.
        t_end_s: Search window end.
        sense_col: Optional column name (e.g. ``v(bl0)``); auto-detect when omitted.

    Returns:
        Settling time in seconds, or None when no crossing is found.
    """
    col = sense_col
    if col is None:
        bl_cols = sorted(
            [name for name in waveform.columns if name.startswith("v(bl")],
            key=lambda name: (len(name), name),
        )
        if bl_cols:
            col = bl_cols[0]
    if col is None or col not in waveform.columns:
        return None
    t = waveform.time_s
    v_bl = waveform.columns[col]
    mask = (t >= t_start_s) & (t <= t_end_s)
    if not np.any(mask):
        return None
    t_win = t[mask]
    v_win = v_bl[mask]
    for v_ref in (v_precharge, float(v_win[0])):
        target = v_ref * droop_frac
        t_cross = _crossing_time(t_win, v_win, target)
        if t_cross is not None:
            return t_cross
    return None


def _hspice_lis_subcolumn(token: str) -> str | None:
    """Map HSPICE ``.lis`` sub-header token to normalized waveform column name."""
    tok = token.strip().lower()
    if not tok or tok in {"time", "voltage", "current", "volt", "vd"}:
        return None
    if tok == "vpre":
        return "i(vpre)"
    return f"v({tok})"


def _parse_hspice_tran_subcolumns(sub_line: str) -> list[str]:
    """Return normalized column names from the sub-header row under a tran table."""
    cols: list[str] = []
    for token in sub_line.split():
        mapped = _hspice_lis_subcolumn(token)
        if mapped is not None:
            cols.append(mapped)
    return cols


def parse_hspice_tran_lis(text: str) -> TranWaveform | None:
    """Parse HSPICE ``.lis`` multi-column transient table (uses last tran block)."""
    lines = text.splitlines()
    header_idx: int | None = None
    sub_cols: list[str] = []
    for idx, line in enumerate(lines):
        if "transient analysis" not in line.lower():
            continue
        for j in range(idx + 1, min(idx + 8, len(lines))):
            stripped = lines[j].strip()
            if stripped.lower() != "x":
                continue
            for k in range(j + 1, min(j + 6, len(lines))):
                sub_line = lines[k].strip()
                if not sub_line or sub_line.lower().startswith("time"):
                    continue
                tokens = _parse_hspice_tran_subcolumns(sub_line)
                if tokens:
                    header_idx = j
                    sub_cols = tokens
                    break
    if header_idx is None or not sub_cols:
        return None

    col_names = ["time"] + sub_cols

    rows: list[list[float]] = []
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped or stripped in {"x", "y", "******"} or stripped.startswith("*"):
            if rows:
                break
            continue
        parts = stripped.split()
        fields = _parse_hspice_fields(parts, len(col_names))
        if fields is not None:
            rows.append(fields)

    if not rows:
        return None
    data = np.array(rows, dtype=float)
    columns = {name: data[:, col_idx] for col_idx, name in enumerate(col_names)}
    return TranWaveform(time_s=columns["time"], columns=columns)


def parse_tran_table(text: str) -> TranWaveform | None:
    """Parse Spectre ``.print``, HSPICE ``.lis``, or ngspice batch transient tables."""
    hspice = parse_hspice_tran_lis(text)
    if hspice is not None:
        return hspice
    if "#branch" in text.lower():
        waveform = parse_ngspice_tran_log(text)
        if waveform is not None:
            return waveform
    waveform = parse_spectre_tran_print(text)
    if waveform is not None:
        return waveform
    return parse_ngspice_tran_log(text)


def extract_esw_j(
    waveform: TranWaveform,
    *,
    t_start_s: float = 0.0,
    t_end_s: float = 20e-9,
) -> float | None:
    """Integrate gate switching energy ``∫ v(g)·i(Vg) dt`` from a transient waveform."""
    if "v(g)" not in waveform.columns or "i(vg)" not in waveform.columns:
        return None
    t = waveform.time_s
    mask = (t >= t_start_s) & (t <= t_end_s)
    if int(np.sum(mask)) < 2:
        return None
    t_win = t[mask]
    power = waveform.columns["v(g)"][mask] * waveform.columns["i(vg)"][mask]
    return float(abs(np.trapezoid(power, t_win)))
