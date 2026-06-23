"""Benchmark orchestration for Pareto roadmap extraction."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd

from bench.extract.measures import collect_simulation_measures
from bench.models import ACCESS_MODEL_IDS, load_access_model
from bench.simulator import (
    SimulationResult,
    available_backends,
    resolve_backend,
    run_simulation,
    simulator_available,
)
from pareto.config import ParetoConfig, load_corners, load_pareto_config, resolve_conditions
from pareto.derive import derive_pareto_points, points_to_dataframe
from pareto.extract.performance import extract_performance_measures
from pareto.extract.retention import extract_t_ret
from pareto.metrics import ParetoPoint, compute_t_refresh
from pareto.netlist.performance_1t1c import write_performance_decks
from pareto.netlist.retention_hold import write_retention_decks
from pareto.simulator_compare import write_simulator_comparison

logger = logging.getLogger(__name__)


def generate_decks(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    backend: str | None = None,
) -> Path:
    """Generate retention and performance SPICE decks.

    Args:
        output_dir: Root output directory.
        model_ids: Models to include (default: all seven).
        corner_name: Corner key from pareto.yaml / corners.
        backend: Simulator backend override.

    Returns:
        Path to the decks directory.
    """
    cfg = load_pareto_config()
    corners = load_corners()
    if corner_name not in corners:
        raise KeyError(f"Unknown corner: {corner_name}")
    corner = corners[corner_name]
    models = model_ids or list(ACCESS_MODEL_IDS)
    resolved = resolve_backend(backend)
    deck_root = output_dir / "decks" / corner_name
    ccell_values = list(cfg.ccell_values_ff)

    for model_id in models:
        model = load_access_model(model_id)
        conditions = resolve_conditions(model, corner)
        model_dir = deck_root / model_id
        write_retention_decks(model_dir, conditions, ccell_values, cfg.retention, backend=resolved)
        write_performance_decks(
            model_dir, conditions, ccell_values, cfg.performance, backend=resolved
        )

    logger.info("Pareto decks: %d models @ %s → %s", len(models), corner_name, deck_root)
    return deck_root


def _read_print_file(result: SimulationResult) -> str | None:
    if result.print_path and result.print_path.is_file():
        return result.print_path.read_text(encoding="utf-8", errors="replace")
    print_path = result.deck_path.parent / f"{result.deck_path.stem}.print"
    if print_path.is_file():
        return print_path.read_text(encoding="utf-8", errors="replace")
    return None


def _sim_workdir(result: SimulationResult) -> tuple[Path, str]:
    """Return deck directory and stem for measure collection."""
    cwd = result.deck_path.parent.resolve()
    stem = result.deck_path.stem
    for candidate in (cwd, *cwd.parents):
        if (candidate / f"{stem}.mt0").is_file() or (candidate / f"{stem}.measure").is_file():
            return candidate, stem
    nested = sorted(cwd.rglob(f"{stem}.mt0"))
    if nested:
        return nested[0].parent, stem
    return cwd, stem


def _collect_point_from_sims(
    model_id: str,
    corner_name: str,
    ccell_ff: float,
    retention_sim: SimulationResult | None,
    perf_sim: SimulationResult | None,
    cfg: ParetoConfig,
) -> ParetoPoint:
    model = load_access_model(model_id)
    corners = load_corners()
    corner = corners[corner_name]
    conditions = resolve_conditions(model, corner)

    ret_measures: dict[str, float] = {}
    perf_measures: dict[str, float] = {}
    ret_wave: str | None = None
    perf_wave: str | None = None

    if retention_sim is not None:
        cwd, stem = _sim_workdir(retention_sim)
        ret_measures = collect_simulation_measures(cwd, stem)
        ret_measures.update(retention_sim.measures)
        ret_wave = _read_print_file(retention_sim)
    if perf_sim is not None:
        cwd, stem = _sim_workdir(perf_sim)
        perf_measures = collect_simulation_measures(cwd, stem)
        perf_measures.update(perf_sim.measures)
        perf_wave = _read_print_file(perf_sim)

    t_ret = extract_t_ret(ret_measures, ccell_ff, cfg.retention, ret_wave)
    perf = extract_performance_measures(
        perf_measures,
        cfg.performance,
        conditions.vdd,
        conditions.vdd_half,
        perf_wave,
    )
    if perf.get("t_rcd_s") is None and perf_wave is None:
        try:
            from pareto.derive import derive_pareto_points

            derived = derive_pareto_points(corners=[corner_name])
            match = [
                p
                for p in derived
                if p.model_id == model_id
                and p.corner == corner_name
                and p.ccell_ff == ccell_ff
            ]
            if match and match[0].t_rcd_s is not None:
                perf["t_rcd_s"] = match[0].t_rcd_s
                if perf.get("e_read_j") is None and match[0].e_read_j is not None:
                    perf["e_read_j"] = match[0].e_read_j
        except FileNotFoundError:
            pass
    i_leak = perf.get("i_leak_a") or ret_measures.get("i_leak_hold")
    i_leak_f = abs(float(i_leak)) if i_leak is not None else None
    i_leak_density = i_leak_f / (model.fpitch_m**2) if i_leak_f and model.fpitch_m > 0 else None
    sim = None
    if retention_sim is not None:
        sim = retention_sim.backend.value
    elif perf_sim is not None:
        sim = perf_sim.backend.value

    return ParetoPoint(
        model_id=model_id,
        architecture=model.architecture,
        corner=corner_name,
        ccell_ff=ccell_ff,
        temp_c=corner.temp_c,
        vdd=conditions.vdd,
        fpitch_m=model.fpitch_m,
        t_ret_s=t_ret,
        t_refresh_s=compute_t_refresh(t_ret),
        t_rcd_s=perf.get("t_rcd_s"),
        t_wr_s=perf.get("t_wr_s"),
        e_read_j=perf.get("e_read_j"),
        e_write_j=perf.get("e_write_j"),
        i_leak_a=i_leak_f,
        i_leak_density_a_m2=i_leak_density,
        source="simulation",
        simulator=sim,
    )


def run_pareto_benchmark(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    backend: str | None = None,
    *,
    generate_only: bool = False,
) -> pd.DataFrame:
    """Run retention + performance sims and export roadmap CSV.

    Args:
        output_dir: Output root.
        model_ids: Optional model filter.
        corner_name: PVT corner.
        backend: Simulator override.
        generate_only: Write decks without simulating.

    Returns:
        Metrics dataframe.
    """
    cfg = load_pareto_config()
    deck_root = generate_decks(output_dir, model_ids, corner_name, backend)
    if generate_only:
        return pd.DataFrame()

    resolved = resolve_backend(backend)
    if resolved.value == "ngspice":
        logger.warning(
            "ngspice Pareto decks are experimental (OSDI BSIM-CMG); retention holds may fail — "
            "derived metrics are kept when simulation measures are missing."
        )
    if not simulator_available(resolved):
        raise RuntimeError(f"Simulator {resolved.value} not available")

    models = model_ids or list(ACCESS_MODEL_IDS)
    points: list[ParetoPoint] = []

    for model_id in models:
        model_dir = deck_root / model_id
        for ccell in cfg.ccell_values_ff:
            ret_deck = model_dir / f"{model_id}_{corner_name}_retention_{int(ccell)}ff.sp"
            perf_deck = model_dir / f"{model_id}_{corner_name}_perf_{int(ccell)}ff.sp"
            ret_sim = run_simulation(ret_deck, backend=resolved) if ret_deck.is_file() else None
            perf_sim = run_simulation(perf_deck, backend=resolved) if perf_deck.is_file() else None
            pt = _collect_point_from_sims(model_id, corner_name, ccell, ret_sim, perf_sim, cfg)
            points.append(pt)
            logger.debug("  %s @ %s C=%.0ffF t_ret=%s t_rcd=%s", model_id, corner_name, ccell, pt.t_ret_s, pt.t_rcd_s)

    df = points_to_dataframe(points)
    out_csv = output_dir / corner_name / "pareto_metrics.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    logger.info("Wrote %s (%d rows)", out_csv, len(df))
    return df


def run_all_corners(
    output_dir: Path,
    backend: str | None = None,
    *,
    generate_only: bool = False,
) -> pd.DataFrame:
    """Run Pareto benchmark for all configured pareto corners.

    Args:
        output_dir: Output root.
        backend: Simulator override.
        generate_only: Decks only.

    Returns:
        Combined metrics dataframe.
    """
    cfg = load_pareto_config()
    frames: list[pd.DataFrame] = []
    for corner in cfg.pareto_corners:
        df = run_pareto_benchmark(
            output_dir,
            corner_name=corner,
            backend=backend,
            generate_only=generate_only,
        )
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined_path = output_dir / "pareto_metrics_all_corners.csv"
    combined.to_csv(combined_path, index=False)
    roadmap_path = output_dir / "pareto_roadmap.csv"
    combined.to_csv(roadmap_path, index=False)
    return combined


def run_all_simulators(
    output_dir: Path,
    model_ids: list[str] | None = None,
    *,
    generate_only: bool = False,
    backends: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Run Pareto benchmark on every available simulator and write comparison tables.

    Results are stored under ``output_dir/{backend}/``. When at least two simulators
    complete, comparison CSVs are written to ``output_dir/simulator_compare/``.

    Args:
        output_dir: Base output directory for all simulator runs.
        model_ids: Optional model subset.
        generate_only: When True, only generate decks per backend.
        backends: Explicit simulator list; default is all discoverable backends.

    Returns:
        Mapping of backend name to combined metrics dataframe.
    """
    if backends:
        resolved_backends = [resolve_backend(name) for name in backends]
    else:
        resolved_backends = available_backends()

    if not resolved_backends:
        raise RuntimeError("No simulators available for multi-backend Pareto benchmark.")

    names = [b.value for b in resolved_backends]
    logger.info("Multi-simulator Pareto benchmark: %s", ", ".join(names))

    results: dict[str, pd.DataFrame] = {}
    for backend in resolved_backends:
        sim_dir = output_dir / backend.value
        logger.info("--- Backend: %s → %s ---", backend.value, sim_dir)
        df = run_all_corners(sim_dir, backend=backend.value, generate_only=generate_only)
        if not df.empty:
            results[backend.value] = df

    if len(results) >= 2 and not generate_only:
        write_simulator_comparison(output_dir, backends=list(results))
    elif len(results) < 2:
        logger.warning("Only one simulator ran; skipping comparison tables.")

    return results


