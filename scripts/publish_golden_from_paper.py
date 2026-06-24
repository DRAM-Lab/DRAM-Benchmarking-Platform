#!/usr/bin/env python3
"""Publish ``models/OpenDRAMmodelV1/validation/golden/*.yaml`` from paper PDF extraction.

Workflow::

    python scripts/extract_paper_refs.py --docs-root data/paper/docs
    python scripts/publish_golden_from_paper.py

Paper-transcribed metrics (Ion, Ioff, t_read) use ``validation: paper`` and are
checked via ``dram-validate paper``, not against pinned SPICE in ``check``.
Card geometry (fpitch) and bench-only metrics (Ron, Cgg) use ``validation: spice``
with Spectre TT pinned bands where the PDF has no comparable column.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from validation.card import model_bundle_fingerprint, parse_card_metrics
from validation.golden import ACCESS_MODEL_IDS, ALL_MODEL_IDS
from validation.paper_refs import load_extracted_refs
from validation.paths import (
    GOLDEN_ROOT,
    OPEN_DRAMMODEL_V1_ROOT,
    PINNED_CELL_METRICS_PATH,
    PINNED_METRICS_PATH,
    PROJECT_ROOT,
)

RELEASE_MANIFEST = OPEN_DRAMMODEL_V1_ROOT / "validation" / "RELEASE_MANIFEST.yaml"
MAPPING_PATH = PROJECT_ROOT / "data" / "paper" / "model_mapping.yaml"
EXTRACTED_REFS_PATH = PROJECT_ROOT / "data" / "paper" / "extracted_refs.yaml"

VCT_TRENDS: list[dict[str, Any]] = [
    {
        "metric": "Ion",
        "models": ["VCT_082", "VCT_091", "VCT_102", "VCT_125"],
        "direction": "increasing",
        "confidence": "high",
    },
    {
        "metric": "Ioff",
        "models": ["VCT_082", "VCT_091", "VCT_102", "VCT_125"],
        "direction": "non_decreasing",
        "confidence": "medium",
    },
]

DOI_PART1 = "10.1109/JXCDC.2026.3704358"
DOI_PART2 = "10.1109/JXCDC.2026.3704508"

SPICE_ONLY_METRICS: tuple[str, ...] = ("Ron", "Cgg")
PAPER_METRIC_NAMES: tuple[str, ...] = ("Ion", "Ioff", "t_read", "nominal_vdd", "vth0", "rdsw", "u0", "vsat")

RTOL_BY_CONFIDENCE: dict[str, float] = {
    "high": 0.10,
    "medium": 0.15,
    "low": 0.20,
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _format_source(source: dict[str, Any], *, part: int) -> str:
    doi = DOI_PART1 if part == 1 else DOI_PART2
    bits: list[str] = [f"Open DRAM Model Part {part}"]
    if source.get("section"):
        bits.append(f"§{source['section']}")
    if source.get("table"):
        bits.append(f"Table {source['table']}")
    if source.get("case") is not None:
        bits.append(f"Case {source['case']}")
    if source.get("figure"):
        bits.append(f"Fig. {source['figure']}")
    return " ".join(bits) + f" (IEEE JxCDC 2026, DOI {doi})"


def _config_sources(config: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()
    for metric in config.get("metrics", {}).values():
        src = metric.get("source")
        if not isinstance(src, dict):
            continue
        part = int(src.get("part", 1))
        line = _format_source(src, part=part)
        if line not in seen:
            seen.add(line)
            sources.append(line)
    desc = config.get("description", "")
    if desc and desc not in seen:
        sources.append(desc)
    return sources


def _load_mapping() -> dict[str, Any]:
    data = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))
    return data.get("models", {})


def _load_pinned_device() -> pd.DataFrame:
    if not PINNED_METRICS_PATH.is_file():
        raise FileNotFoundError(
            f"Pinned device metrics missing: {PINNED_METRICS_PATH}. "
            "Run the device benchmark and refresh pinned CSVs first."
        )
    return pd.read_csv(PINNED_METRICS_PATH)


def _pinned_row(df: pd.DataFrame, model_id: str) -> dict[str, Any]:
    subset = df[df["model_id"] == model_id]
    if subset.empty:
        raise ValueError(f"No pinned row for {model_id}")
    return subset.iloc[0].to_dict()


def _default_rtol(confidence: str, *, is_fpitch: bool = False) -> float:
    if is_fpitch:
        return 0.05
    return RTOL_BY_CONFIDENCE.get(confidence, 0.15)


def _uses_paper_ion_ioff(model_id: str, card_vdd: float | None, paper_vdd: float | None) -> bool:
    """Return True when card corner matches paper Vdd and node is not interpolated."""
    if model_id in {"VCT_091", "VCT_102", "VCT_125", "BCAT_125"}:
        return False
    if card_vdd is None or paper_vdd is None:
        return False
    return abs(card_vdd - paper_vdd) < 0.05


def _paper_metric_band(
    name: str,
    raw: dict[str, Any],
    *,
    validation: str,
) -> dict[str, Any]:
    band: dict[str, Any] = {
        "confidence": raw.get("confidence", "medium"),
        "validation": validation,
        "paper_source": raw.get("source"),
    }
    if raw.get("value") is not None:
        band["value"] = float(raw["value"])
    if raw.get("max") is not None:
        band["max"] = float(raw["max"])
    if raw.get("min") is not None:
        band["min"] = float(raw["min"])
    if validation == "spice":
        conf = str(band["confidence"])
        if name == "fpitch":
            band["tol"] = _default_rtol(conf, is_fpitch=True)
        elif band.get("value") is not None:
            band["rtol"] = _default_rtol(conf)
    return band


def _spice_metric_from_pinned(
    name: str,
    column: str,
    row: dict[str, Any],
    *,
    confidence: str = "medium",
    note: str | None = None,
) -> dict[str, Any]:
    val = row.get(column)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        raise ValueError(f"Pinned column {column} missing for spice metric {name}")
    band: dict[str, Any] = {
        "value": float(val),
        "confidence": confidence,
        "validation": "spice",
        "rtol": _default_rtol(confidence),
    }
    if note:
        band["source_note"] = note
    return band


def _load_pinned_cell() -> pd.DataFrame | None:
    if not PINNED_CELL_METRICS_PATH.is_file():
        return None
    return pd.read_csv(PINNED_CELL_METRICS_PATH)


def build_golden_spec(
    model_id: str,
    *,
    refs: dict[str, Any],
    mapping: dict[str, Any],
    pinned: pd.DataFrame,
    pinned_cell: pd.DataFrame | None,
) -> dict[str, Any]:
    """Build one golden YAML document for ``model_id``."""
    map_entry = mapping[model_id]
    primary_id = map_entry["primary_config"]
    configs = refs.get("configs", {})
    if primary_id not in configs:
        raise KeyError(f"Paper config {primary_id} missing for {model_id}")

    config = configs[primary_id]
    card = parse_card_metrics(model_id)
    pinned_row = _pinned_row(pinned, model_id) if model_id in ACCESS_MODEL_IDS else {}

    card_vdd = card.get("nominal_vdd")
    paper_vdd = config.get("corner", {}).get("vdd_v")
    paper_ion_ioff = _uses_paper_ion_ioff(model_id, card_vdd, paper_vdd)

    corner: dict[str, float] = {"temp": float(config.get("corner", {}).get("temp_c", 27))}
    if card_vdd is not None:
        corner["vdd"] = float(card_vdd)
    elif paper_vdd is not None:
        corner["vdd"] = float(paper_vdd)

    metrics: dict[str, Any] = {}
    paper_metrics = config.get("metrics", {})

    for pname in ("Ion", "Ioff"):
        if pname not in paper_metrics:
            continue
        mode = "paper" if paper_ion_ioff else "spice"
        raw = paper_metrics[pname]
        band = _paper_metric_band(pname, raw, validation=mode)
        if mode == "spice":
            col = "ion_a" if pname == "Ion" else "ioff_a"
            spice_val = pinned_row.get(col)
            if spice_val is not None and not pd.isna(spice_val):
                band["value"] = float(spice_val)
                if pname == "Ioff" and raw.get("max") is not None:
                    band["max"] = max(float(raw["max"]), float(spice_val) * 10)
                band["rtol"] = _default_rtol(str(band["confidence"]))
                band["source_note"] = (
                    "SPICE TT pinned — card Vdd or roadmap node differs from paper anchor"
                )
        metrics[pname] = band

    if "tRC_ns" in paper_metrics and model_id in ACCESS_MODEL_IDS:
        trc = paper_metrics["tRC_ns"]
        metrics["t_read"] = {
            "value": float(trc["value"]) * 1e-9,
            "confidence": trc.get("confidence", "medium"),
            "validation": "paper" if paper_ion_ioff else "spice",
            "paper_source": trc.get("source"),
        }
        if metrics["t_read"]["validation"] == "spice":
            cell_row = None
            if pinned_cell is not None:
                subset = pinned_cell[pinned_cell["model_id"] == model_id]
                if not subset.empty:
                    cell_row = subset.iloc[0]
            if cell_row is not None and not pd.isna(cell_row.get("t_read_s")):
                metrics["t_read"]["value"] = float(cell_row["t_read_s"])
                metrics["t_read"]["rtol"] = 0.10
                metrics["t_read"]["source_note"] = "SPICE 1T1C pinned (paper tRC is array-level)"

    if "fpitch" in card:
        metrics["fpitch"] = {
            "value": float(card["fpitch"]),
            "tol": 0.05,
            "confidence": "high",
            "validation": "spice",
            "source_note": "BSIM card parameter (models/access_tx/*.inc)",
        }

    if model_id in ACCESS_MODEL_IDS:
        for sname, col in (("Ron", "ron_ohm"), ("Cgg", "cgg_f")):
            metrics[sname] = _spice_metric_from_pinned(
                sname,
                col,
                pinned_row,
                confidence="medium",
                note="Spectre TT pinned — not transcribed in Part I/II device tables",
            )

    if model_id == "hv_peri_28_32":
        for key in ("nominal_vdd", "vth0", "rdsw", "u0", "vsat"):
            if key in card:
                src = paper_metrics.get(key, {})
                conf = src.get("confidence", "medium")
                metrics[key] = {
                    "value": float(card[key]),
                    "confidence": conf,
                    "validation": "spice",
                    "rtol": _default_rtol(str(conf)),
                    "source_note": "Parsed from peri card — supplement anchor where available",
                }

    if model_id == "3D_gaa_AOS" and "I_hold" not in metrics:
        metrics["I_hold"] = {
            "max": 5.0e-10,
            "confidence": "low",
            "validation": "spice",
            "source_note": "AOS hold leakage envelope (low confidence)",
        }

    spec: dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": "scripts/publish_golden_from_paper.py",
            "extracted_refs_sha256": _file_sha256(EXTRACTED_REFS_PATH),
            "model_bundle_fingerprint": model_bundle_fingerprint(),
        },
        "model": f"{model_id}.inc",
        "architecture": config.get("architecture", "unknown"),
        "paper_config": primary_id,
        "corner": corner,
        "sources": _config_sources(config),
        "metrics": metrics,
    }
    if map_entry.get("notes"):
        spec["mapping_notes"] = map_entry["notes"]
    if model_id.startswith("VCT_"):
        spec["trends"] = VCT_TRENDS
    return spec


def publish_all_golden(*, golden_root: Path | None = None) -> list[Path]:
    """Write golden YAML files and release manifest."""
    root = golden_root or GOLDEN_ROOT
    root.mkdir(parents=True, exist_ok=True)

    refs = load_extracted_refs()
    mapping = _load_mapping()
    pinned = _load_pinned_device()
    pinned_cell = _load_pinned_cell()

    written: list[Path] = []
    card_hashes: dict[str, str] = {}

    for model_id in ALL_MODEL_IDS:
        if model_id not in mapping:
            raise KeyError(f"model_mapping.yaml missing entry for {model_id}")
        spec = build_golden_spec(
            model_id, refs=refs, mapping=mapping, pinned=pinned, pinned_cell=pinned_cell
        )
        out = root / f"{model_id.lower()}.yaml"
        header = (
            "# Auto-generated by scripts/publish_golden_from_paper.py — do not edit by hand.\n"
            "# Re-run after PDF extraction or pinned metric refresh.\n"
        )
        out.write_text(
            header + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        written.append(out)
        try:
            from validation.paths import resolve_model_inc

            card_hashes[model_id] = _file_sha256(resolve_model_inc(model_id))
        except FileNotFoundError:
            pass

    manifest = {
        "model_bundle": "OpenDRAMmodelV1",
        "distribution": "vendored",
        "upstream": "https://github.com/MATRIX-PDK/OpenDRAMmodelV1",
        "upstream_snapshot": "c53ccc9",
        "model_bundle_fingerprint": model_bundle_fingerprint(),
        "golden_schema": "validation/golden/v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "extracted_refs_sha256": _file_sha256(EXTRACTED_REFS_PATH),
        "reference_backend": "spectre",
        "reference_corner": "tt",
        "card_hashes": card_hashes,
        "golden_files": [p.name for p in written],
        "evidence": {
            "paper_metrics": "data/paper/extracted_refs.yaml (PDF via extract_paper_refs.py)",
            "spice_regression": str(PINNED_METRICS_PATH.relative_to(PROJECT_ROOT)),
        },
    }
    RELEASE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    RELEASE_MANIFEST.write_text(
        "# Auto-generated release manifest for vendored OpenDRAMmodelV1 bundle.\n"
        + yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish golden YAML from paper extraction.")
    parser.add_argument(
        "--golden-root",
        type=Path,
        default=None,
        help=f"Output directory (default: {GOLDEN_ROOT})",
    )
    args = parser.parse_args()

    if not EXTRACTED_REFS_PATH.is_file():
        print(f"Missing {EXTRACTED_REFS_PATH} — run scripts/extract_paper_refs.py first")
        return 1

    paths = publish_all_golden(golden_root=args.golden_root)
    for path in paths:
        print(f"Wrote {path}")
    print(f"Wrote {RELEASE_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
