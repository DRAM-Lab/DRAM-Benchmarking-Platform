"""Command-line interface for OpenDRAM device benchmark."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from bench.report import generate_report
from bench.conditions import load_corners
from bench.models import ACCESS_MODEL_IDS, load_all_access_models
from bench.runner import (
    generate_decks,
    run_all_corners,
    run_all_simulators,
    run_all_simulators_all_corners,
    run_device_benchmark,
    run_full_benchmark,
)
from bench.simulator import resolve_backend, use_multi_simulator_mode
from bench.simulator_compare import write_simulator_comparison, write_simulator_comparison_all_corners


def _configure_logging(verbose: bool = False) -> None:
    """Set up concise benchmark logging (summaries at INFO, per-model at DEBUG)."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s" if not verbose else "%(levelname)s: %(message)s",
        force=True,
    )


_SIMULATOR_CHOICES = ["spectre", "hspice", "ngspice"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dram-device",
        description="OpenDRAM cross-architecture access device benchmark",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-models", help="List registered access models")

    gen = sub.add_parser("generate", help="Generate SPICE decks only")
    gen.add_argument("--all", action="store_true", help="All seven models")
    gen.add_argument("--model", action="append", dest="models", help="Model ID (repeatable)")
    gen.add_argument("--corner", default="tt", help="Corner name (default: tt)")
    gen.add_argument("--output", type=Path, default=Path("build"), help="Output directory")
    gen.add_argument(
        "--simulator",
        choices=_SIMULATOR_CHOICES,
        default=None,
        help="Simulator backend for deck syntax (default: auto)",
    )

    run = sub.add_parser("run", help="Run device benchmark")
    run.add_argument("--all", action="store_true", help="Run all models")
    run.add_argument("--model", action="append", dest="models", help="Model ID (repeatable)")
    run.add_argument("--corner", default="all", help="Corner name or 'all' (default: all)")
    run.add_argument("--output", type=Path, default=Path("results"), help="Output directory")
    run.add_argument(
        "--device-only",
        action="store_true",
        help="Run device benchmark only (skip 1T1C and mini-array)",
    )
    run.add_argument(
        "--generate-only",
        action="store_true",
        help="Only write decks; do not invoke simulator",
    )
    run.add_argument(
        "--simulator",
        choices=_SIMULATOR_CHOICES,
        default=None,
        help="Simulator backend (default: auto-detect Spectre via Cadence env)",
    )
    run.add_argument(
        "--all-simulators",
        action="store_true",
        help="Force every available simulator + comparison (overrides single-sim pin)",
    )
    run.add_argument(
        "--single-simulator",
        action="store_true",
        help="Run one simulator only (skip automatic multi-simulator comparison)",
    )
    run.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Per-model debug logging (default: phase summaries only)",
    )

    plot = sub.add_parser("plot", help="Generate Pareto/scaling figures from CSV")
    plot.add_argument("--input", type=Path, required=True, help="device_metrics.csv path")
    plot.add_argument("--output", type=Path, default=Path("results/figures"), help="Figure dir")

    report = sub.add_parser("report", help="Generate markdown results report with plots")
    report.add_argument("--input", type=Path, required=True, help="device_metrics.csv path")
    report.add_argument(
        "--output",
        type=Path,
        default=Path("results/RESULTS.md"),
        help="Output markdown report",
    )
    report.add_argument(
        "--figures",
        type=Path,
        default=None,
        help="Figures directory (default: figures/ next to report)",
    )
    report.add_argument("--corner", default="tt", help="Corner label for report header")
    report.add_argument(
        "--reference-corner",
        default="tt",
        help="Reference corner for tables/plots when input spans corners",
    )
    report.add_argument(
        "--golden-status",
        default=None,
        help="Golden validation status string for report header",
    )
    report.add_argument(
        "--cell-input",
        type=Path,
        default=None,
        help="cell_1t1c_metrics.csv path (default: sibling of device CSV)",
    )
    report.add_argument(
        "--simulator-compare",
        type=Path,
        default=None,
        help="simulator_compare/ directory (default: auto-detect next to input CSV)",
    )
    report.add_argument(
        "--mini-input",
        type=Path,
        default=None,
        help="mini_array_metrics.csv path (default: sibling of device CSV)",
    )

    validate = sub.add_parser("validate-golden", help="Compare results to golden CSVs")
    validate.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Results directory (corner dir, or base dir with --all-corners)",
    )
    validate.add_argument("--corner", default="tt", help="Corner name (single-corner mode)")
    validate.add_argument(
        "--all-corners",
        action="store_true",
        help="Validate every corner under --input/{corner}/",
    )
    validate.add_argument("--rtol", type=float, default=0.02, help="Relative tolerance")

    compare = sub.add_parser(
        "compare-simulators",
        help="Compare metrics CSVs from per-simulator result trees",
    )
    compare.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Base results directory containing {spectre,hspice,ngspice}/ subdirs",
    )
    compare.add_argument("--corner", default="tt", help="Corner subdirectory (default: tt)")
    compare.add_argument(
        "--all-corners",
        action="store_true",
        help="Regenerate comparison for every defined corner",
    )
    compare.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Comparison output dir (default: input/simulator_compare)",
    )
    compare.add_argument(
        "--simulator",
        action="append",
        dest="simulators",
        choices=_SIMULATOR_CHOICES,
        help="Simulator subset to compare (repeatable)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))

    if args.command == "list-models":
        models = load_all_access_models()
        for mid, model in models.items():
            print(
                f"{mid:12s}  arch={model.architecture:6s}  Vdd={model.nominal_vdd:.2f}V  "
                f"fpitch={model.fpitch_m * 1e9:.1f}nm  vsat={model.vsat:.0f}"
            )
        return 0

    if args.command == "generate":
        if args.all:
            model_ids = list(ACCESS_MODEL_IDS)
        else:
            model_ids = args.models
        if not model_ids:
            parser.error("Specify --all or one or more --model")
        generate_decks(args.output, model_ids, args.corner, backend=args.simulator)
        print(f"Decks written under {args.output / 'decks' / args.corner}")
        return 0

    if args.command == "run":
        model_ids: list[str] | None
        if args.all:
            model_ids = list(ACCESS_MODEL_IDS)
        elif args.models:
            model_ids = args.models
        else:
            parser.error("Specify --all or one or more --model")

        simulate = not args.generate_only
        multi_mode = args.all_simulators or (
            not args.single_simulator and use_multi_simulator_mode(args.simulator)
        )

        if simulate and not multi_mode:
            try:
                backend = resolve_backend(args.simulator)
                logging.info("Simulator: %s", backend.value)
            except RuntimeError as exc:
                logging.error("%s", exc)
                logging.error("Use --generate-only to create decks without a simulator.")
                return 1
        elif simulate and multi_mode:
            from bench.simulator import available_backends

            names = [b.value for b in available_backends()]
            logging.info("Multi-simulator mode: %s", ", ".join(names))

        if multi_mode:
            if args.corner == "all":
                run_all_simulators_all_corners(
                    args.output,
                    model_ids,
                    simulate=simulate,
                    full=not args.device_only,
                )
            else:
                run_all_simulators(
                    args.output,
                    model_ids,
                    args.corner,
                    simulate=simulate,
                    full=not args.device_only,
                )
        elif args.corner == "all":
            run_all_corners(
                args.output,
                model_ids,
                simulate=simulate,
                backend=args.simulator,
                full=not args.device_only,
            )
        elif args.device_only:
            run_device_benchmark(
                args.output, model_ids, args.corner, simulate=simulate, backend=args.simulator
            )
        else:
            run_full_benchmark(
                args.output, model_ids, args.corner, simulate=simulate, backend=args.simulator
            )
        logging.info("Output → %s", args.output)
        return 0

    if args.command == "plot":
        from bench.analysis import generate_figures

        paths = generate_figures(args.input, args.output)
        for path in paths:
            print(path)
        return 0

    if args.command == "report":
        cell_csv = args.cell_input or (args.input.parent / "cell_1t1c_metrics.csv")
        mini_csv = args.mini_input or (args.input.parent / "mini_array_metrics.csv")
        path = generate_report(
            args.input,
            args.output,
            figures_dir=args.figures,
            corner=args.corner,
            cell_csv=cell_csv,
            mini_array_csv=mini_csv,
            reference_corner=args.reference_corner,
            golden_status=args.golden_status,
            simulator_compare_dir=args.simulator_compare,
        )
        print(path)
        return 0

    if args.command == "validate-golden":
        from bench.golden import validate_all_golden, validate_against_golden

        if args.all_corners:
            summary = validate_all_golden(args.input, rtol=args.rtol)
            failed = {k: v for k, v in summary.items() if v}
            if failed:
                for corner, errors in failed.items():
                    for err in errors:
                        logging.error("[%s] %s", corner, err)
                return 1
            corners = ", ".join(summary)
            print(f"Golden validation passed for all corners: {corners}")
            return 0

        errors = validate_against_golden(args.input, corner=args.corner, rtol=args.rtol)
        if errors:
            for err in errors:
                logging.error("%s", err)
            return 1
        print(f"Golden validation passed ({args.corner}).")
        return 0

    if args.command == "compare-simulators":
        if args.all_corners:
            paths = write_simulator_comparison_all_corners(
                args.input,
                backends=args.simulators,
                output_dir=args.output,
            )
            for path in paths:
                print(path)
        else:
            path = write_simulator_comparison(
                args.input,
                corner=args.corner,
                backends=args.simulators,
                output_dir=args.output,
            )
            print(path)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
