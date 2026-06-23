"""Tests for shared markdown table rendering."""

from __future__ import annotations

import pandas as pd

from dram_benchmark.report.markdown_tables import df_to_markdown, join_md_row, sanitize_md_cell


def test_sanitize_md_cell_escapes_pipes() -> None:
    assert sanitize_md_cell("|ΔV|@5ns_mV") == "\\|ΔV\\|@5ns_mV"
    assert sanitize_md_cell("max |rel diff|") == "max \\|rel diff\\|"


def test_df_to_markdown_escapes_column_headers_with_pipes() -> None:
    df = pd.DataFrame(
        {
            "|ΔV|@5ns_mV": [15.95],
            "model_id": ["VCT_082"],
        }
    )
    table = df_to_markdown(df)
    assert "\\|ΔV\\|@5ns_mV" in table
    assert "| model_id |" in table
    assert table.count("\n") >= 2


def test_join_md_row_renders_valid_two_column_table() -> None:
    table = "\n".join(
        [
            join_md_row(["Comparison", "Max |rel diff|"]),
            join_md_row(["---", "---"]),
            join_md_row(["ion_a ngspice vs spectre", "1.405"]),
        ]
    )
    lines = table.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("| Comparison | Max \\|rel diff\\| |")
