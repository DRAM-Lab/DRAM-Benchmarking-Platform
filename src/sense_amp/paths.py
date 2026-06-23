"""Path resolution for model cards and benchmark artifacts."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = PACKAGE_ROOT

OPEN_DRAMMODEL_V1_ROOT = PROJECT_ROOT / "models" / "OpenDRAMmodelV1"
MODEL_SUBMODULE_REL = "models/OpenDRAMmodelV1/models/access_tx"
DEFAULT_MODEL_ROOT = OPEN_DRAMMODEL_V1_ROOT / "models" / "access_tx"
CONFIG_PATH = PROJECT_ROOT / "bench" / "sense_amp_vct" / "configs" / "read_path.yaml"


def include_search_roots() -> list[Path]:
    """Return ordered search roots for repo-relative ``.include`` paths."""
    roots: list[Path] = [PROJECT_ROOT]
    env_root = os.environ.get("OPEN_DRAM_MODEL_ROOT")
    if env_root:
        model_root = Path(env_root).resolve()
        rel = Path(MODEL_SUBMODULE_REL)
        for ancestor in model_root.parents:
            if (ancestor / rel).is_dir():
                roots.append(ancestor)
                break
    seen: set[Path] = set()
    unique: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def netlist_include_path(inc_path: Path, *, model_id: str | None = None) -> str:
    """Return a repo-relative ``.include`` path for generated SPICE decks."""
    del model_id
    try:
        return inc_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        for root in include_search_roots()[1:]:
            try:
                return inc_path.relative_to(root).as_posix()
            except ValueError:
                continue
        return inc_path.resolve().as_posix()


def resolve_model_root() -> Path:
    """Return the directory containing access transistor ``.inc`` model cards."""
    env_root = os.environ.get("OPEN_DRAM_MODEL_ROOT")
    root = Path(env_root) if env_root else DEFAULT_MODEL_ROOT
    if not root.is_dir():
        raise FileNotFoundError(
            f"Model root not found: {root}. "
            "Initialize models/OpenDRAMmodelV1 or set OPEN_DRAM_MODEL_ROOT."
        )
    return root


def load_read_path_config(config_path: Path | None = None) -> dict:
    """Load the read-path YAML configuration."""
    import yaml

    path = config_path or CONFIG_PATH
    return yaml.safe_load(path.read_text(encoding="utf-8"))
