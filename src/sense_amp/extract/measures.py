"""Simulator output measure extraction helpers."""

from __future__ import annotations

import re
from pathlib import Path

_MEASURE_RE = re.compile(
    r"^\s*(\w+)\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)",
    re.MULTILINE,
)


def parse_measures(text: str) -> dict[str, float]:
    """Parse ``.measure`` results from simulator log or measure files."""
    measures: dict[str, float] = {}
    skip = {"hspice", "option", "simulator", "version", "date", "design"}
    for match in _MEASURE_RE.finditer(text):
        name, value = match.group(1), match.group(2)
        if name.lower() in skip:
            continue
        try:
            measures[name.lower()] = float(value)
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
    """Collect measures with Spectre/HSPICE file priority."""
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

    lis_path = cwd / f"{stem}.lis"
    if lis_path.is_file():
        lis_text = lis_path.read_text(encoding="utf-8", errors="replace")
        for key, value in parse_measures(lis_text).items():
            measures.setdefault(key, value)

    return measures
