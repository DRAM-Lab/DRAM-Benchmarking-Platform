"""Model provenance and confidence-tier documentation."""

from __future__ import annotations

from pathlib import Path

from validation.card import model_git_sha, parse_card_metrics
from validation.golden import GoldenSpec, load_all_golden_specs
from validation.paths import MODEL_SUBMODULE_REL, PROJECT_ROOT


def _confidence_table(spec: GoldenSpec) -> str:
    """Render markdown table rows for one model's metrics."""
    rows: list[str] = []
    for name, band in spec.metrics.items():
        tier = band.confidence.upper()[0]
        ref = ""
        if band.value is not None:
            ref = (
                f"{float(band.value):.4g}"
                if isinstance(band.value, (int, float))
                else str(band.value)
            )
        elif band.min is not None or band.max is not None:
            lo = f"{band.min:.4g}" if band.min is not None else "—"
            hi = f"{band.max:.4g}" if band.max is not None else "—"
            ref = f"[{lo}, {hi}]"
        rows.append(f"| {name} | {tier} | {ref} | {band.column} |")
    return "\n".join(rows)


def generate_model_provenance(
    output_path: Path | None = None,
) -> Path:
    """Generate ``docs/model_provenance.md`` from golden YAML specs.

    Args:
        output_path: Optional output path (default: ``docs/model_provenance.md``).

    Returns:
        Path to the written markdown file.
    """
    out = output_path or (PROJECT_ROOT / "docs" / "model_provenance.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    specs = load_all_golden_specs()
    sha = model_git_sha() or "unknown"

    sections: list[str] = [
        "# OpenDRAM Model Provenance",
        "",
        "Auto-generated confidence tiers and calibration lineage for OpenDRAMmodelV1.",
        "Regenerate with ``dram-validate provenance``.",
        "",
        f"- **Model bundle fingerprint:** `{sha}`",
        f"- **Bundle path:** `{MODEL_SUBMODULE_REL}`",
        "",
        "## Confidence legend",
        "",
        "| Tier | Meaning |",
        "|------|---------|",
        "| **H** | High — literature or MATRIX PDK number with ±5–10% band |",
        "| **M** | Medium — inferred from roadmap or cross-architecture scaling |",
        "| **L** | Low — extrapolated beyond published nodes (e.g. D0-class) |",
        "",
    ]

    for model_id, spec in specs.items():
        card: dict[str, float] = {}
        try:
            card = parse_card_metrics(model_id)
        except FileNotFoundError:
            pass
        sections.extend(
            [
                f"## {model_id}",
                "",
                f"- **Architecture:** {spec.architecture}",
                f"- **Card:** `{spec.model_file}`",
                f"- **Corner:** T={spec.corner.get('temp', 27)} °C, "
                f"Vdd={spec.corner.get('vdd', 'nominal')} V",
                "",
                "| Metric | Confidence | Reference band | Column |",
                "|--------|------------|----------------|--------|",
                _confidence_table(spec),
                "",
            ]
        )
        if spec.sources:
            sections.append("**Sources:** " + "; ".join(spec.sources))
            sections.append("")
        if card:
            nominal = card.get("nominal_vdd")
            if nominal is not None:
                sections.append(f"- **Card nominal Vdd:** {nominal} V")
            fpitch = card.get("fpitch")
            if fpitch is not None:
                sections.append(f"- **Card fpitch:** {fpitch * 1e9:.1f} nm")
            sections.append("")

    out.write_text("\n".join(sections), encoding="utf-8")
    return out


def generate_contributing_checklist(output_path: Path | None = None) -> Path:
    """Write ``CONTRIBUTING_MODELS.md`` PR checklist for model contributions.

    Args:
        output_path: Optional output path.

    Returns:
        Path to written file.
    """
    out = output_path or (PROJECT_ROOT / "CONTRIBUTING_MODELS.md")
    text = """# Contributing OpenDRAM Model Cards

Model pull requests must pass the OpenDRAM validation harness before merge.

## PR checklist

- [ ] Golden YAML regenerated under `models/OpenDRAMmodelV1/validation/golden/<model>.yaml`
- [ ] Confidence tier (H/M/L) assigned per metric with literature citation
- [ ] `pytest` validation suite passes locally
- [ ] Pinned metrics refreshed if SPICE extraction changed (`bench/validation/pinned/`)
- [ ] `docs/model_provenance.md` regenerated (`dram-validate provenance`)
- [ ] Directional trends documented for roadmap-scaling families (VCT, etc.)
- [ ] Model bundle fingerprint noted in `validation/RELEASE_MANIFEST.yaml` when rebasing cards

## Commands

```bash
pip install -e ".[dev]"
python scripts/extract_paper_refs.py --docs-root data/paper/docs
python scripts/publish_golden_from_paper.py
pytest                          # offline + structure checks
dram-validate check         # golden spice bands vs pinned metrics
dram-validate paper         # paper-transcribed metrics vs pinned SPICE
dram-validate provenance    # refresh provenance doc
```

## Tolerance policy

| Confidence | Numeric band |
|------------|--------------|
| High | ±5% if paper states value; ±10% if inferred |
| Medium | ±20% or min/max envelope from benchmark |
| Low | Directional only (increasing/decreasing across nodes) |

See the tolerance policy table above for band definitions.
"""
    out.write_text(text, encoding="utf-8")
    return out
