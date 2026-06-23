"""Generate markdown experiment report with tables and figures."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from bench.analysis import generate_figures
from bench.corner_registry import registry_provenance
from bench.paths import OPEN_DRAMMODEL_V1_ROOT
from bench.simulator import resolve_backend
from bench.simulator_compare import list_compared_backends, simulator_compare_report_markdown
from bench.vct_analysis import vct_scaling_summary_markdown

# Columns shown in the summary table (human-readable headers).
_TABLE_COLUMNS: list[tuple[str, str, str]] = [
    ("model_id", "Model", "s"),
    ("architecture", "Architecture", "s"),
    ("vdd", "Vdd (V)", ".2f"),
    ("ion_a", "Ion (A)", ".3e"),
    ("ioff_a", "Ioff (A)", ".3e"),
    ("vt_v", "Vt (V)", ".3f"),
    ("ss_mv_dec", "SS (mV/dec)", ".1f"),
    ("dibl_mv_v", "DIBL (mV/V)", ".1f"),
    ("ron_ohm", "Ron (Ω)", ".3e"),
    ("cgg_f", "Cgg (F)", ".3e"),
    ("cgd_f", "Cgd (F)", ".3e"),
    ("igidl_a", "GIDL (A)", ".3e"),
    ("ion_per_cgg", "Ion/Cgg (1/s)", ".3e"),
    ("ron_x_cload", "Ron×Cload (s)", ".3e"),
    ("ioff_density_a_m2", "Ioff density (A/m²)", ".3e"),
]


def _git_revision(path: Path) -> str:
    """Best-effort git revision for a path."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except OSError:
        pass
    return "unknown"


