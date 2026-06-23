"""Tests for unified RESULTS.md presentation."""

from __future__ import annotations

from pathlib import Path

from dram_benchmark.report.platform import finalize_results_markdown


def test_finalize_results_markdown_combines_index_and_lane_body(tmp_path: Path) -> None:
    (tmp_path / "device_metrics.csv").write_text("model_id\nVCT_082\n", encoding="utf-8")
    (tmp_path / "MANIFEST.json").write_text(
        '{"generated_at":"2026-06-23T06:00:00Z","model_bundle_revision":"abc123","status":"complete"}',
        encoding="utf-8",
    )
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()
    (fig_dir / "pareto_ion_ioff.svg").write_text("<svg/>", encoding="utf-8")

    results_md = tmp_path / "RESULTS.md"
    results_md.write_text(
        "# Device benchmark\n\n## Executive summary\n\n- bullet\n",
        encoding="utf-8",
    )
    finalize_results_markdown(
        results_md,
        tmp_path,
        suite="device",
        corner="tt",
        simulator="ngspice",
    )
    text = results_md.read_text(encoding="utf-8")

    assert text.startswith("# OpenDRAMBench — Results\n")
    assert "## Run summary" in text
    assert "## Contents" in text
    assert "[Executive summary](#executive-summary)" in text
    assert "## Device benchmark\n" in text
    assert "## Artifacts" in text
    assert "[`device_metrics.csv`](device_metrics.csv)" in text
    assert "[`figures/`](figures/)" in text
    assert "## Reproduce" in text
    assert "README.md" not in text


def test_finalize_results_markdown_is_idempotent(tmp_path: Path) -> None:
    results_md = tmp_path / "RESULTS.md"
    results_md.write_text("# Device benchmark\n\n## Section\n\nbody\n", encoding="utf-8")
    finalize_results_markdown(results_md, tmp_path, suite="device", corner="tt")
    first = results_md.read_text(encoding="utf-8")
    finalize_results_markdown(results_md, tmp_path, suite="device", corner="tt")
    assert results_md.read_text(encoding="utf-8") == first
