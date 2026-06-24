"""Artifact manifest generation for reproducible benchmark runs."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dram_benchmark.paths import (
    PROJECT_ROOT,
    STANDARD_ACCESS_MODEL_IDS,
    model_bundle_revision,
    resolve_engine_root,
    resolve_model_root,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tool_version(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
        if proc.returncode != 0:
            return None
        return (proc.stdout or proc.stderr).strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        return None


def _collect_artifacts(results_dir: Path, *, recursive: bool = False) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    patterns = ("*.csv", "*.json", "*.md", "*.yaml", "*.yml")
    globber = results_dir.rglob if recursive else results_dir.glob
    for pattern in patterns:
        for path in sorted(globber(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(results_dir).as_posix()
            artifacts.append(
                {
                    "path": rel,
                    "bytes": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    figure_globber = results_dir.rglob if recursive else results_dir.glob
    for path in sorted(figure_globber("figures/*.svg")):
        if not path.is_file():
            continue
        rel = path.relative_to(results_dir).as_posix()
        artifacts.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return artifacts


def build_manifest(
    results_dir: Path,
    *,
    suite: str,
    corner: str,
    simulator: str | None = None,
    status: str = "complete",
) -> dict[str, Any]:
    """Build a machine-readable manifest for a benchmark run."""
    model_root = resolve_model_root()
    model_cards = {
        f"{model_id}.inc": _sha256_file(model_root / f"{model_id}.inc")
        for model_id in STANDARD_ACCESS_MODEL_IDS
        if (model_root / f"{model_id}.inc").is_file()
    }

    manifest: dict[str, Any] = {
        "platform": "OpenDRAMBench",
        "platform_version": "0.2.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "suite": suite,
        "corner": corner,
        "simulator": simulator,
        "python": sys.version.split()[0],
        "host": platform.platform(),
        "project_root": str(PROJECT_ROOT),
        "engine_root": str(resolve_engine_root()),
        "model_root": str(model_root),
        "model_bundle_revision": model_bundle_revision(),
        "model_cards": model_cards,
        "tool_versions": {
            "ngspice": _tool_version(["ngspice", "--version"]),
            "hspice": _tool_version(["hspice", "-h"]),
            "spectre": _tool_version(["spectre", "-V"]),
        },
        "artifacts": _collect_artifacts(results_dir, recursive=suite == "all"),
    }
    return manifest


def write_manifest(
    results_dir: Path,
    output_path: Path | None = None,
    **kwargs: Any,
) -> Path:
    """Write MANIFEST.json under the results directory."""
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(results_dir, **kwargs)
    dest = output_path or (results_dir / "MANIFEST.json")
    dest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return dest
