"""Paper reference loading and SPICE-vs-publication correlation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from validation.paths import PROJECT_ROOT

MatchTier = Literal["H", "M", "L", "N"]

PAPER_ROOT = PROJECT_ROOT / "data" / "paper"
EXTRACTED_REFS_PATH = PAPER_ROOT / "extracted_refs.yaml"
MODEL_MAPPING_PATH = PAPER_ROOT / "model_mapping.yaml"


@dataclass(frozen=True)
class PaperMetricRef:
    """One metric transcribed from Part I/II."""

    config_id: str
    name: str
    value: float | None = None
    min: float | None = None
    max: float | None = None
    unit: str = ""
    display: str = ""
    confidence: str = "medium"
    source: dict[str, Any] | None = None
    note: str = ""


@dataclass(frozen=True)
class PaperCorrelationRow:
    """Comparison of pinned SPICE vs paper reference."""

    model_id: str
    paper_config: str
    metric: str
    paper_value: float | None
    paper_display: str
    spice_value: float | None
    spice_column: str
    ratio: float | None
    magnitude_match: MatchTier
    gap_notes: str


def load_extracted_refs(path: Path | None = None) -> dict[str, Any]:
    """Load ``data/paper/extracted_refs.yaml``.

    Args:
        path: Optional override path.

    Returns:
        Parsed YAML document.
    """
    ref_path = path or EXTRACTED_REFS_PATH
    if not ref_path.is_file():
        raise FileNotFoundError(
            f"Paper references missing: {ref_path}. "
            "Run: python scripts/extract_paper_refs.py"
        )
    raw = yaml.safe_load(ref_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid paper refs YAML: {ref_path}")
    return raw


def load_model_mapping(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load model card → paper configuration mapping.

    Args:
        path: Optional override path.

    Returns:
        Dict keyed by model id.
    """
    map_path = path or MODEL_MAPPING_PATH
    if not map_path.is_file():
        raise FileNotFoundError(f"Model mapping missing: {map_path}")
    raw = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    models = raw.get("models", {}) if isinstance(raw, dict) else {}
    if not isinstance(models, dict):
        raise ValueError(f"Invalid model mapping YAML: {map_path}")
    return {str(k): v for k, v in models.items()}


def paper_metrics_for_config(
    config_id: str,
    refs: dict[str, Any] | None = None,
) -> list[PaperMetricRef]:
    """Return metric references for one paper configuration id."""
    doc = refs or load_extracted_refs()
    configs = doc.get("configs", {})
    cfg = configs.get(config_id)
    if not isinstance(cfg, dict):
        return []
    metrics_raw = cfg.get("metrics", {})
    out: list[PaperMetricRef] = []
    if not isinstance(metrics_raw, dict):
        return out
    for name, spec in metrics_raw.items():
        if not isinstance(spec, dict):
            continue
        out.append(
            PaperMetricRef(
                config_id=config_id,
                name=str(name),
                value=float(spec["value"]) if spec.get("value") is not None else None,
                min=float(spec["min"]) if spec.get("min") is not None else None,
                max=float(spec["max"]) if spec.get("max") is not None else None,
                unit=str(spec.get("unit", "")),
                display=str(spec.get("display", "")),
                confidence=str(spec.get("confidence", "medium")),
                source=spec.get("source") if isinstance(spec.get("source"), dict) else None,
                note=str(spec.get("note", "")),
            )
        )
    return out


def _score_ratio(ratio: float | None, confidence: str) -> MatchTier:
    """Score magnitude alignment between paper and SPICE."""
    if ratio is None:
        return "N"
    tol = {"high": 0.15, "medium": 0.35, "low": 0.60}.get(confidence, 0.35)
    if ratio <= tol:
        return "H"
    if ratio <= tol * 2:
        return "M"
    if ratio <= 1.0:
        return "L"
    return "N"


