"""SPICE orchestration for Ccell sweep (retention @ hot, read @ tt)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from bench.extract.measures import collect_simulation_measures
from bench.extract.transient import parse_spectre_tran_print
from bench.models import ACCESS_MODEL_IDS, load_access_model
from bench.simulator import (
    SimulationResult,
    resolve_backend,
    run_simulation,
    simulator_available,
)
from pareto.extract.performance import extract_performance_measures
from pareto.extract.retention import extract_t_ret
from pareto.netlist.performance_1t1c import write_performance_decks
from pareto.netlist.retention_hold import write_retention_decks

from ccell.config import CcellConfig, load_ccell_config, load_corners, resolve_conditions
from ccell.derive import dedupe_sweep_dataframe, derive_ccell_sweep, points_to_dataframe
from ccell.metrics import CcellSweepPoint
from ccell.read_signal import overlay_sense_amp_read

logger = logging.getLogger(__name__)


def generate_decks(
    output_dir: Path,
    model_ids: list[str] | None = None,
    backend: str | None = None,
) -> Path:
    """Generate retention (hot) and performance (tt) SPICE decks."""
    cfg = load_ccell_config()
    corners = load_corners()
    models = model_ids or list(ACCESS_MODEL_IDS)
    resolved = resolve_backend(backend)
    deck_root = output_dir / "decks"
    ccell_values = list(cfg.ccell_values_ff)

    for corner_name in (cfg.retention_corner, cfg.read_corner):
        corner = corners[corner_name]
        corner_dir = deck_root / corner_name
        for model_id in models:
            model = load_access_model(model_id)
            conditions = resolve_conditions(model, corner)
            model_dir = corner_dir / model_id
            if corner_name == cfg.retention_corner:
                write_retention_decks(
                    model_dir, conditions, ccell_values, cfg.retention, backend=resolved
                )
            else:
                write_performance_decks(
                    model_dir, conditions, ccell_values, cfg.performance, backend=resolved
                )

    logger.info("Ccell decks → %s", deck_root)
    return deck_root


def _read_print_file(result: SimulationResult) -> str | None:
    if result.print_path and result.print_path.is_file():
        return result.print_path.read_text(encoding="utf-8", errors="replace")
    print_path = result.deck_path.parent / f"{result.deck_path.stem}.print"
    if print_path.is_file():
        return print_path.read_text(encoding="utf-8", errors="replace")
    return None


def _sim_workdir(result: SimulationResult) -> tuple[Path, str]:
    cwd = result.deck_path.parent.resolve()
    stem = result.deck_path.stem
    for candidate in (cwd, *cwd.parents):
        if (candidate / f"{stem}.mt0").is_file() or (candidate / f"{stem}.measure").is_file():
            return candidate, stem
    nested = sorted(cwd.rglob(f"{stem}.mt0"))
    if nested:
        return nested[0].parent, stem
    return cwd, stem


def _dv_read_from_waveform(
    waveform_text: str | None,
    cfg: CcellConfig,
    v_precharge: float,
) -> float | None:
    """Extract single-ended BL signal at sense-enable time."""
    if not waveform_text:
        return None
    wf = parse_spectre_tran_print(waveform_text)
    if wf is None or "v(bl)" not in wf.columns:
        return None
    sample_t = cfg.performance.wl_read_rise_s + cfg.constraints.t_en_ns * 1e-9
    import numpy as np

    v_bl = float(np.interp(sample_t, wf.time_s, wf.columns["v(bl)"]))
    return max(v_bl - v_precharge, 0.0)


def _collect_point_from_sims(
    model_id: str,
    corner_name: str,
    ccell_ff: float,
    sim: SimulationResult | None,
    cfg: CcellConfig,
) -> CcellSweepPoint:
    model = load_access_model(model_id)
    corner = load_corners()[corner_name]
    conditions = resolve_conditions(model, corner)

    measures: dict[str, float] = {}
    wave: str | None = None
    if sim is not None:
        cwd, stem = _sim_workdir(sim)
        measures = collect_simulation_measures(cwd, stem)
        measures.update(sim.measures)
        wave = _read_print_file(sim)

    t_ret = None
    dv_read = None
    e_read = None
    i_leak = None

    if corner_name == cfg.retention_corner:
        t_ret = extract_t_ret(measures, ccell_ff, cfg.retention, wave)
        i_leak = measures.get("i_leak_hold") or measures.get("i_leak_cell")
    else:
        perf = extract_performance_measures(
            measures,
            cfg.performance,
            conditions.vdd,
            conditions.vdd_half,
            wave,
        )
        e_read = perf.get("e_read_j")
        dv_read = _dv_read_from_waveform(wave, cfg, conditions.vdd_half)
        if dv_read is None:
            dv_read = estimate_dv_read(model, ccell_ff, cfg)

    sim_name = sim.backend.value if sim is not None else None
    return CcellSweepPoint(
        model_id=model_id,
        architecture=model.architecture,
        corner=corner_name,
        ccell_ff=ccell_ff,
        temp_c=corner.temp_c,
        vdd=conditions.vdd,
        fpitch_m=model.fpitch_m,
        t_ret_s=t_ret,
        dv_read_v=dv_read,
        e_read_j=e_read,
        i_leak_a=abs(float(i_leak)) if i_leak is not None else None,
        source="simulation",
        simulator=sim_name,
    )


def run_ccell_benchmark(
    output_dir: Path,
    model_ids: list[str] | None = None,
    backend: str | None = None,
    *,
    generate_only: bool = False,
) -> pd.DataFrame:
    """Run retention + read sims across the Ccell sweep."""
    cfg = load_ccell_config()
    deck_root = generate_decks(output_dir, model_ids, backend)
    if generate_only:
        return pd.DataFrame()

    resolved = resolve_backend(backend)
    if not simulator_available(resolved):
        raise RuntimeError(f"Simulator {resolved.value} not available")

    models = model_ids or list(ACCESS_MODEL_IDS)
    points: list[CcellSweepPoint] = []

    for corner_name in (cfg.retention_corner, cfg.read_corner):
        for model_id in models:
            model_dir = deck_root / corner_name / model_id
            for ccell in cfg.ccell_values_ff:
                if corner_name == cfg.retention_corner:
                    deck = model_dir / f"{model_id}_{corner_name}_retention_{int(ccell)}ff.sp"
                else:
                    deck = model_dir / f"{model_id}_{corner_name}_perf_{int(ccell)}ff.sp"
                sim = run_simulation(deck, backend=resolved) if deck.is_file() else None
                points.append(_collect_point_from_sims(model_id, corner_name, ccell, sim, cfg))

    df = points_to_dataframe(points)
    out_csv = output_dir / "ccell_sweep.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    logger.info("Wrote %s (%d rows)", out_csv, len(df))
    return df


def build_ccell_database(
    output_dir: Path,
    *,
    derive_from_upstream: bool = True,
    run_sim: bool = False,
    backend: str | None = None,
) -> pd.DataFrame:
    """Build full Ccell sweep database (derive and/or simulate)."""
    frames: list[pd.DataFrame] = []

    if derive_from_upstream:
        try:
            derived = points_to_dataframe(derive_ccell_sweep())
            if not derived.empty:
                frames.append(derived)
        except FileNotFoundError as exc:
            logger.warning("Derive skipped: %s", exc)

    if run_sim:
        sim_df = run_ccell_benchmark(output_dir, backend=backend)
        if not sim_df.empty:
            frames.append(sim_df)

    if not frames:
        return pd.DataFrame()

    combined = dedupe_sweep_dataframe(pd.concat(frames, ignore_index=True))
    combined = overlay_sense_amp_read(combined, load_ccell_config())
    out_path = output_dir / "ccell_sweep.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)
    return combined
