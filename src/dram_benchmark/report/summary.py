"""Aggregate reporting across OpenDRAMBench benchmark suites."""

from __future__ import annotations

from pathlib import Path

from dram_benchmark.report.platform import embed_suite_report
from dram_benchmark.suites import BENCHMARK_SUITES, suite_spec


def write_aggregate_summary(parent_dir: Path, *, corner: str = "tt", simulator: str | None = None) -> Path:
    """Write aggregate RESULTS.md body with full inlined suite reports for SUITE=all."""
    parent_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "## Suite index",
        "",
        "| Suite | Role | Status | Detail |",
        "|-------|------|--------|--------|",
    ]

    for suite_name in BENCHMARK_SUITES:
        spec = suite_spec(suite_name, parent_dir / suite_name, corner=corner)
        rel = f"{suite_name}/RESULTS.md"
        if suite_name == "corner_sweep":
            role = "Six-corner PVT matrix (device + 1T1C + mini-array)"
        elif suite_name == "multi_tool":
            role = "Cross-simulator agreement"
        elif suite_name == "sense_amp":
            role = "Read-path ΔV_BL + derived SA requirements"
        elif suite_name == "ccell":
            role = "Ccell retention vs read binding"
        elif suite_name == "validation":
            role = "Golden + literature + paper audit"
        else:
            role = "Full access-device + 1T1C + mini-array @ TT"
        status = "ready" if (spec.results_dir / "RESULTS.md").is_file() else "pending"
        lines.append(f"| `{suite_name}` | {role} | {status} | [{rel}]({rel}) |")

    if simulator:
        lines.extend(["", f"**Pinned simulator (device/corner_sweep):** `{simulator}`"])

    lines.extend(["", "---", ""])

    for suite_name in BENCHMARK_SUITES:
        lines.append(embed_suite_report(suite_name, parent_dir / suite_name).rstrip())
        lines.append("")
        lines.append("---")
        lines.append("")

    out = parent_dir / "RESULTS.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out
