"""Simulator output measure extraction helpers."""

from __future__ import annotations

import re
from pathlib import Path

from bench.extract.dc import _parse_hspice_value, _SPECTRE_SUFFIX

_MEASURE_RE = re.compile(
    r"^\s*(\w+)\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z])?(?:\s+(?:at|from)=.*)?$",
    re.MULTILINE,
)


def _scale_measure_value(raw: str, suffix: str | None) -> float:
    """Apply HSPICE/Spectre unit suffix to a parsed numeric token."""
    value = float(raw)
    if not suffix:
        return value
    scale = _SPECTRE_SUFFIX.get(suffix, _SPECTRE_SUFFIX.get(suffix[:1]))
    if scale is None:
        return value
    return value * scale


def _parse_hspice_voltage_source_current(text: str, probe: str) -> float | None:
    """Parse probe current from HSPICE ``**** voltage sources`` OP table."""
    probe_l = probe.lower().lstrip("v")
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        lower = line.lower()
        if "element" not in lower or "0:" not in lower:
            continue
        parts = line.split()
        col_idx = None
        for j, token in enumerate(parts):
            if not token.lower().startswith("0:"):
                continue
            label = token.split(":", 1)[-1].lower()
            if label == probe_l or label.startswith(probe_l):
                col_idx = j
                break
        if col_idx is None:
            continue
        for follow in lines[idx + 1 : idx + 5]:
            if not follow.strip().lower().startswith("current"):
                continue
            tokens = follow.split()
            if len(tokens) <= col_idx:
                continue
            try:
                return _parse_hspice_value(tokens[col_idx])
            except ValueError:
                return None
    return None


def parse_hspice_op_current(text: str, probe: str = "Vd") -> float | None:
    """Parse ``i(Vprobe)`` from HSPICE ``.lis`` operating-point or DC sections."""
    probe_l = probe.lower()
    patterns = [
        rf"{re.escape(probe_l)}#branch\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?[a-zA-Z]*)",
        rf"i\(\s*v{re.escape(probe_l)}\s*\)\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?[a-zA-Z]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match is None:
            continue
        try:
            return _parse_hspice_value(match.group(1))
        except ValueError:
            continue

    vsrc = _parse_hspice_voltage_source_current(text, probe)
    if vsrc is not None:
        return vsrc

    if probe_l in {"vd", "d"} and "mosfets" in text.lower():
        mosfet_id = re.search(
            r"^\s*id\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?[a-zA-Z]*)",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
        if mosfet_id is not None:
            try:
                return _parse_hspice_value(mosfet_id.group(1))
            except ValueError:
                pass
    return None


def parse_ngspice_op_branch(text: str, branch: str = "vd") -> float | None:
    """Parse ``{branch}#branch`` current from ngspice ``.op`` log output."""
    pattern = re.compile(
        rf"^\s*{re.escape(branch)}#branch\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(text)
    if match is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def parse_op_probe_current(text: str, probe: str = "vd") -> float | None:
    """Parse drain/source probe current from HSPICE or ngspice OP logs."""
    hspice = parse_hspice_op_current(text, probe.upper() if len(probe) == 2 else probe)
    if hspice is not None:
        return hspice
    return parse_ngspice_op_branch(text, probe.lower())


def parse_measures(text: str) -> dict[str, float]:
    """Parse `.measure` results from simulator log or measure files."""
    measures: dict[str, float] = {}
    skip = {"hspice", "option", "simulator", "version", "date", "design"}
    for match in _MEASURE_RE.finditer(text):
        name, raw, suffix = match.group(1), match.group(2), match.group(3)
        if name.lower() in skip:
            continue
        try:
            measures[name.lower()] = _scale_measure_value(raw, suffix)
        except ValueError:
            continue
    return measures


def parse_spectre_mt0(text: str) -> dict[str, float]:
    """Parse Spectre ``.mt0`` table (header row + numeric data row)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_idx = None
    for idx, line in enumerate(lines):
        if "alter#" in line.lower() or re.search(r"\b[a-z_][\w]*\s+temper\b", line, re.I):
            header_idx = idx
            break
    if header_idx is None:
        return {}
    headers = lines[header_idx].split()
    if header_idx + 1 >= len(lines):
        return {}
    values = lines[header_idx + 1].split()
    measures: dict[str, float] = {}
    for name, raw in zip(headers, values, strict=False):
        if name.lower() in {"temper", "alter#"}:
            continue
        try:
            measures[name.lower()] = float(raw)
        except ValueError:
            continue
    return measures


def collect_simulation_measures(cwd: Path, stem: str) -> dict[str, float]:
    """Collect measures with Spectre/HSPICE file priority (avoid log overwrites)."""
    measures: dict[str, float] = {}
    measure_path = cwd / f"{stem}.measure"
    if measure_path.is_file():
        measures.update(parse_measures(measure_path.read_text(encoding="utf-8", errors="replace")))

    mt0_path = cwd / f"{stem}.mt0"
    if mt0_path.is_file():
        mt0_text = mt0_path.read_text(encoding="utf-8", errors="replace")
        mt0_parsed = parse_spectre_mt0(mt0_text)
        if not mt0_parsed:
            mt0_parsed = parse_measures(mt0_text)
        for key, value in mt0_parsed.items():
            measures.setdefault(key, value)

    for lis_name in (f"{stem}.lis", stem):
        lis_path = cwd / lis_name
        if lis_path.is_file():
            for key, value in parse_measures(
                lis_path.read_text(encoding="utf-8", errors="replace")
            ).items():
                measures.setdefault(key, value)

    return measures
