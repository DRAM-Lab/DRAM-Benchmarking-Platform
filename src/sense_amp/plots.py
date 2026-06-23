"""Summary figures for read-path and SA co-design results."""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from sense_amp.extract.transient import dv_key_for_time_ns
from sense_amp.plot_style import (
    FIGSIZE,
    FIGSIZE_TALL,
    LABEL_SIZE,
    LEGEND_SIZE,
    LINEWIDTH_MAIN,
    MARKER_SIZE,
    MODEL_DISPLAY_ORDER,
    MODEL_MARKERS,
    TITLE_SIZE,
    apply_rcparams,
    apply_style,
    model_color,
    save_figure,
)

_RC_APPLIED = False
_DV_COL_RE = re.compile(r"^dv_(\d+)ns$", re.IGNORECASE)


def _ensure_style() -> None:
    global _RC_APPLIED
    if not _RC_APPLIED:
        apply_rcparams()
        _RC_APPLIED = True


def _ordered_models(df: pd.DataFrame) -> list[str]:
    present = set(df["model_id"].astype(str))
    return [mid for mid in MODEL_DISPLAY_ORDER if mid in present]


def _dv_time_columns(df: pd.DataFrame) -> list[tuple[float, str]]:
    cols: list[tuple[float, str]] = []
    for col in df.columns:
        match = _DV_COL_RE.match(str(col))
        if match:
            cols.append((float(match.group(1)), str(col)))
    return sorted(cols)


def _reference_signal(signal_df: pd.DataFrame) -> pd.DataFrame:
    """Filter to Ccell=20 fF and VBL_pre=0.5 for cross-model plots."""
    ref = signal_df[
        (signal_df["ccell_ff"] == 20.0) & (signal_df["vbl_pre_fraction"] == 0.5)
    ].copy()
    if ref.empty:
        ref = signal_df.groupby("model_id", as_index=False).first()
    return ref


