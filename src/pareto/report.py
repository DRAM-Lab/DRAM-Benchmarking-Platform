"""Markdown RESULTS report for the Pareto roadmap experiment."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pareto.applications import (
    jedec_qualification_table,
    recommend_all_profiles,
    recommend_best_effort_profiles,
    recommendations_to_dataframe,
)
from pareto.config import load_pareto_config
from pareto.pareto import filter_pareto_front
from pareto.simulator_compare import (
    collect_pareto_frames,
    compare_pareto_simulators,
    generate_simulator_figures,
    simulator_backend_summary_markdown,
    simulator_comparison_markdown,
    simulator_figures_markdown,
)
from pareto.vct_analysis import corner_shift_summary, vct_scaling_summary_markdown

_ROADMAP_COLUMNS: list[tuple[str, str, str]] = [
    ("model_id", "Model", "s"),
    ("architecture", "Architecture", "s"),
    ("corner", "Corner", "s"),
    ("ccell_ff", "Ccell (fF)", ".0f"),
    ("t_ret_s", "t_ret (ms)", ".3f"),
    ("t_refresh_s", "t_refresh (ms)", ".3f"),
    ("t_rcd_s", "tRCD (ns)", ".2f"),
    ("t_wr_s", "tWR (ns)", ".2f"),
    ("e_read_j", "E_read (fJ)", ".2f"),
    ("i_leak_a", "I_leak (A)", ".3e"),
    ("i_leak_density_a_m2", "I_leak/area (A/m²)", ".3e"),
    ("source", "Source", "s"),
    ("simulator", "Simulator", "s"),
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


def _format_cell(value: object, fmt: str, *, scale: float = 1.0) -> str:
    """Format one table cell with optional unit scaling."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if fmt == "s":
        return str(value)
    try:
        return format(float(value) * scale, fmt)
    except (TypeError, ValueError):
        return str(value)


def _metrics_table(df: pd.DataFrame) -> str:
    """Render roadmap metrics as markdown."""
    col_spec: list[tuple[str, str, str, float]] = []
    for col, header, fmt in _ROADMAP_COLUMNS:
        scale = 1.0
        if col in ("t_ret_s", "t_refresh_s"):
            scale = 1e3
        elif col in ("t_rcd_s", "t_wr_s"):
            scale = 1e9
        elif col == "e_read_j":
            scale = 1e15
        col_spec.append((col, header, fmt, scale))

    headers = [h for _, h, _, _ in col_spec]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        cells = [_format_cell(row.get(col), fmt, scale=scale) for col, _, fmt, scale in col_spec]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _format_seconds(value: float | None, *, unit: str = "ms") -> str:
    if value is None or pd.isna(value):
        return "—"
    if unit == "ms":
        return f"{value * 1e3:.3f} ms"
    if unit == "ns":
        return f"{value * 1e9:.2f} ns"
    return f"{value:.3e} s"


def _architecture_summary(df: pd.DataFrame, corner: str, ccell_ff: float) -> str:
    """Bullet summary by architecture at reference point."""
    subset = df[(df["corner"] == corner) & (df["ccell_ff"] == ccell_ff)]
    lines: list[str] = []
    for arch in ("BCAT", "VCT", "3D_GAA"):
        group = subset[subset["architecture"] == arch]
        if group.empty:
            continue
        ret_group = group.dropna(subset=["t_ret_s"])
        speed_group = group.dropna(subset=["t_rcd_s"])
        leak_group = group.dropna(subset=["i_leak_a"])

        parts: list[str] = []
        if not ret_group.empty:
            best_ret = ret_group.loc[ret_group["t_ret_s"].idxmax()]
            parts.append(
                f"best retention `{best_ret['model_id']}` "
                f"({_format_seconds(float(best_ret['t_ret_s']))})"
            )
        else:
            parts.append("t_ret — (no retention data)")

        if not speed_group.empty:
            best_speed = speed_group.loc[speed_group["t_rcd_s"].idxmin()]
            parts.append(
                f"fastest tRCD `{best_speed['model_id']}` "
                f"({_format_seconds(float(best_speed['t_rcd_s']), unit='ns')})"
            )
        else:
            parts.append("tRCD — (no native perf data)")

        if not leak_group.empty:
            lowest_leak = leak_group.loc[leak_group["i_leak_a"].idxmin()]
            parts.append(
                f"lowest I_leak `{lowest_leak['model_id']}` "
                f"({float(lowest_leak['i_leak_a']):.2e} A)"
            )

        lines.append(f"- **{arch}:** {'; '.join(parts)}.")
    return "\n".join(lines)