def resolve_run_all_simulators(
    *,
    explicit_all: bool = False,
    explicit_single: bool = False,
    backend: str | None = None,
) -> bool:
    """Decide whether to run every available simulator backend.

    Auto-enables when two or more simulators are discoverable, unless the user
    pinned a single backend (``--simulator`` / ``OPEN_DRAM_SIMULATOR``) or set
    ``ALL_SIMULATORS=0`` / ``--single-simulator``.

    Args:
        explicit_all: Force multi-simulator mode (``--all-simulators``).
        explicit_single: Force single-simulator mode (``--single-simulator``).
        backend: Explicit simulator override from CLI.

    Returns:
        True when the benchmark should run on all available backends.
    """
    if explicit_single or backend is not None:
        return False
    if os.environ.get("OPEN_DRAM_SIMULATOR", "").strip():
        return False

    env = os.environ.get("ALL_SIMULATORS", "").strip().lower()
    if env in ("0", "false", "no"):
        return False

    backends = available_backends()
    if explicit_all or env in ("1", "true", "yes"):
        if len(backends) >= 2:
            return True
        if explicit_all or env in ("1", "true", "yes"):
            logger.warning(
                "Multi-simulator mode requested but only %d backend(s) available: %s",
                len(backends),
                ", ".join(b.value for b in backends) or "none",
            )
        return False

    return len(backends) >= 2


