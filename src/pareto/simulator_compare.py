"""Cross-simulator Pareto metric comparison (Spectre / HSPICE / ngspice)."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bench.plot_style import (
    FIGSIZE,
    LABEL_SIZE,
    LEGEND_SIZE,
    LINEWIDTH_SECONDARY,
    MARKER_EDGEWIDTH,
    MARKER_SIZE,
    MULTI_SERIES_COLORS,
    TITLE_SIZE,
    TICK_SIZE,
    apply_rcparams,
    apply_style,
    save_figure,
)
from bench.simulator import SimulatorBackend, available_backends
from bench.simulator_compare import compare_metric_frames

logger = logging.getLogger(__name__)

_RC_APPLIED = False

_SIMULATOR_MARKERS = {
    "hspice": "s",
    "ngspice": "D",
    "spectre": "o",
}

_METRIC_LABELS = {
    "t_ret_s": "t_ret",
    "t_refresh_s": "t_refresh",
    "t_rcd_s": "tRCD",
    "t_wr_s": "tWR",
    "e_read_j": "E_read",
    "e_write_j": "E_write",
    "i_leak_a": "I_leak",
    "i_leak_density_a_m2": "I_leak/area",
}

_PARITY_STEMS = {
    "t_ret_s": "simulator_parity_t_ret",
    "t_refresh_s": "simulator_parity_t_refresh",
    "t_rcd_s": "simulator_parity_t_rcd",
    "t_wr_s": "simulator_parity_t_wr",
    "e_read_j": "simulator_parity_e_read",
    "e_write_j": "simulator_parity_e_write",
    "i_leak_a": "simulator_parity_i_leak",
    "i_leak_density_a_m2": "simulator_parity_i_leak_density",
}

_REL_DIFF_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("timing", ("t_ret_s", "t_refresh_s", "t_rcd_s", "t_wr_s")),
    ("energy", ("e_read_j", "e_write_j")),
    ("leakage", ("i_leak_a", "i_leak_density_a_m2")),
)

_EXTRA_FIGURE_STEMS = (
    "simulator_parity_overview",
    "simulator_max_rel_diff",
    "simulator_rel_diff_heatmap",
    "simulator_rel_diff_timing",
    "simulator_rel_diff_energy",
    "simulator_rel_diff_leakage",
)

_SIMULATOR_FIGURE_CAPTIONS = {
    "simulator_parity_t_ret": "Simulator parity: t_ret vs reference",
    "simulator_parity_t_refresh": "Simulator parity: t_refresh vs reference",
    "simulator_parity_t_rcd": "Simulator parity: tRCD vs reference",
    "simulator_parity_t_wr": "Simulator parity: tWR vs reference",
    "simulator_parity_e_read": "Simulator parity: E_read vs reference",
    "simulator_parity_e_write": "Simulator parity: E_write vs reference",
    "simulator_parity_i_leak": "Simulator parity: I_leak vs reference",
    "simulator_parity_i_leak_density": "Simulator parity: I_leak/area vs reference",
    "simulator_parity_overview": "Simulator parity overview (all metrics)",
    "simulator_max_rel_diff": "Maximum |relative difference| by metric and backend",
    "simulator_rel_diff_heatmap": "Cross-simulator relative difference heatmap",
    "simulator_rel_diff_timing": "Relative differences: timing metrics",
    "simulator_rel_diff_energy": "Relative differences: energy metrics",
    "simulator_rel_diff_leakage": "Relative differences: leakage metrics",
    "simulator_rel_diff_by_model": "Relative differences by model @ reference point",
}

_KEY_COLS = ("model_id", "corner", "ccell_ff")
_PARETO_METRICS = (
    "t_ret_s",
    "t_refresh_s",
    "t_rcd_s",
    "t_wr_s",
    "e_read_j",
    "e_write_j",
    "i_leak_a",
    "i_leak_density_a_m2",
)


def _load_pareto_csv(base_dir: Path, backend: str, corner: str | None = None) -> pd.DataFrame | None:
    """Load pareto metrics CSV for one simulator backend."""
    candidates = []
    if corner is not None:
        candidates.append(base_dir / backend / corner / "pareto_metrics.csv")
        candidates.append(base_dir / backend / f"pareto_metrics_{corner}.csv")
    candidates.extend(
        [
            base_dir / backend / "pareto_metrics_all_corners.csv",
            base_dir / backend / "pareto_roadmap.csv",
        ]
    )
    for path in candidates:
        if path.is_file():
            return pd.read_csv(path)
    return None


def _discover_pareto_backends(base_dir: Path) -> list[str]:
    """Return simulator names with Pareto CSVs under ``base_dir/{backend}/``."""
    names: set[str] = set()
    if not base_dir.is_dir():
        return []
    for path in base_dir.iterdir():
        if not path.is_dir():
            continue
        if _load_pareto_csv(base_dir, path.name, corner=None) is not None:
            names.add(path.name)
    return sorted(names)


def collect_pareto_frames(
    base_dir: Path,
    corner: str | None = None,
    backends: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Load Pareto CSVs for each simulator under ``base_dir/{backend}/``."""
    if backends is not None:
        names = backends
    else:
        discovered = _discover_pareto_backends(base_dir)
        available = [b.value for b in available_backends()]
        names = sorted(set(discovered) | set(available))
    frames: dict[str, pd.DataFrame] = {}
    for name in names:
        df = _load_pareto_csv(base_dir, name, corner)
        if df is not None and not df.empty:
            frames[name] = df
    return frames


