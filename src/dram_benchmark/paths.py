"""Path resolution for the OpenDRAMBench platform."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = PACKAGE_ROOT
MODEL_BUNDLE_ROOT = PROJECT_ROOT / "models" / "OpenDRAMmodelV1"
DEFAULT_MODEL_ROOT = MODEL_BUNDLE_ROOT / "models" / "access_tx"
RESULTS_ROOT = PROJECT_ROOT / "results"
BENCH_CONFIG = PROJECT_ROOT / "bench" / "config" / "corners.yaml"
ENGINE_ROOT = PROJECT_ROOT

STANDARD_ACCESS_MODEL_IDS: tuple[str, ...] = (
    "BCAT_125",
    "VCT_082",
    "VCT_091",
    "VCT_102",
    "VCT_125",
    "3D_gaa_Si",
    "3D_gaa_AOS",
)


def resolve_engine_root() -> Path:
    """Return the self-contained platform project root (SPICE engine lives here)."""
    return PROJECT_ROOT


def resolve_model_root() -> Path:
    """Return the directory containing access transistor `.inc` model cards."""
    env_root = os.environ.get("OPEN_DRAM_MODEL_ROOT")
    root = Path(env_root) if env_root else DEFAULT_MODEL_ROOT
    if not root.is_dir():
        raise FileNotFoundError(
            f"Model root not found: {root}. "
            "Bundled models should live under models/OpenDRAMmodelV1/models/access_tx "
            "or set OPEN_DRAM_MODEL_ROOT."
        )
    return root


def model_bundle_revision() -> str:
    """Return revision id for the bundled OpenDRAMmodelV1 model cards."""
    from validation.card import model_bundle_fingerprint, model_git_sha

    sha = model_git_sha(MODEL_BUNDLE_ROOT)
    if sha:
        return sha
    return model_bundle_fingerprint(MODEL_BUNDLE_ROOT)


def list_access_model_ids() -> tuple[str, ...]:
    """Return standard access model IDs present under the model root."""
    root = resolve_model_root()
    present = {path.stem for path in root.glob("*.inc")}
    missing = [mid for mid in STANDARD_ACCESS_MODEL_IDS if mid not in present]
    if missing:
        raise FileNotFoundError(f"Missing model cards under {root}: {missing}")
    return STANDARD_ACCESS_MODEL_IDS
