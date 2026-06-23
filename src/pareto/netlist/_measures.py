"""Shared SPICE `.measure` dialect helpers for Pareto netlists."""

from __future__ import annotations

import re

from bench.models import AccessModel, osd_instance_name
from bench.simulator import SimulatorBackend, uses_spectre_deck


def fet_name(backend: SimulatorBackend, name: str = "Mn1") -> str:
    """Return the access-device instance name used in `.measure` probes."""
    if backend is SimulatorBackend.NGSPICE:
        return osd_instance_name(name)
    return name


def time_when(expr: str, value: float, td_s: float, *, cross: int = 1) -> str:
    """HSPICE/ngspice ``FIND time WHEN`` crossing measure clause."""
    return f"FIND time WHEN {expr}={value:.6f} CROSS={cross} TD={td_s * 1e9:.0f}ns"


def uses_hspice_measures(backend: SimulatorBackend) -> bool:
    """Return True for HSPICE and ngspice measure dialect."""
    return not uses_spectre_deck(backend)


def access_instance_line(model: AccessModel, backend: SimulatorBackend) -> str:
    """Map the canonical d-g-s instance line to BL-WL-cell ports."""
    return re.sub(
        r"^(\S+) d g s",
        r"\1 bl wl cell",
        model.instance_line_for(backend),
        count=1,
    )
