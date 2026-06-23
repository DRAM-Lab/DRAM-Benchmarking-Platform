"""Composite figure-of-merit calculations."""

from __future__ import annotations

from dataclasses import dataclass, fields

from bench.models import AccessModel


@dataclass
class Cell1T1CMetrics:
    """1T1C macro benchmark result row."""

    model_id: str
    architecture: str
    corner: str
    ccell_ff: float
    t_write_s: float | None = None
    t_read_s: float | None = None
    i_hold_a: float | None = None
    q_read_c: float | None = None

    def as_dict(self) -> dict[str, float | str | None]:
        """Convert to a flat dictionary for CSV export."""
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass
class MiniArrayMetrics:
    """Mini-array (layout / distributed / lumped BL RC) benchmark row."""

    model_id: str
    architecture: str
    corner: str
    n_cells: int
    ccell_ff: float
    bl_topology: str
    rbl_ohm: float
    cbl_ff: float
    r_seg_ohm: float
    c_seg_ff: float
    r_metal_seg_ohm: float = 0.0
    r_contact_ohm: float = 0.0
    c_metal_seg_ff: float = 0.0
    c_wl_coupling_ff: float = 0.0
    c_sa_ff: float = 0.0
    c_far_end_ff: float = 0.0
    t_bl_settle_s: float | None = None
    i_bl_leak_a: float | None = None

    def as_dict(self) -> dict[str, float | str | int | None]:
        """Convert to a flat dictionary for CSV export."""
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass
class DeviceMetrics:
    """Single-device benchmark result row."""

    model_id: str
    architecture: str
    corner: str
    temp_c: float
    vdd: float
    vt_v: float | None = None
    ss_mv_dec: float | None = None
    ion_a: float | None = None
    ioff_a: float | None = None
    dibl_mv_v: float | None = None
    ron_ohm: float | None = None
    ron_boost_ohm: float | None = None
    cgg_f: float | None = None
    cgd_f: float | None = None
    igidl_a: float | None = None
    esw_j: float | None = None
    ion_per_cgg: float | None = None
    ron_x_cload: float | None = None
    ioff_density_a_m2: float | None = None
    fpitch_m: float | None = None
    vsat: float | None = None

    def as_dict(self) -> dict[str, float | str | None]:
        """Convert to a flat dictionary for CSV export."""
        return {field.name: getattr(self, field.name) for field in fields(self)}


def compute_composite_foms(
    metrics: DeviceMetrics,
    model: AccessModel,
    cload_ff: float = 20.0,
) -> DeviceMetrics:
    """Fill composite FOM fields on a metrics row.

    Args:
        metrics: Partial metrics with primary extractions.
        model: Access model metadata.
        cload_ff: Load capacitance for Ron×Cload (fF).

    Returns:
        Updated metrics dataclass.
    """
    metrics.fpitch_m = model.fpitch_m
    metrics.vsat = model.vsat
    if metrics.ion_a and metrics.cgg_f and metrics.cgg_f > 0:
        metrics.ion_per_cgg = metrics.ion_a / metrics.cgg_f
    if metrics.ron_ohm is not None:
        metrics.ron_x_cload = metrics.ron_ohm * (cload_ff * 1e-15)
    if metrics.ioff_a is not None:
        area = model.fpitch_m**2
        metrics.ioff_density_a_m2 = metrics.ioff_a / area if area > 0 else None
    return metrics
