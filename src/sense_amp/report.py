"""Markdown report generation for read-path signal and SA requirement sweeps."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from sense_amp.extract.transient import dv_key_for_time_ns
from sense_amp.paths import load_read_path_config
from sense_amp.plots import generate_figures
from sense_amp.simulator import resolve_backend

REF_CCELL_FF = 20.0
REF_VBL_FRAC = 0.5
DEFAULT_SAMPLE_NS = (5.0, 8.0, 10.0, 12.0, 15.0)


def generate_deck_only_report(
    output_path: Path,
    *,
    corner: str = "tt",
    deck_count: int | None = None,
) -> Path:
    """Write RESULTS.md when only SPICE decks were generated (no ΔV_BL extraction)."""
    cfg = load_read_path_config()
    sa = cfg["sense_amp"]
    deck_note = f"{deck_count} decks" if deck_count is not None else "decks"
    lines = [
        "# Read-Path Signal & SA Requirement Sweep",
        "",
        _scope_section(),
        "",
        "## Run status",
        "",
        f"**Mode:** deck generation only ({deck_note} under `decks/{corner}/`)  ",
        f"**Corner:** {corner}  ",
        "**ΔV_BL extraction:** not run — Spectre or HSPICE required for transient read-path SPICE",
        "",
        "## What you can do next",
        "",
        "1. Run with Spectre/HSPICE: `dram-sense-amp run --all --corner "
        f"{corner} --output {output_path.parent}`",
        "2. Re-run platform lane: `dram-bench run --suite sense_amp --output "
        f"{output_path.parent}`",
        "3. Until signal CSVs exist, the **ccell** lane uses analytic read fallback "
        "(see `ccell/RESULTS.md`).",
        "",
        _behavioral_sa_section(sa),
        "",
        _csv_guide_section(has_signal=False),
        "",
        "---",
        "*Deck-only report — no `read_signal_*.csv` present.*",
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_report(
    output_path: Path,
    *,
    signal_df: pd.DataFrame,
    codesign_df: pd.DataFrame | None = None,
    spec_df: pd.DataFrame | None = None,
    coupling_margin_df: pd.DataFrame | None = None,
    corner: str = "tt",
    figures_dir: Path | None = None,
) -> Path:
    """Write an analysis-first markdown summary with tables and embedded figures."""
    cfg = load_read_path_config()
    sa_cfg = cfg["sense_amp"]
    sample_times = [float(t) for t in cfg["read_timing"].get("sample_times_ns", DEFAULT_SAMPLE_NS)]
    target_yield = float(sa_cfg.get("target_yield", 0.999))

    fig_dir = figures_dir or (output_path.parent / "figures")
    figure_paths = generate_figures(
        output_path.parent,
        signal_df=signal_df,
        codesign_df=codesign_df,
        coupling_margin_df=coupling_margin_df,
    )

    rel_fig_dir = fig_dir.name
    fig_blocks = "\n\n".join(
        f"### {path.stem.replace('_', ' ').title()}\n\n"
        f"![{path.stem}]({rel_fig_dir}/{path.name})"
        for path in figure_paths
    )

    try:
        backend = resolve_backend().value
    except RuntimeError:
        backend = "unknown"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ref_signal = _reference_signal_slice(signal_df)
    signal_summary = _build_signal_summary_table(ref_signal, sample_times_ns=sample_times)

    lines = [
        "# Read-Path Signal & SA Requirement Sweep",
        "",
        f"**Generated:** {timestamp}  ",
        f"**Corner:** {corner}  ",
        f"**Simulator:** {backend}  ",
        f"**Signal rows:** {len(signal_df)}  ",
        f"**Models:** {signal_df['model_id'].nunique() if not signal_df.empty else 0}",
        "",
        _scope_section(),
        "",
        "## Executive summary",
        "",
        _executive_summary(
            signal_summary,
            spec_df,
            codesign_df,
            target_yield=target_yield,
            ref_ccell_ff=REF_CCELL_FF,
        ),
        "",
        _behavioral_sa_section(sa_cfg),
        "",
        "## Read signal @ reference point",
        "",
        f"Reference: **Ccell = {REF_CCELL_FF:.0f} fF**, **VBL_pre = {REF_VBL_FRAC:.0%} × Vdd** "
        "(compare access nodes at equal array loading).",
        "",
        "|ΔV_BL| is the absolute differential BL voltage sampled from SPICE "
        "(access device + lumped BL RC + cell cap).",
        "",
        signal_summary,
        "",
    ]

    if spec_df is not None and not spec_df.empty:
        lines.extend(
            [
                "## Per-node SA requirements (derived, not sized)",
                "",
                "These rows answer: *what behavioral SA spec closes read at the reference point?* "
                "They are **requirements**, not transistor W/L or a benchmark score for a physical SA.",
                "",
                _spec_interpretation_table(spec_df),
                "",
                _df_to_markdown(spec_df),
                "",
            ]
        )

    if codesign_df is not None and not codesign_df.empty:
        passing = codesign_df[codesign_df["passes_target"]]
        lines.extend(
            [
                "## Co-design sweep (yield proxy)",
                "",
                f"Points meeting {target_yield:.1%} analytic yield: "
                f"**{len(passing)} / {len(codesign_df)}** across "
                "G × σ_os × t_en × model.",
                "",
                "Sample of passing combinations (earliest t_en per model preferred):",
                "",
                _df_to_markdown(
                    passing.sort_values(["model_id", "t_en_ns", "sigma_os_mv"]).head(24)
                ),
                "",
            ]
        )

    if coupling_margin_df is not None and not coupling_margin_df.empty:
        lines.extend(
            [
                "## BL–BL coupling margin loss",
                "",
                "Victim read with adjacent aggressor BL activity vs isolated column.",
                "",
                _df_to_markdown(coupling_margin_df),
                "",
            ]
        )

    lines.extend(
        [
            _csv_guide_section(has_signal=True),
            "",
        ]
    )

    if fig_blocks:
        lines.extend(["## Figures", "", fig_blocks, ""])

    lines.extend(
        [
            "## Artifact index",
            "",
            "| File | Contents |",
            "|------|----------|",
            f"| `read_signal_{corner}.csv` | ΔV_BL samples: model × Ccell × VBL_pre |",
            "| `codesign_sweep.csv` | G × σ_os × t_en yield proxy per model |",
            "| `sa_spec_per_node.csv` | Min G, max σ_os, earliest t_en @ reference Ccell |",
            "| `coupling_margin.csv` | ΔV loss vs k_couple (if coupling decks ran) |",
            f"| `{rel_fig_dir}/` | Summary SVG plots |",
            "",
            "---",
            "*Produced by `dram-sense-amp` / `dram-bench run --suite sense_amp`*",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _scope_section() -> str:
    return """## Scope (read this first)

