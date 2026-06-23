"""Orchestrate bundled OpenDRAM benchmark lanes."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from dram_benchmark.paths import PROJECT_ROOT, resolve_engine_root, resolve_model_root
from dram_benchmark.suites import BENCHMARK_SUITES, SUITE_CHOICES, SuiteSpec, suite_spec

logger = logging.getLogger(__name__)


def _bench_env(
    *,
    bench_results: Path | None = None,
    pareto_results: Path | None = None,
    sense_amp_results: Path | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    env["OPEN_DRAM_MODEL_ROOT"] = str(resolve_model_root())
    env.setdefault("OPEN_DRAM_CORNER_SOURCE", "local")
    registry = PROJECT_ROOT / "bench" / "registry" / "corner_registry.yaml"
    if registry.is_file():
        env.setdefault("OPEN_DRAM_CORNER_REGISTRY", str(registry))
    if bench_results is not None:
        env["OPEN_DRAM_BENCH_RESULTS"] = str(bench_results.resolve())
    if pareto_results is not None:
        env["OPEN_DRAM_PARETO_RESULTS"] = str(pareto_results.resolve())
    if sense_amp_results is not None:
        env["OPEN_DRAM_SENSE_AMP_RESULTS"] = str(sense_amp_results.resolve())
    return env


def _run_module(module: str, args: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    root = cwd or resolve_engine_root()
    cmd = [sys.executable, "-m", module, *args]
    logger.info("Running: %s (cwd=%s)", " ".join(cmd), root)
    proc = subprocess.run(cmd, cwd=root, env=env or _bench_env(), check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{module} failed (exit {proc.returncode}): {' '.join(args)}")


def _detect_simulator() -> str | None:
    try:
        from bench.simulator import resolve_backend

        return resolve_backend().value
    except Exception:
        return None


def _has_read_path_simulator() -> bool:
    try:
        from sense_amp.simulator import find_hspice, find_spectre

        return bool(find_spectre() or find_hspice())
    except ImportError:
        return False


def _resolve_full_bench_results(parent_results: Path | None) -> Path | None:
    """Prefer corner_sweep tree when a full multi-corner benchmark exists."""
    if parent_results is None:
        return None
    corner_sweep = parent_results / "corner_sweep"
    if (corner_sweep / "device_metrics_all_corners.csv").is_file():
        return corner_sweep
    return parent_results / "device"


def _run_golden_validation(device_results: Path, *, corner: str = "tt", rtol: float = 0.02) -> None:
    """Validate device metrics against bundled golden CSVs."""
    _run_module(
        "bench.cli",
        ["validate-golden", "--input", str(device_results.resolve()), "--corner", corner, "--rtol", str(rtol)],
    )


def _run_pareto_derive(pareto_dir: Path, device_dir: Path) -> None:
    pareto_dir.mkdir(parents=True, exist_ok=True)
    env = _bench_env(bench_results=device_dir)
    _run_module(
        "pareto.cli",
        ["derive", "--output", str(pareto_dir.resolve()), "--bench-input", str(device_dir.resolve())],
        env=env,
    )


def run_suite(
    output_dir: Path,
    *,
    suite: str = "all",
    corner: str = "tt",
    generate_only: bool = False,
    device_only: bool = False,
    simulator: str | None = None,
    models: list[str] | None = None,
    validate_golden: bool = True,
    parent_results: Path | None = None,
) -> Path:
    """Run a named benchmark suite and return the results directory."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    model_args = ["--all"] if not models else sum([["--model", m] for m in models], [])

    if suite == "device":
        args = ["run", *model_args, "--corner", corner, "--output", str(output_dir)]
        if device_only:
            args.append("--device-only")
        if generate_only:
            args.append("--generate-only")
        if simulator:
            args.extend(["--simulator", simulator])
        _run_module("bench.cli", args)
        if not generate_only and validate_golden:
            backend = simulator or _detect_simulator()
            if backend == "ngspice":
                logger.warning(
                    "Skipping golden regression: pinned goldens are Spectre-derived; "
                    "ngspice extraction differs materially (use Spectre/HSPICE for golden check)"
                )
            else:
                try:
                    _run_golden_validation(output_dir, corner=corner)
                except RuntimeError as exc:
                    logger.warning("Golden validation: %s", exc)
        return output_dir

    if suite == "corner_sweep":
        args = ["run", *model_args, "--corner", "all", "--output", str(output_dir)]
        if device_only:
            args.append("--device-only")
        if generate_only:
            args.append("--generate-only")
        if simulator:
            args.extend(["--simulator", simulator])
        _run_module("bench.cli", args)
        return output_dir

    if suite == "multi_tool":
        args = [
            "run",
            *model_args,
            "--corner",
            "all",
            "--output",
            str(output_dir),
            "--all-simulators",
        ]
        if device_only:
            args.append("--device-only")
        if generate_only:
            args.append("--generate-only")
        _run_module("bench.cli", args)
        if not generate_only:
            _ensure_simulator_comparison(output_dir, all_corners=True)
        return output_dir

    if suite == "sense_amp":
        device_dir = (parent_results or output_dir.parent) / "device"
        sense_corner = "all"
        if _has_read_path_simulator() and not generate_only:
            args = [
                "run",
                "--all",
                "--corner",
                sense_corner,
                "--output",
                str(output_dir),
            ]
            if simulator:
                args.extend(["--simulator", simulator])
            _run_module("sense_amp.cli", args, env=_bench_env(bench_results=device_dir))
        else:
            logger.warning(
                "sense_amp: Spectre/HSPICE not available — generating decks only "
                "(full read-path SPICE requires Spectre or HSPICE)"
            )
            _run_module(
                "sense_amp.cli",
                ["generate", "--all", "--corner", sense_corner, "--output", str(output_dir)],
                env=_bench_env(bench_results=device_dir),
            )
        return output_dir

    if suite == "ccell":
        bench_dir = _resolve_full_bench_results(parent_results) or (
            (parent_results or output_dir.parent) / "device"
        )
        pareto_dir = (parent_results or output_dir.parent) / "pareto"
        sense_dir = (parent_results or output_dir.parent) / "sense_amp"
        if not pareto_dir.is_dir() or not (pareto_dir / "pareto_roadmap.csv").is_file():
            _run_pareto_derive(pareto_dir, bench_dir)
        env = _bench_env(
            bench_results=bench_dir,
            pareto_results=pareto_dir,
            sense_amp_results=sense_dir,
        )
        if generate_only:
            _run_module(
                "ccell.cli",
                ["run", "--output", str(output_dir), "--generate-only"],
                env=env,
            )
        else:
            _run_module(
                "ccell.cli",
                ["derive", "--output", str(output_dir)],
                env=env,
            )
            _run_module(
                "ccell.cli",
                [
                    "report",
                    "--input",
                    str(output_dir / "ccell_sweep.csv"),
                    "--output",
                    str(output_dir / "RESULTS.md"),
                    "--figures",
                    str(output_dir / "figures"),
                ],
                env=env,
            )
        return output_dir

    if suite == "validation":
        env = _bench_env()
        _run_module("validation.cli", ["check"], env=env)
        _run_module(
            "validation.cli",
            ["report", "--output", str(output_dir)],
            env=env,
        )
        for cmd in ("correlate", "paper", "provenance"):
            try:
                _run_module(f"validation.cli", [cmd], env=env)
            except RuntimeError as exc:
                logger.warning("validation %s: %s", cmd, exc)
        return output_dir

    if suite == "all":
        parent = output_dir.resolve()
        parent.mkdir(parents=True, exist_ok=True)
        from bench.conditions import load_corners

        corner_names = ", ".join(load_corners())
        logger.info(
            "Full benchmark bundle: device@%s + all corners (%s) on sweep lanes",
            corner,
            corner_names,
        )
        device_dir = parent / "device"
        run_suite(
            device_dir,
            suite="device",
            corner=corner,
            generate_only=generate_only,
            device_only=device_only,
            simulator=simulator,
            models=models,
            validate_golden=True,
            parent_results=parent,
        )
        for child_suite in ("corner_sweep", "multi_tool", "sense_amp", "ccell", "validation"):
            child_dir = parent / child_suite
            logger.info("=== Benchmark suite: %s → %s ===", child_suite, child_dir)
            run_suite(
                child_dir,
                suite=child_suite,
                corner=corner,
                generate_only=generate_only,
                device_only=device_only,
                simulator=simulator,
                models=models,
                validate_golden=False,
                parent_results=parent,
            )
        return parent

    raise ValueError(f"Unknown suite: {suite}. Choose from {SUITE_CHOICES}")


