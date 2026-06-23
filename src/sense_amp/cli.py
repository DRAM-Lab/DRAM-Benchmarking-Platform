"""Command-line interface for the OpenDRAM sense-amplifier read-path benchmark."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from sense_amp.codesign import export_codesign_artifacts
from sense_amp.models import READ_MODEL_IDS
from sense_amp.report import generate_report
from sense_amp.runner import generate_decks, run_full_read_path

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OpenDRAM VCT sense-amplifier read-path co-design",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_models = sub.add_parser("list-models", help="List supported read-path models")
    list_models.set_defaults(func=_cmd_list_models)

    generate = sub.add_parser("generate", help="Generate read-path SPICE decks")
    generate.add_argument("--output", type=Path, default=Path("build"))
    generate.add_argument("--corner", default="tt")
    generate.add_argument("--model", action="append", dest="models")
    generate.add_argument("--all", action="store_true", help="All read models")
    generate.add_argument("--coupling", action="store_true", help="Include coupling decks")
    generate.add_argument("--simulator", default=None)
    generate.set_defaults(func=_cmd_generate)

    run = sub.add_parser("run", help="Generate decks, simulate, and export CSVs")
    run.add_argument("--output", type=Path, default=Path("results"))
    run.add_argument("--corner", default="tt")
    run.add_argument("--model", action="append", dest="models")
    run.add_argument("--all", action="store_true")
    run.add_argument("--coupling", action="store_true", default=True)
    run.add_argument("--no-coupling", action="store_true")
    run.add_argument("--generate-only", action="store_true")
    run.add_argument("--simulator", default=None)
    run.set_defaults(func=_cmd_run)

    analyze = sub.add_parser("analyze", help="Run SA co-design on existing signal CSVs")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument("--coupling-input", type=Path, default=None)
    analyze.add_argument("--output", type=Path, default=None)
    analyze.add_argument("--report", type=Path, default=None)
    analyze.add_argument("--figures", type=Path, default=None)
    analyze.set_defaults(func=_cmd_analyze)

    report = sub.add_parser("report", help="Regenerate RESULTS.md and figures from CSVs")
    report.add_argument("--input", type=Path, required=True, help="read_signal CSV")
    report.add_argument("--output", type=Path, default=None)
    report.add_argument("--figures", type=Path, default=None)
    report.add_argument("--corner", default="tt")
    report.add_argument("--coupling-input", type=Path, default=None)
    report.set_defaults(func=_cmd_report)

    return parser


def _cmd_list_models(_args: argparse.Namespace) -> int:
    for model_id in READ_MODEL_IDS:
        print(model_id)
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    model_ids = list(READ_MODEL_IDS) if args.all or not args.models else args.models
    paths = generate_decks(
        args.output,
        corner_name=args.corner,
        model_ids=model_ids,
        include_coupling=args.coupling,
        backend=args.simulator,
    )
    print(f"Generated {len(paths)} decks under {args.output / 'decks' / args.corner}")
    return 0


def _write_report_bundle(
    output_dir: Path,
    *,
    signal_df: pd.DataFrame,
    corner: str,
    coupling_df: pd.DataFrame | None = None,
) -> Path:
    """Export codesign CSVs, figures, and RESULTS.md."""
    artifact_paths = export_codesign_artifacts(signal_df, output_dir, coupling_df=coupling_df)
    codesign_df = pd.read_csv(artifact_paths["codesign"])
    spec_df = pd.read_csv(artifact_paths["sa_spec"])
    coupling_margin_df = (
        pd.read_csv(artifact_paths["coupling_margin"])
        if "coupling_margin" in artifact_paths
        else None
    )
    report_path = output_dir / "RESULTS.md"
    generate_report(
        report_path,
        signal_df=signal_df,
        codesign_df=codesign_df,
        spec_df=spec_df,
        coupling_margin_df=coupling_margin_df,
        corner=corner,
        figures_dir=output_dir / "figures",
    )
    return report_path


def _cmd_run(args: argparse.Namespace) -> int:
    model_ids = list(READ_MODEL_IDS) if args.all or not args.models else args.models
    include_coupling = args.coupling and not args.no_coupling
    run_full_read_path(
        args.output,
        corner_name=args.corner,
        model_ids=model_ids,
        include_coupling=include_coupling,
        backend=args.simulator,
        generate_only=args.generate_only,
    )
    if args.generate_only:
        print(f"Decks written under {args.output / 'decks' / args.corner}")
        return 0

    signal_path = args.output / f"read_signal_{args.corner}.csv"
    if not signal_path.is_file():
        logger.error("Missing signal CSV: %s", signal_path)
        return 1
    signal_df = pd.read_csv(signal_path)
    coupling_df = None
    coupling_path = args.output / f"coupling_signal_{args.corner}.csv"
    if coupling_path.is_file():
        coupling_df = pd.read_csv(coupling_path)

    report_path = _write_report_bundle(
        args.output,
        signal_df=signal_df,
        corner=args.corner,
        coupling_df=coupling_df,
    )
    print(f"Wrote {signal_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote figures under {args.output / 'figures'}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    signal_df = pd.read_csv(args.input)
    coupling_df = pd.read_csv(args.coupling_input) if args.coupling_input else None
    output_dir = args.output or args.input.parent
    report_path = _write_report_bundle(
        output_dir,
        signal_df=signal_df,
        corner="custom",
        coupling_df=coupling_df,
    )
    print(f"Wrote {report_path}")
    print(f"Wrote figures under {output_dir / 'figures'}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    output_dir = args.output or args.input.parent
    signal_df = pd.read_csv(args.input)
    coupling_df = pd.read_csv(args.coupling_input) if args.coupling_input else None
    report_path = _write_report_bundle(
        output_dir,
        signal_df=signal_df,
        corner=args.corner,
        coupling_df=coupling_df,
    )
    print(f"Wrote {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
