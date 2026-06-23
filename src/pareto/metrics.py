"""Pareto roadmap metric dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class ParetoPoint:
    """One (model, corner, Ccell) point on the retention–performance surface."""

    model_id: str
    architecture: str
    corner: str
    ccell_ff: float
    temp_c: float
    vdd: float
    fpitch_m: float
    t_ret_s: float | None = None
    t_refresh_s: float | None = None
    t_rcd_s: float | None = None
    t_wr_s: float | None = None
    e_read_j: float | None = None
    e_write_j: float | None = None
    i_leak_a: float | None = None
    i_leak_density_a_m2: float | None = None
    source: str = "simulation"
    simulator: str | None = None

    def as_dict(self) -> dict[str, float | str | None]:
        """Convert to a flat dictionary for CSV export."""
        return {field.name: getattr(self, field.name) for field in fields(self)}


def compute_t_refresh(t_ret_s: float | None) -> float | None:
    """Map retention time to simplified refresh interval ``t_ret / ln(2)``.

    Args:
        t_ret_s: Time to ΔV threshold (seconds).

    Returns:
        Approximate refresh interval or None if input is missing.
    """
    if t_ret_s is None or t_ret_s <= 0:
        return None
    import math

    return t_ret_s / math.log(2.0)
