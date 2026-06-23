"""Parse DC sweep data and derive device metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass

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
class DcCurve:
    """Parsed Id–V sweep."""

    x: np.ndarray
    y: np.ndarray
    x_name: str
    y_name: str


def _parse_spectre_value(token: str) -> float:
    """Parse Spectre print value token (e.g. ``-56.0642`` or ``-56.0642 f``)."""
    token = token.strip()
    if not token:
        raise ValueError("empty token")
    parts = token.split()
    if len(parts) == 1:
        return float(parts[0])
    value = float(parts[0])
    suffix = parts[1]
    scale = _SPECTRE_SUFFIX.get(suffix, _SPECTRE_SUFFIX.get(suffix[:1]))
    if scale is None:
        return value
    return value * scale


def _parse_spectre_row(tokens: list[str]) -> tuple[float, float] | None:
    """Parse one Spectre print row into (x, y) with optional SI suffixes."""
    if len(tokens) < 2:
        return None
    idx = 0
    try:
        x = float(tokens[idx])
        idx += 1
        if idx < len(tokens) and tokens[idx] in _SPECTRE_SUFFIX:
            x *= _SPECTRE_SUFFIX[tokens[idx]]
            idx += 1
        y = float(tokens[idx])
        idx += 1
        if idx < len(tokens) and tokens[idx] in _SPECTRE_SUFFIX:
            y *= _SPECTRE_SUFFIX[tokens[idx]]
        return x, y
    except (ValueError, IndexError):
        return None


def parse_spectre_dc_print(text: str, x_name: str = "dc", y_name: str = "i(vd)") -> DcCurve | None:
    """Parse Spectre `.print` DC table output."""
    lines = text.splitlines()
    header_idx = None
    for idx, line in enumerate(lines):
        lower = line.lower()
        if x_name in lower and y_name.replace("(", "").replace(")", "") in lower.replace("(", "").replace(")", ""):
            header_idx = idx
            break
    if header_idx is None:
        return None

    xs: list[float] = []
    ys: list[float] = []
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped or stripped in {"x", "y", "******"} or stripped.startswith("*"):
            if xs:
                break
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        parsed = _parse_spectre_row(parts)
        if parsed is None:
            continue
        x_val, y_val = parsed
        xs.append(x_val)
        ys.append(y_val)
    if not xs:
        return None
    return DcCurve(x=np.array(xs), y=np.array(ys), x_name=x_name, y_name=y_name)


def parse_ngspice_dc_log(text: str) -> DcCurve | None:
    """Parse ngspice DC table embedded in batch log (``v-sweep`` / ``vd#branch``)."""
    lines = text.splitlines()
    header_idx = None
    for idx, line in enumerate(lines):
        lower = line.lower()
        if "v-sweep" in lower and "vd#branch" in lower:
            header_idx = idx
            break
    if header_idx is None:
        return None

    xs: list[float] = []
    ys: list[float] = []
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Index") or stripped.startswith("---"):
            continue
        parts = re.split(r"\s+", stripped)
        if len(parts) < 3:
            continue
        try:
            int(parts[0])
            xs.append(float(parts[1]))
            ys.append(float(parts[2]))
        except ValueError:
            if xs:
                break
            continue
    if not xs:
        return None
    return DcCurve(x=np.array(xs), y=np.array(ys), x_name="v(g)", y_name="i(vd)")


def _parse_hspice_value(token: str) -> float:
    """Parse HSPICE table token with optional SI suffix (e.g. ``-29.1624f``, ``375.0000m``)."""
    token = token.strip()
    if not token:
        raise ValueError("empty token")
    match = re.match(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)$", token)
    if not match:
        return float(token)
    value = float(match.group(1))
    suffix = match.group(2)
    if suffix:
        scale = _SPECTRE_SUFFIX.get(suffix, _SPECTRE_SUFFIX.get(suffix[:1]))
        if scale is not None:
            value *= scale
    return value


def _parse_hspice_fields(tokens: list[str], count: int) -> list[float] | None:
    """Parse ``count`` numeric HSPICE table fields from a token list."""
    if len(tokens) < count:
        return None
    try:
        return [_parse_hspice_value(tok) for tok in tokens[:count]]
    except ValueError:
        return None


def parse_hspice_dc_lis(text: str) -> DcCurve | None:
    """Parse HSPICE ``.lis`` DC transfer table (swept Vg, ``i(Vd)`` column)."""
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if "dc transfer curves" in line.lower():
            start = idx
            break
    if start is None:
        return None

    header_idx = None
    for idx in range(start, min(start + 20, len(lines))):
        if lines[idx].strip().lower() == "x":
            header_idx = idx
            break
    if header_idx is None:
        return None

    xs: list[float] = []
    ys: list[float] = []
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped or stripped in {"x", "y", "******"} or stripped.startswith("*"):
            if xs:
                break
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        n_fields = 3 if len(parts) >= 3 else 2
        fields = _parse_hspice_fields(parts, n_fields)
        if fields is None:
            if xs:
                break
            continue
        if n_fields >= 3:
            xs.append(fields[2])
            ys.append(fields[1])
        else:
            xs.append(fields[0])
            ys.append(fields[1])
    if not xs:
        return None
    return DcCurve(x=np.array(xs), y=np.array(ys), x_name="v(g)", y_name="i(vd)")


def parse_dc_table(text: str, x_col: str = "v(g)", y_col: str = "i(vd)") -> DcCurve | None:
    """Parse HSPICE `.print dc`, Spectre `.print`, ngspice batch log, or HSPICE `.lis` tables."""
    spectre = parse_spectre_dc_print(text, x_name="dc", y_name=y_col)
    if spectre is not None:
        return spectre

    hspice = parse_hspice_dc_lis(text)
    if hspice is not None:
        return hspice

    ngspice = parse_ngspice_dc_log(text)
    if ngspice is not None:
        return ngspice

    lines = text.splitlines()
    header_idx = None
    for idx, line in enumerate(lines):
        if x_col in line.lower() and y_col in line.lower():
            header_idx = idx
            break
    if header_idx is None:
        return None

    xs: list[float] = []
    ys: list[float] = []
    for line in lines[header_idx + 1 :]:
        if not line.strip() or line.startswith("*"):
            break
        parts = re.split(r"\s+", line.strip())
        if len(parts) < 2:
            continue
        try:
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
        except ValueError:
            continue
    if not xs:
        return None
    return DcCurve(x=np.array(xs), y=np.array(ys), x_name=x_col, y_name=y_col)


def extract_vt_ss(curve: DcCurve, vdd: float) -> tuple[float, float]:
    """Extract Vt (gm peak) and SS from an Id–Vg curve.

    Args:
        curve: Id–Vg data (y = drain current).
        vdd: Supply voltage for Ion/Ioff reference.

    Returns:
        Tuple of (Vt, SS_mV_dec).
    """
    ids = np.abs(curve.y)
    gm = np.gradient(ids, curve.x)
    vt_idx = int(np.argmax(gm))
    vt = float(curve.x[vt_idx])

    ion = float(np.interp(vdd, curve.x, ids))
    ioff = float(ids[0])
    if ioff <= 0 or ion <= 0:
        ss = float("nan")
    else:
        ss = 60.0 / np.log10(ion / ioff)
    return vt, float(ss)


def extract_vt_at_current(curve: DcCurve, i_ref: float) -> float | None:
    """Extract threshold voltage at a constant drain-current reference.

    Uses log-linear interpolation in the subthreshold region. Preferred for
    DIBL extraction when gm-peak Vt collapses to the supply rail.

    Args:
        curve: Id–Vg data (y = drain current, x = Vg).
        i_ref: Reference current magnitude (A).

    Returns:
        Vt in volts, or None if ``i_ref`` is never reached.
    """
    ids = np.abs(curve.y)
    if i_ref <= 0 or not np.any(ids > 0):
        return None
    above = ids >= i_ref
    if not np.any(above):
        return None
    idx = int(np.argmax(above))
    if idx == 0:
        return float(curve.x[0])
    x0, x1 = float(curve.x[idx - 1]), float(curve.x[idx])
    y0, y1 = float(max(ids[idx - 1], 1e-30)), float(max(ids[idx], 1e-30))
    if y1 <= y0:
        return x1
    log_frac = (np.log(i_ref) - np.log(y0)) / (np.log(y1) - np.log(y0))
    log_frac = float(np.clip(log_frac, 0.0, 1.0))
    return x0 + log_frac * (x1 - x0)


def extract_dibl(vt_half: float, vt_full: float, vds_half: float, vds_full: float) -> float:
    """Compute DIBL in mV/V from two threshold voltages.

    Args:
        vt_half: Vt at Vds = Vdd/2.
        vt_full: Vt at Vds = Vdd.
        vds_half: Low drain bias.
        vds_full: High drain bias.

    Returns:
        DIBL in mV/V.
    """
    dvds = vds_full - vds_half
    if dvds == 0:
        return float("nan")
    return abs(vt_half - vt_full) / dvds * 1000.0


def extract_ron_resistive_ratio(curve: DcCurve) -> float | None:
    """Extract Ron as ``|Vd/Ids|`` at the peak |Ids| point (matches Spectre PARAM measure)."""
    ids = np.abs(curve.y)
    if not np.any(ids > 0):
        return None
    idx = int(np.argmax(ids))
    i_val = float(curve.y[idx])
    if abs(i_val) <= 0:
        return None
    return float(abs(curve.x[idx] / i_val))


def extract_ron_from_idvd(curve: DcCurve, target_id: float = 1e-6) -> float:
    """Extract Ron as dV/dI near a target drain current.

    Args:
        curve: Id–Vd curve at Vgs = Vwl.
        target_id: Target |Ids| for Ron estimate (A).

    Returns:
        Ron in ohms.
    """
    ids = np.abs(curve.y)
    i_peak = float(np.max(ids))
    if i_peak <= 0:
        return float("nan")
    if i_peak < target_id:
        target_id = max(1e-9, i_peak * 0.5)
    idx = int(np.argmin(np.abs(ids - target_id)))
    if idx <= 0 or idx >= len(ids) - 1:
        return float("nan")
    dv = curve.x[idx + 1] - curve.x[idx - 1]
    di = ids[idx + 1] - ids[idx - 1]
    if di == 0:
        return float("nan")
    return float(abs(dv / di))
