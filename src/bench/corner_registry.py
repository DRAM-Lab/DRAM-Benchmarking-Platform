"""Resolve and load IDEA153 corner registry for dram-device.

Supports three modes via ``OPEN_DRAM_CORNER_SOURCE``:

- ``auto`` (default): registry YAML when available, else local ``corners.yaml``
- ``registry``: canonical ``corner_registry.yaml`` (``opendram_corner`` or pure YAML)
- ``local``: repo ``bench/device_benchmark/configs/corners.yaml`` only
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml

from bench.paths import CONFIG_PATH, PROJECT_ROOT, resolve_corner_registry_path

CornerSourceMode = Literal["auto", "local", "registry"]
EffectiveSource = Literal["local", "registry"]


def corner_source_mode() -> CornerSourceMode:
    raw = os.environ.get("OPEN_DRAM_CORNER_SOURCE", "auto").strip().lower()
    if raw in ("local", "registry"):
        return raw  # type: ignore[return-value]
    return "auto"


def opendram_corner_available() -> bool:
    """True when ``opendram_corner`` package is importable."""
    return _bootstrap_corner_pipeline()


def registry_available() -> bool:
    """True when a registry YAML path resolves."""
    return resolve_corner_registry_path() is not None


def effective_corner_source(
    *,
    registry_path: Path | None = None,
    local_path: Path | None = None,
) -> EffectiveSource:
    """Resolve which corner backend is active."""
    mode = corner_source_mode()
    reg = registry_path or resolve_corner_registry_path()
    local = local_path or CONFIG_PATH

    if mode == "local":
        if not local.is_file():
            raise FileNotFoundError(f"Local corners config not found: {local}")
        return "local"
    if mode == "registry":
        if reg is None or not reg.is_file():
            raise FileNotFoundError(
                "Registry mode requires corner_registry.yaml "
                "(set OPEN_DRAM_CORNER_REGISTRY or sibling OpenDRAM-corner-pipeline)"
            )
        return "registry"
    if reg is not None and reg.is_file():
        return "registry"
    if local.is_file():
        return "local"
    raise FileNotFoundError(
        f"No corner config found (registry missing; local not found: {local})"
    )


def _bootstrap_corner_pipeline() -> bool:
    try:
        import opendram_corner  # noqa: F401

        return True
    except ImportError:
        return False


def _bench_from_registry_yaml(path: Path) -> dict[str, Any]:
    if opendram_corner_available():
        from opendram_corner.consumer import bench_config, bench_config_yaml

        try:
            return bench_config(path)
        except Exception:
            return bench_config_yaml(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    corners = {
        name: {"temp_c": float(spec["temp_c"]), "vdd_scale": float(spec["vdd_scale"])}
        for name, spec in raw["corners"].items()
    }
    out: dict[str, Any] = {"corners": corners}
    if raw.get("bench_defaults"):
        out.update(raw["bench_defaults"])
    return out


def load_bench_config(
    *,
    registry_path: Path | None = None,
    local_path: Path | None = None,
) -> dict[str, Any]:
    """Load full bench config from registry and/or local YAML."""
    source = effective_corner_source(registry_path=registry_path, local_path=local_path)
    if source == "local":
        path = local_path or CONFIG_PATH
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    reg = registry_path or resolve_corner_registry_path()
    assert reg is not None
    return _bench_from_registry_yaml(reg)


def load_corners_from_registry(
    *,
    registry_path: Path | None = None,
    local_path: Path | None = None,
):
    """Load corner map using the active corner source."""
    from bench.conditions import Corner

    payload = load_bench_config(registry_path=registry_path, local_path=local_path)
    return {
        name: Corner(name=name, temp_c=float(spec["temp_c"]), vdd_scale=float(spec["vdd_scale"]))
        for name, spec in payload["corners"].items()
    }


def registry_provenance() -> dict[str, str] | None:
    """Return IDEA153 registry metadata when the registry backend is active."""
    try:
        source = effective_corner_source()
    except FileNotFoundError:
        return None
    if source != "registry":
        return None
    reg_path = resolve_corner_registry_path()
    if reg_path is None or not reg_path.is_file():
        return None
    if opendram_corner_available():
        from opendram_corner.registry import load_registry

        reg = load_registry(reg_path)
        return {
            "source": source,
            "registry_path": str(reg_path),
            "registry_version": reg.registry_version,
            "model_sha": reg.model_sha,
            "confidence_policy": reg.confidence_policy,
        }
    raw = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    return {
        "source": source,
        "registry_path": str(reg_path),
        "registry_version": str(raw.get("registry_version", "unknown")),
        "model_sha": str(raw.get("model_sha", "unpinned")),
        "confidence_policy": str(raw.get("confidence_policy", "unknown")),
    }