def plot_dv_vs_time(signal_df: pd.DataFrame, output_path: Path) -> Path | None:
    """Plot |ΔV_BL| vs sample time for each model (reference Ccell / VBL_pre)."""
    _ensure_style()
    ref = _reference_signal(signal_df)
    time_cols = _dv_time_columns(ref)
    if not time_cols:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(ref)):
        row = ref[ref["model_id"] == model_id]
        if row.empty:
            continue
        row = row.iloc[0]
        times = [t for t, _ in time_cols]
        values = [abs(float(row[col])) * 1000.0 for _, col in time_cols]
        ax.plot(
            times,
            values,
            marker=MODEL_MARKERS.get(model_id, "o"),
            markersize=MARKER_SIZE,
            linewidth=LINEWIDTH_MAIN,
            label=model_id,
            color=model_color(model_id, idx),
        )

    ax.set_xlabel("Time (ns)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("|ΔV_BL| (mV)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title("Read signal development @ Ccell=20 fF, VBL_pre=0.5 Vdd", fontsize=TITLE_SIZE)
    ax.legend(fontsize=LEGEND_SIZE, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_dv_vs_ccell(
    signal_df: pd.DataFrame,
    output_path: Path,
    *,
    t_ns: float = 10.0,
) -> Path | None:
    """Plot |ΔV_BL| vs Ccell at a fixed sample time."""
    _ensure_style()
    col = dv_key_for_time_ns(t_ns)
    if col not in signal_df.columns:
        return None

    subset = signal_df[signal_df["vbl_pre_fraction"] == 0.5].copy()
    if subset.empty:
        subset = signal_df.copy()

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(subset)):
        group = subset[subset["model_id"] == model_id].sort_values("ccell_ff")
        if group.empty:
            continue
        ax.plot(
            group["ccell_ff"],
            group[col].abs() * 1000.0,
            marker=MODEL_MARKERS.get(model_id, "o"),
            markersize=MARKER_SIZE,
            linewidth=LINEWIDTH_MAIN,
            label=model_id,
            color=model_color(model_id, idx),
        )

    ax.set_xlabel("Ccell (fF)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel(f"|ΔV_BL| @ {int(t_ns)} ns (mV)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title("Cell capacitance sensitivity", fontsize=TITLE_SIZE)
    ax.legend(fontsize=LEGEND_SIZE, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_yield_vs_ten(codesign_df: pd.DataFrame, output_path: Path) -> Path | None:
    """Plot yield proxy vs sense-enable time for default gain and σ_os tiers."""
    _ensure_style()
    if codesign_df.empty:
        return None

    default_gain = float(codesign_df["gain"].median())
    subset = codesign_df[
        (codesign_df["gain"] == default_gain) & (codesign_df["sigma_os_mv"] == 10.0)
    ]
    if subset.empty:
        subset = codesign_df[codesign_df["gain"] == default_gain]
    if subset.empty:
        subset = codesign_df

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(subset)):
        group = subset[subset["model_id"] == model_id].sort_values("t_en_ns")
        if group.empty:
            continue
        ax.plot(
            group["t_en_ns"],
            group["yield_fraction"] * 100.0,
            marker=MODEL_MARKERS.get(model_id, "o"),
            markersize=MARKER_SIZE,
            linewidth=LINEWIDTH_MAIN,
            label=model_id,
            color=model_color(model_id, idx),
        )

    ax.axhline(99.9, color="#666666", linestyle="--", linewidth=1.5, label="99.9% target")
    ax.set_xlabel("t_en (ns)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("Yield proxy (%)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title("SA yield vs sense-enable time (G=10, σ_os=10 mV)", fontsize=TITLE_SIZE)
    ax.set_ylim(-5, 105)
    ax.legend(fontsize=LEGEND_SIZE, framealpha=0.9, ncol=2)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_min_dv_requirement(codesign_df: pd.DataFrame, output_path: Path) -> Path | None:
    """Bar chart of minimum |ΔV_BL| for 99.9% yield per model."""
    _ensure_style()
    if codesign_df.empty or "min_delta_v_mv" not in codesign_df.columns:
        return None

    rows: list[dict[str, float | str]] = []
    for model_id in _ordered_models(codesign_df):
        group = codesign_df[codesign_df["model_id"] == model_id]
        valid = group["min_delta_v_mv"].dropna()
        if valid.empty:
            continue
        rows.append({"model_id": model_id, "min_delta_v_mv": float(valid.min())})
    if not rows:
        return None

    chart_df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    colors = [model_color(mid, idx) for idx, mid in enumerate(chart_df["model_id"])]
    ax.bar(chart_df["model_id"], chart_df["min_delta_v_mv"], color=colors, edgecolor="white")
    ax.set_xlabel("Model", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("Min |ΔV_BL| @ 99.9% yield (mV)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title("Input-referred signal budget (analytic yield proxy)", fontsize=TITLE_SIZE)
    ax.tick_params(axis="x", rotation=20)
    apply_style(ax, grid_axis="y")
    return save_figure(fig, output_path)


def plot_coupling_margin(coupling_margin_df: pd.DataFrame, output_path: Path) -> Path | None:
    """Plot coupled vs isolated |ΔV_BL| across k_couple."""
    _ensure_style()
    if coupling_margin_df.empty:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE_TALL)
    for idx, model_id in enumerate(_ordered_models(coupling_margin_df)):
        group = coupling_margin_df[coupling_margin_df["model_id"] == model_id]
        group = group.sort_values("k_couple")
        if group.empty:
            continue
        ax.plot(
            group["k_couple"],
            group["delta_v_coupled_mv"],
            marker=MODEL_MARKERS.get(model_id, "o"),
            markersize=MARKER_SIZE,
            linewidth=LINEWIDTH_MAIN,
            label=f"{model_id} (coupled)",
            color=model_color(model_id, idx),
        )
        iso = float(group["delta_v_iso_mv"].iloc[0])
        ax.axhline(iso, color=model_color(model_id, idx), linestyle=":", linewidth=1.2, alpha=0.7)

    ax.set_xlabel("k_couple", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("|ΔV_BL| victim (mV)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title("Coupling impact on victim read signal", fontsize=TITLE_SIZE)
    ax.legend(fontsize=LEGEND_SIZE, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def generate_figures(
    output_dir: Path,
    *,
    signal_df: pd.DataFrame,
    codesign_df: pd.DataFrame | None = None,
    coupling_margin_df: pd.DataFrame | None = None,
) -> list[Path]:
    """Generate all summary figures and return written paths."""
    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    plotters = [
        ("dv_vs_time", lambda p: plot_dv_vs_time(signal_df, p)),
        ("dv_vs_ccell", lambda p: plot_dv_vs_ccell(signal_df, p)),
    ]
    if codesign_df is not None and not codesign_df.empty:
        plotters.extend(
            [
                ("yield_vs_ten", lambda p: plot_yield_vs_ten(codesign_df, p)),
                ("min_dv_requirement", lambda p: plot_min_dv_requirement(codesign_df, p)),
            ]
        )
    if coupling_margin_df is not None and not coupling_margin_df.empty:
        plotters.append(("coupling_margin", lambda p: plot_coupling_margin(coupling_margin_df, p)))

    for stem, plotter in plotters:
        path = plotter(fig_dir / f"{stem}.svg")
        if path is not None:
            paths.append(path)
    return paths
