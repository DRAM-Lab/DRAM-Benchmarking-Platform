"""Pareto and scaling visualization for benchmark results (dev-plot style)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from bench.plot_style import (
    ARCHITECTURE_COLORS,
    FIGSIZE,
    LABEL_SIZE,
    LEGEND_SIZE,
    LINE_COLORS,
    LINEWIDTH_MAIN,
    LINEWIDTH_SECONDARY,
    MARKER_EDGEWIDTH,
    MARKER_SIZE,
    MODEL_COLORS,
    MODEL_DISPLAY_ORDER,
    MODEL_MARKERS,
    TITLE_SIZE,
    TICK_SIZE,
    apply_rcparams,
    apply_style,
    model_color,
    save_figure,
)

_RC_APPLIED = False


def _ensure_style() -> None:
    global _RC_APPLIED
    if not _RC_APPLIED:
        apply_rcparams()
        _RC_APPLIED = True


def _ordered_models(df: pd.DataFrame) -> list[str]:
    present = set(df["model_id"].astype(str))
    return [mid for mid in MODEL_DISPLAY_ORDER if mid in present]


def plot_ion_ioff_pareto(df: pd.DataFrame, output_path: Path) -> Path:
    """Create Ion vs Ioff Pareto-style scatter across architectures."""
    _ensure_style()
    fig, ax = plt.subplots(figsize=FIGSIZE)

    for arch, group in df.groupby("architecture"):
        color = ARCHITECTURE_COLORS.get(str(arch), LINE_COLORS["ion"])
        ax.scatter(
            group["ioff_a"],
            group["ion_a"],
            label=arch,
            s=MARKER_SIZE * 18,
            color=color,
            edgecolors="white",
            linewidths=MARKER_EDGEWIDTH,
            alpha=0.95,
            zorder=3,
        )

    for model_id in _ordered_models(df):
        row = df[df["model_id"] == model_id].iloc[0]
        ax.annotate(
            model_id,
            (row["ioff_a"], row["ion_a"]),
            fontsize=8,
            fontweight="bold",
            xytext=(4, 4),
            textcoords="offset points",
            color=model_color(model_id),
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Ioff (A)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("Ion (A)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title("DRAM Access Device: Ion vs Ioff", fontsize=TITLE_SIZE, fontweight="bold")
    ax.legend(fontsize=LEGEND_SIZE, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_vct_scaling(df: pd.DataFrame, output_path: Path) -> Path:
    """Plot VCT family scaling for Ron and vsat proxy."""
    _ensure_style()
    vct = df[df["architecture"] == "VCT"].copy()
    if vct.empty:
        raise ValueError("No VCT models in input data")

    vct["node"] = vct["model_id"].str.replace("VCT_", "", regex=False).astype(int)
    vct = vct.sort_values("node")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    axes[0].plot(
        vct["node"],
        vct["ron_ohm"],
        "o-",
        color=LINE_COLORS["ron"],
        linewidth=LINEWIDTH_MAIN,
        markersize=MARKER_SIZE,
        markerfacecolor="white",
        markeredgewidth=MARKER_EDGEWIDTH,
        markeredgecolor=LINE_COLORS["ron"],
        label="Ron",
    )
    axes[0].set_xlabel("VCT roadmap label", fontsize=LABEL_SIZE, fontweight="bold")
    axes[0].set_ylabel("Ron (Ω)", fontsize=LABEL_SIZE, fontweight="bold")
    axes[0].set_title("VCT Ron scaling", fontsize=TITLE_SIZE - 1, fontweight="bold")
    apply_style(axes[0])

    axes[1].plot(
        vct["node"],
        vct["vsat"],
        "s-",
        color=LINE_COLORS["vsat"],
        linewidth=LINEWIDTH_MAIN,
        markersize=MARKER_SIZE,
        markerfacecolor="white",
        markeredgewidth=MARKER_EDGEWIDTH,
        markeredgecolor=LINE_COLORS["vsat"],
        label="vsat (card)",
    )
    axes[1].set_xlabel("VCT roadmap label", fontsize=LABEL_SIZE, fontweight="bold")
    axes[1].set_ylabel("vsat", fontsize=LABEL_SIZE, fontweight="bold")
    axes[1].set_title("VCT vsat (model card)", fontsize=TITLE_SIZE - 1, fontweight="bold")
    apply_style(axes[1])

    return save_figure(fig, output_path)


def plot_radar(df: pd.DataFrame, output_path: Path, model_ids: list[str] | None = None) -> Path:
    """Radar chart comparing normalized metrics for selected models."""
    _ensure_style()
    if model_ids is None:
        subset = df[df["model_id"].isin(_ordered_models(df))].copy()
        subset["model_id"] = pd.Categorical(
            subset["model_id"], categories=_ordered_models(df), ordered=True
        )
        subset = subset.sort_values("model_id")
    else:
        subset = df[df["model_id"].isin(model_ids)].copy()
    if subset.empty:
        raise ValueError("No rows to plot")

    metrics = ["ion_a", "ioff_a", "ron_ohm", "cgg_f", "ion_per_cgg"]
    labels = ["Ion", "Ioff", "Ron", "Cgg", "Ion/Cgg"]
    present = [(m, label) for m, label in zip(metrics, labels, strict=True) if m in subset.columns]
    if not present:
        raise ValueError("No radar metrics in input data")
    metrics, labels = zip(*present, strict=True)

    normalized = subset.copy()
    for col in metrics:
        vals = normalized[col].astype(float)
        max_v = vals.max()
        min_v = vals.min()
        if max_v == min_v:
            normalized[col] = 1.0
        else:
            normalized[col] = (vals - min_v) / (max_v - min_v)
            if col in ("ioff_a", "ron_ohm", "cgg_f"):
                normalized[col] = 1.0 - normalized[col]

    angles = [n / float(len(metrics)) * 2 * 3.14159265 for n in range(len(metrics))]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
    for idx, (_, row) in enumerate(normalized.iterrows()):
        model_id = str(row["model_id"])
        color = model_color(model_id, idx)
        marker = MODEL_MARKERS.get(model_id, "o")
        values = [row[m] for m in metrics]
        values += values[:1]
        ax.plot(
            angles,
            values,
            marker=marker,
            linewidth=LINEWIDTH_SECONDARY,
            markersize=MARKER_SIZE,
            color=color,
            label=model_id,
        )
        ax.fill(angles, values, alpha=0.08, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=TICK_SIZE, fontweight="bold")
    ax.set_title("Normalized device FOM radar", fontsize=TITLE_SIZE, fontweight="bold", pad=20)
    ax.tick_params(labelsize=TICK_SIZE)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=LEGEND_SIZE - 1, ncol=1)
    ax.grid(alpha=0.35, linewidth=1.1)
    return save_figure(fig, output_path)


def plot_corner_sensitivity(df: pd.DataFrame, output_path: Path, metric: str = "ion_a") -> Path:
    """Plot a metric across PVT corners for each model."""
    _ensure_style()
    if "corner" not in df.columns:
        raise ValueError("corner column required for corner sensitivity plot")

    corner_order = ["tt", "ff", "ss", "cold", "hot", "ss_125"]
    present = set(df["corner"].astype(str))
    present_corners = [c for c in corner_order if c in present]
    present_corners.extend(sorted(present - set(present_corners)))
    plot_df = df.copy()
    plot_df["corner"] = pd.Categorical(plot_df["corner"], categories=present_corners, ordered=True)
    plot_df = plot_df.sort_values(["model_id", "corner"])

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(plot_df)):
        group = plot_df[plot_df["model_id"] == model_id].sort_values("corner")
        if group.empty:
            continue
        color = model_color(model_id, idx)
        ax.plot(
            group["corner"].astype(str),
            group[metric],
            marker=MODEL_MARKERS.get(model_id, "o"),
            linewidth=LINEWIDTH_SECONDARY,
            markersize=MARKER_SIZE,
            color=color,
            label=model_id,
        )

    ylabel = {"ion_a": "Ion (A)", "ioff_a": "Ioff (A)", "ron_ohm": "Ron (Ω)"}.get(metric, metric)
    ax.set_yscale("log" if metric in ("ion_a", "ioff_a") else "linear")
    ax.set_xlabel("Corner", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(f"Corner sensitivity: {ylabel}", fontsize=TITLE_SIZE, fontweight="bold")
    ax.legend(fontsize=LEGEND_SIZE - 1, ncol=2, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def plot_ccell_scaling(cell_csv: Path, output_path: Path, corner: str = "tt") -> Path:
    """Plot 1T1C read time vs Ccell for each model."""
    _ensure_style()
    df = pd.read_csv(cell_csv)
    if "corner" in df.columns:
        df = df[df["corner"] == corner]
    if df.empty or "t_read_s" not in df.columns:
        raise ValueError("No 1T1C read data for Ccell scaling plot")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for idx, model_id in enumerate(_ordered_models(df)):
        group = df[df["model_id"] == model_id].sort_values("ccell_ff")
        if group.empty:
            continue
        color = model_color(model_id, idx)
        ax.plot(
            group["ccell_ff"],
            group["t_read_s"],
            marker=MODEL_MARKERS.get(model_id, "o"),
            linewidth=LINEWIDTH_SECONDARY,
            markersize=MARKER_SIZE,
            color=color,
            label=model_id,
        )

    ax.set_xlabel("Ccell (fF)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_ylabel("t_read (s)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title("1T1C read time vs Ccell", fontsize=TITLE_SIZE, fontweight="bold")
    ax.legend(fontsize=LEGEND_SIZE - 1, ncol=2, framealpha=0.9)
    apply_style(ax)
    return save_figure(fig, output_path)


def generate_figures(
    metrics_csv: Path,
    output_dir: Path,
    *,
    reference_corner: str = "tt",
    cell_csv: Path | None = None,
    include_corner_sensitivity: bool = True,
) -> list[Path]:
    """Generate standard figure set from a metrics CSV (SVG, dev-plot style).

    Args:
        metrics_csv: Device metrics CSV (single- or multi-corner).
        output_dir: Directory for SVG outputs.
        reference_corner: Corner used for Pareto/VCT/radar when CSV spans corners.
        cell_csv: Optional 1T1C metrics for Ccell scaling plot.
        include_corner_sensitivity: Add Ion-vs-corner plot when multi-corner data present.
    """
    df = pd.read_csv(metrics_csv)
    output_dir.mkdir(parents=True, exist_ok=True)

    if "corner" in df.columns:
        plot_df = df[df["corner"] == reference_corner].copy()
        if plot_df.empty:
            plot_df = df.groupby("model_id", as_index=False).first()
    else:
        plot_df = df

    paths: list[Path] = [
        plot_ion_ioff_pareto(plot_df, output_dir / "pareto_ion_ioff"),
        plot_vct_scaling(plot_df, output_dir / "vct_scaling"),
        plot_radar(plot_df, output_dir / "radar_fom"),
    ]

    if include_corner_sensitivity and "corner" in df.columns and df["corner"].nunique() > 1:
        paths.append(
            plot_corner_sensitivity(df, output_dir / "corner_sensitivity_ion", metric="ion_a")
        )
        paths.append(
            plot_corner_sensitivity(df, output_dir / "corner_sensitivity_ioff", metric="ioff_a")
        )

    if cell_csv and cell_csv.is_file():
        paths.append(plot_ccell_scaling(cell_csv, output_dir / "ccell_scaling", corner=reference_corner))

    return paths