| Measured in SPICE | Derived via behavioral SA sweep |
|-------------------|----------------------------------|
| ΔV_BL(t) on the read column | Min gain **G**, max offset **σ_os**, earliest **t_en** |
| Access device from OpenDRAM cards (`l`, `nfin`) | 99.9% yield **proxy** (not foundry MC) |
| Ccell, BL RC (pitch-scaled), WL / precharge timing | Input-referred read **budget** per model |

**Not in scope:** sense-amplifier transistor netlists, W/L sizing, layout mismatch, or SA bench scores.
The lane benchmarks **bitline signal development** and maps it to **SA specification tables** for co-design."""


def _behavioral_sa_section(sa_cfg: dict) -> str:
    gains = sa_cfg.get("gain_sweep", [sa_cfg.get("default_gain", 10.0)])
    sigmas = sa_cfg.get("sigma_os_mv", [10.0])
    return (
        "## Behavioral SA assumptions\n\n"
        f"| Parameter | Value |\n"
        f"|-----------|-------|\n"
        f"| Gain sweep G | {', '.join(str(g) for g in gains)} |\n"
        f"| Offset tiers σ_os | {', '.join(str(s) for s in sigmas)} mV |\n"
        f"| Output margin m_min | {sa_cfg.get('m_min_mv', 50.0)} mV |\n"
        f"| Target yield proxy | {sa_cfg.get('target_yield', 0.999):.1%} |\n"
        f"| Margin model | M = G·|ΔV_BL| − |V_os|; pass if M > m_min |"
    )


def _reference_signal_slice(signal_df: pd.DataFrame) -> pd.DataFrame:
    if signal_df.empty:
        return signal_df
    ref = signal_df[
        (signal_df["ccell_ff"] == REF_CCELL_FF)
        & (signal_df["vbl_pre_fraction"] == REF_VBL_FRAC)
    ]
    if ref.empty:
        return signal_df.groupby("model_id", as_index=False).first()
    return ref.sort_values("model_id")


def _build_signal_summary_table(
    ref_df: pd.DataFrame,
    *,
    sample_times_ns: list[float],
) -> str:
    if ref_df.empty:
        return "_No read signal data._"

    rows: list[dict[str, object]] = []
    for _, row in ref_df.iterrows():
        entry: dict[str, object] = {"model_id": row["model_id"]}
        for t_ns in sample_times_ns:
            key = dv_key_for_time_ns(t_ns)
            val = row.get(key)
            if pd.notna(val):
                entry[f"|ΔV|@{int(t_ns)}ns_mV"] = abs(float(val)) * 1000.0
        rows.append(entry)

    summary = pd.DataFrame(rows)
    if f"|ΔV|@{int(sample_times_ns[-1])}ns_mV" in summary.columns:
        sort_col = f"|ΔV|@{int(sample_times_ns[-1])}ns_mV"
        summary = summary.sort_values(sort_col, ascending=False)
    return _df_to_markdown(summary)


def _executive_summary(
    signal_table_md: str,
    spec_df: pd.DataFrame | None,
    codesign_df: pd.DataFrame | None,
    *,
    target_yield: float,
    ref_ccell_ff: float,
) -> str:
    bullets: list[str] = []

    if spec_df is not None and not spec_df.empty:
        passed = spec_df[spec_df["status"] == "PASS"]
        failed = spec_df[spec_df["status"] != "PASS"]
        bullets.append(
            f"- **SA closure @ {ref_ccell_ff:.0f} fF:** {len(passed)} / {len(spec_df)} "
            "access models meet the behavioral yield proxy at the reference point."
        )
        if not passed.empty and "min_delta_v_bl_mv" in passed.columns:
            best = passed.loc[passed["min_delta_v_bl_mv"].idxmin()]
            worst = passed.loc[passed["min_delta_v_bl_mv"].idxmax()]
            bullets.append(
                f"- **Tightest read budget:** `{worst['model_id']}` needs "
                f"≥ {worst['min_delta_v_bl_mv']:.1f} mV input-referred |ΔV_BL|."
            )
            bullets.append(
                f"- **Most margin:** `{best['model_id']}` closes with "
                f"≥ {best['min_delta_v_bl_mv']:.1f} mV input-referred |ΔV_BL|."
            )
        if not failed.empty:
            bullets.append(
                f"- **No closure under swept tiers:** {', '.join(failed['model_id'].astype(str))} "
                f"(see SA spec table — may need stronger G, lower σ_os, or later t_en)."
            )

    if codesign_df is not None and not codesign_df.empty:
        rate = codesign_df["passes_target"].mean()
        bullets.append(
            f"- **Co-design pass rate:** {rate:.1%} of G×σ_os×t_en points exceed "
            f"{target_yield:.1%} yield proxy."
        )

    bullets.append(
        "- **Downstream:** `ccell` consumes `read_signal_*.csv` when present; "
        "otherwise analytic read fallback."
    )

    if signal_table_md.startswith("_No"):
        bullets.insert(0, "- **Read signal:** no ΔV_BL CSV — deck-only or failed extraction.")

    return "\n".join(bullets) if bullets else "_See tables below._"


def _spec_interpretation_table(spec_df: pd.DataFrame) -> str:
    if spec_df.empty:
        return ""
    rows = []
    for _, row in spec_df.iterrows():
        if row.get("status") == "PASS":
            interp = (
                f"Sense by **{row.get('earliest_t_en_ns', '?'):g} ns** with "
                f"G ≥ **{row.get('min_gain', '?'):g}**, σ_os ≤ **{row.get('max_sigma_os_mv', '?'):g} mV**"
            )
        else:
            interp = "No tier in sweep meets target — weaker signal or tighter SA needed"
        rows.append({"model_id": row["model_id"], "status": row.get("status"), "read_guidance": interp})
    return _df_to_markdown(pd.DataFrame(rows))


def _csv_guide_section(*, has_signal: bool) -> str:
    lines = [
        "## How to analyze the CSVs",
        "",
        "### `read_signal_<corner>.csv`",
        "",
        "| Column | Meaning |",
        "|--------|---------|",
        "| `model_id` | OpenDRAM access card |",
        "| `ccell_ff` | Cell capacitance (fF) |",
        "| `vbl_pre_fraction` | BL precharge as fraction of Vdd |",
        "| `dv_<t>ns` | |ΔV_BL| at sample time (V) — **primary SPICE output** |",
        "",
        "### `sa_spec_per_node.csv`",
        "",
        "| Column | Meaning |",
        "|--------|---------|",
        "| `min_gain` | Smallest G in sweep that passes yield proxy |",
        "| `max_sigma_os_mv` | Largest σ_os tier that still passes |",
        "| `earliest_t_en_ns` | Earliest sense-enable time that passes |",
        "| `min_delta_v_bl_mv` | Input-referred signal budget for target yield |",
        "| `status` | PASS if any sweep point meets target |",
        "",
        "### `codesign_sweep.csv`",
        "",
        "Full factorial of model × G × σ_os × t_en with `yield_fraction` and `passes_target`.",
        "Use this to explore timing vs offset tradeoffs beyond the per-node summary.",
    ]
    if not has_signal:
        lines.extend(
            [
                "",
                "_Signal CSV not generated in this run — tables above apply after SPICE extraction._",
            ]
        )
    return "\n".join(lines)


def _df_to_markdown(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavored markdown table."""
    if df.empty:
        return "_No data._"
    headers = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    body = []
    for row in df.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, float):
                if pd.isna(value):
                    cells.append("—")
                else:
                    cells.append(f"{value:.4g}")
            else:
                cells.append(str(value))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([headers, sep, *body])
