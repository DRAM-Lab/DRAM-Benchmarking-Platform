"""Tests for benchmark suite path resolution and validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from dram_benchmark.suites import (
    expected_corner_sweep_rows,
    load_corner_names,
    resolve_bench_input_dir,
    suite_spec,
)
from dram_benchmark.validation import (
    validate_corner_sweep_csv,
    validate_multi_tool_tree,
    validate_results_tree,
)


@pytest.fixture
def corner_sweep_csv(tmp_path: Path) -> Path:
    rows = []
    for corner in load_corner_names():
        for model_id in (
            "BCAT_125",
            "VCT_082",
            "VCT_091",
            "VCT_102",
            "VCT_125",
            "3D_gaa_Si",
            "3D_gaa_AOS",
        ):
            rows.append(
                {
                    "model_id": model_id,
                    "architecture": "VCT",
                    "corner": corner,
                    "temp_c": 27.0,
                    "vdd": 0.9,
                    "ion_a": 1e-6,
                    "ioff_a": 1e-14,
                    "ron_ohm": 1e5,
                    "cgg_f": 1e-17,
                    "fpitch_m": 6e-8,
                    "vsat": 25000.0,
                }
            )
    path = tmp_path / "device_metrics_all_corners.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    for corner in load_corner_names():
        (tmp_path / corner).mkdir()
    return path


def test_suite_spec_corner_sweep_paths(tmp_path: Path, corner_sweep_csv: Path) -> None:
    spec = suite_spec("corner_sweep", tmp_path)
    assert spec.metrics_csv == corner_sweep_csv
    assert spec.report_corner_label_resolved == "all"


def test_suite_spec_corner_sweep_multi_sim_paths(tmp_path: Path) -> None:
    backend = tmp_path / "spectre"
    backend.mkdir(parents=True)
    metrics = backend / "device_metrics_all_corners.csv"
    pd.DataFrame({"model_id": ["VCT_082"], "corner": ["tt"]}).to_csv(metrics, index=False)
    spec = suite_spec("corner_sweep", tmp_path)
    assert spec.metrics_csv == metrics


def test_resolve_bench_input_dir_prefers_corner_sweep_backend(tmp_path: Path) -> None:
    sweep = tmp_path / "corner_sweep" / "spectre"
    sweep.mkdir(parents=True)
    pd.DataFrame({"model_id": ["VCT_082"]}).to_csv(
        sweep / "device_metrics_all_corners.csv", index=False
    )
    device = tmp_path / "device" / "spectre" / "tt"
    device.mkdir(parents=True)
    pd.DataFrame({"model_id": ["VCT_082"]}).to_csv(device / "device_metrics.csv", index=False)

    resolved = resolve_bench_input_dir(tmp_path)
    assert resolved == sweep


def test_resolve_bench_input_dir_device_multi_sim_single_corner(tmp_path: Path) -> None:
    device = tmp_path / "device" / "spectre" / "tt"
    device.mkdir(parents=True)
    pd.DataFrame({"model_id": ["VCT_082"]}).to_csv(device / "device_metrics.csv", index=False)

    resolved = resolve_bench_input_dir(tmp_path)
    assert resolved == device


def test_suite_spec_multi_tool_paths(tmp_path: Path) -> None:
    metrics = tmp_path / "ngspice" / "tt" / "device_metrics.csv"
    metrics.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "model_id": ["VCT_082"],
            "architecture": ["VCT"],
            "corner": ["tt"],
            "temp_c": [27.0],
            "vdd": [0.9],
            "ion_a": [1e-6],
            "ioff_a": [1e-14],
            "ron_ohm": [1e5],
            "cgg_f": [1e-17],
            "fpitch_m": [6e-8],
            "vsat": [25000.0],
        }
    ).to_csv(metrics, index=False)
    spec = suite_spec("multi_tool", tmp_path)
    assert spec.metrics_csv == metrics
    assert spec.simulator_compare_dir is None


def test_validate_corner_sweep_csv(corner_sweep_csv: Path) -> None:
    result = validate_corner_sweep_csv(corner_sweep_csv)
    assert result.passed
    assert expected_corner_sweep_rows() == 42


def test_validate_multi_tool_single_backend_warns(tmp_path: Path) -> None:
    from dram_benchmark.paths import STANDARD_ACCESS_MODEL_IDS

    for model_id in STANDARD_ACCESS_MODEL_IDS:
        metrics = tmp_path / "ngspice" / "tt" / "device_metrics.csv"
        metrics.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for model_id in STANDARD_ACCESS_MODEL_IDS:
        rows.append(
            {
                "model_id": model_id,
                "architecture": "VCT",
                "corner": "tt",
                "temp_c": 27.0,
                "vdd": 0.9,
                "ion_a": 1e-6,
                "ioff_a": 1e-14,
                "ron_ohm": 1e5,
                "cgg_f": 1e-17,
                "fpitch_m": 6e-8,
                "vsat": 25000.0,
            }
        )
    pd.DataFrame(rows).to_csv(metrics, index=False)
    result = validate_multi_tool_tree(tmp_path)
    assert result.passed
    assert any(row["check"] == "simulator_compare_csv" and row["status"] == "WARN" for row in result.checks)


def test_validate_results_tree_validation_lane(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "device_metrics.csv").write_text("model_id\nVCT_082\n", encoding="utf-8")
    (tmp_path / "RESULTS.md").write_text("# Validation\n\n" + "x" * 300, encoding="utf-8")
    result = validate_results_tree(tmp_path, suite="validation")
    assert result.passed
    assert any(row["check"] == "validation_data" for row in result.checks)


def test_validate_results_tree_ccell_lane(tmp_path: Path) -> None:
    rows = [{"model_id": f"VCT_{n}", "c_cell_f": 1e-15} for n in (82, 91, 102, 125)]
    rows.extend([{"model_id": "BCAT_125", "c_cell_f": 1e-15}, {"model_id": "3D_gaa_Si", "c_cell_f": 1e-15}, {"model_id": "3D_gaa_AOS", "c_cell_f": 1e-15}])
    pd.DataFrame(rows).to_csv(tmp_path / "ccell_sweep.csv", index=False)
    (tmp_path / "RESULTS.md").write_text("# Ccell\n\n" + "x" * 300, encoding="utf-8")
    result = validate_results_tree(tmp_path, suite="ccell")
    assert result.passed


def test_pareto_derive_flat_device_layout(tmp_path: Path) -> None:
    from pareto.derive import derive_pareto_points

    rows = []
    for model_id in ("BCAT_125", "VCT_082", "VCT_091", "VCT_102", "VCT_125", "3D_gaa_Si", "3D_gaa_AOS"):
        rows.append(
            {
                "model_id": model_id,
                "architecture": "VCT",
                "corner": "tt",
                "temp_c": 27.0,
                "vdd": 0.9,
                "ioff_a": 1e-14,
                "esw_j": 1e-17,
                "fpitch_m": 6e-8,
            }
        )
    pd.DataFrame(rows).to_csv(tmp_path / "device_metrics.csv", index=False)
    cell_rows = []
    for model_id in ("BCAT_125", "VCT_082", "VCT_091", "VCT_102", "VCT_125", "3D_gaa_Si", "3D_gaa_AOS"):
        for ccell in (10.0, 20.0, 30.0):
            cell_rows.append(
                {
                    "model_id": model_id,
                    "architecture": "VCT",
                    "corner": "tt",
                    "ccell_ff": ccell,
                    "i_hold_a": 1e-11,
                    "q_read_c": 1e-18,
                    "t_read_s": 20e-9,
                    "t_write_s": 10e-9,
                }
            )
    pd.DataFrame(cell_rows).to_csv(tmp_path / "cell_1t1c_metrics.csv", index=False)
    points = derive_pareto_points(bench_root=tmp_path, corners=["tt"])
    assert points