def _ccell_scaling_summary(df: pd.DataFrame, corner: str) -> str:
    """Summarize Ccell sensitivity trends."""
    lines: list[str] = []
    ref = df[df["corner"] == corner]
    for model_id in sorted(ref["model_id"].unique()):
        group = ref[ref["model_id"] == model_id].sort_values("ccell_ff")
        valid = group.dropna(subset=["t_ret_s"])
        if len(valid) < 2:
            continue
        t_min = float(valid.iloc[0]["t_ret_s"]) * 1e3
        t_max = float(valid.iloc[-1]["t_ret_s"]) * 1e3
        lines.append(
            f"- **{model_id}:** t_ret scales {t_min:.3f} → {t_max:.3f} ms "
            f"({valid.iloc[0]['ccell_ff']:.0f} → {valid.iloc[-1]['ccell_ff']:.0f} fF); "
            "retention is **Ccell-linear** under the leakage proxy."
        )
    return "\n".join(lines[:7])


def _executive_summary(
    df: pd.DataFrame,
    ref_corner: str,
    ref_ccell: float,
    recs: list,
    cfg: object,
) -> list[str]:
    """Build data-driven executive summary bullets."""
    ref = df[(df["corner"] == ref_corner) & (df["ccell_ff"] == ref_ccell)]
    sources = sorted(df["source"].dropna().unique())
    source_note = ", ".join(sources) if sources else "unknown"
    simulators = sorted(df.get("simulator", pd.Series(dtype=str)).dropna().unique())
    lines = [
        f"- **Data source:** {source_note}.",
    ]
    if simulators:
        lines.append(f"- **Simulator(s):** {', '.join(simulators)}.")
    if ref["t_ret_s"].isna().all() and ref["t_rcd_s"].notna().any():
        lines.append(
            "- **Note:** native retention metrics are missing (common when ngspice decks "
            "fail or hold measures do not cross); performance rows may use derived fallbacks."
        )
    if not ref.empty and ref["t_ret_s"].notna().any():
        best_ret = ref.loc[ref["t_ret_s"].idxmax()]
        lines.append(
            f"- **Best retention @ {ref_corner}/{ref_ccell:.0f} fF:** "
            f"`{best_ret['model_id']}` ({_format_seconds(float(best_ret['t_ret_s']))})."
        )
        speed = ref.dropna(subset=["t_rcd_s"])
        if not speed.empty:
            fastest = speed.loc[speed["t_rcd_s"].idxmin()]
            lines.append(
                f"- **Fastest tRCD @ reference:** `{fastest['model_id']}` "
                f"({_format_seconds(float(fastest['t_rcd_s']), unit='ns')})."
            )
    for profile_name, target_ms in (
        ("mobile", 32),
        ("datacenter", 64),
        ("edge_iot", 128),
    ):
        rec = next((r for r in recs if r.profile == profile_name), None)
        if rec is not None:
            status = "meets" if rec.meets_target else "exceeds gate but below target"
            lines.append(
                f"- **{profile_name} JEDEC ({target_ms} ms):** `{rec.model_id}` @ "
                f"{rec.ccell_ff:.0f} fF — {_format_seconds(rec.t_ret_s)} ({status})."
            )
        else:
            lines.append(
                f"- **{profile_name} JEDEC ({target_ms} ms):** no qualified architecture "
                f"on native/derived sweep."
            )
    lines.append(
        "- **Ccell scaling** improves ``t_ret`` roughly linearly with capacitance; "
        "larger Ccell is the primary knob to close JEDEC gaps on these open models."
    )
    return lines


