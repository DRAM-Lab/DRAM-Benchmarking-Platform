"""Generate results/RESULTS.md with tables, figures, and data exports."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from dram_benchmark.report.markdown_tables import join_md_row
from validation.card import model_git_sha
from validation.correlation import correlate_device_metrics, correlation_dataframe
from validation.paths import MODEL_SUBMODULE_REL, PROJECT_ROOT
from validation.plots import generate_all_figures
from validation.sensitivity.local_oat import (
    OATResult,
)
from validation.simulator_compare import (
    SimulatorCompareSnapshot,
    export_simulator_compare_tables,
    generate_simulator_compare_markdown,
    load_pinned_simulator_compare,
)
from validation.validation_results import ValidationRun

logger = logging.getLogger(__name__)

RESULTS_ROOT = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_ROOT / "figures"
DATA_DIR = RESULTS_ROOT / "data"
RESULTS_MD_PATH = RESULTS_ROOT / "RESULTS.md"


def _format_cell(value: object, fmt: str) -> str:
    """Format one markdown table cell."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if fmt == "s":
        return str(value)
    try:
        return format(float(value), fmt)
    except (TypeError, ValueError):
        return str(value)


def _table(df: pd.DataFrame, columns: list[tuple[str, str, str]]) -> str:
    """Render a markdown table from column specs."""
    headers = [h for _, h, _ in columns]
    lines = [
        join_md_row(headers),
        join_md_row(["---"] * len(headers)),
    ]
    for _, row in df.iterrows():
        cells = [_format_cell(row.get(col), fmt) for col, _, fmt in columns]
        lines.append(join_md_row(cells))
    return "\n".join(lines)


def _figure_md(name: str, title: str, rel_path: str) -> str:
    """Markdown section for one embedded figure."""
    return "\n".join(
        [
            f"### {title}",
            "",
            f"![{title}]({rel_path})",
            "",
            f"*Figure: `{rel_path}`*",
            "",
        ]
    )


