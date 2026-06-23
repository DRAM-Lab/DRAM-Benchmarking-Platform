"""Benchmark suite definitions and artifact path resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from dram_benchmark.paths import BENCH_CONFIG, STANDARD_ACCESS_MODEL_IDS

# Ordered execution for SUITE=all (pareto is a ccell dependency, not a top-level suite)
BENCHMARK_SUITES: tuple[str, ...] = (
    "device",
    "corner_sweep",
    "multi_tool",
    "sense_amp",
    "ccell",
    "validation",
)
SUITE_CHOICES: tuple[str, ...] = (*BENCHMARK_SUITES, "all")

SIMULATOR_BACKENDS: tuple[str, ...] = ("spectre", "hspice", "ngspice")


@dataclass(frozen=True)
class SuiteSpec:
    """Resolved paths and report parameters for one benchmark suite."""

    name: str
    results_dir: Path
    reference_corner: str = "tt"
    report_corner_label: str = "tt"

    @property
    def metrics_csv(self) -> Path | None:
        if self.name == "validation":
            return self.results_dir / "data" / "device_metrics.csv"
        if self.name == "ccell":
            return self.results_dir / "ccell_sweep.csv"
        if self.name == "sense_amp":
            for name in (
                "read_signal_tt.csv",
                "read_signal_all_corners.csv",
                f"read_signal_{self.reference_corner}.csv",
            ):
                path = self.results_dir / name
                if path.is_file():
                    return path
            return None
        if self.name == "corner_sweep":
            return self.results_dir / "device_metrics_all_corners.csv"
        if self.name == "multi_tool":
            for backend in SIMULATOR_BACKENDS:
                path = self.results_dir / backend / self.reference_corner / "device_metrics.csv"
                if path.is_file():
                    return path
            return None
        return self.results_dir / "device_metrics.csv"

    @property
    def simulator_compare_dir(self) -> Path | None:
        if self.name != "multi_tool":
            return None
        compare = self.results_dir / "simulator_compare"
        return compare if compare.is_dir() else None

    @property
    def cell_metrics_csv(self) -> Path | None:
        if self.name in {"corner_sweep"}:
            path = self.results_dir / "cell_1t1c_metrics_all_corners.csv"
        elif self.name == "multi_tool" and self.metrics_csv is not None:
            path = self.metrics_csv.parent / "cell_1t1c_metrics.csv"
        elif self.name == "device":
            path = self.results_dir / "cell_1t1c_metrics.csv"
        else:
            return None
        return path if path.is_file() else None

    @property
    def mini_array_metrics_csv(self) -> Path | None:
        if self.name == "corner_sweep":
            path = self.results_dir / "mini_array_metrics_all_corners.csv"
        elif self.name == "multi_tool" and self.metrics_csv is not None:
            path = self.metrics_csv.parent / "mini_array_metrics.csv"
        elif self.name == "device":
            path = self.results_dir / "mini_array_metrics.csv"
        else:
            return None
        return path if path.is_file() else None

    @property
    def report_corner_label_resolved(self) -> str:
        if self.name == "corner_sweep":
            return "all"
        return self.report_corner_label


def load_corner_names(config_path: Path | None = None) -> tuple[str, ...]:
    """Load corner names from the platform bench config."""
    path = config_path or BENCH_CONFIG
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return tuple(raw["corners"].keys())


def suite_spec(name: str, results_dir: Path, *, corner: str = "tt") -> SuiteSpec:
    """Build a :class:`SuiteSpec` for a named suite."""
    resolved = results_dir.resolve()
    if name == "corner_sweep":
        return SuiteSpec(
            name=name,
            results_dir=resolved,
            reference_corner=corner,
            report_corner_label="all",
        )
    return SuiteSpec(
        name=name,
        results_dir=resolved,
        reference_corner=corner,
        report_corner_label=corner,
    )


def discover_simulator_backends(results_dir: Path, corner: str = "tt") -> list[str]:
    """Return simulator backend directories that produced device metrics."""
    found: list[str] = []
    for backend in SIMULATOR_BACKENDS:
        metrics = results_dir / backend / corner / "device_metrics.csv"
        if metrics.is_file():
            found.append(backend)
    return found


def expected_corner_sweep_rows(corner_count: int | None = None) -> int:
    """Return expected row count for a full corner sweep device matrix."""
    corners = corner_count or len(load_corner_names())
    return len(STANDARD_ACCESS_MODEL_IDS) * corners


def suite_results_dir(parent: Path, suite: str) -> Path:
    """Return canonical output directory for a suite under a parent results tree."""
    if suite == "all":
        return parent.resolve()
    return (parent / suite).resolve()
