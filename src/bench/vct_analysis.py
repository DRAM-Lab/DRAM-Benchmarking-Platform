"""VCT scaling analysis document generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

VCT_NODES: tuple[str, ...] = ("082", "091", "102", "125")


def _pct_change(new: float, old: float) -> str:
    if old == 0:
        return "—"
    return f"{(new - old) / abs(old) * 100:+.1f}%"


def vct_scaling_frame(df: pd.DataFrame, corner: str = "tt") -> pd.DataFrame:
    """Return sorted VCT node rows for a corner."""
    subset = df.copy()
    if "corner" in subset.columns:
        subset = subset[subset["corner"] == corner]
    vct = subset[subset["architecture"] == "VCT"].copy()
    vct["node"] = vct["model_id"].str.replace("VCT_", "", regex=False)
    return vct[vct["node"].isin(VCT_NODES)].sort_values("node")


def vct_scaling_summary_markdown(df: pd.DataFrame, corner: str = "tt") -> str:
    """Compact VCT scaling summary for embedding in RESULTS.md.

    Args:
        df: Device metrics DataFrame.
        corner: Corner filter.

    Returns:
        Markdown fragment (empty string if no VCT data).
    """
    vct = vct_scaling_frame(df, corner=corner)
    if vct.empty:
        return ""

    lines = [
        "| Node | Ion (A) | Ioff (A) | Ron (Ω) | vsat |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, row in vct.iterrows():
        lines.append(
            f"| {row['node']} | {row['ion_a']:.3e} | {row['ioff_a']:.3e} | "
            f"{row['ron_ohm']:.3e} | {row['vsat']:.0f} |"
        )

    first = vct.iloc[0]
    last = vct.iloc[-1]
    bullets = [
        f"- **082 → 125 Ion:** {_pct_change(last['ion_a'], first['ion_a'])} "
        f"({first['ion_a']:.3e} → {last['ion_a']:.3e} A)",
        f"- **082 → 125 Ioff:** {_pct_change(last['ioff_a'], first['ioff_a'])} "
        f"({first['ioff_a']:.3e} → {last['ioff_a']:.3e} A)",
        f"- **082 → 125 Ron:** {_pct_change(last['ron_ohm'], first['ron_ohm'])} "
        f"({first['ron_ohm']:.3e} → {last['ron_ohm']:.3e} Ω)",
        "- Drive improves with node; Ioff rises — retention vs drive trade-off in the VCT cards.",
        "- Full step-by-step analysis: [vct_scaling_analysis.md](../docs/vct_scaling_analysis.md)",
    ]

    return "\n".join(
        [
            "\n".join(lines),
            "",
            "\n".join(bullets),
        ]
    )


def generate_vct_scaling_analysis(
    metrics_csv: Path,
    output_md: Path,
    corner: str = "tt",
) -> Path:
    """Write VCT scaling trajectory analysis from device metrics CSV.

    Args:
        metrics_csv: Device metrics CSV path.
        output_md: Output markdown path.
        corner: Corner filter.

    Returns:
        Path to written document.
    """
    df = pd.read_csv(metrics_csv)
    vct = vct_scaling_frame(df, corner=corner)
    if vct.empty:
        raise ValueError("No VCT models in metrics CSV")

    lines = [
        "# VCT Scaling Analysis (082 → 125)",
        "",
        f"Auto-generated from `{metrics_csv.name}` @ **{corner}** corner.",
        "",
        "## Node summary",
        "",
        "| Node | Ion (A) | Ioff (A) | Ron (Ω) | vsat (card) | Ion/Cgg (1/s) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in vct.iterrows():
        lines.append(
            f"| {row['node']} | {row['ion_a']:.3e} | {row['ioff_a']:.3e} | "
            f"{row['ron_ohm']:.3e} | {row['vsat']:.0f} | {row.get('ion_per_cgg', float('nan')):.3e} |"
        )

    lines.extend(["", "## Step-to-step trends", ""])
    prev = None
    for _, row in vct.iterrows():
        node = row["node"]
        if prev is None:
            lines.append(f"### VCT_{node} (baseline node in sweep)")
            prev = row
            continue
        lines.append(f"### VCT_{prev['node']} → VCT_{node}")
        lines.append(
            f"- Ion: {_pct_change(row['ion_a'], prev['ion_a'])} "
            f"({prev['ion_a']:.3e} → {row['ion_a']:.3e} A)"
        )
        lines.append(
            f"- Ioff: {_pct_change(row['ioff_a'], prev['ioff_a'])} "
            f"({prev['ioff_a']:.3e} → {row['ioff_a']:.3e} A)"
        )
        lines.append(
            f"- Ron: {_pct_change(row['ron_ohm'], prev['ron_ohm'])} "
            f"({prev['ron_ohm']:.3e} → {row['ron_ohm']:.3e} Ω)"
        )
        lines.append(
            f"- vsat (model card): {_pct_change(row['vsat'], prev['vsat'])} "
            f"({prev['vsat']:.0f} → {row['vsat']:.0f})"
        )
        lines.append("")
        prev = row

    lines.extend(
        [
            "## Observations",
            "",
            "- **Drive (Ion)** improves monotonically from 082 to 125 in the calibrated cards.",
            "- **Ron** decreases with node, consistent with higher vsat on later VCT labels.",
            "- **Ioff** rises with node — retention/leakage trades off against drive in this open model set.",
            "- Saturation in vsat between 102 and 125 suggests diminishing vertical-scaling returns at the card level.",
            "",
            "See `results/figures/vct_scaling.svg` for the corresponding plots.",
        ]
    )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_md