def _figure_block(figures_dir: Path | None, stems: list[str]) -> str:
    """Embed markdown figure links."""
    if figures_dir is None:
        return ""
    rel = figures_dir.name
    lines = ["", "## Figures", ""]
    captions = {
        "pareto_retention_trcd_tt": "Pareto front: retention vs tRCD @ TT",
        "pareto_retention_trcd_hot": "Pareto front: retention vs tRCD @ hot (85 °C)",
        "pareto_retention_energy_tt": "Retention vs read energy @ TT",
        "pareto_retention_energy_hot": "Retention vs read energy @ hot",
        "pareto_retention_leak_tt": "Retention vs standby leakage @ TT",
        "pareto_retention_leak_hot": "Retention vs standby leakage @ hot",
        "architecture_comparison": "Architecture comparison (best t_ret and tRCD per family)",
        "corner_temperature_shift": "TT → hot retention shift by model",
        "ccell_pareto_overlay": "Ccell sweep overlay on retention–tRCD plane",
        "vct_pareto_trajectory": "VCT 082→125 Pareto trajectory",
        "vct_multimetric_scaling": "VCT multimetric node scaling",
        "vct_trajectory_tt": "VCT scaling animation @ TT",
        "vct_trajectory_hot": "VCT scaling animation @ hot",
    }
    for stem in stems:
        svg = figures_dir / f"{stem}.svg"
        gif = figures_dir / f"{stem}.gif"
        if svg.is_file():
            cap = captions.get(stem, stem)
            lines.append(f"### {cap}")
            lines.append("")
            lines.append(f"![{cap}]({rel}/{stem}.svg)")
            lines.append("")
        elif gif.is_file():
            cap = captions.get(stem, stem)
            lines.append(f"### {cap}")
            lines.append("")
            lines.append(f"![{cap}]({rel}/{stem}.gif)")
            lines.append("")
    return "\n".join(lines)