def compare_pareto_simulators(
    frames: dict[str, pd.DataFrame],
    reference: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge per-simulator Pareto metrics and compute relative differences."""
    return compare_metric_frames(frames, _KEY_COLS, _PARETO_METRICS, reference=reference)


def _ensure_style() -> None:
    global _RC_APPLIED
    if not _RC_APPLIED:
        apply_rcparams()
        _RC_APPLIED = True


def _resolve_reference_backend(frames: dict[str, pd.DataFrame], reference: str | None) -> str:
    if reference is not None:
        return reference
    if SimulatorBackend.SPECTRE.value in frames:
        return SimulatorBackend.SPECTRE.value
    return sorted(frames)[0]


def _filter_reference_subset(
    df: pd.DataFrame,
    *,
    ref_corner: str,
    ref_ccell: float,
) -> pd.DataFrame:
    subset = df[(df["corner"] == ref_corner) & (df["ccell_ff"] == ref_ccell)].copy()
    if subset.empty:
        subset = df[df["corner"] == ref_corner].copy()
    if subset.empty:
        subset = df.copy()
    return subset


def _non_reference_backends(wide: pd.DataFrame, metric: str, reference: str) -> list[str]:
    prefix = f"{metric}_"
    return sorted(
        {
            col[len(prefix) :]
            for col in wide.columns
            if col.startswith(prefix) and col[len(prefix) :] != reference
        }
    )


def _comparison_backends(diff: pd.DataFrame, reference: str) -> list[str]:
    suffix = f"_vs_{reference}"
    backends: set[str] = set()
    for col in diff.columns:
        if not col.startswith("rel_diff_") or not col.endswith(suffix):
            continue
        body = col[len("rel_diff_") : -len(suffix)]
        for metric in _PARETO_METRICS:
            prefix = f"{metric}_"
            if body.startswith(prefix):
                backends.add(body[len(prefix) :])
                break
    return sorted(backends)


def _backend_color(name: str, index: int) -> str:
    return MULTI_SERIES_COLORS[index % len(MULTI_SERIES_COLORS)]


def _metric_scale(metric: str) -> tuple[float, str]:
    if metric.endswith("_s"):
        if metric in ("t_ret_s", "t_refresh_s"):
            return 1e3, "ms"
        return 1e9, "ns"
    if metric.endswith("_j"):
        return 1e15, "fJ"
    if metric == "i_leak_a":
        return 1e12, "pA"
    if metric == "i_leak_density_a_m2":
        return 1.0, "A/m²"
    return 1.0, ""


def _parity_stem(metric: str) -> str:
    return _PARITY_STEMS.get(metric, f"simulator_parity_{metric.removesuffix('_s').removesuffix('_j')}")


def _rel_diff_columns(diff: pd.DataFrame, reference: str) -> list[str]:
    suffix = f"_vs_{reference}"
    return sorted(
        col
        for col in diff.columns
        if col.startswith("rel_diff_") and col.endswith(suffix)
    )


def _rel_diff_series_label(col: str, reference: str) -> tuple[str, str, str]:
    """Return (backend, metric, display label) parsed from a rel-diff column."""
    body = col[len("rel_diff_") : -len(f"_vs_{reference}")]
    for metric in _PARETO_METRICS:
        prefix = f"{metric}_"
        if body.startswith(prefix):
            backend = body[len(prefix) :]
            label = f"{backend} {_METRIC_LABELS.get(metric, metric)}"
            return backend, metric, label
    return body, body, body


def plot_simulator_parity(
    wide: pd.DataFrame,
    output_path: Path,
    *,
    metric: str,
    reference: str,
    ref_corner: str,
    ref_ccell: float,
    backends: list[str] | None = None,
    annotate: bool = True,
    ax: plt.Axes | None = None,
) -> Path | None:
    """Scatter parity plot: reference metric vs each alternate backend."""
    _ensure_style()
    subset = _filter_reference_subset(wide, ref_corner=ref_corner, ref_ccell=ref_ccell)
    ref_col = f"{metric}_{reference}"
    if ref_col not in subset.columns:
        return None

    others = backends or _non_reference_backends(subset, metric, reference)
    if not others:
        return None

    scale, unit = _metric_scale(metric)
    label = _METRIC_LABELS.get(metric, metric)
    owns_fig = ax is None
    if owns_fig:
        fig, ax = plt.subplots(figsize=FIGSIZE)
    else:
        fig = ax.figure
    plotted = False

    for idx, backend in enumerate(others):
        other_col = f"{metric}_{backend}"
        if other_col not in subset.columns:
            continue
        pair = subset[["model_id", ref_col, other_col]].dropna()
        if pair.empty:
            continue
        x = pair[ref_col] * scale
        y = pair[other_col] * scale
        ax.scatter(
            x,
            y,
            s=MARKER_SIZE * (24 if owns_fig else 12),
            color=_backend_color(backend, idx),
            marker=_SIMULATOR_MARKERS.get(backend, "o"),
            edgecolors="white",
            linewidths=MARKER_EDGEWIDTH,
            label=backend,
            zorder=2,
        )
        if annotate:
            for _, row in pair.iterrows():
                ax.annotate(
                    str(row["model_id"]).replace("_", "\n"),
                    (row[ref_col] * scale, row[other_col] * scale),
                    textcoords="offset points",
                    xytext=(4, 4),
                    fontsize=7,
                    ha="left",
                )
        plotted = True

    if not plotted:
        if owns_fig:
            plt.close(fig)
        return None

    lo = min(ax.get_xlim()[0], ax.get_ylim()[0])
    hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([lo, hi], [lo, hi], "--", color="#333333", linewidth=LINEWIDTH_SECONDARY, alpha=0.7, zorder=1)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    if owns_fig:
        ax.set_xlabel(f"{label} — {reference} ({unit})", fontsize=LABEL_SIZE, fontweight="bold")
        ax.set_ylabel(f"{label} — alternate backend ({unit})", fontsize=LABEL_SIZE, fontweight="bold")
        ax.set_title(
            f"Simulator parity: {label} @ {ref_corner}, Ccell={ref_ccell:.0f} fF",
            fontsize=TITLE_SIZE,
            fontweight="bold",
        )
        ax.legend(fontsize=LEGEND_SIZE, framealpha=0.9)
        ax.set_aspect("equal", adjustable="box")
    else:
        ax.set_title(label, fontsize=LABEL_SIZE, fontweight="bold")
        ax.tick_params(labelsize=TICK_SIZE - 1)
    apply_style(ax)
    return save_figure(fig, output_path) if owns_fig else None


def plot_simulator_parity_overview(
    wide: pd.DataFrame,
    output_path: Path,
    *,
    reference: str,
    ref_corner: str,
    ref_ccell: float,
) -> Path | None:
    """Multi-panel parity grid for every metric with paired data."""
    _ensure_style()
    metrics = [metric for metric in _PARETO_METRICS if _parity_stem(metric)]
    ncols = 4
    nrows = int(np.ceil(len(metrics) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(FIGSIZE[0], FIGSIZE[1] * nrows * 0.75))
    axes_flat = np.atleast_1d(axes).ravel()
    plotted_any = False

    for ax, metric in zip(axes_flat, metrics, strict=False):
        path = plot_simulator_parity(
            wide,
            output_path,
            metric=metric,
            reference=reference,
            ref_corner=ref_corner,
            ref_ccell=ref_ccell,
            annotate=False,
            ax=ax,
        )
        if ax.collections or ax.lines:
            plotted_any = True
        else:
            ax.set_visible(False)

    for ax in axes_flat[len(metrics) :]:
        ax.set_visible(False)

    if not plotted_any:
        plt.close(fig)
        return None

    handles, labels = axes_flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=min(3, len(labels)), fontsize=LEGEND_SIZE)
    fig.suptitle(
        f"Simulator parity overview @ {ref_corner}, Ccell={ref_ccell:.0f} fF (ref={reference})",
        fontsize=TITLE_SIZE,
        fontweight="bold",
        y=1.02,
    )
    return save_figure(fig, output_path)


def plot_simulator_rel_diff_by_model(
    diff: pd.DataFrame,
    output_path: Path,
    *,
    reference: str,
    ref_corner: str,
    ref_ccell: float,
    metrics: tuple[str, ...] = _PARETO_METRICS,
    title_suffix: str | None = None,
) -> Path | None:
    """Grouped bar chart of relative differences per model at the reference point."""
    _ensure_style()
    subset = _filter_reference_subset(diff, ref_corner=ref_corner, ref_ccell=ref_ccell)
    if subset.empty:
        return None

    backends = _comparison_backends(diff, reference)
    if not backends:
        return None

    models = sorted(subset["model_id"].astype(str).unique())
    series: list[tuple[str, str, np.ndarray]] = []
    for backend in backends:
        for metric in metrics:
            col = f"rel_diff_{metric}_{backend}_vs_{reference}"
            if col not in subset.columns:
                continue
            values = []
            for model_id in models:
                row = subset[subset["model_id"] == model_id]
                val = row[col].iloc[0] if not row.empty else np.nan
                values.append(val * 100 if pd.notna(val) else np.nan)
            if any(pd.notna(v) for v in values):
                label = f"{backend} {_METRIC_LABELS.get(metric, metric)}"
                series.append((label, backend, np.array(values, dtype=float)))

    if not series:
        return None

    fig, ax = plt.subplots(figsize=FIGSIZE)
    x = np.arange(len(models))
    width = 0.8 / len(series)
    for idx, (label, backend, values) in enumerate(series):
        offset = (idx - (len(series) - 1) / 2) * width
        backend_idx = backends.index(backend)
        ax.bar(
            x + offset,
            values,
            width=width,
            label=label,
            color=_backend_color(backend, backend_idx),
            alpha=0.85 if idx % max(len(metrics), 1) == 0 else 0.65,
            edgecolor="white",
            linewidth=0.8,
        )

    ax.axhline(0.0, color="#333333", linewidth=1.0, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=35, ha="right")
    ax.set_ylabel(f"Relative difference vs {reference} (%)", fontsize=LABEL_SIZE, fontweight="bold")
    suffix = f" — {title_suffix}" if title_suffix else ""
    ax.set_title(
        f"Cross-simulator relative differences{suffix} @ {ref_corner}, Ccell={ref_ccell:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    ax.legend(fontsize=LEGEND_SIZE - 1, ncol=2, framealpha=0.9)
    apply_style(ax, grid_axis="y")
    return save_figure(fig, output_path)


def plot_simulator_max_rel_diff(
    diff: pd.DataFrame,
    output_path: Path,
    *,
    reference: str,
    ref_corner: str,
    ref_ccell: float,
) -> Path | None:
    """Bar chart of maximum |relative difference| per metric and backend."""
    _ensure_style()
    subset = _filter_reference_subset(diff, ref_corner=ref_corner, ref_ccell=ref_ccell)
    rel_cols = _rel_diff_columns(subset, reference)
    if not rel_cols:
        return None

    entries: list[tuple[str, str, float]] = []
    for col in rel_cols:
        backend, metric, _ = _rel_diff_series_label(col, reference)
        values = subset[col].abs().dropna()
        if values.empty:
            continue
        entries.append((backend, _METRIC_LABELS.get(metric, metric), float(values.max()) * 100))

    if not entries:
        return None

    backends = sorted({entry[0] for entry in entries})
    metric_order = list(_METRIC_LABELS.values())
    metrics = sorted(
        {entry[1] for entry in entries},
        key=lambda label: metric_order.index(label) if label in metric_order else len(metric_order),
    )
    fig, ax = plt.subplots(figsize=FIGSIZE)
    x = np.arange(len(metrics))
    width = 0.8 / max(len(backends), 1)
    for idx, backend in enumerate(backends):
        heights = []
        for metric in metrics:
            match = [value for b, m, value in entries if b == backend and m == metric]
            heights.append(match[0] if match else np.nan)
        offset = (idx - (len(backends) - 1) / 2) * width
        ax.bar(
            x + offset,
            heights,
            width=width,
            label=backend,
            color=_backend_color(backend, idx),
            edgecolor="white",
            linewidth=0.8,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=35, ha="right")
    ax.set_ylabel(f"Max |relative difference| vs {reference} (%)", fontsize=LABEL_SIZE, fontweight="bold")
    ax.set_title(
        f"Maximum cross-simulator deviation @ {ref_corner}, Ccell={ref_ccell:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    ax.legend(fontsize=LEGEND_SIZE, framealpha=0.9)
    apply_style(ax, grid_axis="y")
    return save_figure(fig, output_path)


def plot_simulator_rel_diff_heatmap(
    diff: pd.DataFrame,
    output_path: Path,
    *,
    reference: str,
    ref_corner: str,
    ref_ccell: float,
) -> Path | None:
    """Heatmap of relative differences (models × backend/metric pairs)."""
    _ensure_style()
    subset = _filter_reference_subset(diff, ref_corner=ref_corner, ref_ccell=ref_ccell)
    rel_cols = _rel_diff_columns(subset, reference)
    if not rel_cols:
        return None

    models = sorted(subset["model_id"].astype(str).unique())
    col_labels = [_rel_diff_series_label(col, reference)[2] for col in rel_cols]
    matrix = np.full((len(models), len(rel_cols)), np.nan)
    for row_idx, model_id in enumerate(models):
        row = subset[subset["model_id"] == model_id]
        if row.empty:
            continue
        for col_idx, col in enumerate(rel_cols):
            val = row[col].iloc[0]
            if pd.notna(val):
                matrix[row_idx, col_idx] = float(val) * 100

    if not np.isfinite(matrix).any():
        return None

    vmax = np.nanmax(np.abs(matrix))
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    fig, ax = plt.subplots(figsize=(max(FIGSIZE[0], len(rel_cols) * 0.9), max(FIGSIZE[1], len(models) * 0.45)))
    im = ax.imshow(matrix, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_xticks(np.arange(len(rel_cols)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=TICK_SIZE)
    ax.set_yticks(np.arange(len(models)))
    ax.set_yticklabels(models, fontsize=TICK_SIZE)
    ax.set_title(
        f"Cross-simulator relative difference heatmap @ {ref_corner}, Ccell={ref_ccell:.0f} fF",
        fontsize=TITLE_SIZE,
        fontweight="bold",
    )
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label(f"Rel diff vs {reference} (%)", fontsize=LABEL_SIZE, fontweight="bold")
    apply_style(ax, grid_axis=None)
    ax.grid(False)
    return save_figure(fig, output_path)


def generate_simulator_figures(
    frames: dict[str, pd.DataFrame],
    output_dir: Path,
    *,
    reference: str | None = None,
    ref_corner: str = "tt",
    ref_ccell: float = 20.0,
) -> list[Path]:
    """Generate parity and rel-diff figures for multi-simulator Pareto runs."""
    if len(frames) < 2:
        return []

    ref_name = _resolve_reference_backend(frames, reference)
    wide, diff = compare_pareto_simulators(frames, reference=ref_name)
    if wide.empty:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for metric in _PARETO_METRICS:
        stem = _parity_stem(metric)
        try:
            path = plot_simulator_parity(
                wide,
                output_dir / stem,
                metric=metric,
                reference=ref_name,
                ref_corner=ref_corner,
                ref_ccell=ref_ccell,
            )
            if path is not None:
                paths.append(path)
        except ValueError:
            continue

    for plot_fn, stem in (
        (plot_simulator_parity_overview, "simulator_parity_overview"),
        (plot_simulator_max_rel_diff, "simulator_max_rel_diff"),
        (plot_simulator_rel_diff_heatmap, "simulator_rel_diff_heatmap"),
    ):
        try:
            path = plot_fn(
                wide if plot_fn is plot_simulator_parity_overview else diff,
                output_dir / stem,
                reference=ref_name,
                ref_corner=ref_corner,
                ref_ccell=ref_ccell,
            )
            if path is not None:
                paths.append(path)
        except ValueError:
            continue

    for group_name, metrics in _REL_DIFF_GROUPS:
        try:
            path = plot_simulator_rel_diff_by_model(
                diff,
                output_dir / f"simulator_rel_diff_{group_name}",
                reference=ref_name,
                ref_corner=ref_corner,
                ref_ccell=ref_ccell,
                metrics=metrics,
                title_suffix=group_name,
            )
            if path is not None:
                paths.append(path)
        except ValueError:
            continue

    try:
        path = plot_simulator_rel_diff_by_model(
            diff,
            output_dir / "simulator_rel_diff_by_model",
            reference=ref_name,
            ref_corner=ref_corner,
            ref_ccell=ref_ccell,
            metrics=_PARETO_METRICS,
            title_suffix="all metrics",
        )
        if path is not None:
            paths.append(path)
    except ValueError:
        pass

    if paths:
        logger.info("Simulator comparison figures → %s", output_dir)
    return paths


def _simulator_figure_stems(figures_dir: Path) -> list[str]:
    stems = list(_PARITY_STEMS.values()) + list(_EXTRA_FIGURE_STEMS) + ["simulator_rel_diff_by_model"]
    present = [stem for stem in stems if (figures_dir / f"{stem}.svg").is_file()]
    if present:
        return present
    return sorted(path.stem for path in figures_dir.glob("simulator_*.svg"))


def simulator_figures_markdown(figures_dir: Path | None, stems: list[str] | None = None) -> str:
    """Embed simulator comparison figure links for RESULTS.md."""
    if figures_dir is None:
        return ""
    rel = figures_dir.name
    figure_stems = stems or _simulator_figure_stems(figures_dir)
    lines: list[str] = []
    for stem in figure_stems:
        svg = figures_dir / f"{stem}.svg"
        if not svg.is_file():
            continue
        cap = _SIMULATOR_FIGURE_CAPTIONS.get(stem, stem.replace("_", " "))
        if not lines:
            lines.extend(["", "#### Simulator comparison figures", ""])
        lines.extend([f"##### {cap}", "", f"![{cap}]({rel}/{stem}.svg)", ""])
    return "\n".join(lines)


def _format_rel_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:+.2g}%"


def simulator_backend_summary_markdown(frames: dict[str, pd.DataFrame]) -> str:
    """Summarize metric coverage per backend for RESULTS.md."""
    if len(frames) < 2:
        return ""

    lines = [
        "## Simulator verification (Spectre / HSPICE / ngspice)",
        "",
        "Per-backend metric coverage in the multi-simulator run:",
        "",
        "| Backend | Rows | "
        + " | ".join(_METRIC_LABELS[m] for m in _PARETO_METRICS)
        + " |",
        "| --- | --- | " + " | ".join(["---"] * len(_PARETO_METRICS)) + " |",
    ]
    for name in sorted(frames):
        df = frames[name]
        counts = [
            str(df[metric].notna().sum() if metric in df.columns else 0)
            for metric in _PARETO_METRICS
        ]
        lines.append(f"| {name} | {len(df)} | " + " | ".join(counts) + " |")
    lines.append("")
    return "\n".join(lines)


def simulator_comparison_markdown(
    diff: pd.DataFrame,
    *,
    reference: str,
    ref_corner: str,
    ref_ccell: float,
) -> str:
    """Render a compact markdown section for RESULTS.md."""
    if diff.empty:
        return ""

    subset = diff[(diff["corner"] == ref_corner) & (diff["ccell_ff"] == ref_ccell)].copy()
    if subset.empty:
        subset = diff[diff["corner"] == ref_corner].copy()
    if subset.empty:
        subset = diff.copy()

    rel_cols = [c for c in diff.columns if c.startswith("rel_diff_")]
    if not rel_cols:
        return ""

    alt_backends = _comparison_backends(diff, reference)
    header = ["Model", "Metric", *alt_backends]
    lines = [
        "### Cross-simulator relative differences",
        "",
        f"Reference backend: **{reference}**. Relative differences at **{ref_corner}** "
        f"@ Ccell = {ref_ccell:.0f} fF (positive = backend higher than reference).",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]

    for _, row in subset.sort_values("model_id").iterrows():
        model_id = row["model_id"]
        for metric, label in _METRIC_LABELS.items():
            values = []
            for backend in alt_backends:
                col = f"rel_diff_{metric}_{backend}_vs_{reference}"
                val = row.get(col) if col in row.index else None
                values.append(val)
            if all(pd.isna(v) for v in values):
                continue
            cells = [str(model_id), label] + [_format_rel_pct(v) for v in values]
            lines.append("| " + " | ".join(cells) + " |")

    if len(lines) <= 6:
        return ""

    lines.extend(
        [
            "",
            "Full wide merge and rel-diff CSVs: `simulator_compare/pareto_metrics_wide.csv`, "
            "`simulator_compare/pareto_metrics_rel_diff.csv`.",
        ]
    )
    return "\n".join(lines)


def write_simulator_comparison(
    base_dir: Path,
    corner: str = "tt",
    backends: list[str] | None = None,
    output_dir: Path | None = None,
    reference: str | None = None,
) -> Path | None:
    """Write Pareto comparison CSVs and return path to markdown snippet source data."""
    out = output_dir or (base_dir / "simulator_compare")
    out.mkdir(parents=True, exist_ok=True)

    frames = collect_pareto_frames(base_dir, corner=None, backends=backends)
    if len(frames) < 2:
        logger.info("Skip Pareto simulator compare: need >=2 backends with data")
        return None

    ref_name = reference or (
        SimulatorBackend.SPECTRE.value
        if SimulatorBackend.SPECTRE.value in frames
        else sorted(frames)[0]
    )
    wide, diff = compare_pareto_simulators(frames, reference=ref_name)
    if wide.empty:
        return None

    wide_path = out / "pareto_metrics_wide.csv"
    diff_path = out / "pareto_metrics_rel_diff.csv"
    wide.to_csv(wide_path, index=False)
    diff.to_csv(diff_path, index=False)

    summaries = [
        f"# Pareto simulator comparison ({corner})",
        "",
        f"Reference: {ref_name}",
        "",
        f"- Wide: `{wide_path.name}`",
        f"- Rel diff: `{diff_path.name}`",
        "",
    ]
    rel_cols = [c for c in diff.columns if c.startswith("rel_diff_")]
    if rel_cols:
        max_abs = diff[rel_cols].abs().max()
        summaries.append("| metric | max |rel diff| |")
        summaries.append("| --- | --- |")
        for col in rel_cols:
            val = max_abs[col]
            if pd.notna(val):
                summaries.append(f"| {col} | {val:.4g} |")
        summaries.append("")

    summary_path = out / "SIMULATOR_COMPARE.md"
    summary_path.write_text("\n".join(summaries), encoding="utf-8")
    logger.info("Pareto simulator comparison → %s", summary_path)
    return summary_path
