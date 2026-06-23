"""Path resolution for the Pareto roadmap experiment."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = PACKAGE_ROOT
CONFIG_PATH = PROJECT_ROOT / "bench" / "pareto_roadmap" / "configs" / "pareto.yaml"
DEFAULT_BENCH_RESULTS = PROJECT_ROOT / "results" / "device"


def resolve_bench_results() -> Path:
    """Return device-benchmark results directory for derive mode."""
    env = os.environ.get("OPEN_DRAM_BENCH_RESULTS")
    root = Path(env) if env else DEFAULT_BENCH_RESULTS
    if not root.is_dir():
        raise FileNotFoundError(
            f"Device benchmark results not found: {root}. "
            "Run the device suite first or set OPEN_DRAM_BENCH_RESULTS."
        )
    return root