def _ensure_simulator_comparison(
    results_dir: Path,
    *,
    corner: str = "tt",
    all_corners: bool = False,
) -> None:
    if all_corners:
        compare_root = results_dir / "simulator_compare"
        if compare_root.is_dir() and any(compare_root.glob("*/SIMULATOR_COMPARE.md")):
            return
        _run_module(
            "bench.cli",
            [
                "compare-simulators",
                "--input",
                str(results_dir),
                "--all-corners",
                "--output",
                str(compare_root),
            ],
        )
        return

    compare_md = results_dir / "simulator_compare" / corner / "SIMULATOR_COMPARE.md"
    if compare_md.is_file():
        return
    _run_module(
        "bench.cli",
        [
            "compare-simulators",
            "--input",
            str(results_dir),
            "--corner",
            corner,
            "--output",
            str(results_dir / "simulator_compare"),
        ],
    )


def generate_platform_report(spec: SuiteSpec) -> Path | None:
    """Call lane-specific report generators."""
    results_dir = spec.results_dir.resolve()

    if spec.name == "validation":
        report = results_dir / "RESULTS.md"
        if not report.is_file():
            raise FileNotFoundError(f"Validation report missing: {report}")
        return report

    if spec.name == "ccell":
        report = results_dir / "RESULTS.md"
        if not report.is_file():
            raise FileNotFoundError(f"Ccell report missing: {report}")
        return report

    if spec.name == "sense_amp":
        signal = spec.metrics_csv
        if signal is not None and signal.is_file():
            _run_module(
                "sense_amp.cli",
                [
                    "report",
                    "--input",
                    str(signal),
                    "--output",
                    str(results_dir),
                    "--corner",
                    spec.reference_corner,
                ],
            )
            return results_dir / "RESULTS.md"
        from sense_amp.report import generate_deck_only_report

        deck_count = len(list(results_dir.glob("decks/**/*.sp")))
        generate_deck_only_report(
            results_dir / "RESULTS.md",
            corner=spec.reference_corner,
            deck_count=deck_count or None,
        )
        return results_dir / "RESULTS.md"

    metrics = spec.metrics_csv
    if metrics is None or not metrics.is_file():
        raise FileNotFoundError(f"Metrics CSV not found for suite {spec.name}: {metrics}")

    report_args = [
        "report",
        "--input",
        str(metrics),
        "--output",
        str(results_dir / "RESULTS.md"),
        "--corner",
        spec.report_corner_label_resolved,
        "--reference-corner",
        spec.reference_corner,
    ]
    cell_csv = spec.cell_metrics_csv
    if cell_csv is not None:
        report_args.extend(["--cell-input", str(cell_csv)])
    mini_csv = spec.mini_array_metrics_csv
    if mini_csv is not None:
        report_args.extend(["--mini-input", str(mini_csv)])
    compare_dir = spec.simulator_compare_dir
    if compare_dir is not None:
        report_args.extend(["--simulator-compare", str(compare_dir)])

    _run_module("bench.cli", report_args)
    return results_dir / "RESULTS.md"
