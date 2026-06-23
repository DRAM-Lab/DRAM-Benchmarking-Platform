"""Platform wrapper and footer for unified RESULTS.md reports."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dram_benchmark.paths import model_bundle_revision, resolve_model_root
from dram_benchmark.suites import BENCHMARK_SUITES

_PLATFORM_TITLE = "# OpenDRAMBench — Results"
_AGGREGATE_TITLE = "# OpenDRAMBench — Aggregate Results"


def _demote_h1(markdown: str) -> str:
    """Demote top-level headings so the platform title remains the sole H1."""
    out: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            out.append("#" + line)
        else:
            out.append(line)
    return "\n".join(out)


def _demote_headings(markdown: str, levels: int = 1) -> str:
    """Increase heading level by ``levels`` (# -> ##, ## -> ###, …)."""
    if levels <= 0:
        return markdown
    out: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            if 0 < hashes < 6:
                out.append("#" * (hashes + levels) + line[hashes:])
                continue
        out.append(line)
    return "\n".join(out)


def _extract_toc(markdown: str) -> str:
    """Build a shallow table of contents from ## headings."""
    headings: list[tuple[str, str]] = []
    for line in markdown.splitlines():
        match = re.match(r"^## (.+)$", line)
        if not match:
            continue
        title = match.group(1).strip()
        anchor = re.sub(r"[^\w\s-]", "", title.lower())
        anchor = re.sub(r"\s+", "-", anchor.strip())
        headings.append((title, anchor))
    if not headings:
        return ""
    lines = ["## Contents", ""]
    for title, anchor in headings:
        lines.append(f"- [{title}](#{anchor})")
    lines.append("")
    return "\n".join(lines)


def _read_manifest(results_dir: Path) -> dict[str, Any] | None:
    path = results_dir / "MANIFEST.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _simulator_label(manifest: dict[str, Any] | None, results_dir: Path) -> str:
    if manifest:
        sim = manifest.get("simulator")
        if sim:
            return str(sim)
        tools = manifest.get("tool_versions") or {}
        active = [name for name, ver in tools.items() if ver]
        if active:
            return ", ".join(active)
    try:
        from bench.simulator import resolve_backend

        return resolve_backend().value
    except Exception:
        pass
    return "—"


def _artifact_rows(results_dir: Path, *, suite: str) -> list[tuple[str, str]]:
    """Return (relative_path, description) for artifacts that exist."""
    candidates: list[tuple[str, str]] = [
        ("MANIFEST.json", "Provenance manifest with SHA-256 checksums"),
        ("device_metrics.csv", "Device-level metrics (Ion, Ioff, Ron, Cgg, …)"),
        ("cell_1t1c_metrics.csv", "1T1C transient sweep (10 / 20 / 30 fF)"),
        ("cell_1t1c_metrics_20ff.csv", "1T1C @ 20 fF reference (one row per model)"),
        ("mini_array_metrics.csv", "Mini-array BL RC and settle metrics"),
        ("device_metrics_all_corners.csv", "Six-corner PVT device matrix"),
        ("cell_1t1c_metrics_all_corners.csv", "1T1C metrics across all corners"),
        ("mini_array_metrics_all_corners.csv", "Mini-array metrics across all corners"),
        ("ccell_sweep.csv", "Ccell retention vs read binding sweep"),
        ("pareto_roadmap.csv", "Pareto roadmap points (ccell dependency)"),
        ("read_signal_tt.csv", "Read-path ΔV_BL samples @ TT"),
        ("read_signal_all_corners.csv", "Read-path ΔV_BL across all PVT corners"),
        ("sa_spec_per_node.csv", "Derived SA requirements per access node"),
    ]
    rows: list[tuple[str, str]] = []
    for rel, desc in candidates:
        if (results_dir / rel).is_file():
            rows.append((rel, desc))

    if suite == "multi_tool":
        compare = results_dir / "simulator_compare"
        if compare.is_dir():
            rows.append(("simulator_compare/", "Cross-simulator agreement tables"))

    if suite == "validation":
        data_dir = results_dir / "data"
        if data_dir.is_dir():
            rows.append(("data/", "Validation audit CSV exports"))

    decks = results_dir / "decks"
    if decks.is_dir() and any(decks.rglob("*.sp")):
        rows.append(("decks/", "Generated SPICE decks"))

    figures = results_dir / "figures"
    if figures.is_dir() and any(figures.glob("*.svg")):
        rows.append(("figures/", "Summary SVG plots"))

    return rows


def _artifacts_section(results_dir: Path, *, suite: str) -> str:
    rows = _artifact_rows(results_dir, suite=suite)
    if not rows:
        return ""
    lines = [
        "## Artifacts",
        "",
        "| File | Description |",
        "|------|-------------|",
    ]
    for rel, desc in rows:
        lines.append(f"| [`{rel}`]({rel}) | {desc} |")
    lines.append("")
    return "\n".join(lines)


def _suite_layout_section(results_dir: Path) -> str:
    if not any((results_dir / name).is_dir() for name in BENCHMARK_SUITES):
        return ""

    lines = [
        "## Suite layout",
        "",
        "Full benchmark run (`SUITE=all`). Each lane has its own report:",
        "",
        "| Suite | Report | Role |",
        "|-------|--------|------|",
    ]
    roles = {
        "device": "Access device + 1T1C + mini-array @ TT",
        "corner_sweep": "Six-corner PVT matrix (device + 1T1C + mini-array)",
        "multi_tool": "Cross-simulator agreement",
        "sense_amp": "Read-path ΔV_BL + SA requirements",
        "ccell": "Ccell retention vs read binding",
        "validation": "Golden + literature + paper audit",
    }
    for name in BENCHMARK_SUITES:
        report = f"{name}/RESULTS.md"
        status = "ready" if (results_dir / name / "RESULTS.md").is_file() else "pending"
        lines.append(f"| `{name}` | [{report}]({report}) [{status}] | {roles.get(name, '')} |")
    lines.append("")
    return "\n".join(lines)


def _reproduce_section(*, suite: str, corner: str, results_dir: Path) -> str:
    replay_line = (
        f"SUITE=device ./scripts/run_experiments.sh  # device lane only (faster)"
        if suite == "all"
        else f"SUITE={suite} ./scripts/run_experiments.sh     # replay this suite"
    )
    return "\n".join(
        [
            "## Reproduce",
            "",
            "```bash",
            "./scripts/run_experiments.sh                    # default: full benchmark bundle",
            replay_line,
            f"dram-bench run --suite {suite} --corner {corner} --output {results_dir.name}",
            "```",
            "",
            "Metric definitions: [docs/benchmark_spec.md](../docs/benchmark_spec.md)",
            "",
            "---",
            "*Report produced by `dram-bench` / `run_experiments.sh`*",
            "",
        ]
    )


def _run_summary_table(
    *,
    suite: str,
    corner: str,
    simulator: str,
    timestamp: str,
    bundle: str,
    status: str = "complete",
) -> str:
    return "\n".join(
        [
            "## Run summary",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Suite | `{suite}` |",
            f"| Corner | `{corner}` |",
            f"| Simulator | {simulator} |",
            f"| Generated | {timestamp} |",
            f"| Status | {status} |",
            f"| Model bundle | OpenDRAMmodelV1 `{bundle}` |",
            "",
        ]
    )


def _strip_lane_footer(body: str) -> str:
    """Remove lane-local artifact/footer blocks replaced by the platform wrapper."""
    body = re.sub(
        r"\n## Artifacts\n.*?\n---\n\*Report produced by.*?\*\n?",
        "\n",
        body,
        flags=re.DOTALL,
    )
    body = re.sub(r"\n## Artifacts\n.*?(?=\n## [^#]|\Z)", "\n", body, flags=re.DOTALL)
    body = re.sub(r"\n## Reproduce\n.*", "\n", body, flags=re.DOTALL)
    return body.rstrip() + "\n"


def extract_lane_body(markdown: str) -> str:
    """Return report body from a finalized lane RESULTS.md (strip platform wrapper)."""
    text = markdown.strip()
    if text.startswith(_PLATFORM_TITLE) or text.startswith(_AGGREGATE_TITLE):
        parts = text.split("\n---\n", 1)
        body = parts[1] if len(parts) == 2 else text
    else:
        body = _demote_h1(text)
    return _strip_lane_footer(body.strip())


def prefix_suite_asset_paths(markdown: str, suite_prefix: str) -> str:
    """Rewrite relative asset paths when a lane report is embedded in the aggregate."""

    def fix_path(path: str) -> str:
        if path.startswith(("http://", "https://", "/")) or "://" in path:
            return path
        if path.startswith("../"):
            return path
        if path.startswith(f"{suite_prefix}/"):
            return path
        return f"{suite_prefix}/{path}"

    def repl_link(match: re.Match[str]) -> str:
        label, path = match.group(1), match.group(2)
        return f"[{label}]({fix_path(path)})"

    return re.sub(r"\[([^\]]*)\]\(([^)]+)\)", repl_link, markdown)


def embed_suite_report(suite_name: str, suite_dir: Path) -> str:
    """Format one suite lane for inclusion in the aggregate RESULTS.md."""
    report = suite_dir / "RESULTS.md"
    if not report.is_file():
        return f"## Suite: {suite_name}\n\n_Report not generated yet._\n"

    body = extract_lane_body(report.read_text(encoding="utf-8"))
    body = _demote_headings(body, levels=1)
    body = prefix_suite_asset_paths(body, suite_name)
    detail_link = f"{suite_name}/RESULTS.md"
    return (
        f"## Suite: {suite_name}\n\n"
        f"Detail report: [{detail_link}]({detail_link})\n\n"
        f"{body.rstrip()}\n"
    )


def finalize_results_markdown(
    results_md: Path,
    results_dir: Path,
    *,
    suite: str,
    corner: str,
    simulator: str | None = None,
) -> None:
    """Wrap lane report content into a single RESULTS.md with index and footer."""
    if not results_md.is_file():
        return

    raw = results_md.read_text(encoding="utf-8")
    is_aggregate = suite == "all"
    if raw.startswith(_PLATFORM_TITLE) or (
        is_aggregate and "## Reproduce" in raw and raw.startswith(_AGGREGATE_TITLE)
    ):
        return

    manifest = _read_manifest(results_dir)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if manifest and manifest.get("generated_at"):
        try:
            parsed = datetime.fromisoformat(str(manifest["generated_at"]).replace("Z", "+00:00"))
            timestamp = parsed.strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            pass

    sim_label = simulator or _simulator_label(manifest, results_dir)
    bundle = manifest.get("model_bundle_revision") if manifest else model_bundle_revision()
    status = manifest.get("status", "complete") if manifest else "complete"

    body = _strip_lane_footer(raw)
    if is_aggregate:
        lane_body = body
        title = _AGGREGATE_TITLE
        intro = (
            "Self-contained benchmark automation for Open DRAM Model cards. "
            "Full per-suite reports are inlined below; each lane also keeps its own "
            "suite-level `RESULTS.md` for direct linking."
        )
    else:
        lane_body = _demote_h1(body)
        title = _PLATFORM_TITLE
        models = ", ".join(sorted(p.stem for p in resolve_model_root().glob("*.inc")))
        intro = (
            "Reproducible benchmark automation for Open DRAM model cards. "
            "This platform extends the Open DRAM Model Part I/II artifacts with push-button reruns, "
            "multi-tool comparison, validation, and provenance manifests."
        )
        intro += f"\n\n**Models:** {models}"

    footer_parts: list[str] = []
    if not (is_aggregate and "## Suite:" in lane_body):
        layout = _suite_layout_section(results_dir)
        if layout:
            footer_parts.append(layout)
    artifacts = _artifacts_section(results_dir, suite=suite)
    if artifacts:
        footer_parts.append(artifacts)
    footer_parts.append(_reproduce_section(suite=suite, corner=corner, results_dir=results_dir))
    footer = "\n\n".join(part.strip() for part in footer_parts if part)
    full_body = lane_body.rstrip() + "\n\n" + footer
    toc = _extract_toc(full_body)

    header_parts = [
        title,
        "",
        intro,
        "",
        _run_summary_table(
            suite=suite,
            corner=corner,
            simulator=sim_label,
            timestamp=timestamp,
            bundle=str(bundle),
            status=str(status),
        ),
    ]
    if toc:
        header_parts.append(toc)
    header_parts.extend(["---", ""])

    results_md.write_text("\n".join(header_parts) + full_body, encoding="utf-8")
