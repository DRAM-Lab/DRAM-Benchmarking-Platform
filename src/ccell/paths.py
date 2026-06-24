"""Path resolution for the Ccell roadmap experiment."""

from __future__ import annotations

import os
from pathlib import Path

from dram_benchmark.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root()
CONFIG_PATH = PROJECT_ROOT / "bench" / "ccell_roadmap" / "configs" / "ccell.yaml"
DEFAULT_BENCH_RESULTS = PROJECT_ROOT / "results" / "device"
DEFAULT_PARETO_RESULTS = PROJECT_ROOT / "results" / "pareto"
DEFAULT_SENSE_AMP_RESULTS = PROJECT_ROOT / "results" / "sense_amp"


def resolve_bench_results() -> Path:
    """Return device-benchmark results directory."""
    env = os.environ.get("OPEN_DRAM_BENCH_RESULTS")
    root = Path(env) if env else DEFAULT_BENCH_RESULTS
    if not root.is_dir():
        raise FileNotFoundError(
            f"Device benchmark results not found: {root}. "
            "Run the device suite first or set OPEN_DRAM_BENCH_RESULTS."
        )
    return root


def resolve_pareto_results() -> Path | None:
    """Return pareto roadmap results directory when present."""
    env = os.environ.get("OPEN_DRAM_PARETO_RESULTS")
    root = Path(env) if env else DEFAULT_PARETO_RESULTS
    return root if root.is_dir() else None


def resolve_sa_spec_csv() -> Path | None:
    """Locate per-node SA spec CSV from sense-amp results."""
    env = os.environ.get("OPEN_DRAM_SENSE_AMP_RESULTS")
    base = Path(env) if env else DEFAULT_SENSE_AMP_RESULTS
    path = base / "sa_spec_per_node.csv"
    return path if path.is_file() else None


def resolve_sense_amp_csv(corner: str = "tt") -> Path | None:
    """Locate read_signal CSV from sense-amp results."""
    env = os.environ.get("OPEN_DRAM_SENSE_AMP_RESULTS")
    base = Path(env) if env else DEFAULT_SENSE_AMP_RESULTS
    for name in (f"read_signal_{corner}.csv", "read_signal_tt.csv"):
        path = base / name
        if path.is_file():
            return path
    return None


def load_all_sense_amp_signals() -> "pd.DataFrame | None":
    """Load per-corner or combined read-path signal tables when available."""
    import pandas as pd

    env = os.environ.get("OPEN_DRAM_SENSE_AMP_RESULTS")
    base = Path(env) if env else DEFAULT_SENSE_AMP_RESULTS
    combined = base / "read_signal_all_corners.csv"
    if combined.is_file():
        return pd.read_csv(combined)

    frames = []
    for path in sorted(base.glob("read_signal_*.csv")):
        if path.name == "read_signal_all_corners.csv":
            continue
        frames.append(pd.read_csv(path))
    if frames:
        return pd.concat(frames, ignore_index=True)
    single = resolve_sense_amp_csv("tt")
    return pd.read_csv(single) if single is not None else None
