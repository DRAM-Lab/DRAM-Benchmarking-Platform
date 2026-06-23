"""Command-line interface for OpenDRAMBench."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dram_benchmark.manifest import write_manifest
from dram_benchmark.orchestrator import generate_platform_report, run_suite
from dram_benchmark.paths import RESULTS_ROOT, list_access_model_ids, resolve_model_root
from dram_benchmark.report.platform import finalize_results_markdown
from dram_benchmark.report.summary import write_aggregate_summary
from dram_benchmark.suites import PAPER_A1_SUITES, SUITE_CHOICES, suite_spec
from dram_benchmark.validation import validate_results_tree

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dram-bench",
        description="OpenDRAMBench — reproducible automation for Open DRAM model cards",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-models", help="List bundled access transistor models")

    run = sub.add_parser("run", help="Run a benchmark suite")
    run.add_argument(
        "--suite",
        choices=SUITE_CHOICES,
        default="device",
        help="Benchmark suite (use all for full Paper A1)",
    )
    run.add_argument("--corner", default="tt", help="Corner for single-corner suites")
    run.add_argument("--output", type=Path, default=RESULTS_ROOT, help="Results directory")
    run.add_argument("--generate-only", action="store_true", help="Generate decks only")
    run.add_argument(
        "--device-only",
        action="store_true",
        help="Device benchmark only (skip 1T1C and mini-array)",
    )
    run.add_argument("--simulator", default=None, help="Force simulator backend")
    run.add_argument("--model", action="append", dest="models", help="Model ID (repeatable)")
    run.add_argument(
        "--skip-golden",
        action="store_true",
        help="Skip device golden regression check",
    )
    run.add_argument("-v", "--verbose", action="store_true")

    manifest = sub.add_parser("manifest", help="Write MANIFEST.json for a results tree")
    manifest.add_argument("--results", type=Path, default=RESULTS_ROOT)
    manifest.add_argument("--suite", default="device", choices=SUITE_CHOICES)
    manifest.add_argument("--corner", default="tt")
    manifest.add_argument("--simulator", default=None)

    validate = sub.add_parser("validate", help="Validate results artifacts")
    validate.add_argument("--results", type=Path, default=RESULTS_ROOT)
    validate.add_argument("--suite", default="device", choices=SUITE_CHOICES)
    validate.add_argument("--corner", default="tt")
    validate.add_argument("--json", type=Path, default=None, help="Write validation JSON")

    report = sub.add_parser("report", help="Regenerate RESULTS.md with platform header")
    report.add_argument("--results", type=Path, default=RESULTS_ROOT)
    report.add_argument("--suite", default="device", choices=SUITE_CHOICES)
    report.add_argument("--corner", default="tt")

    return parser


def _postprocess_suite(
    results_dir: Path,
    *,
    suite: str,
    corner: str,
    simulator: str | None,
) -> int:
    spec = suite_spec(suite, results_dir, corner=corner)
    generate_platform_report(spec)

    write_manifest(
        results_dir,
        suite=suite,
        corner=corner,
        simulator=simulator,
    )
    finalize_results_markdown(
        spec.results_dir / "RESULTS.md",
        results_dir,
        suite=spec.name,
        corner=spec.reference_corner,
        simulator=simulator,
    )
    validation = validate_results_tree(results_dir, suite=suite, corner=corner)
    for row in validation.checks:
        level = logging.ERROR if row["status"] == "FAIL" else logging.INFO
        logger.log(level, "[%s] %s %s", row["status"], row["check"], row["detail"])
    return 0 if validation.passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))

    if args.command == "list-models":
        root = resolve_model_root()
        for model_id in list_access_model_ids():
            path = root / f"{model_id}.inc"
            print(f"{model_id:12s}  {path.stat().st_size:>8d} bytes")
        return 0

    if args.command == "run":
        device_only = getattr(args, "device_only", False)
        run_suite(
            args.output,
            suite=args.suite,
            corner=args.corner,
            generate_only=args.generate_only,
            device_only=device_only,
            simulator=args.simulator,
            models=args.models,
            validate_golden=not getattr(args, "skip_golden", False),
            parent_results=args.output if args.suite == "all" else None,
        )
        if args.generate_only:
            print(f"Decks → {args.output}")
            return 0

        if args.suite == "all":
            exit_code = 0
            for child_suite in PAPER_A1_SUITES:
                child_dir = args.output / child_suite
                code = _postprocess_suite(
                    child_dir,
                    suite=child_suite,
                    corner=args.corner,
                    simulator=args.simulator,
                )
                exit_code = max(exit_code, code)
            write_aggregate_summary(args.output, corner=args.corner, simulator=args.simulator)
            write_manifest(
                args.output,
                suite="all",
                corner=args.corner,
                simulator=args.simulator,
            )
            finalize_results_markdown(
                args.output / "RESULTS.md",
                args.output,
                suite="all",
                corner=args.corner,
                simulator=args.simulator,
            )
            validation = validate_results_tree(args.output, suite="all", corner=args.corner)
            for row in validation.checks:
                level = logging.ERROR if row["status"] == "FAIL" else logging.INFO
                logger.log(level, "[%s] %s %s", row["status"], row["check"], row["detail"])
            if not validation.passed:
                exit_code = 1
            print(f"Aggregate → {args.output / 'RESULTS.md'}")
            return exit_code

        return _postprocess_suite(
            args.output,
            suite=args.suite,
            corner=args.corner,
            simulator=args.simulator,
        )

    if args.command == "manifest":
        path = write_manifest(
            args.results,
            suite=args.suite,
            corner=args.corner,
            simulator=args.simulator,
        )
        print(path)
        return 0

    if args.command == "validate":
        validation = validate_results_tree(
            args.results,
            suite=args.suite,
            corner=args.corner,
        )
        for row in validation.checks:
            print(f"[{row['status']}] {row['check']}: {row['detail']}")
        if args.json:
            args.json.write_text(json.dumps(validation.checks, indent=2) + "\n", encoding="utf-8")
            print(args.json)
        return 0 if validation.passed else 1

    if args.command == "report":
        return _postprocess_suite(
            args.results,
            suite=args.suite,
            corner=args.corner,
            simulator=None,
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
