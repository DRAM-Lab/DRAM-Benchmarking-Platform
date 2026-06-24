"""Path resolution for validation artifacts and model cards."""

from __future__ import annotations

import os
from pathlib import Path

from dram_benchmark.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root()

OPEN_DRAMMODEL_V1_ROOT = PROJECT_ROOT / "models" / "OpenDRAMmodelV1"
MODEL_SUBMODULE_REL = "models/OpenDRAMmodelV1"
DEFAULT_ACCESS_MODEL_ROOT = OPEN_DRAMMODEL_V1_ROOT / "models" / "access_tx"
DEFAULT_PERI_MODEL_ROOT = OPEN_DRAMMODEL_V1_ROOT / "models" / "peri_tx"
GOLDEN_ROOT = OPEN_DRAMMODEL_V1_ROOT / "validation" / "golden"
LITERATURE_ROOT = PROJECT_ROOT / "data" / "literature"
PAPER_ROOT = PROJECT_ROOT / "data" / "paper"
LOCAL_PAPER_DOCS_ROOT = PAPER_ROOT / "docs"
PAPER_DOCS_ROOT = LOCAL_PAPER_DOCS_ROOT
PINNED_METRICS_PATH = PROJECT_ROOT / "bench" / "validation" / "pinned" / "tt_device_metrics.csv"
PINNED_CELL_METRICS_PATH = PINNED_METRICS_PATH.parent / "tt_cell_1t1c_metrics_20ff.csv"
RESULTS_ROOT = PROJECT_ROOT / "results"

PAPER_PDF_NAMES: tuple[str, ...] = (
    "Open_DRAM_Model_Part_I_Cross-Layer_Device_Array_and_Circuit_Analysis_"
    "with_BL-to-BL_Coupling_Mitigation_for_4F_VCT_DRAM.pdf",
    "Open_DRAM_Model_Part_II_Enabling_Processing-in-Memory_in_3D_DRAM.pdf",
)


def paper_pdfs_present(docs_root: Path) -> bool:
    """Return True when Part I and Part II PDFs exist under ``docs_root``."""
    return all((docs_root / name).is_file() for name in PAPER_PDF_NAMES)


def resolve_paper_docs_root(explicit: Path | None = None) -> Path:
    """Resolve the directory containing Open DRAM Model Part I/II PDFs."""
    if explicit is not None:
        return explicit
    env = os.environ.get("PAPER_DOCS_ROOT")
    if env:
        return Path(env)
    for candidate in (LOCAL_PAPER_DOCS_ROOT,):
        if paper_pdfs_present(candidate):
            return candidate
    return LOCAL_PAPER_DOCS_ROOT


def resolve_access_model_root() -> Path:
    """Return the directory containing access transistor ``.inc`` cards."""
    env_root = os.environ.get("OPEN_DRAM_MODEL_ROOT")
    root = Path(env_root) if env_root else DEFAULT_ACCESS_MODEL_ROOT
    if not root.is_dir():
        msg = (
            f"Model root not found: {root}. "
            "Bundled models should live under models/OpenDRAMmodelV1/models/access_tx "
            "or set OPEN_DRAM_MODEL_ROOT."
        )
        raise FileNotFoundError(msg)
    return root


def resolve_peri_model_root() -> Path:
    """Return the directory containing periphery transistor ``.inc`` cards."""
    root = DEFAULT_PERI_MODEL_ROOT
    if not root.is_dir():
        raise FileNotFoundError(
            f"Periphery model root not found: {root}. "
            "Bundled models should live under models/OpenDRAMmodelV1/models/peri_tx."
        )
    return root


def resolve_model_inc(model_id: str) -> Path:
    """Resolve a model card path by identifier."""
    if model_id == "hv_peri_28_32":
        path = resolve_peri_model_root() / f"{model_id}.inc"
    else:
        path = resolve_access_model_root() / f"{model_id}.inc"
    if not path.is_file():
        raise FileNotFoundError(f"Model card not found: {path}")
    return path
