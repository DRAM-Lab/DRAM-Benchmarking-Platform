"""Tests for bench report generation with incomplete metrics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bench.report import _executive_summary, generate_report


def test_executive_summary_all_na_t_read() -> None:
    device_df = pd.DataFrame(
        {
            "model_id": ["M1", "M2"],
            "ion_a": [1e-5, 2e-5],
            "ioff_a": [1e-14, 2e-14],
        }
    )
    cell_df = pd.DataFrame(
        {
            "model_id": ["M1", "M2"],
            "ccell_ff": [20.0, 20.0],
            "t_read_s": [float("nan"), float("nan")],
        }
    )
    summary = _executive_summary(device_df, cell_df)
    assert "Highest Ion" in summary
    assert "Fastest 1T1C read" not in summary


def test_generate_report_with_empty_cell_metrics(tmp_path: Path) -> None:
    metrics = tmp_path / "device_metrics.csv"
    cell = tmp_path / "cell_1t1c_metrics.csv"
    output = tmp_path / "RESULTS.md"
    pd.DataFrame(
        {
            "model_id": ["BCAT_125", "VCT_082"],
            "architecture": ["BCAT", "VCT"],
            "corner": ["tt", "tt"],
            "ion_a": [0.0, 0.0],
            "ioff_a": [0.0, 0.0],
            "ron_ohm": [float("nan"), float("nan")],
            "vsat": [1910.0, 25420.0],
        }
    ).to_csv(metrics, index=False)
    pd.DataFrame(
        {
            "model_id": ["BCAT_125", "VCT_082"],
            "architecture": ["BCAT", "VCT"],
            "corner": ["tt", "tt"],
            "ccell_ff": [20.0, 20.0],
            "t_write_s": [float("nan"), float("nan")],
            "t_read_s": [float("nan"), float("nan")],
            "i_hold_a": [float("nan"), float("nan")],
            "q_read_c": [float("nan"), float("nan")],
        }
    ).to_csv(cell, index=False)

    path = generate_report(
        metrics,
        output,
        corner="tt",
        cell_csv=cell,
        reference_corner="tt",
    )
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Device benchmark" in text
    assert "Fastest 1T1C read" not in text