def _pick_primary_simulator(results: dict[str, pd.DataFrame]) -> str:
    for name in ("spectre", "hspice", "ngspice"):
        if name in results:
            return name
    return next(iter(results))


_ROADMAP_KEYS = ("model_id", "corner", "ccell_ff")
_ROADMAP_META = ("architecture", "temp_c", "vdd", "fpitch_m", "source", "simulator")
_ROADMAP_METRICS = (
    "t_ret_s",
    "t_refresh_s",
    "t_rcd_s",
    "t_wr_s",
    "e_read_j",
    "e_write_j",
    "i_leak_a",
    "i_leak_density_a_m2",
)


def _coalesce_roadmap_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge derived and simulation frames, keeping non-null simulation metrics."""
    if not frames:
        return pd.DataFrame()
    if len(frames) == 1:
        return frames[0].copy()

    combined = pd.concat(frames, ignore_index=True)
    source_rank = {"derived": 0, "interpolated_ccell": 1, "simulation": 2}
    combined["_rank"] = combined["source"].map(lambda value: source_rank.get(str(value), 1))

    rows: list[pd.Series] = []
    for _, group in combined.groupby(list(_ROADMAP_KEYS), sort=False):
        ordered = group.sort_values("_rank")
        merged = ordered.iloc[-1].copy()
        for _, other in ordered.iloc[:-1].iloc[::-1].iterrows():
            for col in _ROADMAP_METRICS:
                if col not in merged.index:
                    continue
                if pd.isna(merged[col]) and pd.notna(other.get(col)):
                    merged[col] = other[col]
            for col in _ROADMAP_META:
                if col == "source" and pd.notna(merged.get("simulator")):
                    continue
                if pd.isna(merged.get(col)) and pd.notna(other.get(col)):
                    merged[col] = other[col]
        rows.append(merged)

    out = pd.DataFrame(rows).drop(columns=["_rank"], errors="ignore")
    return out.sort_values(list(_ROADMAP_KEYS)).reset_index(drop=True)


def build_roadmap_database(
    output_dir: Path,
    *,
    derive_from_bench: bool = True,
    run_sim: bool = False,
    backend: str | None = None,
    all_simulators: bool | None = None,
    single_simulator: bool = False,
) -> pd.DataFrame:
    """Build the full roadmap database (derive and/or simulate).

    Args:
        output_dir: Output directory for CSV artifacts.
        derive_from_bench: Merge points derived from device-benchmark CSVs.
        run_sim: Run native Pareto SPICE decks when simulator is available.
        backend: Simulator override.
        all_simulators: Force multi-simulator mode (``True``) or disable auto
            (``False``). ``None`` auto-enables when >=2 backends are available.
        single_simulator: Force single-backend mode (``--single-simulator``).

    Returns:
        Combined roadmap dataframe.
    """
    frames: list[pd.DataFrame] = []
    run_all = resolve_run_all_simulators(
        explicit_all=all_simulators is True,
        explicit_single=single_simulator or all_simulators is False,
        backend=backend,
    )

    if run_sim and run_all:
        names = [b.value for b in available_backends()]
        logger.info("Multi-simulator benchmark (auto): %s", ", ".join(names))
        if derive_from_bench:
            logger.info("Skipping derive merge for multi-simulator comparison run")
            derive_from_bench = False

    if derive_from_bench:
        try:
            derived = points_to_dataframe(derive_pareto_points())
            if not derived.empty:
                frames.append(derived)
        except FileNotFoundError as exc:
            logger.warning("Derive skipped: %s", exc)

    if run_sim:
        if run_all:
            sim_results = run_all_simulators(output_dir, generate_only=False)
            if sim_results:
                primary = _pick_primary_simulator(sim_results)
                sim_df = sim_results[primary].copy()
                frames.append(sim_df)
        else:
            sim_df = run_all_corners(output_dir, backend=backend)
            if not sim_df.empty:
                frames.append(sim_df)

    if not frames:
        return pd.DataFrame()

    combined = _coalesce_roadmap_frames(frames)
    out_path = output_dir / "pareto_roadmap.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)
    return combined
