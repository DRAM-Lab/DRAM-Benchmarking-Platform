"""Command-line interface for OpenDRAM validation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from validation.card import parse_card_metrics
from validation.correlation import generate_literature_report
from validation.golden import load_all_golden_specs
from validation.logging_config import configure_logging
from validation.paper_refs import generate_paper_correlation_report
from validation.paths import (
    PINNED_METRICS_PATH,
    PROJECT_ROOT,
    RESULTS_ROOT,
)
from validation.provenance import (
    generate_contributing_checklist,
    generate_model_provenance,
)
from validation.report import generate_full_report
from validation.sensitivity.local_oat import (
    default_oat_cache_path,
    generate_local_sensitivity_report,
    load_cached_oat,
)
from validation.sensitivity.sobol import generate_sobol_report, run_sobol_screen
from validation.simulator_compare import (
    load_pinned_simulator_compare,
    refresh_simulator_compare,
)
from validation.validation_results import run_validation

logger = logging.getLogger("validation.cli")


def _load_pinned_metrics() -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Load pinned TT metrics for offline validation."""
    if not PINNED_METRICS_PATH.is_file():
        raise FileNotFoundError(
            "Pinned metrics missing. Copy golden TT CSVs to "
            f"{PINNED_METRICS_PATH.parent}/ and re-run dram-validate check."
        )

    device = pd.read_csv(PINNED_METRICS_PATH)
    logger.debug("Loaded pinned device metrics from %s", PINNED_METRICS_PATH)

    cell_path = PINNED_METRICS_PATH.parent / "tt_cell_1t1c_metrics_20ff.csv"
    cell_df: pd.DataFrame | None = None
    if cell_path.is_file():
        cell_df = pd.read_csv(cell_path)
        logger.debug("Loaded pinned cell metrics from %s", cell_path)
    return device, cell_df


def _load_card_metrics() -> dict[str, dict[str, float]]:
    """Load periphery card metrics when model cards are present."""
    try:
        return {"hv_peri_28_32": parse_card_metrics("hv_peri_28_32")}
    except FileNotFoundError:
        logger.warning("hv_peri_28_32 card not found — skipping card-level checks")
        return {}


def cmd_check(args: argparse.Namespace) -> int:
    """Validate golden YAML specs against pinned metrics."""
    device_df, cell_df = _load_pinned_metrics()
    card_metrics = _load_card_metrics()
    validation = run_validation(device_df, cell_df=cell_df, card_metrics=card_metrics)

    failed = False
    for _, row in validation.model_summary.iterrows():
        model_id = str(row["model_id"])
        if row["status"] == "PASS":
            logger.info("PASS %s", model_id)
        else:
            failed = True
            logger.error("FAIL %s (%d errors)", model_id, row["n_errors"])
            for err in validation.errors_by_model.get(model_id, []):
                logger.error("  %s", err)

    for err in validation.trend_errors:
        failed = True
        logger.error("FAIL trend: %s", err)

    logger.info(
        "Validation complete: %d pass, %d fail, %d trend errors",
        validation.pass_count,
        validation.fail_count,
        len(validation.trend_errors),
    )
    return 1 if failed else 0


def cmd_report(args: argparse.Namespace) -> int:
    """Run validation, generate figures, data exports, and RESULTS.md."""
    results_root = Path(args.output) if args.output else RESULTS_ROOT
    log_file = results_root / "validation.log"
    configure_logging(verbose=args.verbose, log_file=log_file)

    logger.info("Starting validation report → %s", results_root)
    device_df, cell_df = _load_pinned_metrics()
    card_metrics = _load_card_metrics()
    validation = run_validation(device_df, cell_df=cell_df, card_metrics=card_metrics)

    cache = Path(args.cache) if args.cache else default_oat_cache_path()
    if cache.is_file():
        oat_results = load_cached_oat(cache)
        logger.info("Loaded %d OAT entries from %s", len(oat_results), cache)
    else:
        logger.warning("OAT cache missing at %s — sensitivity plots will be empty", cache)
        oat_results = []

    summary_path = generate_full_report(
        validation,
        device_df,
        cell_df,
        oat_results,
        results_root=results_root,
    )
    logger.info("Report: %s", summary_path)
    logger.info("Figures: %s", results_root / "figures")
    logger.info("Data: %s", results_root / "data")
    logger.info(
        "Result: %s (%d/%d models pass)",
        "PASS" if validation.all_passed else "FAIL",
        validation.pass_count,
        len(validation.model_summary),
    )
    return 0 if validation.all_passed else 1


def cmd_provenance(_args: argparse.Namespace) -> int:
    """Generate provenance and contributing docs."""
    path = generate_model_provenance()
    checklist = generate_contributing_checklist()
    logger.info("Wrote %s", path)
    logger.info("Wrote %s", checklist)
    return 0