def export_data_tables(
    run: ValidationRun,
    device_df: pd.DataFrame,
    cell_df: pd.DataFrame | None,
    oat_results: list[OATResult],
    data_dir: Path,
    simulator_compare: SimulatorCompareSnapshot | None = None,
) -> dict[str, Path]:
    """Write CSV exports under ``results/data/``.

    Returns:
        Mapping of logical name to file path.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["model_summary"] = data_dir / "model_summary.csv"
    run.model_summary.to_csv(paths["model_summary"], index=False)

    paths["metric_detail"] = data_dir / "metric_detail.csv"
    run.metric_detail.to_csv(paths["metric_detail"], index=False)

    paths["trend_detail"] = data_dir / "trend_detail.csv"
    run.trend_detail.to_csv(paths["trend_detail"], index=False)

    paths["device_metrics_tt"] = data_dir / "device_metrics_tt.csv"
    device_df.to_csv(paths["device_metrics_tt"], index=False)

    if cell_df is not None:
        paths["cell_metrics_tt"] = data_dir / "cell_metrics_tt_20ff.csv"
        cell_df.to_csv(paths["cell_metrics_tt"], index=False)

    corr = correlation_dataframe(correlate_device_metrics(device_df))
    paths["correlation_matrix"] = data_dir / "correlation_matrix.csv"
    corr.to_csv(paths["correlation_matrix"], index=False)

    oat_rows: list[dict[str, Any]] = [
        {
            "model_id": r.model_id,
            "param": r.param,
            "metric": r.metric,
            "nominal": r.nominal,
            "delta_frac": r.delta_frac,
            "relative_change": r.relative_change,
            "abs_change": abs(r.relative_change),
        }
        for r in oat_results
    ]
    paths["sensitivity_oat"] = data_dir / "sensitivity_oat.csv"
    pd.DataFrame(oat_rows).to_csv(paths["sensitivity_oat"], index=False)

    if simulator_compare is not None:
        paths.update(export_simulator_compare_tables(simulator_compare, data_dir))

    logger.info("Exported %d data tables to %s", len(paths), data_dir)
    return paths


def generate_summary_markdown(
    run: ValidationRun,
    device_df: pd.DataFrame,
    cell_df: pd.DataFrame | None,
    figure_paths: dict[str, Path],
    data_paths: dict[str, Path],
    output_path: Path | None = None,
    simulator_compare: SimulatorCompareSnapshot | None = None,
) -> Path:
    """Write ``results/RESULTS.md`` with analysis, figures, and data links.

    Args:
        run: Structured validation outcome.
        device_df: Pinned device metrics.
        cell_df: Optional cell metrics.
        figure_paths: Generated figure paths keyed by stem.
        data_paths: Exported CSV paths keyed by logical name.
        output_path: Override summary path.

    Returns:
        Path to written RESULTS.md.
    """
    out = output_path or RESULTS_MD_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sha = model_git_sha() or "unknown"
    corr = pd.read_csv(data_paths["correlation_matrix"])

    status_icon = "PASS" if run.all_passed else "FAIL"
    lines: list[str] = [
        "# OpenDRAM Validation Summary",
        "",
        f"**Status:** {status_icon} — {run.pass_count}/{len(run.model_summary)} models pass, "
        f"{len(run.trend_errors)} trend violation(s)",
        "",
        f"- **Generated:** {ts}",
        f"- **Model SHA:** `{sha}`",
        "- **Corner:** TT (27 °C)",
        "- **Pinned metrics:** `bench/validation/pinned/` (TT corner)",
        "",
        "## Executive summary",
        "",
    ]

    if run.all_passed:
        lines.append(
            "All golden YAML tolerance bands and declared VCT trends are satisfied "
            "against pinned SPICE-extracted metrics."
        )
    else:
        failed = run.model_summary[run.model_summary["status"] == "FAIL"]["model_id"].tolist()
        lines.append(
            f"**Action required:** review failing models: {', '.join(failed)}."
        )
    lines.append("")

    # Model status table
    lines.extend(
        [
            "## 1. Model validation status",
            "",
            _table(
                run.model_summary,
                [
                    ("model_id", "Model", "s"),
                    ("architecture", "Architecture", "s"),
                    ("status", "Status", "s"),
                    ("n_errors", "Errors", "d"),
                ],
            ),
            "",
            _figure_md(
                "validation_status",
                "Validation error count per model",
                "figures/validation_status.svg",
            ),
        ]
    )

    # Metric detail (failed + margins)
    fail_metrics = run.metric_detail[run.metric_detail["status"] == "FAIL"]
    lines.extend(
        [
            "## 2. Golden metric margins",
            "",
            "Relative margin = (observed − golden) / golden × 100% "
            "for metrics with a reference value.",
            "",
            _table(
                run.metric_detail[
                    run.metric_detail["metric"].isin(["Ion", "Ron", "Ioff", "fpitch", "Cgg"])
                ],
                [
                    ("model_id", "Model", "s"),
                    ("metric", "Metric", "s"),
                    ("confidence", "Conf.", "s"),
                    ("golden_value", "Golden", ".3e"),
                    ("observed", "Observed", ".3e"),
                    ("rel_margin_pct", "Margin %", ".1f"),
                    ("status", "Status", "s"),
                ],
            ),
            "",
            _figure_md(
                "golden_margins",
                "Signed margin vs golden reference",
                "figures/golden_margins.svg",
            ),
        ]
    )
    if not fail_metrics.empty:
        lines.extend(
            [
                "### Failed metric checks",
                "",
                _table(
                    fail_metrics,
                    [
                        ("model_id", "Model", "s"),
                        ("metric", "Metric", "s"),
                        ("error", "Error", "s"),
                    ],
                ),
                "",
            ]
        )

    # Trends
    lines.extend(
        [
            "## 3. Roadmap trends",
            "",
            _table(
                run.trend_detail,
                [
                    ("metric", "Metric", "s"),
                    ("direction", "Direction", "s"),
                    ("models", "Models", "s"),
                    ("status", "Status", "s"),
                ],
            ),
            "",
            _figure_md("vct_scaling", "VCT Ion / Ioff / Ron scaling", "figures/vct_scaling.svg"),
        ]
    )

    # Literature
    lines.extend(
        [
            "## 4. Literature correlation",
            "",
            _table(
                corr,
                [
                    ("model_id", "Model", "s"),
                    ("metric", "Metric", "s"),
                    ("open_value", "Open value", ".4g"),
                    ("literature_band", "Literature band", "s"),
                    ("direction_match", "Dir", "s"),
                    ("magnitude_match", "Mag", "s"),
                ],
            ),
            "",
            _figure_md(
                "literature_correlation",
                "Pitch and Vdd vs public roadmap",
                "figures/literature_correlation.svg",
            ),
        ]
    )

    # Confidence
    lines.extend(
        [
            "## 5. Confidence tiers",
            "",
            "| Tier | Meaning |",
            "|------|---------|",
            "| H | High — literature or PDK number, ±5–10% |",
            "| M | Medium — inferred scaling, ±20% envelope |",
            "| L | Low — extrapolated / directional only |",
            "",
            _figure_md(
                "confidence_tiers",
                "H/M/L metric count per model",
                "figures/confidence_tiers.svg",
            ),
            _figure_md(
                "architecture_radar",
                "Cross-architecture normalized comparison",
                "figures/architecture_radar.svg",
            ),
        ]
    )

    # Sensitivity
    oat_df = pd.read_csv(data_paths["sensitivity_oat"])
    top_rows = (
        oat_df[oat_df["metric"] == "i_hold_a"]
        .sort_values("abs_change", ascending=False)
        .head(8)
    )
    lines.extend(
        [
            "## 6. Local sensitivity (OAT ±5%)",
            "",
            "Top parameters by abs Δi_hold from cached local OAT sensitivity screen.",
            "",
            _table(
                top_rows,
                [
                    ("model_id", "Model", "s"),
                    ("param", "Parameter", "s"),
                    ("abs_change", "abs Δ", ".4f"),
                    ("nominal", "Nominal", ".4g"),
                ],
            ),
            "",
            _figure_md(
                "sensitivity_oat_ihold",
                "OAT sensitivity — i_hold",
                "figures/sensitivity_oat_ihold.svg",
            ),
            _figure_md(
                "sensitivity_oat_ion",
                "OAT sensitivity — Ion",
                "figures/sensitivity_oat_ion.svg",
            ),
        ]
    )

    # Device metrics snapshot
    lines.extend(
        [
            "## 7. Pinned device metrics (TT)",
            "",
            _table(
                device_df,
                [
                    ("model_id", "Model", "s"),
                    ("architecture", "Arch.", "s"),
                    ("vdd", "Vdd (V)", ".2f"),
                    ("ion_a", "Ion (A)", ".3e"),
                    ("ioff_a", "Ioff (A)", ".3e"),
                    ("ron_ohm", "Ron (Ω)", ".3e"),
                    ("fpitch_m", "fpitch (m)", ".2e"),
                ],
            ),
            "",
        ]
    )

    if cell_df is not None:
        lines.extend(
            [
                "## 8. Pinned 1T1C metrics (20 fF, TT)",
                "",
                _table(
                    cell_df,
                    [
                        ("model_id", "Model", "s"),
                        ("t_read_s", "t_read (s)", ".3e"),
                        ("t_write_s", "t_write (s)", ".3e"),
                        ("i_hold_a", "I_hold (A)", ".3e"),
                    ],
                ),
                "",
            ]
        )

    lines.extend(generate_simulator_compare_markdown(simulator_compare, figure_paths))

    # Data index
    lines.extend(
        [
            "## Data files",
            "",
            "| File | Description |",
            "|------|-------------|",
        ]
    )
    descriptions = {
        "model_summary": "Per-model pass/fail summary",
        "metric_detail": "Full golden vs observed detail",
        "trend_detail": "Roadmap trend checks",
        "device_metrics_tt": "Pinned TT device metrics",
        "cell_metrics_tt": "Pinned TT 1T1C metrics at 20 fF",
        "correlation_matrix": "Literature alignment scores",
        "sensitivity_oat": "Cached local OAT perturbation results",
        "simulator_device_rel_diff": "Spectre vs HSPICE/ngspice device rel differences",
        "simulator_device_wide": "Per-simulator device metrics (wide merge)",
        "simulator_device_summary": "Max abs rel diff by metric and backend",
        "simulator_device_detail": "Per-model simulator metric deltas",
        "simulator_cell_rel_diff": "1T1C cell metric rel differences across simulators (20 fF)",
        "simulator_cell_wide": "Per-simulator 1T1C metrics wide merge (20 fF)",
        "simulator_cell_summary": "Max abs 1T1C rel diff by metric and backend",
        "simulator_cell_detail": "Per-model 1T1C simulator metric deltas",
        "simulator_mini_array_rel_diff": "Mini-array metric rel differences across simulators",
        "simulator_mini_array_wide": "Per-simulator mini-array metrics wide merge",
        "simulator_mini_array_summary": "Max abs mini-array rel diff by metric and backend",
        "simulator_mini_array_detail": "Per-model mini-array simulator metric deltas",
    }
    for key, path in sorted(data_paths.items()):
        rel = path.relative_to(out.parent)
        desc = descriptions.get(key, key)
        lines.append(f"| [`{rel}`]({rel}) | {desc} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "Regenerate: `dram-validate report` or `./run_validation.sh`",
            "",
            f"Model cards: `{MODEL_SUBMODULE_REL}`",
        ]
    )

    out.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote results report: %s", out)
    return out


def generate_full_report(
    run: ValidationRun,
    device_df: pd.DataFrame,
    cell_df: pd.DataFrame | None,
    oat_results: list[OATResult],
    *,
    results_root: Path | None = None,
) -> Path:
    """Generate figures, data exports, and RESULTS.md in one pass.

    Args:
        run: Validation outcome.
        device_df: Device metrics.
        cell_df: Optional cell metrics.
        oat_results: Local OAT cache entries.
        results_root: Override results directory.

    Returns:
        Path to RESULTS.md.
    """
    root = results_root or RESULTS_ROOT
    figures_dir = root / "figures"
    data_dir = root / "data"

    simulator_compare = load_pinned_simulator_compare()
    figure_paths = generate_all_figures(
        run, device_df, oat_results, figures_dir, simulator_compare=simulator_compare
    )
    data_paths = export_data_tables(
        run,
        device_df,
        cell_df,
        oat_results,
        data_dir,
        simulator_compare=simulator_compare,
    )

    return generate_summary_markdown(
        run,
        device_df,
        cell_df,
        figure_paths,
        data_paths,
        output_path=root / "RESULTS.md",
        simulator_compare=simulator_compare,
    )
