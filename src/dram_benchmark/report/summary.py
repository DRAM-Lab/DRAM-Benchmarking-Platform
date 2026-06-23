"""Aggregate reporting across OpenDRAMBench benchmark suites."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dram_benchmark.suites import BENCHMARK_SUITES, SuiteSpec, discover_simulator_backends, suite_spec


def write_aggregate_summary(parent_dir: Path, *, corner: str = "tt", simulator: str | None = None) -> Path:
    """Write or refresh the top-level aggregate RESULTS.md for SUITE=all."""
    parent_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# OpenDRAMBench — Aggregate Results",
        "",
        f"**Generated:** {timestamp}",
        f"**Reference corner:** {corner}",
        "",
        "Self-contained benchmark automation for Open DRAM Model cards. "
        "This aggregate indexes each benchmark lane; open a suite report for detailed tables.",
        "",
        "| Suite | Role | Primary artifact |",
        "|-------|------|------------------|",
        "| `device` | Full access-device + 1T1C + mini-array @ TT | `device/device_metrics.csv` |",
        "| `corner_sweep` | Six-corner PVT matrix (device + 1T1C + mini-array) | `corner_sweep/device_metrics_all_corners.csv` |",
        "| `multi_tool` | Cross-simulator agreement | `multi_tool/simulator_compare/` |",
        "| `sense_amp` | Read-path ΔV_BL + derived SA requirements | `sense_amp/sa_spec_per_node.csv` |",
        "| `ccell` | Ccell retention vs read binding | `ccell/ccell_sweep.csv` |",
        "| `validation` | Golden + literature + paper audit | `validation/RESULTS.md` |",
        "",
        "## Suite index",
        "",
    ]

    for suite_name in BENCHMARK_SUITES:
        spec = suite_spec(suite_name, parent_dir / suite_name, corner=corner)
        rel = f"{suite_name}/RESULTS.md"
        if suite_name == "corner_sweep":
            artifact = f"{suite_name}/device_metrics_all_corners.csv"
        elif suite_name == "multi_tool":
            backends = discover_simulator_backends(spec.results_dir, corner)
            artifact = f"{suite_name}/simulator_compare/{corner}/"
            if backends:
                artifact += f" ({', '.join(backends)})"
        elif suite_name == "ccell":
            artifact = f"{suite_name}/ccell_sweep.csv"
        elif suite_name == "validation":
            artifact = f"{suite_name}/data/"
        elif suite_name == "sense_amp":
            artifact = f"{suite_name}/sa_spec_per_node.csv (or read_signal_tt.csv / decks/)"
        else:
            artifact = f"{suite_name}/device_metrics.csv"
        status = "ready" if (spec.results_dir / "RESULTS.md").is_file() else "pending"
        lines.append(
            f"- **{suite_name}** [{status}] — [{rel}]({rel}), primary: `{artifact}`"
        )

    if simulator:
        lines.extend(["", f"**Pinned simulator (device/corner_sweep):** `{simulator}`"])

    out = parent_dir / "RESULTS.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