def cmd_correlate(_args: argparse.Namespace) -> int:
    """Generate literature correlation report."""
    device_df, _ = _load_pinned_metrics()
    path = generate_literature_report(device_df)
    logger.info("Wrote %s", path)
    return 0


def cmd_sensitivity(args: argparse.Namespace) -> int:
    """Generate local and optional Sobol sensitivity reports."""
    cache = Path(args.cache) if args.cache else default_oat_cache_path()
    if not cache.is_file():
        logger.error("OAT cache missing: %s", cache)
        return 1
    results = load_cached_oat(cache)
    local_path = PROJECT_ROOT / "docs" / "sensitivity_local.md"
    generate_local_sensitivity_report(results, local_path)
    logger.info("Wrote %s", local_path)

    if args.sobol:
        params = ["phig", "dvt0", "u0", "vsat", "rdsw", "agidl", "cdsc"][:8]
        indices = run_sobol_screen("VCT_125", list(dict.fromkeys(params)), n_samples=args.samples)
        sobol_path = PROJECT_ROOT / "docs" / "sensitivity_sobol.md"
        generate_sobol_report(indices, sobol_path)
        logger.info("Wrote %s", sobol_path)
    return 0


def cmd_paper(_args: argparse.Namespace) -> int:
    """Generate paper-vs-SPICE correlation report from extracted paper references."""
    device_df, _ = _load_pinned_metrics()
    path = generate_paper_correlation_report(device_df)
    logger.info("Wrote %s", path)
    return 0


def cmd_simulators(args: argparse.Namespace) -> int:
    """Show or refresh Spectre/HSPICE/ngspice comparison artifacts."""
    if args.refresh:
        pinned_dir = refresh_simulator_compare(device_only=not args.full)
        logger.info("Pinned simulator comparison → %s", pinned_dir)
        return 0

    snapshot = load_pinned_simulator_compare()
    if snapshot is None:
        logger.error(
            "No pinned simulator comparison under bench/validation/pinned/simulator_compare/. "
            "Run with --refresh (requires dram-device and Spectre)."
        )
        return 1

    summary = snapshot.device_rel_diff
    logger.info(
        "Simulator compare (%s, ref=%s): %d models, backends=%s",
        snapshot.corner,
        snapshot.reference,
        len(summary),
        ", ".join(snapshot.backends),
    )
    return 0


def cmd_list_golden(_args: argparse.Namespace) -> int:
    """List loaded golden specifications."""
    for model_id, spec in load_all_golden_specs().items():
        logger.info("%-16s  %-8s  %d metrics", model_id, spec.architecture, len(spec.metrics))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="dram-validate",
        description="OpenDRAM model validation harness",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Validate golden YAML vs pinned metrics").set_defaults(
        func=cmd_check
    )

    report = sub.add_parser(
        "report",
        help="Generate results/RESULTS.md, figures, and data exports",
    )
    report.add_argument(
        "--output",
        type=str,
        default="",
        help="Results root directory (default: results/)",
    )
    report.add_argument("--cache", type=str, default="", help="OAT JSON cache path")
    report.set_defaults(func=cmd_report)

    sub.add_parser("provenance", help="Generate model_provenance.md").set_defaults(
        func=cmd_provenance
    )
    sub.add_parser("correlate", help="Generate literature correlation report").set_defaults(
        func=cmd_correlate
    )
    sub.add_parser(
        "paper",
        help="Generate paper (Part I/II) vs SPICE correlation report",
    ).set_defaults(func=cmd_paper)
    sub.add_parser("list-golden", help="List golden YAML specs").set_defaults(
        func=cmd_list_golden
    )

    sens = sub.add_parser("sensitivity", help="Generate sensitivity reports")
    sens.add_argument("--cache", type=str, default="", help="OAT JSON cache path")
    sens.add_argument("--sobol", action="store_true", help="Also run Sobol screen (needs SALib)")
    sens.add_argument("--samples", type=int, default=256, help="Saltelli sample count")
    sens.set_defaults(func=cmd_sensitivity)

    sims = sub.add_parser(
        "simulators",
        help="Spectre/HSPICE/ngspice comparison (pinned or live refresh)",
    )
    sims.add_argument(
        "--refresh",
        action="store_true",
        help="Run dram-device multi-simulator benchmark and pin CSVs",
    )
    sims.add_argument(
        "--full",
        action="store_true",
        help="With --refresh, include 1T1C and mini-array (not just device metrics)",
    )
    sims.set_defaults(func=cmd_simulators)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=getattr(args, "verbose", False))
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
