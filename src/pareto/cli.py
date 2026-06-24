"""Command-line interface for the Pareto roadmap experiment."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from bench.models import ACCESS_MODEL_IDS
from pareto.analysis import generate_figures
from pareto.config import load_pareto_config
from pareto.derive import derive_pareto_points, points_to_dataframe
from pareto.report import generate_report
from pareto.runner import (
    build_roadmap_database,
    generate_decks,
    resolve_run_all_simulators,
    run_all_corners,
    run_all_simulators,
)

_SIMULATOR_CHOICES = ["spectre", "hspice", "ngspice"]


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def cmd_derive(args: argparse.Namespace) -> int:
    """Build roadmap from device-benchmark CSVs."""
    points = derive_pareto_points(bench_root=args.bench_input)
    df = points_to_dataframe(points)
    if df.empty:
        logging.error("No derived points — run dram-bench device lane first (dram-bench run --suite device).")
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / "pareto_roadmap.csv"
    df.to_csv(out, index=False)
    logging.info("Wrote %s (%d rows)", out, len(df))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run Pareto SPICE benchmark or derive-only pipeline."""
    if args.derive_only:
        return cmd_derive(args)

    if args.generate_only:
        run_all = resolve_run_all_simulators(
            explicit_all=args.all_simulators,
            explicit_single=args.single_simulator,
            backend=args.simulator,
        )
        if run_all:
            run_all_simulators(args.output, generate_only=True)
        else:
            generate_decks(
                args.output,
                corner_name=args.corner if args.corner != "all" else "tt",
                backend=args.simulator,
            )
        return 0

    df = build_roadmap_database(
        args.output,
        derive_from_bench=not args.no_derive,
        run_sim=True,
        backend=args.simulator,
        all_simulators=True if args.all_simulators else None,
        single_simulator=args.single_simulator,
    )
    if df.empty:
        logging.error("No roadmap data produced.")
        return 1
    logging.info("Roadmap: %d rows → %s", len(df), args.output / "pareto_roadmap.csv")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate SPICE decks only."""
    cfg = load_pareto_config()
    corners = [args.corner] if args.corner != "all" else list(cfg.pareto_corners)
    models = list(ACCESS_MODEL_IDS) if args.all else [args.model]
    for corner in corners:
        generate_decks(args.output, models if not args.all else None, corner, args.simulator)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate figures and markdown atlas."""
    cfg = load_pareto_config()
    roadmap = args.input
    if not roadmap.is_file():
        logging.error("Roadmap CSV not found: %s", roadmap)
        return 1

    figures_dir = args.figures
    paths = generate_figures(
        roadmap,
        figures_dir,
        reference_corner=args.reference_corner or cfg.reference_corner,
        reference_ccell_ff=args.reference_ccell or cfg.reference_ccell_ff,
    )
    for path in paths:
        logging.info("Figure: %s", path)

    report_path = args.output
    generate_report(
        roadmap,
        report_path,
        reference_corner=args.reference_corner or cfg.reference_corner,
        reference_ccell_ff=args.reference_ccell or cfg.reference_ccell_ff,
        figures_dir=figures_dir,
        project_root=Path(__file__).resolve().parents[2],
        results_root=args.input.parent,
    )
    logging.info("Report: %s", report_path)
    return 0


def cmd_compare_simulators(args: argparse.Namespace) -> int:
    """Compare Pareto metrics across simulator result trees."""
    from pareto.simulator_compare import write_simulator_comparison

    path = write_simulator_comparison(
        args.input,
        backends=args.simulators,
        output_dir=args.output,
    )
    if path is None:
        logging.error("Need >=2 simulators with Pareto CSV data under %s", args.input)
        return 1
    logging.info("Comparison: %s", path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="dram-pareto",
        description="OpenDRAM retention–performance Pareto roadmap",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p_derive = sub.add_parser("derive", help="Derive roadmap from device-benchmark CSVs")
    p_derive.add_argument(
        "--bench-input",
        type=Path,
        default=None,
        help="Device benchmark results directory",
    )
    p_derive.add_argument("--output", type=Path, default=Path("results"), help="Output directory")
    p_derive.set_defaults(func=cmd_derive)

    p_run = sub.add_parser("run", help="Build full roadmap (native sim by default)")
    p_run.add_argument(
        "--bench-input",
        type=Path,
        default=None,
        help="Device benchmark results directory (derive mode)",
    )
    p_run.add_argument("--output", type=Path, default=Path("results"), help="Output directory")
    p_run.add_argument("--corner", default="all", help="Corner or 'all'")
    p_run.add_argument(
        "--simulator",
        choices=_SIMULATOR_CHOICES,
        default=None,
        help="Simulator backend (default: auto-detect)",
    )
    p_run.add_argument(
        "--all-simulators",
        action="store_true",
        help="Force multi-simulator run (default: auto when >=2 backends found)",
    )
    p_run.add_argument(
        "--single-simulator",
        action="store_true",
        help="Force single-backend run even when multiple simulators are available",
    )
    p_run.add_argument("--generate-only", action="store_true", help="Decks only")
    p_run.add_argument("--derive-only", action="store_true", help="Skip simulation")
    p_run.add_argument("--no-derive", action="store_true", help="Simulation only")
    p_run.set_defaults(func=cmd_run)

    p_gen = sub.add_parser("generate", help="Generate Pareto SPICE decks")
    p_gen.add_argument("--output", type=Path, default=Path("build"), help="Deck output root")
    p_gen.add_argument("--model", default="VCT_125", help="Single model ID")
    p_gen.add_argument("--all", action="store_true", help="All seven models")
    p_gen.add_argument("--corner", default="tt", help="Corner name")
    p_gen.add_argument("--simulator", choices=_SIMULATOR_CHOICES, default=None)
    p_gen.set_defaults(func=cmd_generate)

    p_compare = sub.add_parser(
        "compare-simulators",
        help="Compare Pareto metrics CSVs from per-simulator result trees",
    )
    p_compare.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Base results directory containing {spectre,hspice,ngspice}/ subdirs",
    )
    p_compare.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Comparison output dir (default: input/simulator_compare)",
    )
    p_compare.add_argument(
        "--simulator",
        action="append",
        dest="simulators",
        choices=_SIMULATOR_CHOICES,
        help="Simulator subset (repeatable; default: all with data)",
    )
    p_compare.set_defaults(func=cmd_compare_simulators)

    p_report = sub.add_parser("report", help="Figures + markdown atlas")
    p_report.add_argument(
        "--input",
        type=Path,
        default=Path("results/pareto_roadmap.csv"),
        help="Roadmap CSV",
    )
    p_report.add_argument(
        "--output",
        type=Path,
        default=Path("results/RESULTS.md"),
        help="Markdown report path",
    )
    p_report.add_argument(
        "--figures",
        type=Path,
        default=Path("results/figures"),
        help="Figures directory",
    )
    p_report.add_argument("--reference-corner", default=None)
    p_report.add_argument("--reference-ccell", type=float, default=None)
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
