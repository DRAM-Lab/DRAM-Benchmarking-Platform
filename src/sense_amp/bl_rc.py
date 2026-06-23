"""Bitline RC scaling from feature pitch."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BitlineRC:
    """Lumped bitline resistance and capacitance for one column."""

    rbl_ohm: float
    cbl_f: float
    fpitch_m: float
    pitch_ratio: float


def resolve_bitline_rc(model_fpitch_m: float, config: dict) -> BitlineRC:
    """Scale lumped BL RC from 60 nm reference assumptions.

    Args:
        model_fpitch_m: Model feature pitch in meters.
        config: Read-path YAML configuration.

    Returns:
        Scaled :class:`BitlineRC` for the model pitch.
    """
    bl_cfg = config.get("bitline", {})
    ref_fpitch = float(bl_cfg.get("ref_fpitch_m", 6.0e-8))
    pitch_ratio = model_fpitch_m / ref_fpitch
    rbl_at_ref = float(bl_cfg.get("rbl_ohm_at_60nm", 50.0))
    cbl_at_ref = float(bl_cfg.get("cbl_ff_at_60nm", 200.0))
    rbl_ohm = rbl_at_ref / max(pitch_ratio, 1e-6)
    cbl_f = cbl_at_ref * pitch_ratio * 1e-15
    return BitlineRC(
        rbl_ohm=rbl_ohm,
        cbl_f=cbl_f,
        fpitch_m=model_fpitch_m,
        pitch_ratio=pitch_ratio,
    )
