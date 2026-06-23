"""Tests for read-path RESULTS.md reporting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sense_amp.report import generate_deck_only_report, generate_report


def test_deck_only_report_has_scope_section(tmp_path: Path) -> None:
    path = tmp_path / "RESULTS.md"
    generate_deck_only_report(path, corner="tt", deck_count=84)
    text = path.read_text(encoding="utf-8")
    assert "Read-Path Signal & SA Requirement Sweep" in text
    assert "Not in scope" in text
    assert "deck generation only" in text


def test_signal_report_executive_summary(tmp_path: Path) -> None:
    signal_rows = []
    for model_id in ("VCT_082", "VCT_125"):
        row = {
            "model_id": model_id,
            "ccell_ff": 20.0,
            "vbl_pre_fraction": 0.5,
            "dv_10ns": 0.08 if model_id == "VCT_125" else 0.05,
        }
        signal_rows.append(row)
    signal_df = pd.DataFrame(signal_rows)
    spec_df = pd.DataFrame(
        [
            {
                "model_id": "VCT_082",
                "ccell_ff": 20.0,
                "max_sigma_os_mv": 10.0,
                "min_gain": 10.0,
                "earliest_t_en_ns": 10.0,
                "recommended_vbl_pre_fraction": 0.5,
                "min_delta_v_bl_mv": 45.0,
                "status": "PASS",
            },
            {
                "model_id": "VCT_125",
                "ccell_ff": 20.0,
                "max_sigma_os_mv": 15.0,
                "min_gain": 5.0,
                "earliest_t_en_ns": 8.0,
                "recommended_vbl_pre_fraction": 0.5,
                "min_delta_v_bl_mv": 30.0,
                "status": "PASS",
            },
        ]
    )
    path = tmp_path / "RESULTS.md"
    generate_report(
        path,
        signal_df=signal_df,
        spec_df=spec_df,
        corner="tt",
        figures_dir=tmp_path / "figures",
    )
    text = path.read_text(encoding="utf-8")
    assert "Executive summary" in text
    assert "Per-node SA requirements" in text
    assert "How to analyze the CSVs" in text
    assert "VCT_125" in text
