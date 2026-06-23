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


def _device_metrics_csv(results_dir: Path, reference_corner: str) -> Path:
    """Resolve primary device metrics CSV for the device suite."""
    backend_dir = _backend_with_all_corners_csv(results_dir)
    if backend_dir is not None:
        return backend_dir / "device_metrics_all_corners.csv"
    for backend in SIMULATOR_BACKENDS:
        path = results_dir / backend / reference_corner / "device_metrics.csv"
        if path.is_file():
            return path
    corner_path = results_dir / reference_corner / "device_metrics.csv"
    if corner_path.is_file():
        return corner_path
    return results_dir / "device_metrics.csv"


def _device_cell_metrics_csv(results_dir: Path, reference_corner: str) -> Path:
    """Resolve 1T1C metrics CSV for the device suite."""
    backend_dir = _backend_with_all_corners_csv(results_dir)
    if backend_dir is not None:
        return backend_dir / "cell_1t1c_metrics_all_corners.csv"
    for backend in SIMULATOR_BACKENDS:
        path = results_dir / backend / reference_corner / "cell_1t1c_metrics.csv"
        if path.is_file():
            return path
    corner_path = results_dir / reference_corner / "cell_1t1c_metrics.csv"
    if corner_path.is_file():
        return corner_path
    return results_dir / "cell_1t1c_metrics.csv"


def _device_mini_array_metrics_csv(results_dir: Path, reference_corner: str) -> Path:
    """Resolve mini-array metrics CSV for the device suite."""
    backend_dir = _backend_with_all_corners_csv(results_dir)
    if backend_dir is not None:
        return backend_dir / "mini_array_metrics_all_corners.csv"
    for backend in SIMULATOR_BACKENDS:
        path = results_dir / backend / reference_corner / "mini_array_metrics.csv"
        if path.is_file():
            return path
    corner_path = results_dir / reference_corner / "mini_array_metrics.csv"
    if corner_path.is_file():
        return corner_path
    return results_dir / "mini_array_metrics.csv"


def _backend_with_all_corners_csv(tree: Path) -> Path | None:
    """Return ``tree/{backend}`` when it holds aggregated all-corner device metrics."""
    for backend in SIMULATOR_BACKENDS:
        backend_dir = tree / backend
        if (backend_dir / "device_metrics_all_corners.csv").is_file():
            return backend_dir
    return None


def resolve_bench_input_dir(
    parent_results: Path,
    *,
    reference_corner: str = "tt",
) -> Path | None:
    """Locate device-benchmark CSV tree for pareto/ccell derive.

    Multi-simulator runs store aggregates under ``{suite}/{backend}/`` rather than
    at the suite root. Prefer ``corner_sweep`` when present, then fall back to
    ``device``.
    """
    parent = parent_results.resolve()
    corner_sweep = parent / "corner_sweep"
    if corner_sweep.is_dir():
        backend_dir = _backend_with_all_corners_csv(corner_sweep)
        if backend_dir is not None:
            return backend_dir
        if (corner_sweep / "device_metrics_all_corners.csv").is_file():
            return corner_sweep

    device = parent / "device"
    if not device.is_dir():
        return None

    backend_dir = _backend_with_all_corners_csv(device)
    if backend_dir is not None:
        return backend_dir
    if (device / "device_metrics_all_corners.csv").is_file():
        return device

    for backend in SIMULATOR_BACKENDS:
        corner_dir = device / backend / reference_corner
        if (corner_dir / "device_metrics.csv").is_file():
            return corner_dir
    if (device / reference_corner / "device_metrics.csv").is_file():
        return device / reference_corner
    if (device / "device_metrics.csv").is_file():
        return device
    return None


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
            backend_dir = _backend_with_all_corners_csv(self.results_dir)
            if backend_dir is not None:
                return backend_dir / "device_metrics_all_corners.csv"
            return self.results_dir / "device_metrics_all_corners.csv"
        if self.name == "multi_tool":
            for backend in SIMULATOR_BACKENDS:
                path = self.results_dir / backend / self.reference_corner / "device_metrics.csv"
                if path.is_file():
                    return path
            return None
        return _device_metrics_csv(self.results_dir, self.reference_corner)

    @property
    def simulator_compare_dir(self) -> Path | None:
        if self.name != "multi_tool":
            return None
        compare = self.results_dir / "simulator_compare"
        return compare if compare.is_dir() else None

    @property
    def cell_metrics_csv(self) -> Path | None:
        if self.name in {"corner_sweep"}:
            backend_dir = _backend_with_all_corners_csv(self.results_dir)
            base = backend_dir if backend_dir is not None else self.results_dir
            path = base / "cell_1t1c_metrics_all_corners.csv"
        elif self.name == "multi_tool" and self.metrics_csv is not None:
            path = self.metrics_csv.parent / "cell_1t1c_metrics.csv"
        elif self.name == "device":
            path = _device_cell_metrics_csv(self.results_dir, self.reference_corner)
        else:
            return None
        return path if path.is_file() else None

    @property
    def mini_array_metrics_csv(self) -> Path | None:
        if self.name == "corner_sweep":
            backend_dir = _backend_with_all_corners_csv(self.results_dir)
            base = backend_dir if backend_dir is not None else self.results_dir
            path = base / "mini_array_metrics_all_corners.csv"
        elif self.name == "multi_tool" and self.metrics_csv is not None:
            path = self.metrics_csv.parent / "mini_array_metrics.csv"
        elif self.name == "device":
            path = _device_mini_array_metrics_csv(self.results_dir, self.reference_corner)
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
