#!/usr/bin/env python3
"""Extract Open DRAM Model paper reference metrics into ``data/paper/extracted_refs.yaml``.

Reads Part I / Part II PDFs from ``data/paper/docs`` or ``PAPER_DOCS_ROOT`` / ``--docs-root``,
and writes structured YAML used by the validation harness for paper-vs-SPICE correlation.

Usage::

    python scripts/extract_paper_refs.py --docs-root data/paper/docs
    PAPER_DOCS_ROOT=/path/to/paper/pdfs python scripts/extract_paper_refs.py
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from validation.paths import (
    PAPER_PDF_NAMES,
    PROJECT_ROOT,
    resolve_paper_docs_root,
)

OUTPUT_PATH = PROJECT_ROOT / "data" / "paper" / "extracted_refs.yaml"
MAPPING_PATH = PROJECT_ROOT / "data" / "paper" / "model_mapping.yaml"

PART1_NAME = PAPER_PDF_NAMES[0]
PART2_NAME = PAPER_PDF_NAMES[1]
SUPPLEMENT_NAME = "supp1-3704358.docx"

REQUIRED_PDFS: tuple[str, ...] = (PART1_NAME, PART2_NAME)


def resolve_docs_root(explicit: Path | None = None) -> Path:
    """Resolve the paper PDF directory for extraction."""
    return resolve_paper_docs_root(explicit)


def required_paper_pdfs(docs_root: Path) -> list[Path]:
    """Return missing Part I/II PDF paths under ``docs_root``."""
    return [docs_root / name for name in REQUIRED_PDFS if not (docs_root / name).is_file()]


def _pdf_to_text(pdf_path: Path) -> str:
    """Run ``pdftotext`` and return document body."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Paper PDF not found: {pdf_path}")
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _verify_snippets(part1: str, part2: str) -> list[str]:
    """Return warnings when expected paper anchors are missing from extracted text."""
    warnings: list[str] = []
    anchors = [
        ("part1", part1, "2.44"),
        ("part1", part1, "D/R 12.5nm"),
        ("part1", part1, "21.5"),
        ("part1", part1, "12.0"),
        ("part2", part2, "9.03"),
        ("part2", part2, "10.4"),
        ("part2", part2, "D/R 10.2nm"),
    ]
    for label, text, needle in anchors:
        if needle not in text:
            warnings.append(f"{label}: anchor '{needle}' not found in PDF text")
    return warnings