def _format_cell(value: object, fmt: str) -> str:
    """Format one table cell."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if fmt == "s":
        return str(value)
    if fmt == "d":
        try:
            return str(int(float(value)))
        except (TypeError, ValueError):
            return str(value)
    try:
        return format(float(value), fmt)
    except (TypeError, ValueError):
        return str(value)


def metrics_table_markdown(df: pd.DataFrame) -> str:
    """Render device metrics as a markdown table."""
    headers = [header for _, header, _ in _TABLE_COLUMNS]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        cells = [
            _format_cell(row.get(col), fmt) for col, _, fmt in _TABLE_COLUMNS
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def architecture_summary(df: pd.DataFrame) -> str:
    """Short bullet summary grouped by architecture."""
    lines: list[str] = []
    for arch, group in df.groupby("architecture"):
        best_ion = group.loc[group["ion_a"].idxmax()]
        lowest_ioff = group.loc[group["ioff_a"].idxmin()]
        lines.append(
            f"- **{arch}**: highest Ion = `{best_ion['model_id']}` "
            f"({best_ion['ion_a']:.3e} A); lowest Ioff = `{lowest_ioff['model_id']}` "
            f"({lowest_ioff['ioff_a']:.3e} A)"
        )
    return "\n".join(lines)


def _simple_table(df: pd.DataFrame, columns: list[tuple[str, str, str]]) -> str:
    """Render a generic markdown table."""
    headers = [header for _, header, _ in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        cells = [_format_cell(row.get(col), fmt) for col, _, fmt in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


_CELL_COLUMNS: list[tuple[str, str, str]] = [
    ("model_id", "Model", "s"),
    ("ccell_ff", "Ccell (fF)", ".0f"),
    ("t_write_s", "t_write (s)", ".3e"),
    ("t_read_s", "t_read (s)", ".3e"),
    ("i_hold_a", "I_hold (A)", ".3e"),
    ("q_read_c", "Q_read (C)", ".3e"),
]

_MINI_COLUMNS: list[tuple[str, str, str]] = [
    ("model_id", "Model", "s"),
    ("n_cells", "N cells", "d"),
    ("bl_topology", "BL topology", "s"),
    ("t_bl_settle_s", "t_BL settle (s)", ".3e"),
    ("i_bl_leak_a", "I_BL leak (A)", ".3e"),
    ("r_metal_seg_ohm", "R_metal/pitch (Ω)", ".2f"),
    ("r_contact_ohm", "R_contact (Ω)", ".2f"),
    ("c_sa_ff", "C_SA (fF)", ".1f"),
]


def device_vs_cell_ranking(device_df: pd.DataFrame, cell_df: pd.DataFrame) -> str:
    """Compare device Ion ranking with 1T1C read-speed ranking @ 20 fF."""
    if cell_df.empty:
        return "_1T1C metrics not available._"
    dev = device_df.drop_duplicates(subset=["model_id"], keep="first")
    ref = cell_df[cell_df["ccell_ff"] == 20.0].copy()
    if ref.empty:
        ref = cell_df.groupby("model_id").first().reset_index()
    ref = ref.dropna(subset=["t_read_s"])
    if ref.empty:
        return "_No valid t_read data._"
    dev_rank = dev.sort_values("ion_a", ascending=False)["model_id"].tolist()
    cell_rank = ref.sort_values("t_read_s", ascending=True)["model_id"].tolist()
    lines = [
        f"- **Fastest device Ion:** `{dev_rank[0]}`",
        f"- **Fastest 1T1C read (20 fF):** `{cell_rank[0]}`",
    ]
    if dev_rank[0] != cell_rank[0]:
        lines.append(
            f"- Device-level Ion leader (`{dev_rank[0]}`) differs from "
            f"1T1C read leader (`{cell_rank[0]}`) — array RC and Ccell matter."
        )
    else:
        lines.append("- Device Ion and 1T1C read leaders align at 20 fF.")
    return "\n".join(lines)


def _filter_reference_corner(df: pd.DataFrame, reference_corner: str) -> pd.DataFrame:
    """Return rows for the reference corner, or the input if already single-corner."""
    if "corner" not in df.columns:
        return df
    subset = df[df["corner"] == reference_corner].copy()
    if subset.empty:
        return df.groupby("model_id", as_index=False).first()
    return subset


def corner_summary_table(df: pd.DataFrame) -> str:
    """Compact Ion/Ioff summary grouped by corner."""
    if "corner" not in df.columns or df["corner"].nunique() <= 1:
        return ""
    rows: list[str] = [
        "| Corner | Mean Ion (A) | Mean Ioff (A) | Max Ion model |",
        "| --- | --- | --- | --- |",
    ]
    for corner, group in df.groupby("corner"):
        best = group.loc[group["ion_a"].idxmax()]
        rows.append(
            f"| {corner} | {group['ion_a'].mean():.3e} | {group['ioff_a'].mean():.3e} | "
            f"`{best['model_id']}` ({best['ion_a']:.3e} A) |"
        )
    return "\n".join(rows)


def _cell_ccell_sweep_table(cell_df: pd.DataFrame) -> str:
    """Render full 1T1C Ccell sweep (10/20/30 fF) sorted by model and Ccell."""
    if cell_df.empty:
        return ""
    sweep = cell_df.sort_values(["model_id", "ccell_ff"]).copy()
    return _simple_table(sweep, _CELL_COLUMNS)


def generate_report(
    metrics_csv: Path,
    output_md: Path,
    figures_dir: Path | None = None,
    corner: str = "tt",
    cell_csv: Path | None = None,
    mini_array_csv: Path | None = None,
    reference_corner: str = "tt",
    golden_status: str | None = None,
    simulator_compare_dir: Path | None = None,
) -> Path:
    """Build a markdown report with metrics table and embedded figures.

    Args:
        metrics_csv: Path to ``device_metrics.csv`` or combined all-corner CSV.
        output_md: Output markdown file path.
        figures_dir: Directory for figure SVGs (default: sibling ``figures/``).
        corner: Corner label for the report header (``all`` when multi-corner).
        cell_csv: Optional ``cell_1t1c_metrics.csv`` path.
        mini_array_csv: Optional ``mini_array_metrics.csv`` path.
        reference_corner: Corner for primary tables/plots when data spans corners.
        golden_status: Optional golden validation summary line.
        simulator_compare_dir: Optional ``simulator_compare/`` directory for cross-tool section.

    Returns:
        Path to the written markdown file.
    """
    if not metrics_csv.is_file():
        raise FileNotFoundError(f"Metrics CSV not found: {metrics_csv}")

    df_all = pd.read_csv(metrics_csv)
    df = _filter_reference_corner(df_all, reference_corner)

    cell_df_all = pd.read_csv(cell_csv) if cell_csv and cell_csv.is_file() else pd.DataFrame()
    mini_df_all = (
        pd.read_csv(mini_array_csv) if mini_array_csv and mini_array_csv.is_file() else pd.DataFrame()
    )
    cell_df = _filter_reference_corner(cell_df_all, reference_corner) if not cell_df_all.empty else cell_df_all
    mini_df = _filter_reference_corner(mini_df_all, reference_corner) if not mini_df_all.empty else mini_df_all

    fig_dir = figures_dir or (output_md.parent / "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    figure_paths = generate_figures(
        metrics_csv,
        fig_dir,
        reference_corner=reference_corner,
        cell_csv=cell_csv if cell_csv and cell_csv.is_file() else None,
        include_corner_sensitivity=True,
    )

    try:
        backend = resolve_backend().value
    except RuntimeError:
        backend = "unknown"

    results_root = metrics_csv.parent.parent if metrics_csv.parent.name in {
        "tt", "ff", "ss", "cold", "hot",
    } else metrics_csv.parent
    compare_dir = simulator_compare_dir or (results_root / "simulator_compare")
    compare_section = ""
    compared_backends = list_compared_backends(results_root)
    if compare_dir.is_dir():
        compare_section = simulator_compare_report_markdown(
            compare_dir,
            reference_corner=reference_corner,
            results_root=results_root,
        )
    if compared_backends:
        simulator_line = f"**Simulators:** {', '.join(compared_backends)} (primary tables: **{reference_corner}**, Spectre when present)"
    else:
        simulator_line = f"**Simulator:** {backend}"

    try:
        model_rev = _git_revision(OPEN_DRAMMODEL_V1_ROOT)
    except FileNotFoundError:
        model_rev = "unknown"

    rel_fig_dir = figures_dir.name if figures_dir else "figures"
    fig_blocks = "\n\n".join(
        f"### {path.stem.replace('_', ' ').title()}\n\n"
        f"![{path.stem}]({rel_fig_dir}/{path.name})"
        for path in figure_paths
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_models = df["model_id"].nunique() if "model_id" in df.columns else len(df)

    corner_section = ""
    corner_table = corner_summary_table(df_all)
    if corner_table:
        corner_section = f"""
