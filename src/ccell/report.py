"""Markdown RESULTS report for the Ccell roadmap experiment."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from dram_benchmark.report.markdown_tables import join_md_row
from ccell.binding import build_binding_summary
from ccell.config import load_ccell_config
from ccell.read_signal import read_threshold_summary


def _git_revision(path: Path) -> str:
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


def _format_cell(value: object, fmt: str = "s", *, scale: float = 1.0) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if fmt == "s":
        return str(value)
    try:
        return format(float(value) * scale, fmt)
    except (TypeError, ValueError):
        return str(value)


def _table(df: pd.DataFrame, columns: list[tuple[str, str, str, float]]) -> str:
    headers = [h for _, h, _, _ in columns]
    lines = [
        join_md_row(headers),
        join_md_row(["---"] * len(headers)),
    ]
    for _, row in df.iterrows():
        cells = [_format_cell(row.get(col), fmt, scale=scale) for col, _, fmt, scale in columns]
        lines.append(join_md_row(cells))
    return "\n".join(lines)


def generate_report(
    sweep_csv: Path,
    ccell_min_csv: Path,
    output_path: Path,
    *,
    feasibility_csv: Path | None = None,
    three_d_csv: Path | None = None,
    whatif_csv: Path | None = None,
    figures_dir: Path | None = None,
    project_root: Path | None = None,
) -> None:
    """Write Ccell roadmap RESULTS.md from CSV artifacts."""
    cfg = load_ccell_config()
    sweep_df = pd.read_csv(sweep_csv)
    ccell_min_df = pd.read_csv(ccell_min_csv)
    read_threshold_text = read_threshold_summary(cfg, sweep_df)
    root = project_root or Path(__file__).resolve().parents[2]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# OpenDRAM Cell Capacitance Roadmap",
        "",
        f"_Generated: {generated} · revision `{_git_revision(root)}`_",
        "",
        "## Executive summary",
        "",
        f"- **Ccell sweep:** {len(sweep_df)} rows across "
        f"{sweep_df['model_id'].nunique()} models, "
        f"Ccell ∈ {{{', '.join(str(int(v)) for v in cfg.ccell_values_ff)}}} fF.",
        f"- **Retention corner:** {cfg.retention_corner} @ "
        f"{cfg.constraints.min_t_ret_s * 1e3:.0f} ms target (ΔV = "
        f"{cfg.retention.delta_v_v * 1e3:.0f} mV loss).",
        f"- **Read corner:** {cfg.read_corner} @ {read_threshold_text}, "
        f"t_en = {cfg.constraints.t_en_ns:.0f} ns.",
        "",
        "## Ccell_min table (dual constraint)",
        "",
    ]

    min_cols = [
        ("model_id", "Model", "s", 1.0),
        ("architecture", "Arch", "s", 1.0),
        ("ccell_min_ret_ff", "Ccell_min ret (fF)", ".1f", 1.0),
        ("ccell_min_read_ff", "Ccell_min read (fF)", ".1f", 1.0),
        ("ccell_min_ff", "Ccell_min (fF)", ".1f", 1.0),
        ("binding", "Binding", "s", 1.0),
        ("cap_limited", "Cap-limited", "s", 1.0),
    ]
    lines.append(_table(ccell_min_df, min_cols))

    binding_df = build_binding_summary(ccell_min_df)
    if not binding_df.empty:
        lines.extend(["", "## Binding classification", ""])
        for _, row in binding_df.iterrows():
            lines.append(
                f"- **{row['binding']}:** {row['model_count']} models "
                f"({row['models']})"
            )

    if feasibility_csv and feasibility_csv.is_file():
        feas_df = pd.read_csv(feasibility_csv)
        lines.extend(["", "## Dielectric k scenario feasibility", ""])
        for scenario in sorted(feas_df["scenario"].unique()):
            subset = feas_df[feas_df["scenario"] == scenario]
            limited = subset[subset["cap_limited"] == True]  # noqa: E712
            lines.append(f"### {scenario}")
            lines.append("")
            feas_cols = [
                ("model_id", "Model", "s", 1.0),
                ("k", "k", ".0f", 1.0),
                ("achievable_ccell_ff", "Achievable (fF)", ".1f", 1.0),
                ("ccell_min_ff", "Required (fF)", ".1f", 1.0),
                ("cap_limited", "Cap-limited", "s", 1.0),
            ]
            lines.append(_table(subset, feas_cols))
            if not limited.empty:
                names = ", ".join(limited["model_id"].astype(str))
                lines.append("")
                lines.append(f"_Cap-limited under {scenario}: {names}_")
            lines.append("")

    if three_d_csv and three_d_csv.is_file():
        three_d_df = pd.read_csv(three_d_csv)
        lines.extend(["", "## 3D vertical capacitor boost", ""])
        three_cols = [
            ("model_id", "Model", "s", 1.0),
            ("beta", "β", ".1f", 1.0),
            ("effective_achievable_ff", "Effective Ccell (fF)", ".1f", 1.0),
            ("ccell_min_ff", "Required (fF)", ".1f", 1.0),
            ("cap_feasible", "Feasible", "s", 1.0),
        ]
        lines.append(_table(three_d_df, three_cols))

    if whatif_csv and whatif_csv.is_file():
        whatif_df = pd.read_csv(whatif_csv)
        lines.extend(["", "## Device leakage what-if", ""])
        whatif_cols = [
            ("model_id", "Model", "s", 1.0),
            ("ioff_scale", "Ioff scale", ".2f", 1.0),
            ("ccell_min_ff", "Ccell_min (fF)", ".1f", 1.0),
            ("ccell_min_reduction_ff", "ΔCcell_min (fF)", ".1f", 1.0),
        ]
        lines.append(_table(whatif_df, whatif_cols))

    if figures_dir and figures_dir.is_dir():
        lines.extend(["", "## Figures", ""])
        for svg in sorted(figures_dir.glob("*.svg")):
            if svg.is_relative_to(output_path.parent):
                rel = svg.relative_to(output_path.parent)
            else:
                rel = svg
            title = svg.stem.replace("_", " ")
            lines.append(f"### {title}")
            lines.append("")
            lines.append(f"![{title}]({rel})")
            lines.append("")

    lines.extend(
        [
            "## Methodology",
            "",
            "- Retention and read decks reuse vendored pareto and sense-amp lanes.",
            "- Geometric capacitor model: "
            f"Ccell = k·ε₀·α·structure·fpitch² / t_EOT · β with t_EOT = "
            f"{cfg.capacitor_geometry.t_dielectric_nm:.1f} nm.",
            "- See [docs/ccell_metric_spec.md](../docs/ccell_metric_spec.md).",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
