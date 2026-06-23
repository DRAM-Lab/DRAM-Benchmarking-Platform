"""Yield proxy and Monte Carlo margin models for sense amplifiers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import special

from sense_amp.sa.behavioral import SenseAmpParams, sense_margin_v


@dataclass(frozen=True)
class YieldResult:
    """Outcome of a yield evaluation."""

    yield_fraction: float
    margin_mean_v: float
    margin_p4sigma_v: float
    pass_count: int
    sample_count: int


def analytic_yield_fraction(
    delta_v_bl_v: float,
    *,
    gain: float,
    sigma_os_v: float,
    m_min_v: float,
) -> float:
    """Compute pass probability when V_os ~ N(0, sigma_os^2).

    Pass criterion: G * |ΔV_BL| - |V_os| > M_min.

    Args:
        delta_v_bl_v: Differential BL voltage in volts.
        gain: SA gain.
        sigma_os_v: Offset standard deviation in volts.
        m_min_v: Minimum output margin in volts.

    Returns:
        Pass probability in [0, 1].
    """
    threshold = gain * abs(delta_v_bl_v) - m_min_v
    if threshold <= 0 or sigma_os_v <= 0:
        return 0.0
    # P(|V_os| < threshold) for zero-mean Gaussian offset.
    return float(special.erf(threshold / (sigma_os_v * np.sqrt(2.0))))


def monte_carlo_yield(
    delta_v_bl_v: float,
    *,
    gain: float,
    sigma_os_v: float,
    m_min_v: float,
    n_samples: int = 4096,
    seed: int = 42,
) -> YieldResult:
    """Estimate read yield via Monte Carlo on input-referred offset.

    Args:
        delta_v_bl_v: Differential BL voltage in volts.
        gain: SA gain.
        sigma_os_v: Offset standard deviation in volts.
        m_min_v: Minimum output margin in volts.
        n_samples: Number of Monte Carlo draws.
        seed: RNG seed for reproducibility.

    Returns:
        :class:`YieldResult` with empirical yield and margin statistics.
    """
    rng = np.random.default_rng(seed)
    v_os = rng.normal(0.0, sigma_os_v, size=n_samples)
    params = [
        SenseAmpParams(gain=gain, v_os_v=float(os), t_en_ns=0.0, m_min_v=m_min_v)
        for os in v_os
    ]
    margins = np.array([sense_margin_v(delta_v_bl_v, p) for p in params], dtype=float)
    pass_mask = margins > m_min_v
    pass_count = int(np.sum(pass_mask))
    margin_mean = float(np.mean(margins))
    margin_p4sigma = float(np.percentile(margins, 0.27))  # ~4-sigma left tail for normal
    return YieldResult(
        yield_fraction=pass_count / n_samples,
        margin_mean_v=margin_mean,
        margin_p4sigma_v=margin_p4sigma,
        pass_count=pass_count,
        sample_count=n_samples,
    )


def minimum_delta_v_for_yield(
    *,
    gain: float,
    sigma_os_v: float,
    m_min_v: float,
    target_yield: float = 0.999,
) -> float | None:
    """Solve for minimum |ΔV_BL| achieving target yield analytically.

    Args:
        gain: SA gain.
        sigma_os_v: Offset standard deviation in volts.
        m_min_v: Minimum output margin in volts.
        target_yield: Target pass probability.

    Returns:
        Required |ΔV_BL| in volts, or None if unattainable.
    """
    if gain <= 0 or sigma_os_v <= 0 or not 0 < target_yield < 1:
        return None
    # erf(x) = target_yield => x = erfinv(target_yield)
    x = float(special.erfinv(target_yield))
    threshold = x * sigma_os_v * np.sqrt(2.0)
    required = (threshold + m_min_v) / gain
    return required if required > 0 else None


def minimum_t_en_ns(
    dv_by_time_ns: dict[float, float],
    *,
    gain: float,
    sigma_os_v: float,
    m_min_v: float,
    target_yield: float = 0.999,
) -> float | None:
    """Return earliest sample time (ns) that meets the target yield.

    Args:
        dv_by_time_ns: Mapping of time in ns to |ΔV_BL| in volts.
        gain: SA gain.
        sigma_os_v: Offset standard deviation in volts.
        m_min_v: Minimum output margin in volts.
        target_yield: Target pass probability.

    Returns:
        Minimum qualifying ``t_en`` in nanoseconds, or None.
    """
    for t_ns in sorted(dv_by_time_ns):
        y = analytic_yield_fraction(
            dv_by_time_ns[t_ns],
            gain=gain,
            sigma_os_v=sigma_os_v,
            m_min_v=m_min_v,
        )
        if y >= target_yield:
            return t_ns
    return None