def correlate_paper_metrics(
    device_df: pd.DataFrame,
    refs: dict[str, Any] | None = None,
    mapping: dict[str, dict[str, Any]] | None = None,
) -> list[PaperCorrelationRow]:
    """Compare pinned SPICE metrics against paper-extracted references.

    Args:
        device_df: Pinned device metrics dataframe.
        refs: Optional pre-loaded paper refs.
        mapping: Optional model mapping override.

    Returns:
        List of correlation rows for bridged metrics.
    """
    doc = refs or load_extracted_refs()
    model_map = mapping or load_model_mapping()
    bridge_raw = doc.get("metric_bridge", {})
    bridge: dict[str, dict[str, str]] = (
        {str(k): v for k, v in bridge_raw.items()} if isinstance(bridge_raw, dict) else {}
    )

    rows: list[PaperCorrelationRow] = []
    for model_id, map_entry in model_map.items():
        if not isinstance(map_entry, dict):
            continue
        config_id = str(map_entry.get("primary_config", ""))
        if not config_id:
            continue
        dev_row = device_df[device_df["model_id"] == model_id]
        if dev_row.empty:
            continue
        dev = dev_row.iloc[0].to_dict()
        for pm in paper_metrics_for_config(config_id, doc):
            bridge_entry = bridge.get(pm.name)
            if not bridge_entry:
                continue
            col = bridge_entry.get("spice_column", "")
            if not col or col not in dev:
                continue
            spice_val = dev.get(col)
            if spice_val is None or (isinstance(spice_val, float) and pd.isna(spice_val)):
                spice_f: float | None = None
            else:
                spice_f = float(spice_val)

            paper_val = pm.value if pm.value is not None else pm.max
            ratio: float | None = None
            if paper_val is not None and spice_f is not None and paper_val != 0:
                ratio = abs(spice_f - paper_val) / abs(paper_val)

            gap = bridge_entry.get("note", "")
            if pm.display:
                gap = f"{pm.display}. {gap}".strip()
            if ratio is not None and ratio > 0.5:
                gap = (
                    f"Large gap ({ratio * 100:.0f}% rel. error) — expected when TCAD table "
                    f"Ion/Ioff differs from BSIM benchmark extraction. {gap}"
                )

            rows.append(
                PaperCorrelationRow(
                    model_id=model_id,
                    paper_config=config_id,
                    metric=pm.name,
                    paper_value=paper_val,
                    paper_display=pm.display or (f"{paper_val:.4e}" if paper_val else "—"),
                    spice_value=spice_f,
                    spice_column=str(col),
                    ratio=ratio,
                    magnitude_match=_score_ratio(ratio, pm.confidence),
                    gap_notes=gap.strip(),
                )
            )
    return rows


def paper_correlation_dataframe(rows: list[PaperCorrelationRow]) -> pd.DataFrame:
    """Convert paper correlation rows to a dataframe."""
    return pd.DataFrame(
        [
            {
                "model_id": r.model_id,
                "paper_config": r.paper_config,
                "metric": r.metric,
                "paper_value": r.paper_value,
                "paper_display": r.paper_display,
                "spice_value": r.spice_value,
                "spice_column": r.spice_column,
                "rel_error": r.ratio,
                "magnitude_match": r.magnitude_match,
                "gap_notes": r.gap_notes,
            }
            for r in rows
        ]
    )


def generate_paper_correlation_report(
    device_df: pd.DataFrame,
    output_path: Path | None = None,
) -> Path:
    """Write markdown report comparing SPICE metrics to paper tables.

    Args:
        device_df: Pinned device metrics.
        output_path: Optional output path.

    Returns:
        Path to written markdown file.
    """
    out = output_path or (PROJECT_ROOT / "docs" / "paper_correlation.md")
    refs = load_extracted_refs()
    rows = correlate_paper_metrics(device_df, refs=refs)
    meta = refs.get("meta", {})

    lines = [
        "# Paper Correlation (Part I/II vs Pinned SPICE)",
        "",
        "Metrics transcribed from Open DRAM Model Part I/II papers and compared",
        "to pinned TT SPICE extraction. Regenerate with `dram-validate paper`.",
        "",
        f"- **Extracted:** {meta.get('extracted_at', 'unknown')}",
        f"- **Docs root:** `{meta.get('docs_root', '')}`",
        "",
        "## Alignment matrix",
        "",
        "| Model | Paper config | Metric | Paper | SPICE | Rel err | Mag | Notes |",
        "|-------|--------------|--------|-------|-------|---------|-----|-------|",
    ]

    for r in rows:
        paper_s = r.paper_display or (f"{r.paper_value:.4e}" if r.paper_value else "—")
        spice_s = f"{r.spice_value:.4e}" if r.spice_value is not None else "—"
        rel_s = f"{r.ratio * 100:.1f}%" if r.ratio is not None else "—"
        lines.append(
            f"| {r.model_id} | `{r.paper_config}` | {r.metric} | {paper_s} | "
            f"{spice_s} | {rel_s} | {r.magnitude_match} | {r.gap_notes[:80]} |"
        )

    extrap = [r for r in rows if r.magnitude_match in ("L", "N")]
    lines.extend(["", "## Extrapolation / metric-definition watchlist", ""])
    if extrap:
        for r in extrap:
            lines.append(f"- **{r.model_id}** `{r.metric}` — {r.gap_notes[:120]}")
    else:
        lines.append("- No large gaps flagged for bridged metrics.")

    lines.extend(
        [
            "",
            "## Scoring legend",
            "",
            "- **Mag H/M/L/N:** high / medium / low / no comparable SPICE column",
            "- Paper Ion/Ioff are TCAD table values; benchmark uses BSIM card extraction",
            "- Re-extract paper tables: `python scripts/extract_paper_refs.py`",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
