"""VCT scaling trajectory analysis for Pareto roadmap results."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

VCT_NODES: tuple[str, ...] = ("082", "091", "102", "125")


def _pct_change(new: float, old: float) -> str:
    if old == 0:
        return "—"
    return f"{(new - old) / abs(old) * 100:+.1f}%"


def vct_pareto_frame(df: pd.DataFrame, corner: str = "tt", ccell_ff: float = 20.0) -> pd.DataFrame:
    """Return sorted VCT rows for Pareto trajectory analysis."""
    subset = df[
        (df["architecture"] == "VCT")
        & (df["corner"] == corner)
        & (df["ccell_ff"] == ccell_ff)
    ].copy()
    subset["node"] = subset["model_id"].str.replace("VCT_", "", regex=False)
    return subset[subset["node"].isin(VCT_NODES)].sort_values("node")


def vct_scaling_summary_markdown(
    df: pd.DataFrame,
    corner: str = "tt",
    ccell_ff: float = 20.0,
) -> str:
    """Compact VCT Pareto scaling summary for RESULTS.md."""
    vct = vct_pareto_frame(df, corner=corner, ccell_ff=ccell_ff)
    if vct.empty:
        return ""

    lines = [
        "| Node | t_ret (ms) | tRCD (ns) | E_read (fJ) | I_leak (A) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, row in vct.iterrows():
        t_ret = row.get("t_ret_s")
        t_rcd = row.get("t_rcd_s")
        e_read = row.get("e_read_j")
        i_leak = row.get("i_leak_a")
        lines.append(
            f"| {row['node']} | "
            f"{t_ret * 1e3:.3f} | "
            f"{t_rcd * 1e9:.2f} | "
            f"{e_read * 1e15:.2f} | "
            f"{i_leak:.2e} |"
        )

    first = vct.iloc[0]
    last = vct.iloc[-1]
    bullets = [
        f"- **082 → 125 t_ret:** {_pct_change(last['t_ret_s'], first['t_ret_s'])} "
        f"({first['t_ret_s'] * 1e3:.3f} → {last['t_ret_s'] * 1e3:.3f} ms)",
        f"- **082 → 125 tRCD:** {_pct_change(last['t_rcd_s'], first['t_rcd_s'])} "
        f"({first['t_rcd_s'] * 1e9:.2f} → {last['t_rcd_s'] * 1e9:.2f} ns)",
        f"- **082 → 125 I_leak:** {_pct_change(last['i_leak_a'], first['i_leak_a'])} "
        f"({first['i_leak_a']:.2e} → {last['i_leak_a']:.2e} A)",
        "- VCT node scaling moves the Pareto point modestly: tRCD and t_ret change by "
        "only a few percent in this open-model proxy, while architecture choice "
        "(BCAT vs VCT vs 3D GAA) dominates the retention–performance gap.",
    ]
    return "\n".join(lines + [""] + bullets)


def corner_shift_summary(
    df: pd.DataFrame,
    ccell_ff: float = 20.0,
) -> str:
    """Summarize tt → hot shifts for all models."""
    lines: list[str] = []
    ref = df[df["ccell_ff"] == ccell_ff]
    for model_id in sorted(ref["model_id"].unique()):
        tt = ref[(ref["model_id"] == model_id) & (ref["corner"] == "tt")]
        hot = ref[(ref["model_id"] == model_id) & (ref["corner"] == "hot")]
        if tt.empty or hot.empty:
            continue
        t_ret_tt = float(tt.iloc[0]["t_ret_s"])
        t_ret_hot = float(hot.iloc[0]["t_ret_s"])
        t_rcd_tt = float(tt.iloc[0]["t_rcd_s"])
        t_rcd_hot = float(hot.iloc[0]["t_rcd_s"])
        lines.append(
            f"- **{model_id}:** t_ret {_pct_change(t_ret_hot, t_ret_tt)} "
            f"({t_ret_tt * 1e3:.3f} → {t_ret_hot * 1e3:.3f} ms); "
            f"tRCD {_pct_change(t_rcd_hot, t_rcd_tt)} "
            f"({t_rcd_tt * 1e9:.2f} → {t_rcd_hot * 1e9:.2f} ns)"
        )
    return "\n".join(lines)


def generate_vct_scaling_doc(
    roadmap_csv: Path,
    output_md: Path,
    *,
    corner: str = "tt",
    ccell_ff: float = 20.0,
) -> Path:
    """Write standalone VCT Pareto scaling document."""
    df = pd.read_csv(roadmap_csv)
    body = vct_scaling_summary_markdown(df, corner=corner, ccell_ff=ccell_ff)
    lines = [
        "# VCT Pareto Scaling (082 → 125)",
        "",
        f"Derived from `{roadmap_csv.name}` @ **{corner}**, Ccell = {ccell_ff:.0f} fF.",
        "",
        body or "_No VCT data._",
        "",
        "See `results/figures/vct_pareto_trajectory.svg` and "
        "`results/figures/vct_trajectory.gif` for visual trajectory.",
    ]
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_md
