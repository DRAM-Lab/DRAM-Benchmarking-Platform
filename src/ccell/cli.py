"""Command-line interface for the Ccell roadmap experiment."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from ccell.analysis import generate_figures
from ccell.binding import device_whatif_table
from ccell.ccell_min import extract_ccell_min_for_model
from ccell.config import load_ccell_config
from ccell.derive import derive_ccell_sweep, points_to_dataframe
from ccell.read_signal import overlay_sense_amp_read
from ccell.dielectric import annotate_ccell_min_with_feasibility, build_feasibility_table
from ccell.report import generate_report
from ccell.runner import build_ccell_database, generate_decks
from ccell.three_d import build_three_d_comparison

_SIMULATOR_CHOICES = ["spectre", "hspice", "ngspice"]


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _write_analysis_tables(sweep_df: pd.DataFrame, output_dir: Path) -> dict[str, Path]:
    """Compute Ccell_min, feasibility, 3D, and what-if tables."""
    cfg = load_ccell_config()
    output_dir.mkdir(parents=True, exist_ok=True)

    min_rows = [
        extract_ccell_min_for_model(sweep_df, model_id, cfg)
        for model_id in sorted(sweep_df["model_id"].unique())
    ]
    min_rows = annotate_ccell_min_with_feasibility(min_rows, cfg, scenario_name="S-base")
    ccell_min_df = pd.DataFrame([r.as_dict() for r in min_rows])

    ccell_min_path = output_dir / "ccell_min.csv"
    ccell_min_df.to_csv(ccell_min_path, index=False)

    feas_frames = [
        build_feasibility_table(ccell_min_df, cfg, scenario)
        for scenario in cfg.dielectric_scenarios
    ]
    feasibility_df = pd.concat(feas_frames, ignore_index=True)
    feasibility_path = output_dir / "feasibility.csv"
    feasibility_df.to_csv(feasibility_path, index=False)

    three_d_df = build_three_d_comparison(ccell_min_df, cfg, scenario_name="S-base")
    three_d_path = output_dir / "three_d_boost.csv"
    three_d_df.to_csv(three_d_path, index=False)

    whatif_df = device_whatif_table(sweep_df, cfg)
    whatif_path = output_dir / "device_whatif.csv"
    whatif_df.to_csv(whatif_path, index=False)

    return {
        "ccell_min": ccell_min_path,
        "feasibility": feasibility_path,
        "three_d": three_d_path,
        "whatif": whatif_path,
    }


def cmd_derive(args: argparse.Namespace) -> int:
    points = derive_ccell_sweep()
    df = points_to_dataframe(points)
    if df.empty:
        logging.error("No derived sweep points.")
        return 1
    df = overlay_sense_amp_read(df, load_ccell_config())
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / "ccell_sweep.csv"
    df.to_csv(out, index=False)
    logging.info("Wrote %s (%d rows)", out, len(df))
    _write_analysis_tables(df, args.output)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if args.derive_only:
        return cmd_derive(args)
    if args.generate_only:
        generate_decks(args.output, backend=args.simulator)
        return 0

    df = build_ccell_database(
        args.output,
        derive_from_upstream=not args.no_derive,
        run_sim=True,
        backend=args.simulator,
    )
    if df.empty:
        logging.error("No Ccell sweep data produced.")
        return 1
    _write_analysis_tables(df, args.output)
    logging.info("Sweep: %d rows → %s", len(df), args.output / "ccell_sweep.csv")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    sweep = args.input
    if not sweep.is_file():
        logging.error("Sweep CSV not found: %s", sweep)
        return 1

    tables = _write_analysis_tables(pd.read_csv(sweep), args.input.parent)
    figures_dir = args.figures
    generate_figures(
        sweep,
        tables["ccell_min"],
        tables["feasibility"],
        figures_dir,
    )
    generate_report(
        sweep,
        tables["ccell_min"],
        args.output,
        feasibility_csv=tables["feasibility"],
        three_d_csv=tables["three_d"],
        whatif_csv=tables["whatif"],
        figures_dir=figures_dir,
        project_root=Path(__file__).resolve().parents[2],
    )
    logging.info("Report: %s", args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dram-ccell",
        description="OpenDRAM cell-capacitance roadmap",
    )
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_derive = sub.add_parser("derive", help="Derive sweep from upstream experiments")
    p_derive.add_argument("--output", type=Path, default=Path("results"))
    p_derive.set_defaults(func=cmd_derive)

    p_run = sub.add_parser("run", help="Build sweep database (sim + derive)")
    p_run.add_argument("--output", type=Path, default=Path("results"))
    p_run.add_argument("--simulator", choices=_SIMULATOR_CHOICES, default=None)
    p_run.add_argument("--generate-only", action="store_true")
    p_run.add_argument("--derive-only", action="store_true")
    p_run.add_argument("--no-derive", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_report = sub.add_parser("report", help="Figures + RESULTS.md")
    p_report.add_argument("--input", type=Path, default=Path("results/ccell_sweep.csv"))
    p_report.add_argument("--output", type=Path, default=Path("results/RESULTS.md"))
    p_report.add_argument("--figures", type=Path, default=Path("results/figures"))
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
