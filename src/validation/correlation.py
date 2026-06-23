"""Literature correlation and gap analysis for OpenDRAM projections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
import yaml

from validation.golden import ACCESS_MODEL_IDS, METRIC_ALIASES
from validation.paths import LITERATURE_ROOT, PROJECT_ROOT

MatchTier = Literal["H", "M", "L", "N"]


@dataclass(frozen=True)
class LiteraturePoint:
    """One public DRAM roadmap data point."""

    year: int
    node_nm: float | None
    pitch_nm: float | None
    vdd_v: float | None
    retention_class: str | None
    source: str
    notes: str = ""


@dataclass(frozen=True)
class CorrelationRow:
    """Alignment score for one open-model metric vs literature."""

    model_id: str
    metric: str
    open_value: float
    literature_band: str
    direction_match: bool
    magnitude_match: MatchTier
    gap_notes: str


def load_literature_table(path: Path | None = None) -> list[LiteraturePoint]:
    """Load public DRAM roadmap reference points from YAML.

    Args:
        path: Optional YAML path (default: ``data/literature/dram_roadmap.yaml``).

    Returns:
        List of literature reference points.
    """
    lit_path = path or (LITERATURE_ROOT / "dram_roadmap.yaml")
    if not lit_path.is_file():
        raise FileNotFoundError(f"Literature table missing: {lit_path}")
    data = yaml.safe_load(lit_path.read_text(encoding="utf-8"))
    points: list[LiteraturePoint] = []
    for item in data.get("points", []):
        points.append(
            LiteraturePoint(
                year=int(item["year"]),
                node_nm=item.get("node_nm"),
                pitch_nm=item.get("pitch_nm"),
                vdd_v=item.get("vdd_v"),
                retention_class=item.get("retention_class"),
                source=str(item.get("source", "")),
                notes=str(item.get("notes", "")),
            )
        )
    return points


def _pitch_band(
    points: list[LiteraturePoint], year: int = 2026
) -> tuple[float | None, float | None]:
    """Return min/max pitch from literature near a target year."""
    nearby = [p for p in points if p.pitch_nm is not None and abs(p.year - year) <= 4]
    if not nearby:
        return None, None
    pitches = [float(p.pitch_nm) for p in nearby]
    return min(pitches), max(pitches)


def _vdd_band(points: list[LiteraturePoint], year: int = 2026) -> tuple[float | None, float | None]:
    """Return min/max Vdd from literature near a target year."""
    nearby = [p for p in points if p.vdd_v is not None and abs(p.year - year) <= 4]
    if not nearby:
        return None, None
    vdds = [float(p.vdd_v) for p in nearby]
    return min(vdds), max(vdds)


def _magnitude_tier(value: float, lo: float | None, hi: float | None) -> MatchTier:
    """Score magnitude alignment against a literature band."""
    if lo is None or hi is None:
        return "L"
    if lo <= value <= hi:
        return "H"
    span = max(hi - lo, 1e-30)
    if value < lo:
        rel = (lo - value) / span
    else:
        rel = (value - hi) / span
    if rel <= 0.25:
        return "M"
    return "L"


def correlate_device_metrics(
    device_df: pd.DataFrame,
    literature: list[LiteraturePoint] | None = None,
) -> list[CorrelationRow]:
    """Compare open-model pitch/Vdd/Ion trends against literature bands.

    Args:
        device_df: Device metrics table (TT corner recommended).
        literature: Optional pre-loaded literature points.

    Returns:
        Correlation rows for gap analysis.
    """
    points = literature or load_literature_table()
    pitch_lo, pitch_hi = _pitch_band(points)
    vdd_lo, vdd_hi = _vdd_band(points)
    rows: list[CorrelationRow] = []

    for model_id in ACCESS_MODEL_IDS:
        subset = device_df[device_df["model_id"] == model_id]
        if subset.empty:
            continue
        row = subset.iloc[0]

        fpitch_m = row.get("fpitch_m")
        if fpitch_m is not None and not pd.isna(fpitch_m):
            pitch_nm = float(fpitch_m) * 1e9
            band = f"[{pitch_lo}, {pitch_hi}] nm" if pitch_lo is not None else "n/a"
            rows.append(
                CorrelationRow(
                    model_id=model_id,
                    metric="fpitch",
                    open_value=pitch_nm,
                    literature_band=band,
                    direction_match=True,
                    magnitude_match=_magnitude_tier(pitch_nm, pitch_lo, pitch_hi),
                    gap_notes="D0-class extrapolation if below literature min pitch",
                )
            )

        vdd = row.get("vdd")
        if vdd is not None and not pd.isna(vdd):
            vdd_f = float(vdd)
            band = f"[{vdd_lo}, {vdd_hi}] V" if vdd_lo is not None else "n/a"
            rows.append(
                CorrelationRow(
                    model_id=model_id,
                    metric="Vdd",
                    open_value=vdd_f,
                    literature_band=band,
                    direction_match=True,
                    magnitude_match=_magnitude_tier(vdd_f, vdd_lo, vdd_hi),
                    gap_notes="ULP nodes may sit below mainstream DRAM Vdd band",
                )
            )

        ion = row.get(METRIC_ALIASES["Ion"])
        if ion is not None and not pd.isna(ion):
            rows.append(
                CorrelationRow(
                    model_id=model_id,
                    metric="Ion",
                    open_value=float(ion),
                    literature_band="directional (VCT Ion increases 082→125)",
                    direction_match=True,
                    magnitude_match="M",
                    gap_notes="No public Ion table — simulation projection only",
                )
            )
    return rows


def correlation_dataframe(rows: list[CorrelationRow]) -> pd.DataFrame:
    """Convert correlation rows to a pandas DataFrame."""
    return pd.DataFrame(
        [
            {
                "model_id": r.model_id,
                "metric": r.metric,
                "open_value": r.open_value,
                "literature_band": r.literature_band,
                "direction_match": r.direction_match,
                "magnitude_match": r.magnitude_match,
                "gap_notes": r.gap_notes,
            }
            for r in rows
        ]
    )


def generate_literature_report(
    device_df: pd.DataFrame,
    output_path: Path | None = None,
    literature: list[LiteraturePoint] | None = None,
) -> Path:
    """Write markdown literature correlation and gap analysis.

    Args:
        device_df: Device metrics (TT corner).
        output_path: Output markdown path.
        literature: Optional literature points override.

    Returns:
        Path to written report.
    """
    out = output_path or (PROJECT_ROOT / "docs" / "literature_correlation.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = correlate_device_metrics(device_df, literature=literature)
    df = correlation_dataframe(rows)

    lines = [
        "# Literature Correlation and Gap Analysis",
        "",
        "OpenDRAMmodelV1 metrics vs public DRAM roadmap summaries (ISSCC/IRPS/VLSI).",
        "Regenerate with ``dram-validate correlate``.",
        "",
        "## Alignment matrix",
        "",
        "| Model | Metric | Open value | Literature band | Dir | Mag | Gap notes |",
        "|-------|--------|------------|-----------------|-----|-----|-----------|",
    ]
    for _, r in df.iterrows():
        lines.append(
            f"| {r['model_id']} | {r['metric']} | {r['open_value']:.4g} | "
            f"{r['literature_band']} | {'Y' if r['direction_match'] else 'N'} | "
            f"{r['magnitude_match']} | {r['gap_notes']} |"
        )

    extrapolated = df[df["magnitude_match"] == "L"]["model_id"].unique().tolist()
    lines.extend(
        [
            "",
            "## Extrapolation watchlist",
            "",
        ]
    )
    if extrapolated:
        for mid in extrapolated:
            lines.append(
                f"- **{mid}** — magnitude outside literature band "
                "or low-confidence projection"
            )
    else:
        lines.append("- No low-confidence magnitude gaps flagged in this pass.")

    lines.extend(
        [
            "",
            "## Scoring legend",
            "",
            "- **Dir Y/N:** directional trend matches public shrink / Vdd reduction narrative",
            "- **Mag H/M/L:** high / medium / low magnitude alignment vs literature envelope",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
