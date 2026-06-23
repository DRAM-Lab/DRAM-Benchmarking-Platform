"""Co-design sweeps and per-node SA specification tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sense_amp.extract.transient import dv_key_for_time_ns
from sense_amp.paths import load_read_path_config
from sense_amp.sa.yield_model import (
    analytic_yield_fraction,
    minimum_delta_v_for_yield,
    minimum_t_en_ns,
)


def _reference_row(
    signal_df: pd.DataFrame,
    *,
    model_id: str,
    ccell_ff: float,
    vbl_pre_fraction: float,
) -> pd.Series | None:
    subset = signal_df[
        (signal_df["model_id"] == model_id)
        & (signal_df["ccell_ff"] == ccell_ff)
        & (signal_df["vbl_pre_fraction"] == vbl_pre_fraction)
    ]
    if subset.empty:
        return None
    return subset.iloc[0]


def build_codesign_table(
    signal_df: pd.DataFrame,
    *,
    config: dict | None = None,
) -> pd.DataFrame:
    """Build co-design sweep table with yield proxy vs timing and SA tiers.

    Args:
        signal_df: Read signal metrics from :func:`runner.run_read_signal_sweep`.
        config: Optional read-path configuration.

    Returns:
        DataFrame with margin and yield columns for each sweep point.
    """
    cfg = config or load_read_path_config()
    sa_cfg = cfg["sense_amp"]
    gain_default = float(sa_cfg["default_gain"])
    gains = [float(g) for g in sa_cfg.get("gain_sweep", [gain_default])]
    sigma_os_mv = [float(v) for v in sa_cfg["sigma_os_mv"]]
    m_min_v = float(sa_cfg["m_min_mv"]) / 1000.0
    target_yield = float(sa_cfg.get("target_yield", 0.999))
    sample_times_ns = [float(t) for t in cfg["read_timing"]["sample_times_ns"]]
    ref_ccell = 20.0
    ref_vbl = 0.5

    rows: list[dict[str, float | str | bool]] = []
    for model_id in sorted(signal_df["model_id"].unique()):
        row = _reference_row(
            signal_df,
            model_id=model_id,
            ccell_ff=ref_ccell,
            vbl_pre_fraction=ref_vbl,
        )
        if row is None:
            continue
        for gain in gains:
            for sigma_mv in sigma_os_mv:
                sigma_v = sigma_mv / 1000.0
                dv_by_time = {
                    t_ns: abs(float(row.get(dv_key_for_time_ns(t_ns), 0.0)))
                    for t_ns in sample_times_ns
                }
                t_min = minimum_t_en_ns(
                    dv_by_time,
                    gain=gain,
                    sigma_os_v=sigma_v,
                    m_min_v=m_min_v,
                    target_yield=target_yield,
                )
                min_dv = minimum_delta_v_for_yield(
                    gain=gain,
                    sigma_os_v=sigma_v,
                    m_min_v=m_min_v,
                    target_yield=target_yield,
                )
                for t_ns in sample_times_ns:
                    dv_v = dv_by_time[t_ns]
                    y = analytic_yield_fraction(
                        dv_v,
                        gain=gain,
                        sigma_os_v=sigma_v,
                        m_min_v=m_min_v,
                    )
                    rows.append(
                        {
                            "model_id": model_id,
                            "ccell_ff": ref_ccell,
                            "vbl_pre_fraction": ref_vbl,
                            "gain": gain,
                            "sigma_os_mv": sigma_mv,
                            "t_en_ns": t_ns,
                            "delta_v_bl_v": dv_v,
                            "delta_v_bl_mv": dv_v * 1000.0,
                            "yield_fraction": y,
                            "passes_target": y >= target_yield,
                            "t_en_min_ns": t_min if t_min is not None else float("nan"),
                            "min_delta_v_mv": (
                                min_dv * 1000.0 if min_dv is not None else float("nan")
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def build_sa_spec_table(
    codesign_df: pd.DataFrame,
    *,
    config: dict | None = None,
) -> pd.DataFrame:
    """Derive per-node SA specification rows at the reference Ccell point.

    Args:
        codesign_df: Output of :func:`build_codesign_table`.
        config: Optional read-path configuration.

    Returns:
        DataFrame with max V_os, min G, earliest t_en, and recommended VBL_pre.
    """
    cfg = config or load_read_path_config()
    target_yield = float(cfg["sense_amp"].get("target_yield", 0.999))
    ref_ccell = 20.0

    rows: list[dict[str, float | str]] = []
    subset = codesign_df[codesign_df["ccell_ff"] == ref_ccell]
    for model_id in sorted(subset["model_id"].unique()):
        model_rows = subset[subset["model_id"] == model_id]
        passing = model_rows[model_rows["yield_fraction"] >= target_yield]
        if passing.empty:
            rows.append(
                {
                    "model_id": model_id,
                    "ccell_ff": ref_ccell,
                    "max_sigma_os_mv": float("nan"),
                    "min_gain": float("nan"),
                    "earliest_t_en_ns": float("nan"),
                    "recommended_vbl_pre_fraction": float("nan"),
                    "min_delta_v_bl_mv": float("nan"),
                    "status": "FAIL",
                }
            )
            continue

        best = passing.sort_values(["t_en_ns", "sigma_os_mv"], ascending=[True, False]).iloc[0]
        min_dv = float(passing["min_delta_v_mv"].min())
        rows.append(
            {
                "model_id": model_id,
                "ccell_ff": ref_ccell,
                "max_sigma_os_mv": float(best["sigma_os_mv"]),
                "min_gain": float(best["gain"]),
                "earliest_t_en_ns": float(best["t_en_ns"]),
                "recommended_vbl_pre_fraction": float(best["vbl_pre_fraction"]),
                "min_delta_v_bl_mv": min_dv,
                "status": "PASS",
            }
        )
    return pd.DataFrame(rows)


def build_coupling_margin_table(
    signal_df: pd.DataFrame,
    coupling_df: pd.DataFrame,
    *,
    config: dict | None = None,
) -> pd.DataFrame:
    """Quantify coupling-induced margin loss vs isolated read.

    Args:
        signal_df: Isolated read signal metrics.
        coupling_df: Coupling victim read metrics.
        config: Optional read-path configuration.

    Returns:
        DataFrame with ΔV_couple and residual margin proxy.
    """
    cfg = config or load_read_path_config()
    sample_times_ns = [float(t) for t in cfg["read_timing"]["sample_times_ns"]]
    ref_t = 10.0 if 10.0 in sample_times_ns else sample_times_ns[len(sample_times_ns) // 2]
    key = dv_key_for_time_ns(ref_t)

    rows: list[dict[str, float | str]] = []
    for model_id in sorted(coupling_df["model_id"].unique()):
        iso = signal_df[
            (signal_df["model_id"] == model_id)
            & (signal_df["ccell_ff"] == 20.0)
            & (signal_df["vbl_pre_fraction"] == 0.5)
        ]
        if iso.empty:
            continue
        iso_dv = abs(float(iso.iloc[0].get(key, 0.0)))
        coupled = coupling_df[coupling_df["model_id"] == model_id]
        for _, crow in coupled.iterrows():
            victim_dv = abs(float(crow.get(key, 0.0)))
            rows.append(
                {
                    "model_id": model_id,
                    "k_couple": float(crow["k_couple"]),
                    "t_sample_ns": ref_t,
                    "delta_v_iso_mv": iso_dv * 1000.0,
                    "delta_v_coupled_mv": victim_dv * 1000.0,
                    "delta_v_couple_mv": (iso_dv - victim_dv) * 1000.0,
                }
            )
    return pd.DataFrame(rows)


def export_codesign_artifacts(
    signal_df: pd.DataFrame,
    output_dir: Path,
    *,
    coupling_df: pd.DataFrame | None = None,
    config: dict | None = None,
) -> dict[str, Path]:
    """Write co-design, SA spec, and optional coupling margin CSVs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = config or load_read_path_config()
    codesign_df = build_codesign_table(signal_df, config=cfg)
    spec_df = build_sa_spec_table(codesign_df, config=cfg)

    paths = {
        "codesign": output_dir / "codesign_sweep.csv",
        "sa_spec": output_dir / "sa_spec_per_node.csv",
    }
    codesign_df.to_csv(paths["codesign"], index=False)
    spec_df.to_csv(paths["sa_spec"], index=False)

    if coupling_df is not None and not coupling_df.empty:
        margin_df = build_coupling_margin_table(signal_df, coupling_df, config=cfg)
        coupling_path = output_dir / "coupling_margin.csv"
        margin_df.to_csv(coupling_path, index=False)
        paths["coupling_margin"] = coupling_path

    return paths
