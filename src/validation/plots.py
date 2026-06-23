"""Validation analysis figures."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from validation.correlation import (
    LiteraturePoint,
    correlate_device_metrics,
    correlation_dataframe,
    load_literature_table,
)
from validation.plot_style import (
    CONFIDENCE_COLORS,
    FAIL_COLOR,
    FIGSIZE,
    MATCH_COLORS,
    MODEL_DISPLAY_ORDER,
    PASS_COLOR,
    apply_rcparams,
    apply_style,
    model_color,
    save_figure,
)
from validation.sensitivity.local_oat import (
    OATResult,
    rank_oat_results,
)
from validation.simulator_compare import (
    KEY_CELL_METRICS,
    KEY_DEVICE_METRICS,
    KEY_MINI_ARRAY_METRICS,
    SimulatorCompareSnapshot,
    per_model_metric_table,
    summarize_metric_differences,
)
from validation.validation_results import ValidationRun

logger = logging.getLogger(__name__)


def _ordered_models(df: pd.DataFrame, col: str = "model_id") -> list[str]:
    """Return model ids in display order present in df."""
    present = set(df[col].astype(str))
    ordered = [m for m in MODEL_DISPLAY_ORDER if m in present]
    ordered.extend(sorted(present - set(ordered)))
    return ordered


def plot_validation_status(
    model_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """Bar chart of error counts per model (green = pass)."""
    apply_rcparams()
    order = _ordered_models(model_summary)
    df = model_summary.set_index("model_id").loc[order].reset_index()

    colors = [PASS_COLOR if s == "PASS" else FAIL_COLOR for s in df["status"]]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    x = np.arange(len(df))
    ax.bar(x, df["n_errors"], color=colors, edgecolor="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df["model_id"], rotation=35, ha="right")
    ax.set_ylabel("Validation errors")
    ax.set_title("Golden validation status (TT corner)")
    apply_style(ax, grid_axis="y")
    return save_figure(fig, output_path)


def plot_golden_margins(
    metric_detail: pd.DataFrame,
    output_path: Path,
) -> Path:
    """Grouped bar chart of relative margin vs golden reference values."""
    apply_rcparams()
    subset = metric_detail[
        metric_detail["rel_margin_pct"].notna()
        & metric_detail["metric"].isin(["Ion", "Ron", "Ioff", "fpitch"])
    ].copy()
    if subset.empty:
        logger.warning("No golden margin data for plot_golden_margins")
        return output_path

    metrics = ["Ion", "Ron", "Ioff", "fpitch"]
    models = _ordered_models(subset)
    x = np.arange(len(models))
    width = 0.2
    fig, ax = plt.subplots(figsize=FIGSIZE)

    for i, metric in enumerate(metrics):
        mdf = subset[subset["metric"] == metric].set_index("model_id")
        vals = [mdf.loc[m, "rel_margin_pct"] if m in mdf.index else 0.0 for m in models]
        offset = (i - 1.5) * width
        ax.bar(x + offset, vals, width, label=metric)

    ax.axhline(0, color="#333333", linewidth=1.0)
    ax.axhline(10, color=FAIL_COLOR, linestyle="--", linewidth=1.0, alpha=0.6, label="±10%")
    ax.axhline(-10, color=FAIL_COLOR, linestyle="--", linewidth=1.0, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=35, ha="right")
    ax.set_ylabel("Relative margin vs golden (%)")
    ax.set_title("Observed vs golden reference (signed %)")
    ax.legend(fontsize=9, ncol=3)
    apply_style(ax, grid_axis="y")
    return save_figure(fig, output_path)


def plot_vct_scaling(device_df: pd.DataFrame, output_path: Path) -> Path:
    """VCT node scaling for Ion, Ioff, Ron."""
    apply_rcparams()
    vct = device_df[device_df["architecture"] == "VCT"].copy()
    if vct.empty:
        logger.warning("No VCT models for scaling plot")
        return output_path

    vct["node"] = vct["model_id"].str.replace("VCT_", "", regex=False).astype(int)
    vct = vct.sort_values("node")
    nodes = vct["node"].tolist()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    specs = [
        ("ion_a", "Ion (A)", "#0033cc"),
        ("ioff_a", "Ioff (A)", "#cc0000"),
        ("ron_ohm", "Ron (Ω)", "#7f3fbf"),
    ]
    for ax, (col, label, color) in zip(axes, specs):
        ax.plot(nodes, vct[col], marker="o", color=color, linewidth=3, markersize=8)
        ax.set_xlabel("VCT roadmap node")
        ax.set_ylabel(label)
        ax.set_title(label)
        apply_style(ax)

    fig.suptitle("VCT scaling 082 → 125 (TT)", fontsize=15, fontweight="bold")
    return save_figure(fig, output_path)


def plot_literature_correlation(
    device_df: pd.DataFrame,
    output_path: Path,
    literature: list[LiteraturePoint] | None = None,
) -> Path:
    """Pitch and Vdd vs literature envelope."""
    apply_rcparams()
    points = literature or load_literature_table()
    corr = correlation_dataframe(correlate_device_metrics(device_df, literature=points))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Pitch panel
    ax = axes[0]
    lit_years = [p.year for p in points if p.pitch_nm is not None]
    lit_pitch = [p.pitch_nm for p in points if p.pitch_nm is not None]
    ax.plot(lit_years, lit_pitch, "o--", color="#888888", label="Literature", linewidth=2)

    pitch_rows = corr[corr["metric"] == "fpitch"]
    for _, row in pitch_rows.iterrows():
        color = MATCH_COLORS.get(str(row["magnitude_match"]), "#0033cc")
        ax.scatter(
            [2026],
            [row["open_value"]],
            s=120,
            color=color,
            label=row["model_id"],
            zorder=5,
        )
    ax.set_xlabel("Year")
    ax.set_ylabel("Pitch (nm)")
    ax.set_title("Feature pitch vs literature")
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    apply_style(ax)

    # Vdd panel
    ax = axes[1]
    lit_vdd_years = [p.year for p in points if p.vdd_v is not None]
    lit_vdd = [p.vdd_v for p in points if p.vdd_v is not None]
    ax.plot(lit_vdd_years, lit_vdd, "o--", color="#888888", label="Literature", linewidth=2)

    vdd_rows = corr[corr["metric"] == "Vdd"]
    for _, row in vdd_rows.iterrows():
        color = MATCH_COLORS.get(str(row["magnitude_match"]), "#0033cc")
        ax.scatter(
            [2026],
            [row["open_value"]],
            s=120,
            color=color,
            label=row["model_id"],
            zorder=5,
        )
    ax.set_xlabel("Year")
    ax.set_ylabel("Vdd (V)")
    ax.set_title("Array Vdd vs literature")
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    apply_style(ax)

    fig.suptitle(
        "Literature correlation (H=green, M=orange, L=red)",
        fontsize=14,
        fontweight="bold",
    )
    return save_figure(fig, output_path)


def plot_confidence_tiers(metric_detail: pd.DataFrame, output_path: Path) -> Path:
    """Stacked bar of H/M/L confidence counts per model."""
    apply_rcparams()
    models = _ordered_models(metric_detail)
    conf_order = ["high", "medium", "low"]
    counts = {c: [] for c in conf_order}
    for model in models:
        mdf = metric_detail[metric_detail["model_id"] == model]
        for conf in conf_order:
            counts[conf].append(int((mdf["confidence"] == conf).sum()))

    x = np.arange(len(models))
    fig, ax = plt.subplots(figsize=FIGSIZE)
    bottom = np.zeros(len(models))
    for conf in conf_order:
        vals = np.array(counts[conf])
        ax.bar(
            x,
            vals,
            bottom=bottom,
            label=conf.capitalize(),
            color=CONFIDENCE_COLORS[conf],
            edgecolor="#333333",
            linewidth=0.5,
        )
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=35, ha="right")
    ax.set_ylabel("Metric count")
    ax.set_title("Confidence tier distribution per model")
    ax.legend()
    apply_style(ax, grid_axis="y")
    return save_figure(fig, output_path)


def plot_sensitivity_oat(
    oat_results: list[OATResult],
    output_path: Path,
    *,
    metric: str = "i_hold_a",
    top_n: int = 8,
) -> Path:
    """Horizontal bar chart of top OAT sensitivity parameters."""
    apply_rcparams()
    ranked = rank_oat_results(oat_results, metric)
    if ranked.empty:
        logger.warning("No OAT data for sensitivity plot")
        return output_path

    top = ranked.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [model_color(str(row["model_id"])) for _, row in top.iterrows()]
    ax.barh(
        [f"{row['param']} ({row['model_id']})" for _, row in top.iterrows()],
        top["abs_change"],
        color=colors,
        edgecolor="#333333",
        linewidth=0.5,
    )
    ax.set_xlabel("|Δmetric| (relative)")
    ax.set_title(f"Local OAT sensitivity — {metric}")
    apply_style(ax, grid_axis="x")
    return save_figure(fig, output_path)


def plot_architecture_radar(
    device_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """Normalized radar comparing architectures on key metrics."""
    apply_rcparams()
    metrics = ["ion_a", "ioff_a", "ron_ohm", "cgg_f"]
    labels = ["Ion", "1/Ioff", "1/Ron", "Cgg"]
    arch_df = device_df.groupby("architecture")[metrics].mean()

    # Invert cost metrics so larger = better on plot
    arch_df = arch_df.copy()
    arch_df["ioff_a"] = 1.0 / arch_df["ioff_a"].clip(lower=1e-30)
    arch_df["ron_ohm"] = 1.0 / arch_df["ron_ohm"].clip(lower=1e-30)

    normed = arch_df / arch_df.max(axis=0)
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    for arch, row in normed.iterrows():
        vals = row.tolist() + row.tolist()[:1]
        color = {"BCAT": "#0033cc", "VCT": "#cc0000", "3D_GAA": "#7f3fbf"}.get(
            str(arch), "#333333"
        )
        ax.plot(angles, vals, "o-", linewidth=2.5, label=str(arch), color=color)
        ax.fill(angles, vals, alpha=0.12, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title("Architecture comparison (normalized)", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=9)
    return save_figure(fig, output_path)


def plot_simulator_max_rel_diff(
    rel_diff: pd.DataFrame,
    output_path: Path,
    *,
    metrics: tuple[str, ...] = KEY_DEVICE_METRICS,
    title: str = "SPICE simulator agreement (device metrics)",
    reference: str = "spectre",
    backends: tuple[str, ...] = ("hspice",),
) -> Path | None:
    """Grouped bar chart of max abs relative difference by metric and backend."""
    apply_rcparams()
    summary = summarize_metric_differences(rel_diff, metrics)
    if summary.empty:
        return None
    summary = summary[summary["backend"].isin(backends)]
    if summary.empty:
        return None

    metrics = list(dict.fromkeys(summary["metric"].tolist()))
    backend_names = list(dict.fromkeys(summary["backend"].tolist()))
    x = np.arange(len(metrics))
    width = 0.8 / max(len(backend_names), 1)
    fig, ax = plt.subplots(figsize=FIGSIZE)

    for i, backend in enumerate(backend_names):
        sub = summary[summary["backend"] == backend].set_index("metric")
        vals = [float(sub.loc[m, "max_abs_rel_diff"]) if m in sub.index else 0.0 for m in metrics]
        offset = (i - (len(backend_names) - 1) / 2) * width
        ax.bar(x + offset, vals, width, label=backend)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=20, ha="right")
    ax.set_ylabel(f"Max abs rel diff vs {reference}")
    ax.set_title(title)
    ax.legend()
    apply_style(ax, grid_axis="y")
    return save_figure(fig, output_path)


def plot_simulator_rel_diff_heatmap(
    rel_diff: pd.DataFrame,
    output_path: Path,
    *,
    metrics: tuple[str, ...] = KEY_DEVICE_METRICS,
    backend: str = "hspice",
    reference: str = "spectre",
    title: str | None = None,
) -> Path | None:
    """Heatmap of per-model relative differences for selected metrics."""
    apply_rcparams()
    detail = per_model_metric_table(rel_diff, metrics, reference=reference)
    detail = detail[detail["backend"] == backend]
    if detail.empty:
        return None

    models = _ordered_models(detail)
    metric_list = list(metrics)
    matrix = np.full((len(metric_list), len(models)), np.nan)
    for i, metric in enumerate(metric_list):
        for j, model in enumerate(models):
            row = detail[(detail["model_id"] == model) & (detail["metric"] == metric)]
            if not row.empty:
                matrix[i, j] = float(row.iloc[0]["rel_diff"])

    fig, ax = plt.subplots(figsize=(max(10, len(models) * 1.1), 4.5))
    vmax = np.nanmax(np.abs(matrix))
    vmax = vmax if vmax > 0 else 1.0
    im = ax.imshow(matrix, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_xticks(np.arange(len(models)))
    ax.set_xticklabels(models, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(metric_list)))
    ax.set_yticklabels(metric_list)
    ax.set_title(title or f"{backend} vs {reference} — relative Δ by model")
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("rel diff")
    return save_figure(fig, output_path)


def plot_simulator_spectre_vs_backend(
    wide: pd.DataFrame,
    output_path: Path,
    *,
    metric_pairs: tuple[tuple[str, str], ...] = (
        ("ion_a", "Ion (A)"),
        ("ioff_a", "Ioff (A)"),
    ),
    backend: str = "hspice",
    reference: str = "spectre",
    title: str | None = None,
    log_scale: bool = True,
) -> Path | None:
    """Scatter panels comparing reference and alternate simulator metrics."""
    apply_rcparams()
    metrics = list(metric_pairs)
    fig, axes = plt.subplots(1, len(metrics), figsize=(6 * len(metrics), 4.5))
    if len(metrics) == 1:
        axes = [axes]

    plotted = False
    for ax, (metric, label) in zip(axes, metrics):
        ref_col = f"{metric}_{reference}"
        other_col = f"{metric}_{backend}"
        if ref_col not in wide.columns or other_col not in wide.columns:
            ax.set_visible(False)
            continue
        sub = wide[[ref_col, other_col, "model_id"]].dropna()
        if sub.empty:
            ax.set_visible(False)
            continue
        plotted = True
        x = sub[ref_col].astype(float)
        y = sub[other_col].astype(float)
        ax.scatter(x, y, s=80, color="#0033cc", edgecolor="#333333", linewidth=0.5)
        for _, row in sub.iterrows():
            ax.annotate(
                str(row["model_id"]).replace("_", " "),
                (row[ref_col], row[other_col]),
                fontsize=7,
                xytext=(4, 4),
                textcoords="offset points",
            )
        lo = min(x.min(), y.min())
        hi = max(x.max(), y.max())
        ax.plot([lo, hi], [lo, hi], "--", color="#888888", linewidth=1.5, label="y = x")
        ax.set_xlabel(f"{reference} {label}")
        ax.set_ylabel(f"{backend} {label}")
        ax.set_title(label)
        if log_scale and x.min() > 0 and y.min() > 0:
            ax.set_xscale("log")
            ax.set_yscale("log")
        apply_style(ax)

    if not plotted:
        plt.close(fig)
        return None

    fig.suptitle(
        title or f"{backend} vs {reference} metrics (TT)",
        fontsize=14,
        fontweight="bold",
    )
    return save_figure(fig, output_path)


def _plot_simulator_suite_figures(
    *,
    rel_diff: pd.DataFrame,
    wide: pd.DataFrame | None,
    figures_dir: Path,
    stem: str,
    metrics: tuple[str, ...],
    metric_pairs: tuple[tuple[str, str], ...],
    title_prefix: str,
    reference: str,
    backends: tuple[str, ...],
    log_scale: bool,
    prefer_backend: str | None = None,
) -> dict[str, Path]:
    """Generate max-rel-diff, heatmap, and scatter figures for one metric suite."""
    paths: dict[str, Path] = {}
    max_path = plot_simulator_max_rel_diff(
        rel_diff,
        figures_dir / f"{stem}_max_rel_diff",
        metrics=metrics,
        title=f"{title_prefix} — max |rel Δ| vs {reference}",
        reference=reference,
        backends=backends,
    )
    if max_path is not None:
        paths[f"{stem}_max_rel_diff"] = max_path

    panel_backend = prefer_backend or (
        "ngspice" if "ngspice" in backends else backends[0]
    )
    heat_path = plot_simulator_rel_diff_heatmap(
        rel_diff,
        figures_dir / f"{stem}_rel_diff_heatmap",
        metrics=metrics,
        backend=panel_backend,
        reference=reference,
        title=f"{title_prefix}: {panel_backend} vs {reference}",
    )
    if heat_path is not None:
        paths[f"{stem}_rel_diff_heatmap"] = heat_path

    if wide is not None and not wide.empty:
        scatter_path = plot_simulator_spectre_vs_backend(
            wide,
            figures_dir / f"{stem}_spectre_vs_backend",
            metric_pairs=metric_pairs,
            backend=panel_backend,
            reference=reference,
            title=f"{title_prefix}: {panel_backend} vs {reference}",
            log_scale=log_scale,
        )
        if scatter_path is not None:
            paths[f"{stem}_spectre_vs_backend"] = scatter_path

    return paths


def generate_simulator_figures(
    snapshot: SimulatorCompareSnapshot | None,
    figures_dir: Path,
) -> dict[str, Path]:
    """Generate simulator cross-check figures when pinned comparison data exists."""
    paths: dict[str, Path] = {}
    if snapshot is None or snapshot.device_rel_diff.empty:
        return paths

    manifest = snapshot.manifest
    status = {
        str(k): str(v).lower() for k, v in manifest.get("backend_status", {}).items()
    }
    active = [
        b
        for b in snapshot.backends
        if b != snapshot.reference and "unavailable" not in status.get(b, "")
    ]
    if not active:
        active = ["hspice"]

    figures_dir.mkdir(parents=True, exist_ok=True)
    backend_tuple = tuple(active)
    device_panel = "hspice" if "hspice" in backend_tuple else backend_tuple[0]

    paths.update(
        _plot_simulator_suite_figures(
            rel_diff=snapshot.device_rel_diff,
            wide=snapshot.device_wide,
            figures_dir=figures_dir,
            stem="simulator",
            metrics=KEY_DEVICE_METRICS,
            metric_pairs=(("ion_a", "Ion (A)"), ("ioff_a", "Ioff (A)")),
            title_prefix="Device metrics",
            reference=snapshot.reference,
            backends=backend_tuple,
            log_scale=True,
            prefer_backend=device_panel,
        )
    )

    if snapshot.cell_rel_diff is not None and not snapshot.cell_rel_diff.empty:
        paths.update(
            _plot_simulator_suite_figures(
                rel_diff=snapshot.cell_rel_diff,
                wide=snapshot.cell_wide,
                figures_dir=figures_dir,
                stem="simulator_cell",
                metrics=KEY_CELL_METRICS,
                metric_pairs=(("t_read_s", "t_read (s)"), ("t_write_s", "t_write (s)")),
                title_prefix="1T1C cell metrics (20 fF)",
                reference=snapshot.reference,
                backends=backend_tuple,
                log_scale=False,
                prefer_backend="ngspice",
            )
        )

    if snapshot.mini_array_rel_diff is not None and not snapshot.mini_array_rel_diff.empty:
        paths.update(
            _plot_simulator_suite_figures(
                rel_diff=snapshot.mini_array_rel_diff,
                wide=snapshot.mini_array_wide,
                figures_dir=figures_dir,
                stem="simulator_mini_array",
                metrics=KEY_MINI_ARRAY_METRICS,
                metric_pairs=(
                    ("t_bl_settle_s", "t_bl_settle (s)"),
                    ("i_bl_leak_a", "I_BL leak (A)"),
                ),
                title_prefix="Mini-array metrics",
                reference=snapshot.reference,
                backends=backend_tuple,
                log_scale=False,
                prefer_backend="ngspice",
            )
        )

    return paths


def generate_all_figures(
    run: ValidationRun,
    device_df: pd.DataFrame,
    oat_results: list[OATResult],
    figures_dir: Path,
    simulator_compare: SimulatorCompareSnapshot | None = None,
) -> dict[str, Path]:
    """Generate full validation figure set.

    Returns:
        Mapping of figure stem to written path.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    logger.info("Writing figures to %s", figures_dir)
    paths["validation_status"] = plot_validation_status(
        run.model_summary, figures_dir / "validation_status"
    )
    paths["golden_margins"] = plot_golden_margins(
        run.metric_detail, figures_dir / "golden_margins"
    )
    paths["vct_scaling"] = plot_vct_scaling(device_df, figures_dir / "vct_scaling")
    paths["literature_correlation"] = plot_literature_correlation(
        device_df, figures_dir / "literature_correlation"
    )
    paths["confidence_tiers"] = plot_confidence_tiers(
        run.metric_detail, figures_dir / "confidence_tiers"
    )
    paths["architecture_radar"] = plot_architecture_radar(
        device_df, figures_dir / "architecture_radar"
    )
    paths["sensitivity_oat_ihold"] = plot_sensitivity_oat(
        oat_results, figures_dir / "sensitivity_oat_ihold", metric="i_hold_a"
    )
    paths["sensitivity_oat_ion"] = plot_sensitivity_oat(
        oat_results, figures_dir / "sensitivity_oat_ion", metric="ion_a"
    )
    paths.update(generate_simulator_figures(simulator_compare, figures_dir))
    return paths