def generate_report(
    roadmap_csv: Path,
    output_md: Path,
    *,
    reference_corner: str | None = None,
    reference_ccell_ff: float | None = None,
    figures_dir: Path | None = None,
    project_root: Path | None = None,
    results_root: Path | None = None,
) -> Path:
    """Write comprehensive Pareto roadmap RESULTS.md."""
    cfg = load_pareto_config()
    ref_corner = reference_corner or cfg.reference_corner
    ref_ccell = reference_ccell_ff if reference_ccell_ff is not None else cfg.reference_ccell_ff
    root = project_root or output_md.parent.parent
    compare_root = results_root or roadmap_csv.parent

    df = pd.read_csv(roadmap_csv)
    sim_frames = collect_pareto_frames(compare_root)
    sim_compare_md = ""
    sim_summary_md = simulator_backend_summary_markdown(sim_frames)
    if len(sim_frames) >= 2:
        ref_backend = "spectre" if "spectre" in sim_frames else sorted(sim_frames)[0]
        _, diff = compare_pareto_simulators(sim_frames, reference=ref_backend)
        rel_md = simulator_comparison_markdown(
            diff,
            reference=ref_backend,
            ref_corner=ref_corner,
            ref_ccell=ref_ccell,
        )
        sim_fig_md = ""
        if figures_dir is not None:
            generate_simulator_figures(
                sim_frames,
                figures_dir,
                reference=ref_backend,
                ref_corner=ref_corner,
                ref_ccell=ref_ccell,
            )
            sim_fig_md = simulator_figures_markdown(figures_dir)
        sim_compare_md = "\n".join(
            part for part in (sim_summary_md, rel_md, sim_fig_md) if part
        )
    ref_subset = df[(df["corner"] == ref_corner) & (df["ccell_ff"] == ref_ccell)].copy()
    hot_subset = df[(df["corner"] == "hot") & (df["ccell_ff"] == ref_ccell)].copy()

    front_tt = filter_pareto_front(
        ref_subset,
        objectives=("t_ret_s", "t_rcd_s", "e_read_j", "i_leak_a"),
        by=("corner",),
    )
    front_hot = filter_pareto_front(
        hot_subset,
        objectives=("t_ret_s", "t_rcd_s", "e_read_j", "i_leak_a"),
        by=("corner",),
    ) if not hot_subset.empty else hot_subset

    recs = recommend_all_profiles(df, cfg, ccell_ff=ref_ccell)
    rec_df = recommendations_to_dataframe(recs)
    fallback_recs = recommend_best_effort_profiles(df, cfg, ccell_ff=ref_ccell)
    fallback_df = recommendations_to_dataframe(fallback_recs)
    jedec_df = jedec_qualification_table(df, cfg, ccell_ff=ref_ccell)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    corners_present = ", ".join(sorted(df["corner"].unique()))
    models_present = df["model_id"].nunique()

    lines = [
        "# OpenDRAM Retention–Performance Pareto Roadmap — RESULTS",
        "",
        f"Generated {timestamp} from `{roadmap_csv.name}`.",
        "",
        "## Executive summary",
        "",
        f"- **Models:** {models_present} access cards across **{corners_present}** corners.",
        f"- **Reference point:** {ref_corner} @ Ccell = {ref_ccell:.0f} fF.",
        * _executive_summary(df, ref_corner, ref_ccell, recs, cfg),
        "- Product-class JEDEC retention targets (32–128 ms @ specified corner) are evaluated "
        "on native SPICE ``t_ret`` (50 mV loss) with Ccell sweep qualification.",
        "",
        "## Metric definitions",
        "",
        "| Metric | Definition |",
        "| --- | --- |",
        f"| t_ret | Time to ΔV_cell = {cfg.retention.delta_v_v * 1e3:.0f} mV loss (hold extrapolation) |",
        f"| t_refresh | Simplified refresh interval ≈ t_ret / ln(2) |",
        f"| tRCD | WL rise → BL +{cfg.performance.bl_signal_v * 1e3:.0f} mV differential |",
        f"| tWR | Write until \\|Vcell − Vtarget\\| < {cfg.performance.write_tol_v * 1e3:.0f} mV |",
        "| E_read | Integrated BL energy during read (proxy: Q_read·Vdd in derive mode) |",
        "| I_leak | Standby hold leakage; density normalized by fpitch² |",
        "",
        f"## Roadmap table @ {ref_corner}, Ccell = {ref_ccell:.0f} fF",
        "",
        _metrics_table(ref_subset.sort_values("t_ret_s", ascending=False)),
        "",
        "## Pareto fronts",
        "",
        f"### TT @ {ref_ccell:.0f} fF",
        "",
        _metrics_table(front_tt.sort_values("t_ret_s", ascending=False)),
        "",
    ]

    if not front_hot.empty:
        lines.extend(
            [
                f"### Hot (85 °C) @ {ref_ccell:.0f} fF",
                "",
                _metrics_table(front_hot.sort_values("t_ret_s", ascending=False)),
                "",
            ]
        )

    lines.extend(
        [
            "## Architecture comparison",
            "",
            _architecture_summary(df, ref_corner, ref_ccell),
            "",
            "## VCT scaling (082 → 125)",
            "",
            vct_scaling_summary_markdown(df, corner=ref_corner, ccell_ff=ref_ccell) or "_No VCT data._",
            "",
            "## Temperature corner sensitivity (TT → hot)",
            "",
            corner_shift_summary(df, ccell_ff=ref_ccell) or "_No hot-corner data._",
            "",
            "## Ccell scaling sensitivity",
            "",
            _ccell_scaling_summary(df, ref_corner) or "_No Ccell sweep._",
            "",
            "## Application recommendations (JEDEC gate)",
            "",
            "Strict qualification requires ``t_ret ≥ target``; Ccell sweep searches larger "
            "capacitance first when reference Ccell fails.",
            "",
            "| Segment | Model | t_ret | Target | Gap | Meets target | tRCD | E_read | I_leak |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    if rec_df.empty:
        lines.append("| — | *No JEDEC-qualified model* | — | — | — | — | — | — | — |")
    else:
        for _, row in rec_df.iterrows():
            gap = row.get("retention_gap_s")
            gap_str = _format_seconds(gap) if pd.notna(gap) else "—"
            e_read = row.get("e_read_j")
            e_str = f"{e_read * 1e15:.2f} fJ" if pd.notna(e_read) else "—"
            i_leak = row.get("i_leak_a")
            i_str = f"{i_leak:.2e} A" if pd.notna(i_leak) else "—"
            meets = "yes" if row.get("meets_target") else "no"
            lines.append(
                f"| {row['profile']} | {row['model_id']} | "
                f"{_format_seconds(row.get('t_ret_s'))} | "
                f"{_format_seconds(row.get('target_t_ret_s'))} | {gap_str} | {meets} | "
                f"{_format_seconds(row.get('t_rcd_s'), unit='ns')} | {e_str} | {i_str} |"
            )

    lines.extend(
        [
            "",
            "### Best-effort fallback (open-model proxy)",
            "",
            "| Segment | Model | t_ret | Target | Gap | tRCD |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    if fallback_df.empty:
        lines.append("| — | — | — | — | — | — |")
    else:
        for _, row in fallback_df.iterrows():
            gap_str = _format_seconds(row.get("retention_gap_s")) if pd.notna(row.get("retention_gap_s")) else "—"
            lines.append(
                f"| {row['profile']} | {row['model_id']} | "
                f"{_format_seconds(row.get('t_ret_s'))} | "
                f"{_format_seconds(row.get('target_t_ret_s'))} | {gap_str} | "
                f"{_format_seconds(row.get('t_rcd_s'), unit='ns')} |"
            )

    if not jedec_df.empty:
        lines.extend(["", "## JEDEC qualification matrix @ reference Ccell", ""])
        qual_cols = [
            "profile",
            "model_id",
            "t_ret_ms",
            "t_refresh_ms",
            "jedec_target_ms",
            "meets_t_ret",
            "meets_t_refresh",
            "source",
        ]
        lines.append("| " + " | ".join(qual_cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(qual_cols)) + " |")
        for _, row in jedec_df.iterrows():
            cells = [str(row[c]) for c in qual_cols]
            lines.append("| " + " | ".join(cells) + " |")

    if sim_compare_md:
        lines.extend(["", sim_compare_md, ""])

    figure_stems = [
        "pareto_retention_trcd_tt",
        "pareto_retention_trcd_hot",
        "pareto_retention_energy_tt",
        "pareto_retention_energy_hot",
        "pareto_retention_leak_tt",
        "pareto_retention_leak_hot",
        "architecture_comparison",
        "corner_temperature_shift",
        "ccell_pareto_overlay",
        "vct_pareto_trajectory",
        "vct_multimetric_scaling",
        "vct_trajectory_tt",
        "vct_trajectory_hot",
        "ccell_sensitivity_BCAT_125",
        "ccell_sensitivity_VCT_125",
        "ccell_sensitivity_3D_gaa_Si",
    ]
    lines.append(_figure_block(figures_dir, figure_stems))

    lines.extend(
        [
            "## Provenance",
            "",
            f"- Roadmap CSV: `{roadmap_csv}`",
            f"- Config: `bench/pareto_roadmap/configs/pareto.yaml`",
            f"- Git revision (experiment): `{_git_revision(root)}`",
            "",
            "## Notes and limitations",
            "",
            "- Derived points reuse device-lane 1T1C hold leakage when native "
            "Pareto SPICE sims are not run.",
            "- Multi-simulator verification (Spectre / HSPICE / ngspice) uses per-backend "
            "result trees under `results/{spectre,hspice,ngspice}/` with Spectre as reference.",
            "- Ccell = 15 fF and 50 fF are **linearly interpolated** from measured 10/20/30 fF sweeps.",
            "- Hot corner (85 °C) requires device-benchmark results under `results/hot/` or "
            "`*_all_corners.csv`.",
            "- Area normalization uses model-card `fpitch` as a density proxy, not layout-accurate.",
            "- Results are technology-assumption-driven open models — not foundry sign-off.",
        ]
    )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_md
