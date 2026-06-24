"""Path resolution for model cards and benchmark artifacts."""

from __future__ import annotations

import os
from pathlib import Path

from dram_benchmark.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root()

OPEN_DRAMMODEL_V1_ROOT = PROJECT_ROOT / "models" / "OpenDRAMmodelV1"
MODEL_SUBMODULE_REL = "models/OpenDRAMmodelV1/models/access_tx"
DEFAULT_MODEL_ROOT = OPEN_DRAMMODEL_V1_ROOT / "models" / "access_tx"
CONFIG_PATH = PROJECT_ROOT / "bench" / "config" / "corners.yaml"
DEFAULT_CORNER_REGISTRY_PATH = PROJECT_ROOT / "bench" / "registry" / "corner_registry.yaml"


def resolve_corner_registry_path() -> Path | None:
    """Return bundled corner registry path when available."""
    env = os.environ.get("OPEN_DRAM_CORNER_REGISTRY")
    if env:
        path = Path(env)
        return path if path.is_file() else None
    if DEFAULT_CORNER_REGISTRY_PATH.is_file():
        return DEFAULT_CORNER_REGISTRY_PATH
    return None


def netlist_include_path(
    inc_path: Path,
    *,
    model_id: str | None = None,
    absolute: bool = False,
) -> str:
    """Return a repo-relative ``.include`` path for generated SPICE decks."""
    if absolute:
        return inc_path.resolve().as_posix()
    try:
        return inc_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        if model_id:
            return f"{MODEL_SUBMODULE_REL}/{model_id}.inc"
        return inc_path.as_posix()


def resolve_model_root() -> Path:
    """Return the directory containing access transistor ``.inc`` model cards."""
    env_root = os.environ.get("OPEN_DRAM_MODEL_ROOT")
    root = Path(env_root) if env_root else DEFAULT_MODEL_ROOT
    if not root.is_dir():
        msg = (
            f"Model root not found: {root}. "
            "Initialize the OpenDRAMmodelV1 bundle under models/OpenDRAMmodelV1 "
            "or set OPEN_DRAM_MODEL_ROOT."
        )
        raise FileNotFoundError(msg)
    return root
