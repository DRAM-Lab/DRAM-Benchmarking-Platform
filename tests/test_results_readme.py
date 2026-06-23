"""Tests for unified RESULTS.md presentation."""

from __future__ import annotations

from pathlib import Path

from dram_benchmark.report.platform import embed_suite_report, finalize_results_markdown
from dram_benchmark.report.summary import write_aggregate_summary


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


def test_embed_suite_report_rewrites_figure_paths(tmp_path: Path) -> None:
    suite_dir = tmp_path / "device"
    suite_dir.mkdir()
    (suite_dir / "figures").mkdir()
    (suite_dir / "figures" / "pareto.svg").write_text("<svg/>", encoding="utf-8")
    (suite_dir / "RESULTS.md").write_text(
        "\n".join(
            [
                "# OpenDRAMBench — Results",
                "",
                "## Contents",
                "",
                "---",
                "## Device benchmark",
                "",
                "![Pareto](figures/pareto.svg)",
                "",
                "## Artifacts",
                "",
                "| File | Description |",
                "|------|-------------|",
                "| [`figures/`](figures/) | Plots |",
                "",
                "## Reproduce",
                "",
                "```bash",
                "./scripts/run_experiments.sh",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    embedded = embed_suite_report("device", suite_dir)
    assert "## Suite: device" in embedded
    assert "![Pareto](device/figures/pareto.svg)" in embedded
    assert "## Artifacts" not in embedded
    assert "## Reproduce" not in embedded


def test_write_aggregate_summary_inlines_suite_reports(tmp_path: Path) -> None:
    device_dir = tmp_path / "device"
    device_dir.mkdir()
    (device_dir / "RESULTS.md").write_text(
        "\n".join(
            [
                "# OpenDRAMBench — Results",
                "",
                "## Contents",
                "",
                "---",
                "## Device benchmark",
                "",
                "| Model | Ion |",
                "| --- | --- |",
                "| VCT_082 | 1e-6 |",
            ]
        ),
        encoding="utf-8",
    )

    write_aggregate_summary(tmp_path, corner="tt")
    finalize_results_markdown(tmp_path / "RESULTS.md", tmp_path, suite="all", corner="tt")

    text = (tmp_path / "RESULTS.md").read_text(encoding="utf-8")
    assert text.startswith("# OpenDRAMBench — Aggregate Results\n")
    assert "## Suite index" in text
    assert "## Suite: device" in text
    assert "### Device benchmark" in text
    assert "VCT_082" in text
    assert "## Reproduce" in text
    assert "## Suite layout" not in text
