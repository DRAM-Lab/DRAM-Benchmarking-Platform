"""Parametric behavioral sense amplifier models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SenseAmpParams:
    """Behavioral sense amplifier parameters."""

    gain: float
    v_os_v: float
    t_en_ns: float
    m_min_v: float
    t_sense_hold_ns: float = 2.0


def sense_margin_v(
    delta_v_bl_v: float,
    params: SenseAmpParams,
) -> float:
    """Compute sense margin M = G * ΔV_BL - |V_os| at the SA output.

    Args:
        delta_v_bl_v: Differential bitline voltage in volts (absolute value used).
        params: Sense amplifier parameters.

    Returns:
        Sense margin in volts at the SA output.
    """
    return params.gain * abs(delta_v_bl_v) - abs(params.v_os_v)


def sense_passes(
    delta_v_bl_v: float,
    params: SenseAmpParams,
) -> bool:
    """Return True when sense margin exceeds the minimum threshold."""
    return sense_margin_v(delta_v_bl_v, params) > params.m_min_v


def input_referred_margin_v(
    delta_v_bl_v: float,
    params: SenseAmpParams,
) -> float:
    """Return input-referred margin ΔV_BL - |V_os| before gain."""
    return abs(delta_v_bl_v) - abs(params.v_os_v)


def sa_output_v(
    delta_v_bl_v: float,
    params: SenseAmpParams,
) -> float:
    """Return linear-region SA output voltage."""
    return params.gain * (delta_v_bl_v - params.v_os_v)
