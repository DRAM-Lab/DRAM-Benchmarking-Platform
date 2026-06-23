"""Pareto roadmap visualization (dev-plot style, aligned with device-benchmark)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter

from bench.plot_style import (
    ARCHITECTURE_COLORS,
    FIGSIZE,
    LABEL_SIZE,
    LEGEND_SIZE,
    LINEWIDTH_MAIN,
    LINEWIDTH_SECONDARY,
    MARKER_EDGEWIDTH,
    MARKER_SIZE,
    MODEL_DISPLAY_ORDER,
    MODEL_MARKERS,
    TITLE_SIZE,
    TICK_SIZE,
    apply_rcparams,
    apply_style,
    model_color,
    save_figure,
)
from pareto.pareto import filter_pareto_front
from pareto.vct_analysis import vct_pareto_frame

_RC_APPLIED = False
VCT_NODES = ("082", "091", "102", "125")


def _ensure_style() -> None:
    global _RC_APPLIED
    if not _RC_APPLIED:
        apply_rcparams()
        _RC_APPLIED = True


def _ordered_models(df: pd.DataFrame) -> list[str]:
    present = set(df["model_id"].astype(str))
    return [mid for mid in MODEL_DISPLAY_ORDER if mid in present]


def plot_retention_vs_trcd(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
    pareto_only: bool = True,
) -> Path:
    """2D Pareto plot: retention time vs tRCD proxy."""
    _ensure_style()
    subset = df[(df["corner"] == corner) & (df["ccell_ff"] == ccell_ff)].copy()
    subset = subset.dropna(subset=["t_ret_s", "t_rcd_s"])
    if subset.empty:
        raise ValueError(f"No data for corner={corner}, Ccell={ccell_ff}fF")

    front = (
        filter_pareto_front(subset, objectives=("t_ret_s", "t_rcd_s", "e_read_j", "i_leak_a"))
        if pareto_only
        else subset
    )

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(subset)):
        group = subset[subset["model_id"] == model_id]
        ax.scatter(
            group["t_rcd_s"] * 1e9,
            group["t_ret_s"] * 1e3,
            s=MARKER_SIZE * 20,
            color=model_color(model_id, idx),
            edgecolors="white",
            linewidths=MARKER_EDGEWIDTH,
            label=model_id,
            zorder=2,
        )

    if not front.empty:
        front_sorted = front.sort_values("t_rcd_s")
        ax.plot(
            front_sorted["t_rcd_s"] * 1e9,
            front_sorted["t_ret_s"] * 1e3,
            "--",
            color="#333333",
            linewidth=LINEWIDTH_SECONDARY,
            alpha=0.7,
            label="Pareto front",
            zorder=1,
        )

    ax.set_xlabel("tRCD proxy (ns)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"Retention vs read delay @ {corner}, Ccell={ccell_ff:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    ax.legend(fontsize=LEGEND_SIZE - 1, ncol=2, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_retention_vs_energy(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
) -> Path:
    """2D plot: retention vs read energy per bit."""
    _ensure_style()
    subset = df[(df["corner"] == corner) & (df["ccell_ff"] == ccell_ff)].copy()
    subset = subset.dropna(subset=["t_ret_s", "e_read_j"])
    if subset.empty:
        raise ValueError("No retention/energy data")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(subset)):
        row = subset[subset["model_id"] == model_id]
        if row.empty:
            continue
        ax.scatter(
            row["e_read_j"] * 1e15,
            row["t_ret_s"] * 1e3,
            s=MARKER_SIZE * 22,
            color=model_color(model_id, idx),
            edgecolors="white",
            linewidths=MARKER_EDGEWIDTH,
            label=model_id,
        )

    ax.set_xlabel("E_read (fJ)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"Retention vs read energy @ {corner}, Ccell={ccell_ff:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    ax.legend(fontsize=LEGEND_SIZE - 1, ncol=2, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_retention_vs_leak(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
) -> Path:
    """2D plot: retention vs standby leakage current."""
    _ensure_style()
    subset = df[(df["corner"] == corner) & (df["ccell_ff"] == ccell_ff)].copy()
    subset = subset.dropna(subset=["t_ret_s", "i_leak_a"])
    if subset.empty:
        raise ValueError("No retention/leakage data")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(subset)):
        row = subset[subset["model_id"] == model_id]
        if row.empty:
            continue
        ax.scatter(
            row["i_leak_a"],
            row["t_ret_s"] * 1e3,
            s=MARKER_SIZE * 22,
            color=model_color(model_id, idx),
            edgecolors="white",
            linewidths=MARKER_EDGEWIDTH,
            label=model_id,
        )

    ax.set_xscale("log")
    ax.set_xlabel("I_leak (A)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"Retention vs standby leakage @ {corner}, Ccell={ccell_ff:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    ax.legend(fontsize=LEGEND_SIZE - 1, ncol=2, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_architecture_comparison(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
) -> Path:
    """Grouped bar chart comparing architectures on t_ret and tRCD."""
    _ensure_style()
    subset = df[(df["corner"] == corner) & (df["ccell_ff"] == ccell_ff)].copy()
    if subset.empty:
        raise ValueError("No architecture comparison data")

    arch_order = ["BCAT", "VCT", "3D_GAA"]
    groups = []
    t_ret_vals = []
    t_rcd_vals = []
    colors = []
    for arch in arch_order:
        rows = subset[subset["architecture"] == arch]
        if rows.empty:
            continue
        ret_rows = rows.dropna(subset=["t_ret_s"])
        speed_rows = rows.dropna(subset=["t_rcd_s"])
        if ret_rows.empty and speed_rows.empty:
            continue
        groups.append(arch)
        if not ret_rows.empty:
            best_ret = ret_rows.loc[ret_rows["t_ret_s"].idxmax()]
            t_ret_vals.append(float(best_ret["t_ret_s"]) * 1e3)
        else:
            t_ret_vals.append(float("nan"))
        if not speed_rows.empty:
            best_speed = speed_rows.loc[speed_rows["t_rcd_s"].idxmin()]
            t_rcd_vals.append(float(best_speed["t_rcd_s"]) * 1e9)
        else:
            t_rcd_vals.append(float("nan"))
        colors.append(ARCHITECTURE_COLORS.get(arch, "#333333"))

    if not groups:
        raise ValueError("No architecture comparison data")

    x = np.arange(len(groups))
    width = 0.35
    fig, ax1 = plt.subplots(figsize=FIGSIZE)
    ax2 = ax1.twinx()
    ax1.bar(x - width / 2, t_ret_vals, width, color=colors, alpha=0.85, label="Best t_ret (ms)")
    ax2.bar(
        x + width / 2,
        t_rcd_vals,
        width,
        color=colors,
        alpha=0.45,
        edgecolor="#333333",
        linewidth=1.5,
        label="Best tRCD (ns)",
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(groups, fontsize=TICK_SIZE, fontweight="bold")
    ax1.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax2.set_ylabel("tRCD (ns)", fontsize=LABEL_SIZE, fontweight="bold")
    ax1.set_title(
        f"Architecture comparison @ {corner}, Ccell={ccell_ff:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    apply_style(ax1)
    return save_figure(fig, output_path)


def plot_corner_temperature_shift(
    df: pd.DataFrame,
    output_path: Path,
    *,
    ccell_ff: float = 20.0,
) -> Path:
    """Plot tt vs hot retention shift per model."""
    _ensure_style()
    subset = df[df["ccell_ff"] == ccell_ff].copy()
    models = _ordered_models(subset)
    tt_vals = []
    hot_vals = []
    labels = []
    for model_id in models:
        tt = subset[(subset["model_id"] == model_id) & (subset["corner"] == "tt")]
        hot = subset[(subset["model_id"] == model_id) & (subset["corner"] == "hot")]
        if tt.empty or hot.empty:
            continue
        labels.append(model_id)
        tt_vals.append(float(tt.iloc[0]["t_ret_s"]) * 1e3)
        hot_vals.append(float(hot.iloc[0]["t_ret_s"]) * 1e3)

    if not labels:
        raise ValueError("No tt/hot pairs for corner shift plot")

    x = np.arange(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width / 2, tt_vals, width, color="#0033cc", label="TT (27 °C)")
    ax.bar(x + width / 2, hot_vals, width, color="#cc0000", label="Hot (85 °C)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"Temperature corner shift: t_ret @ Ccell={ccell_ff:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    ax.legend(fontsize=LEGEND_SIZE)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_ccell_pareto_overlay(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
) -> Path:
    """Overlay Pareto-relevant points across Ccell sweep."""
    _ensure_style()
    subset = df[(df["corner"] == corner)].dropna(subset=["t_ret_s", "t_rcd_s"])
    if subset.empty:
        raise ValueError("No Ccell overlay data")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for ccell in sorted(subset["ccell_ff"].unique()):
        group = subset[subset["ccell_ff"] == ccell]
        ax.scatter(
            group["t_rcd_s"] * 1e9,
            group["t_ret_s"] * 1e3,
            s=MARKER_SIZE * 16,
            alpha=0.75,
            label=f"{ccell:.0f} fF",
        )

    ax.set_xlabel("tRCD proxy (ns)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"Ccell scaling overlay @ {corner}",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    ax.legend(fontsize=LEGEND_SIZE - 1, title="Ccell", title_fontsize=LEGEND_SIZE)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_vct_pareto_trajectory(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
) -> Path:
    """VCT scaling trajectory on retention–tRCD axes (082→125)."""
    _ensure_style()
    vct = vct_pareto_frame(df, corner=corner, ccell_ff=ccell_ff)
    if vct.empty:
        raise ValueError("No VCT data for trajectory plot")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(
        vct["t_rcd_s"] * 1e9,
        vct["t_ret_s"] * 1e3,
        "o-",
        color="#cc0000",
        linewidth=LINEWIDTH_MAIN,
        markersize=MARKER_SIZE + 2,
        markerfacecolor="white",
        markeredgewidth=MARKER_EDGEWIDTH,
        markeredgecolor="#cc0000",
        zorder=3,
    )
    for _, row in vct.iterrows():
        ax.annotate(
            f"VCT_{row['node']}",
            (row["t_rcd_s"] * 1e9, row["t_ret_s"] * 1e3),
            fontsize=9,
            fontweight="bold",
            xytext=(6, 4),
            textcoords="offset points",
            color="#cc0000",
        )

    ax.set_xlabel("tRCD proxy (ns)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"VCT scaling trajectory (082→125) @ {corner}",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_vct_multimetric_scaling(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
) -> Path:
    """Four-panel VCT node scaling for retention, tRCD, energy, and leakage."""
    _ensure_style()
    vct = vct_pareto_frame(df, corner=corner, ccell_ff=ccell_ff)
    if vct.empty:
        raise ValueError("No VCT multimetric data")

    nodes = vct["node"].astype(str).tolist()
    x = np.arange(len(nodes))

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    panels = [
        (axes[0, 0], vct["t_ret_s"] * 1e3, "t_ret (ms)", "#0033cc"),
        (axes[0, 1], vct["t_rcd_s"] * 1e9, "tRCD (ns)", "#cc0000"),
        (axes[1, 0], vct["e_read_j"] * 1e15, "E_read (fJ)", "#7f3fbf"),
        (axes[1, 1], vct["i_leak_a"], "I_leak (A)", "#e67300"),
    ]
    for ax, values, ylabel, color in panels:
        ax.plot(x, values, "o-", color=color, linewidth=LINEWIDTH_SECONDARY, markersize=MARKER_SIZE)
        ax.set_xticks(x)
        ax.set_xticklabels(nodes, fontsize=9, fontweight="bold")
        ax.set_xlabel("VCT node", fontsize=LABEL_SIZE - 1, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=LABEL_SIZE - 1, fontweight="bold")
        apply_style(ax)
        if "I_leak" in ylabel:
            ax.set_yscale("log")

    fig.suptitle(
        f"VCT multimetric scaling @ {corner}, Ccell={ccell_ff:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    fig.tight_layout()
    out = output_path if output_path.suffix.lower() == ".svg" else output_path.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg")
    plt.close(fig)
    return out


def animate_vct_trajectory_gif(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
    fps: int = 1,
) -> Path:
    """Animated GIF stepping through VCT nodes on the retention–tRCD plane."""
    _ensure_style()
    vct = vct_pareto_frame(df, corner=corner, ccell_ff=ccell_ff)
    if len(vct) < 2:
        raise ValueError("Need at least two VCT nodes for animation")

    x_all = vct["t_rcd_s"].to_numpy(dtype=float) * 1e9
    y_all = vct["t_ret_s"].to_numpy(dtype=float) * 1e3
    pad_x = max((x_all.max() - x_all.min()) * 0.15, 0.5)
    pad_y = max((y_all.max() - y_all.min()) * 0.15, 0.001)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    (trail,) = ax.plot([], [], "-", color="#cc0000", linewidth=LINEWIDTH_MAIN, alpha=0.5)
    (point,) = ax.plot([], [], "o", color="#cc0000", markersize=MARKER_SIZE + 4)
    label = ax.text(0.02, 0.95, "", transform=ax.transAxes, fontsize=12, fontweight="bold")
    ax.set_xlim(x_all.min() - pad_x, x_all.max() + pad_x)
    ax.set_ylim(y_all.min() - pad_y, y_all.max() + pad_y)
    ax.set_xlabel("tRCD proxy (ns)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"VCT scaling animation (082→125) @ {corner}",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    apply_style(ax)

    def _update(frame: int) -> tuple:
        trail.set_data(x_all[: frame + 1], y_all[: frame + 1])
        point.set_data([x_all[frame]], [y_all[frame]])
        label.set_text(f"VCT_{vct.iloc[frame]['node']}")
        return trail, point, label

    anim = FuncAnimation(fig, _update, frames=len(vct), interval=1000 // max(fps, 1), blit=True)
    out = output_path if output_path.suffix.lower() == ".gif" else output_path.with_suffix(".gif")
    out.parent.mkdir(parents=True, exist_ok=True)
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return out


def plot_ccell_sensitivity(
    df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str = "tt",
    model_id: str = "VCT_125",
) -> Path:
    """Plot t_ret vs Ccell for one model."""
    _ensure_style()
    subset = df[(df["model_id"] == model_id) & (df["corner"] == corner)].sort_values("ccell_ff")
    if subset.empty:
        raise ValueError(f"No Ccell sweep for {model_id}")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(
        subset["ccell_ff"],
        subset["t_ret_s"] * 1e3,
        marker=MODEL_MARKERS.get(model_id, "o"),
        linewidth=LINEWIDTH_SECONDARY,
        markersize=MARKER_SIZE,
        color=model_color(model_id),
    )
    ax.set_xlabel("Ccell (fF)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_ret (ms)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"Ccell sensitivity: {model_id} @ {corner}",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    apply_style(ax)
    return save_figure(fig, output_path)


def generate_figures(
    roadmap_csv: Path,
    output_dir: Path,
    *,
    reference_corner: str = "tt",
    reference_ccell_ff: float = 20.0,
) -> list[Path]:
    """Generate full Pareto atlas figure set including VCT animation."""
    df = pd.read_csv(roadmap_csv)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for corner in sorted(df["corner"].unique()):
        for plot_fn, stem in (
            (plot_retention_vs_trcd, f"pareto_retention_trcd_{corner}"),
            (plot_retention_vs_energy, f"pareto_retention_energy_{corner}"),
            (plot_retention_vs_leak, f"pareto_retention_leak_{corner}"),
        ):
            try:
                paths.append(
                    plot_fn(
                        df,
                        output_dir / stem,
                        corner=str(corner),
                        ccell_ff=reference_ccell_ff,
                    )
                )
            except ValueError:
                continue

    for plot_fn, stem, kwargs in (
        (plot_architecture_comparison, "architecture_comparison", {"corner": reference_corner, "ccell_ff": reference_ccell_ff}),
        (plot_vct_pareto_trajectory, "vct_pareto_trajectory", {"corner": reference_corner, "ccell_ff": reference_ccell_ff}),
        (plot_vct_multimetric_scaling, "vct_multimetric_scaling", {"corner": reference_corner, "ccell_ff": reference_ccell_ff}),
    ):
        try:
            paths.append(plot_fn(df, output_dir / stem, **kwargs))
        except ValueError:
            continue

    try:
        paths.append(plot_corner_temperature_shift(df, output_dir / "corner_temperature_shift", ccell_ff=reference_ccell_ff))
    except ValueError:
        pass

    try:
        paths.append(plot_ccell_pareto_overlay(df, output_dir / "ccell_pareto_overlay", corner=reference_corner))
    except ValueError:
        pass

    for model_id in _ordered_models(df):
        try:
            paths.append(
                plot_ccell_sensitivity(
                    df,
                    output_dir / f"ccell_sensitivity_{model_id}",
                    corner=reference_corner,
                    model_id=model_id,
                )
            )
        except ValueError:
            continue

    for corner in ("tt", "hot"):
        try:
            paths.append(
                animate_vct_trajectory_gif(
                    df,
                    output_dir / f"vct_trajectory_{corner}",
                    corner=corner,
                    ccell_ff=reference_ccell_ff,
                )
            )
        except (ValueError, ImportError, RuntimeError):
            continue

    return paths
