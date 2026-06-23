"""Ccell sweep metric dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class CcellSweepPoint:
    """One (model, corner, Ccell) point on the retention–read surface."""

    model_id: str
    architecture: str
    corner: str
    ccell_ff: float
    temp_c: float
    vdd: float
    fpitch_m: float
    t_ret_s: float | None = None
    dv_read_v: float | None = None
    e_read_j: float | None = None
    i_leak_a: float | None = None
    source: str = "simulation"
    simulator: str | None = None

    def as_dict(self) -> dict[str, float | str | None]:
        """Convert to a flat dictionary for CSV export."""
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass
class CcellMinRow:
    """Minimum Ccell satisfying dual constraints for one model."""

    model_id: str
    architecture: str
    fpitch_m: float
    ccell_min_ret_ff: float | None
    ccell_min_read_ff: float | None
    ccell_min_ff: float | None
    binding: str
    cap_limited: bool | None = None
    achievable_ccell_ff: float | None = None
    scenario: str | None = None
    beta: float | None = None

    def as_dict(self) -> dict[str, float | str | bool | None]:
        """Convert to a flat dictionary for CSV export."""
        return {field.name: getattr(self, field.name) for field in fields(self)}