def _build_reference_catalog() -> dict[str, Any]:
    """Return curated paper metrics keyed by configuration id.

    Values are transcribed from Part I/II PDF tables and supplement figure
    captions. Units are SI unless ``display`` is provided for human tables.
    """
    return {
        "bcat_6f2_d1b": {
            "description": "6F² D1b BCAT baseline (Part I §III-A; Part II Table 2)",
            "architecture": "BCAT",
            "corner": {"temp_c": 27, "vdd_v": 1.1},
            "design_rule_nm": 12.5,
            "feature_size_nm": 12.54,
            "channel_lg_nm": 120,
            "metrics": {
                "Ion": {
                    "value": 2.44e-6,
                    "unit": "A",
                    "display": "2.44 µA @ Vd=VDD",
                    "source": {"part": 1, "section": "III-A", "table": None},
                    "confidence": "high",
                },
                "Ioff": {
                    "max": 2.0e-16,
                    "unit": "A",
                    "display": "<0.2 fA @ Vd=VDD",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "Cs": {
                    "value": 4.0e-15,
                    "unit": "F",
                    "display": "4.0 fF",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "CBL": {
                    "value": 25.0e-15,
                    "unit": "F",
                    "display": "25.0 fF (1280 cells/BL)",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "RBL": {
                    "value": 49.6e3,
                    "unit": "ohm",
                    "display": "49.6 kΩ",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "CWL": {
                    "value": 30.0e-15,
                    "unit": "F",
                    "display": "30.0 fF",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "RWL": {
                    "value": 81.2e3,
                    "unit": "ohm",
                    "display": "81.2 kΩ",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "delta_vbl_mv": {
                    "value": 75.8,
                    "unit": "mV",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "sense_margin_mv": {
                    "value": 60.4,
                    "unit": "mV",
                    "source": {"part": 1, "section": "III-A"},
                    "confidence": "high",
                },
                "tRC_ns": {
                    "value": 21.5,
                    "unit": "ns",
                    "source": {"part": 1, "table": "timing", "figure": 14},
                    "confidence": "high",
                },
            },
        },
        "vct_4f2_d1b_dr12p5_case3": {
            "description": "4F² VCT D/R 12.5 nm, junction-underlap Case 3 (Part I Table III)",
            "architecture": "VCT",
            "corner": {"temp_c": 27, "vdd_v": 0.9},
            "design_rule_nm": 12.5,
            "metrics": {
                "Ion": {
                    "value": 8.62e-6,
                    "unit": "A",
                    "display": "8.62 µA @ Vd=VDD (TCAD)",
                    "source": {"part": 1, "table": "III", "case": 3},
                    "confidence": "high",
                },
                "Ioff": {
                    "max": 5.43e-18,
                    "unit": "A",
                    "display": "0.00543 fA @ Vd=VDD",
                    "source": {"part": 1, "table": "III", "case": 3},
                    "confidence": "high",
                },
                "Cs": {
                    "value": 4.0e-15,
                    "unit": "F",
                    "display": "4.0 fF",
                    "source": {"part": 1, "table": "III", "case": 3},
                    "confidence": "high",
                },
                "CBL": {
                    "value": 5.80e-15,
                    "unit": "F",
                    "display": "5.80 fF",
                    "source": {"part": 1, "table": "III", "case": 3},
                    "confidence": "high",
                },
                "delta_vbl_mv": {
                    "value": 204.1,
                    "unit": "mV",
                    "source": {"part": 1, "table": "III", "case": 3},
                    "confidence": "high",
                },
                "sense_margin_mv": {
                    "value": 93.9,
                    "unit": "mV",
                    "source": {"part": 1, "table": "III", "case": 3},
                    "confidence": "high",
                },
                "tRC_ns": {
                    "value": 12.0,
                    "unit": "ns",
                    "display": "Half-shield + folded-twist BLSA (Part I Fig. 14)",
                    "source": {"part": 1, "figure": 14},
                    "confidence": "medium",
                },
            },
        },
        "vct_4f2_d1b_plus3_dr10p2": {
            "description": "4F² VCT D1b+3 generation, D/R 10.2 nm (Part II Table 4)",
            "architecture": "VCT",
            "corner": {"temp_c": 27, "vdd_v": 0.9},
            "design_rule_nm": 10.2,
            "metrics": {
                "CBL": {
                    "value": 13.0e-15,
                    "unit": "F",
                    "display": "13.0 fF conventional sensing",
                    "source": {"part": 2, "table": "IV"},
                    "confidence": "high",
                },
                "RBL": {
                    "value": 53.2e3,
                    "unit": "ohm",
                    "display": "53.2 kΩ",
                    "source": {"part": 2, "table": "IV"},
                    "confidence": "high",
                },
                "CWL": {
                    "value": 28.7e-15,
                    "unit": "F",
                    "source": {"part": 2, "table": "IV"},
                    "confidence": "high",
                },
                "RWL": {
                    "value": 32.0e3,
                    "unit": "ohm",
                    "source": {"part": 2, "table": "IV"},
                    "confidence": "high",
                },
                "delta_vbl_mv": {
                    "value": 117.4,
                    "unit": "mV",
                    "display": "Conventional data '0'",
                    "source": {"part": 2, "table": "IV"},
                    "confidence": "high",
                },
                "sense_margin_mv": {
                    "value": 79.4,
                    "unit": "mV",
                    "display": "TRA data '0''0''1'",
                    "source": {"part": 2, "table": "IV"},
                    "confidence": "medium",
                },
            },
        },
        "dram_3d_si": {
            "description": "3D DRAM Si channel (Part II Table 2)",
            "architecture": "3D_GAA",
            "corner": {"temp_c": 27, "vdd_v": 0.75},
            "channel_lg_nm": 100,
            "channel_w_nm": 70,
            "metrics": {
                "Ion": {
                    "value": 9.03e-6,
                    "unit": "A",
                    "display": "9.03 µA",
                    "source": {"part": 2, "table": "II"},
                    "confidence": "high",
                },
                "Ioff": {
                    "max": 2.0e-17,
                    "unit": "A",
                    "display": "0.02 fA",
                    "source": {"part": 2, "table": "II"},
                    "confidence": "high",
                },
                "CBL_per_layer": {
                    "value": 0.0815e-15,
                    "unit": "F",
                    "display": "0.0815 fF per layer",
                    "source": {"part": 2, "table": "II"},
                    "confidence": "high",
                },
                "RBL_per_layer": {
                    "value": 0.292e3,
                    "unit": "ohm",
                    "display": "0.292 kΩ per layer",
                    "source": {"part": 2, "table": "II"},
                    "confidence": "medium",
                },
            },
        },
        "dram_3d_aos": {
            "description": "3D DRAM AOS (IWO) channel (Part II Table 2)",
            "architecture": "3D_GAA",
            "corner": {"temp_c": 27, "vdd_v": 0.75},
            "channel_lg_nm": 40,
            "channel_w_nm": 70,
            "metrics": {
                "Ion": {
                    "value": 10.4e-6,
                    "unit": "A",
                    "display": "10.4 µA",
                    "source": {"part": 2, "table": "II"},
                    "confidence": "high",
                },
                "Ioff": {
                    "max": 2.0e-17,
                    "unit": "A",
                    "display": "<0.02 fA",
                    "source": {"part": 2, "table": "II"},
                    "confidence": "high",
                },
                "CBL_per_layer": {
                    "value": 0.128e-15,
                    "unit": "F",
                    "display": "0.128 fF per layer",
                    "source": {"part": 2, "table": "II"},
                    "confidence": "high",
                },
            },
        },
        "hv_peri_28_32": {
            "description": "HV periphery 28–32 nm class (Part II §Open DRAM Model Information)",
            "architecture": "HV_PERI",
            "corner": {"temp_c": 27, "vdd_v": 1.0},
            "metrics": {
                "nominal_vdd": {
                    "value": 1.0,
                    "unit": "V",
                    "source": {"part": 2, "section": "Open DRAM Model Information"},
                    "confidence": "medium",
                    "note": "PTM 32 nm LP metal-gate card basis; see supplement appendix",
                },
            },
        },
    }


def _build_model_mapping() -> dict[str, Any]:
    """Map OpenDRAMmodelV1 card ids to paper configuration anchors."""
    return {
        "BCAT_125": {
            "primary_config": "bcat_6f2_d1b",
            "notes": (
                "Card targets D1β-class 6F² BCAT (Nominal VDD=0.85 V, fpitch=42 nm). "
                "Paper anchor is D1b baseline @ 1.1 V (Part I §III-A)."
            ),
        },
        "VCT_082": {
            "primary_config": "vct_4f2_d1b_dr12p5_case3",
            "notes": "MATRIX D1α node; paper anchor VCT Case 3 @ D/R 12.5 nm.",
        },
        "VCT_091": {
            "primary_config": "vct_4f2_d1b_dr12p5_case3",
            "notes": "Interpolated VCT roadmap node between D1α and D1β.",
        },
        "VCT_102": {
            "primary_config": "vct_4f2_d1b_dr12p5_case3",
            "notes": "Interpolated VCT roadmap node approaching D1β.",
        },
        "VCT_125": {
            "primary_config": "vct_4f2_d1b_plus3_dr10p2",
            "secondary_config": "vct_4f2_d1b_dr12p5_case3",
            "notes": "MATRIX D1β node; closest published array table is D1b+3 @ D/R 10.2 nm.",
        },
        "3D_gaa_Si": {
            "primary_config": "dram_3d_si",
            "notes": "Card fpitch=22 nm is aggressive vs Part II Table 2 W=70 nm design window.",
        },
        "3D_gaa_AOS": {
            "primary_config": "dram_3d_aos",
            "notes": "AOS channel calibrated to IWO dual-gate literature (Part II §Open DRAM Model).",
        },
        "hv_peri_28_32": {
            "primary_config": "hv_peri_28_32",
            "notes": "HV periphery calibration detailed in supplement appendix.",
        },
    }


def _metric_bridge() -> dict[str, dict[str, str]]:
    """Map paper metric names to pinned SPICE CSV columns where comparable."""
    return {
        "Ion": {
            "spice_column": "ion_a",
            "note": (
                "Paper Ion is TCAD access-device on-current (µA in tables). "
                "Benchmark Ion is |Ids| @ Vgs=Vdd on the BSIM card (A)."
            ),
        },
        "Ioff": {
            "spice_column": "ioff_a",
            "note": "Paper Ioff in fA; benchmark uses SPICE extraction at off bias.",
        },
        "fpitch": {
            "spice_column": "fpitch_m",
            "note": "Card fpitch parameter (m); paper tables use D/R or feature size (nm).",
        },
        "nominal_vdd": {
            "spice_column": "vdd",
            "note": "Nominal array/core Vdd from card header vs paper corner VDD.",
        },
    }


def extract(docs_root: Path) -> dict[str, Any]:
    """Extract and validate paper reference bundle.

    Args:
        docs_root: Directory containing Part I/II PDFs and supplement.

    Returns:
        Parsed reference document ready for YAML serialization.
    """
    part1_path = docs_root / PART1_NAME
    part2_path = docs_root / PART2_NAME
    supplement_path = docs_root / SUPPLEMENT_NAME

    part1_text = _pdf_to_text(part1_path)
    part2_text = _pdf_to_text(part2_path)
    warnings = _verify_snippets(part1_text, part2_text)

    if not supplement_path.is_file():
        warnings.append(f"supplement missing: {supplement_path}")

    supplement_note = None
    if supplement_path.is_file():
        try:
            from docx import Document

            doc = Document(str(supplement_path))
            supplement_note = (
                f"{len(doc.paragraphs)} paragraphs; "
                "TCAD structure figures for 6F² D1b and 4F² VCT scaling."
            )
        except ImportError:
            warnings.append("python-docx not installed; supplement not parsed")

    return {
        "meta": {
            "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "docs_root": str(docs_root.resolve()),
            "documents": {
                "part1": {"file": PART1_NAME, "doi": "10.1109/JXCDC.2026.3704358"},
                "part2": {"file": PART2_NAME, "doi": "10.1109/JXCDC.2026.3704508"},
                "supplement": {"file": SUPPLEMENT_NAME, "note": supplement_note},
            },
            "extraction_warnings": warnings,
        },
        "metric_bridge": _metric_bridge(),
        "configs": _build_reference_catalog(),
    }


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Extract paper reference metrics to YAML.")
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=None,
        help="Directory with Part I/II PDFs (default: data/paper/docs or PAPER_DOCS_ROOT)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Output YAML path",
    )
    args = parser.parse_args()

    docs_root = resolve_docs_root(args.docs_root)
    missing = required_paper_pdfs(docs_root)
    if missing:
        print(f"Skipping paper extraction — PDFs not found under {docs_root}:")
        for path in missing:
            print(f"  - {path.name}")
        print("Set PAPER_DOCS_ROOT or add PDFs to data/paper/docs")
        return 0

    bundle = extract(docs_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Auto-generated via scripts/extract_paper_refs.py\n"
        "# Re-run after paper PDF updates.\n"
    )
    args.output.write_text(
        header + yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    mapping = {
        "meta": {
            "generated_at": bundle["meta"]["extracted_at"],
            "maps": "OpenDRAMmodelV1 card id → paper config in extracted_refs.yaml",
        },
        "models": _build_model_mapping(),
    }
    MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAPPING_PATH.write_text(
        "# Model card → paper configuration mapping\n"
        + yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"Wrote {args.output}")
    print(f"Wrote {MAPPING_PATH}")
    if bundle["meta"]["extraction_warnings"]:
        print("Warnings:")
        for w in bundle["meta"]["extraction_warnings"]:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
