"""Validation checks for OpenDRAMBench artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from dram_benchmark.paths import STANDARD_ACCESS_MODEL_IDS, list_access_model_ids, resolve_model_root
from dram_benchmark.suites import (
    BENCHMARK_SUITES,
    discover_simulator_backends,
    expected_corner_sweep_rows,
    load_corner_names,
    suite_spec,
)

REQUIRED_DEVICE_COLUMNS = (
    "model_id",
    "architecture",
    "corner",
    "temp_c",
    "vdd",
    "ion_a",
    "ioff_a",
    "ron_ohm",
    "cgg_f",
    "fpitch_m",
    "vsat",
)


@dataclass
class ValidationResult:
    """Outcome of platform validation checks."""

    passed: bool
    checks: list[dict[str, str]] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append({"check": name, "status": status, "detail": detail})
        if status == "FAIL":
            self.passed = False

    def merge(self, other: ValidationResult) -> None:
        self.checks.extend(other.checks)
        if not other.passed:
            self.passed = False


def validate_model_provenance() -> ValidationResult:
    """Verify bundled model cards exist and are parseable."""
    result = ValidationResult(passed=True)
    root = resolve_model_root()
    expected = set(STANDARD_ACCESS_MODEL_IDS)
    found = {path.stem for path in root.glob("*.inc")}
    missing = expected - found
    extra = found - expected
    if missing:
        result.add(
            "model_inventory",
            "FAIL",
            f"missing={sorted(missing)} extra={sorted(extra)}",
        )
    elif extra:
        result.add(
            "model_inventory",
            "PASS",
            f"{len(expected)} required access models (+{len(extra)} extra: {sorted(extra)})",
        )
    else:
        result.add("model_inventory", "PASS", f"{len(found)} access models")
    return result


def validate_device_metrics_csv(path: Path, *, min_models: int | None = None) -> ValidationResult:
    """Validate device_metrics.csv schema and completeness."""
    result = ValidationResult(passed=True)
    if not path.is_file():
        result.add("device_metrics_exists", "FAIL", f"missing {path}")
        return result

    result.add("device_metrics_exists", "PASS", path.name)
    df = pd.read_csv(path)
    missing_cols = [col for col in REQUIRED_DEVICE_COLUMNS if col not in df.columns]
    if missing_cols:
        result.add("device_metrics_schema", "FAIL", f"missing columns: {missing_cols}")
        return result
    result.add("device_metrics_schema", "PASS", f"{len(df.columns)} columns")

    expected_models = set(list_access_model_ids())
    found_models = set(df["model_id"].astype(str))
    if not expected_models.issubset(found_models):
        result.add(
            "device_metrics_coverage",
            "FAIL",
            f"missing models: {sorted(expected_models - found_models)}",
        )
    else:
        result.add("device_metrics_coverage", "PASS", f"{len(found_models)} models")

    if min_models is not None and len(found_models) < min_models:
        result.add("device_metrics_min_models", "FAIL", f"expected >= {min_models}")

    for col in ("ion_a", "ioff_a", "ron_ohm"):
        if df[col].isna().all():
            result.add(f"metric_{col}", "FAIL", "all values missing")
        elif df[col].isna().any():
            result.add(f"metric_{col}", "WARN", "some values missing")
        else:
            result.add(f"metric_{col}", "PASS", "populated")

    return result


def validate_corner_sweep_csv(path: Path) -> ValidationResult:
    """Validate the all-corners aggregate produced by corner_sweep."""
    result = ValidationResult(passed=True)
    if not path.is_file():
        result.add("corner_sweep_csv", "FAIL", f"missing {path}")
        return result

    df = pd.read_csv(path)
    expected_rows = expected_corner_sweep_rows()
    result.add("corner_sweep_csv", "PASS", path.name)
    if len(df) < expected_rows:
        result.add(
            "corner_sweep_rows",
            "FAIL",
            f"expected {expected_rows} rows, found {len(df)}",
        )
    else:
        result.add("corner_sweep_rows", "PASS", f"{len(df)} rows")

    corners = load_corner_names()
    found_corners = set(df["corner"].astype(str))
    missing_corners = set(corners) - found_corners
    if missing_corners:
        result.add("corner_sweep_corners", "FAIL", f"missing corners: {sorted(missing_corners)}")
    else:
        result.add("corner_sweep_corners", "PASS", f"{len(found_corners)} corners")

    for corner in corners:
        corner_dir = path.parent / corner
        if corner_dir.is_dir():
            result.add(f"corner_dir_{corner}", "PASS", corner_dir.name)
        else:
            result.add(f"corner_dir_{corner}", "WARN", "per-corner tree missing")

    for rel_name in ("cell_1t1c_metrics_all_corners.csv", "mini_array_metrics_all_corners.csv"):
        aggregate = path.parent / rel_name
        if aggregate.is_file():
            result.add(rel_name, "PASS", rel_name)
        else:
            result.add(rel_name, "WARN", f"missing {rel_name}")

    return result


def validate_multi_tool_tree(results_dir: Path, *, corner: str = "tt") -> ValidationResult:
    """Validate per-simulator trees and comparison artifacts."""
    result = ValidationResult(passed=True)
    backends = discover_simulator_backends(results_dir, corner)
    if not backends:
        result.add("multi_tool_backends", "FAIL", "no simulator result trees found")
        return result

    result.add("multi_tool_backends", "PASS", ", ".join(backends))
    for backend in backends:
        metrics = results_dir / backend / corner / "device_metrics.csv"
        partial = validate_device_metrics_csv(metrics)
        for row in partial.checks:
            row = dict(row)
            row["check"] = f"{backend}_{row['check']}"
            result.checks.append(row)
            if row["status"] == "FAIL":
                result.passed = False

    compare_dir = results_dir / "simulator_compare" / corner
    rel_diff = compare_dir / "device_metrics_rel_diff.csv"
    compare_md = compare_dir / "SIMULATOR_COMPARE.md"
    if len(backends) >= 2:
        if rel_diff.is_file():
            result.add("simulator_compare_csv", "PASS", rel_diff.name)
        else:
            result.add("simulator_compare_csv", "FAIL", f"missing {rel_diff}")
        if compare_md.is_file():
            result.add("simulator_compare_report", "PASS", compare_md.name)
        else:
            result.add("simulator_compare_report", "WARN", "SIMULATOR_COMPARE.md missing")
    else:
        result.add(
            "simulator_compare_csv",
            "WARN",
            f"only one backend ({backends[0]}); cross-tool diff tables skipped",
        )

    return result


def validate_results_tree(results_dir: Path, *, suite: str = "device", corner: str = "tt") -> ValidationResult:
    """Run suite-aware validation checks on a results directory."""
    combined = ValidationResult(passed=True)
    combined.merge(validate_model_provenance())

    spec = suite_spec(suite, results_dir, corner=corner)

    if suite == "corner_sweep":
        combined.merge(validate_corner_sweep_csv(spec.metrics_csv))
        combined.merge(validate_device_metrics_csv(spec.metrics_csv))
    elif suite == "multi_tool":
        combined.merge(validate_multi_tool_tree(results_dir, corner=corner))
    elif suite == "ccell":
        sweep = results_dir / "ccell_sweep.csv"
        if sweep.is_file():
            combined.add("ccell_sweep_csv", "PASS", sweep.name)
            df = pd.read_csv(sweep)
            if len(df) >= 7:
                combined.add("ccell_sweep_rows", "PASS", f"{len(df)} rows")
            else:
                combined.add("ccell_sweep_rows", "WARN", f"only {len(df)} rows")
        else:
            combined.add("ccell_sweep_csv", "FAIL", f"missing {sweep}")
    elif suite == "sense_amp":
        decks = list(results_dir.glob("decks/**/*.sp"))
        signal = results_dir / "read_signal_all_corners.csv"
        if not signal.is_file():
            signal = results_dir / "read_signal_tt.csv"
        if signal.is_file():
            combined.add("sense_amp_signal", "PASS", signal.name)
        elif decks:
            combined.add("sense_amp_signal", "WARN", "decks only (Spectre/HSPICE required for ΔV_BL)")
        else:
            combined.add("sense_amp_signal", "FAIL", "no read-path artifacts")
    elif suite == "validation":
        check_data = results_dir / "data"
        if check_data.is_dir():
            combined.add("validation_data", "PASS", "data/")
        else:
            combined.add("validation_data", "WARN", "validation data exports missing")
    elif suite == "all":
        for child in BENCHMARK_SUITES:
            child_dir = results_dir / child
            if child_dir.is_dir():
                combined.merge(validate_results_tree(child_dir, suite=child, corner=corner))
        aggregate = results_dir / "RESULTS.md"
        if aggregate.is_file():
            combined.add("aggregate_results", "PASS", aggregate.name)
        else:
            combined.add("aggregate_results", "WARN", "aggregate RESULTS.md missing")
    elif spec.metrics_csv is not None:
        combined.merge(validate_device_metrics_csv(spec.metrics_csv))

    manifest = results_dir / "MANIFEST.json"
    if manifest.is_file():
        combined.add("manifest_exists", "PASS", manifest.name)
    else:
        combined.add("manifest_exists", "WARN", "MANIFEST.json not generated yet")

    results_md = results_dir / "RESULTS.md"
    if results_md.is_file() and results_md.stat().st_size > 200:
        combined.add("results_report", "PASS", results_md.name)
    else:
        combined.add("results_report", "WARN", "RESULTS.md missing or empty")

    return combined