## Corner matrix summary

Primary tables and Pareto/VCT/radar plots use **{reference_corner}** reference data.

{corner_table}
"""

    golden_line = f"\n**Golden validation:** {golden_status}\n" if golden_status else ""

    corner_registry_line = ""
    provenance = registry_provenance()
    if provenance:
        corner_registry_line = (
            f"\n**IDEA153 corner registry:** `{provenance['registry_version']}` "
            f"(source: **{provenance['source']}**, model SHA: `{provenance['model_sha']}`)\n"
        )

    vct_section = ""
    vct_summary = vct_scaling_summary_markdown(df, corner=reference_corner)
    if vct_summary:
        vct_section = f"""
## VCT scaling summary ({reference_corner})

{vct_summary}
"""

    cell_section = ""
    if not cell_df.empty:
        ref_cell = cell_df[cell_df["ccell_ff"] == 20.0]
        if ref_cell.empty:
            ref_cell = cell_df.groupby("model_id").first().reset_index()
        sweep_table = _cell_ccell_sweep_table(cell_df)
        cell_section = f"""
## 1T1C macro (20 fF reference)

{_simple_table(ref_cell, _CELL_COLUMNS)}

## 1T1C Ccell sweep ({reference_corner})

Full transient sweep at 10, 20, and 30 fF per model.

{sweep_table}
"""

    mini_section = ""
    if not mini_df.empty:
        mini_section = f"""
## Mini-array (layout BL RC)

{_simple_table(mini_df, _MINI_COLUMNS)}
"""

    body = f"""# OpenDRAM Device Benchmark — Results

**Generated:** {timestamp}  
**Corners:** {corner} (reference: **{reference_corner}** for tables/plots)  
{simulator_line}  
**Models:** {n_models} access devices  
**OpenDRAMmodelV1 revision:** `{model_rev}`{golden_line}{corner_registry_line}

Cross-architecture DRAM access transistor benchmark (BCAT vs VCT vs 3D GAA) using OpenDRAMmodelV1. See [benchmark_spec.md](../docs/benchmark_spec.md) for metric definitions.
{compare_section}{corner_section}
## Architecture highlights ({reference_corner})

{architecture_summary(df)}

## Device vs cell ranking ({reference_corner})

{device_vs_cell_ranking(df, cell_df)}

## Metric table ({reference_corner})

{metrics_table_markdown(df)}
{vct_section}{cell_section}{mini_section}
## Summary figures

{fig_blocks}

## Artifacts

| File | Description |
|------|-------------|
| `{metrics_csv.name}` | Device metrics (CSV) |
| `cell_1t1c_metrics_all_corners.csv` | 1T1C sweep (all corners, when present) |
| `mini_array_metrics_all_corners.csv` | Mini-array (all corners, when present) |
| `{rel_fig_dir}/` | Pareto, VCT scaling, radar, corner sensitivity, Ccell scaling |
| `../docs/vct_scaling_analysis.md` | VCT node scaling write-up |

---
*Report produced by `dram-device report` / `run_experiments.sh`*
"""
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(body, encoding="utf-8")
    return output_md
