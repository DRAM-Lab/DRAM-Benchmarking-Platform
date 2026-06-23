"""Benchmark orchestration: deck generation, simulation, and CSV export."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import yaml

from bench.conditions import Corner, load_corners, resolve_conditions
from bench.extract.dc import extract_dibl, extract_vt_at_current, extract_vt_ss
from bench.metrics import (
    Cell1T1CMetrics,
    DeviceMetrics,
    MiniArrayMetrics,
    compute_composite_foms,
)
from bench.models import ACCESS_MODEL_IDS, AccessModel, load_access_model
from bench.netlist.cell_1t1c import write_cell_decks
from bench.netlist.mini_array import MiniArrayLayout, resolve_mini_array_layout, write_mini_array_deck
from bench.netlist.device import write_device_decks
from bench.corner_registry import load_bench_config
from bench.simulator import (
    SimulationResult,
    SimulatorBackend,
    available_backends,
    load_simulation_result,
    resolve_backend,
    run_simulation,
    simulator_available,
)
from bench.simulator_compare import write_simulator_comparison

logger = logging.getLogger(__name__)


def _load_bench_config() -> dict:
    """Load benchmark YAML configuration (IDEA153 registry when available)."""
    return load_bench_config()


def _resolve_mini_array_layout(model: AccessModel, config: dict) -> MiniArrayLayout:
    """Scale mini-array BL RC from reference fpitch to the model fpitch."""
    return resolve_mini_array_layout(model.fpitch_m, config)


def _model_list(model_ids: list[str] | None) -> list[str]:
    return model_ids or list(ACCESS_MODEL_IDS)


def generate_decks(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    backend: str | None = None,
    *,
    quiet: bool = False,
) -> Path:
    """Generate all SPICE decks without running simulation.

    Args:
        output_dir: Root output directory.
        model_ids: Models to include (default: all seven).
        corner_name: Corner key from corners.yaml.
        backend: Simulator backend override (``spectre``, ``hspice``, or ``ngspice``).
        quiet: When True, suppress the summary log line (caller logs context).

    Returns:
        Path to the decks directory.
    """
    corners = load_corners()
    if corner_name not in corners:
        raise KeyError(f"Unknown corner: {corner_name}")
    corner = corners[corner_name]
    models = _model_list(model_ids)
    resolved = resolve_backend(backend)
    if resolved is SimulatorBackend.NGSPICE:
        from bench.model_compat import ensure_ngspice_osdi

        if ensure_ngspice_osdi() is None:
            raise RuntimeError(
                "ngspice OSDI library not available. Install openvaf, provide "
                "VA-Models (OPEN_DRAM_VA_MODELS_ROOT), or place bsimcmg.osdi under "
                "build/ngspice_osdi/."
            )
    deck_root = output_dir / "decks" / corner_name
    config = _load_bench_config()
    ccell_values = [float(v) for v in config["ccell_values_ff"]]

    for model_id in models:
        model = load_access_model(model_id)
        conditions = resolve_conditions(model, corner)
        model_dir = deck_root / model_id
        layout = _resolve_mini_array_layout(model, config)
        write_device_decks(model_dir, conditions, backend=resolved)
        write_cell_decks(model_dir, conditions, ccell_values, backend=resolved)
        write_mini_array_deck(model_dir, conditions, layout, backend=resolved)
        logger.debug("  deck %s @ %s", model_id, corner_name)

    if not quiet:
        logger.info(
            "Decks: %d models @ %-5s → %s",
            len(models),
            corner_name,
            deck_root,
        )
    return deck_root


def _collect_device_metrics(
    model: AccessModel,
    corner: Corner,
    sims: dict[str, SimulationResult],
) -> DeviceMetrics:
    """Merge measure results from device decks into one metrics row."""
    conditions = resolve_conditions(model, corner)
    half = sims.get("idvg_vds_half")
    full = sims.get("idvg_vds_full")
    idvd = sims.get("idvd_vwl")
    idvd_boost = sims.get("idvd_vwl_boost")
    ac = sims.get("ac_read")
    gidl = sims.get("gidl")
    sw = sims.get("switching")

    row = DeviceMetrics(
        model_id=model.model_id,
        architecture=model.architecture,
        corner=corner.name,
        temp_c=corner.temp_c,
        vdd=conditions.vdd,
    )

    if half:
        row.ion_a = abs(half.measures.get("ion", 0.0))
        row.ioff_a = abs(half.measures.get("ioff", 0.0))
    if full:
        row.ion_a = abs(full.measures.get("ion", row.ion_a or 0.0))
        row.ioff_a = abs(full.measures.get("ioff", row.ioff_a or 0.0))
    if idvd:
        row.ron_ohm = idvd.measures.get("ron")
    if idvd_boost:
        row.ron_boost_ohm = idvd_boost.measures.get("ron")
    if ac:
        row.cgg_f = ac.measures.get("cgg")
        row.cgd_f = ac.measures.get("cgd")
    if gidl:
        row.igidl_a = abs(gidl.measures.get("igidl", 0.0))
        if not row.igidl_a and gidl.log_path and gidl.log_path.is_file():
            from bench.extract.measures import parse_op_probe_current

            igidl = parse_op_probe_current(
                gidl.log_path.read_text(encoding="utf-8", errors="replace"),
                probe="vd",
            )
            if igidl is not None:
                row.igidl_a = abs(igidl)
    if sw:
        row.esw_j = abs(sw.measures.get("esw", 0.0))
        if not row.esw_j:
            sw_text = None
            if sw.print_path and sw.print_path.is_file():
                sw_text = sw.print_path.read_text(encoding="utf-8", errors="replace")
            elif sw.log_path and sw.log_path.is_file():
                sw_text = sw.log_path.read_text(encoding="utf-8", errors="replace")
            if sw_text:
                from bench.extract.transient import extract_esw_j, parse_tran_table

                waveform = parse_tran_table(sw_text)
                if waveform is not None:
                    esw = extract_esw_j(waveform)
                    if esw is not None:
                        row.esw_j = esw
    if ac and row.cgg_f is None:
        qg = ac.measures.get("qg")
        if qg is not None:
            row.cgg_f = abs(qg) / 0.001
        qd = ac.measures.get("qd")
        if qd is not None and row.cgd_f is None:
            row.cgd_f = abs(qd) / 0.001

    # DC-curve refinement from print/log when measures are sparse
    curve_source = None
    if half:
        if half.print_path and half.print_path.is_file():
            curve_source = half.print_path.read_text(encoding="utf-8", errors="replace")
        elif half.log_path and half.log_path.is_file():
            curve_source = half.log_path.read_text(encoding="utf-8", errors="replace")
    if curve_source:
        from bench.extract.dc import parse_dc_table

        curve_half = parse_dc_table(curve_source)
        curve_full = None
        if full:
            full_text = None
            if full.print_path and full.print_path.is_file():
                full_text = full.print_path.read_text(encoding="utf-8", errors="replace")
            elif full.log_path and full.log_path.is_file():
                full_text = full.log_path.read_text(encoding="utf-8", errors="replace")
            if full_text:
                curve_full = parse_dc_table(full_text)
        if curve_half is not None:
            vt, ss = extract_vt_ss(curve_half, conditions.vdd)
            row.vt_v = vt
            row.ss_mv_dec = ss
            i_ref = max(abs(row.ion_a or 1e-6) * 1e-5, 1e-10)
            vt_cc_half = extract_vt_at_current(curve_half, i_ref)
            vt_cc_full = extract_vt_at_current(curve_full, i_ref) if curve_full else None
            if vt_cc_half is not None and vt_cc_full is not None:
                row.dibl_mv_v = extract_dibl(
                    vt_cc_half, vt_cc_full, conditions.vdd_half, conditions.vdd
                )
            elif curve_full is not None:
                vt_full, _ = extract_vt_ss(curve_full, conditions.vdd)
                if vt < conditions.vdd * 0.95 and vt_full < conditions.vdd * 0.95:
                    row.dibl_mv_v = extract_dibl(
                        vt, vt_full, conditions.vdd_half, conditions.vdd
                    )

    if idvd and row.ron_ohm is None:
        from bench.extract.dc import (
            extract_ron_from_idvd,
            extract_ron_resistive_ratio,
            parse_dc_table,
        )

        idvd_text = None
        if idvd.print_path and idvd.print_path.is_file():
            idvd_text = idvd.print_path.read_text(encoding="utf-8", errors="replace")
        elif idvd.log_path and idvd.log_path.is_file():
            idvd_text = idvd.log_path.read_text(encoding="utf-8", errors="replace")
        if idvd_text:
            idvd_curve = parse_dc_table(idvd_text, x_col="dc", y_col="i(vd)")
            if idvd_curve is not None:
                row.ron_ohm = extract_ron_resistive_ratio(idvd_curve)
                if row.ron_ohm is None or pd.isna(row.ron_ohm):
                    row.ron_ohm = extract_ron_from_idvd(idvd_curve)
                if row.ron_ohm is None or pd.isna(row.ron_ohm):
                    i_peak = float(max(abs(y) for y in idvd_curve.y))
                    if i_peak > 0:
                        row.ron_ohm = extract_ron_from_idvd(
                            idvd_curve, target_id=max(1e-9, i_peak * 0.5)
                        )

    if idvd_boost and row.ron_boost_ohm is None:
        from bench.extract.dc import (
            extract_ron_from_idvd,
            extract_ron_resistive_ratio,
            parse_dc_table,
        )

        boost_text = None
        if idvd_boost.print_path and idvd_boost.print_path.is_file():
            boost_text = idvd_boost.print_path.read_text(encoding="utf-8", errors="replace")
        elif idvd_boost.log_path and idvd_boost.log_path.is_file():
            boost_text = idvd_boost.log_path.read_text(encoding="utf-8", errors="replace")
        if boost_text:
            boost_curve = parse_dc_table(boost_text, x_col="dc", y_col="i(vd)")
            if boost_curve is not None:
                row.ron_boost_ohm = extract_ron_resistive_ratio(boost_curve)
                if row.ron_boost_ohm is None or pd.isna(row.ron_boost_ohm):
                    row.ron_boost_ohm = extract_ron_from_idvd(boost_curve)
                if row.ron_boost_ohm is None or pd.isna(row.ron_boost_ohm):
                    i_peak = float(max(abs(y) for y in boost_curve.y))
                    if i_peak > 0:
                        row.ron_boost_ohm = extract_ron_from_idvd(
                            boost_curve, target_id=max(1e-9, i_peak * 0.5)
                        )

    return compute_composite_foms(row, model)


def _simulation_waveform_text(result: SimulationResult) -> str | None:
    """Return printable transient/DC text from Spectre ``.print`` or HSPICE ``.lis``."""
    if result.print_path and result.print_path.is_file():
        return result.print_path.read_text(encoding="utf-8", errors="replace")
    if result.log_path and result.log_path.is_file():
        return result.log_path.read_text(encoding="utf-8", errors="replace")
    return None


def _collect_cell_metrics(
    model: AccessModel,
    corner: Corner,
    sims: dict[str, SimulationResult],
) -> list[Cell1T1CMetrics]:
    """Merge 1T1C simulation results into metric rows (one per Ccell deck)."""
    from bench.extract.transient import extract_t_read_cell, parse_tran_table

    conditions = resolve_conditions(model, corner)
    v_write = 0.9 * conditions.vdd
    rows: list[Cell1T1CMetrics] = []
    for key, result in sorted(sims.items()):
        if not key.startswith("1t1c_"):
            continue
        ccell_ff = float(key.replace("1t1c_", "").replace("ff", ""))
        t_read = result.measures.get("t_read")
        t_write = result.measures.get("t_write")
        wf_text = _simulation_waveform_text(result)
        if wf_text:
            waveform = parse_tran_table(wf_text)
            if waveform is not None:
                if pd.isna(t_read):
                    t_read = extract_t_read_cell(waveform, v_sense=conditions.vdd_half)
                if pd.isna(t_write) and "v(cell)" in waveform.columns:
                    t_write = extract_t_read_cell(
                        waveform,
                        v_sense=v_write,
                        t_read_start_s=1e-9,
                        t_read_end_s=10e-9,
                    )
        rows.append(
            Cell1T1CMetrics(
                model_id=model.model_id,
                architecture=model.architecture,
                corner=corner.name,
                ccell_ff=ccell_ff,
                t_write_s=t_write,
                t_read_s=t_read,
                i_hold_a=abs(result.measures.get("i_hold", 0.0)) or None,
                q_read_c=result.measures.get("q_read"),
            )
        )
    return rows


def _collect_mini_array_metrics(
    model: AccessModel,
    corner: Corner,
    result: SimulationResult,
    layout: MiniArrayLayout,
) -> MiniArrayMetrics:
    """Build mini-array metrics from one simulation result."""
    from bench.extract.transient import extract_t_bl_settle, parse_tran_table

    t_bl_settle = result.measures.get("t_bl_settle")
    wf_text = _simulation_waveform_text(result)
    if pd.isna(t_bl_settle) and wf_text:
        waveform = parse_tran_table(wf_text)
        if waveform is not None:
            t_bl_settle = extract_t_bl_settle(
                waveform,
                v_precharge=resolve_conditions(model, corner).vdd_half,
            )
    return MiniArrayMetrics(
        model_id=model.model_id,
        architecture=model.architecture,
        corner=corner.name,
        n_cells=layout.n_cells,
        ccell_ff=layout.ccell_ff,
        bl_topology=layout.topology,
        rbl_ohm=layout.rbl_ohm,
        cbl_ff=layout.cbl_ff,
        r_seg_ohm=layout.r_seg_ohm,
        c_seg_ff=layout.c_seg_ff,
        r_metal_seg_ohm=layout.r_metal_seg_ohm,
        r_contact_ohm=layout.r_contact_ohm,
        c_metal_seg_ff=layout.c_metal_seg_ff,
        c_wl_coupling_ff=layout.c_wl_coupling_ff,
        c_sa_ff=layout.c_sa_ff,
        c_far_end_ff=layout.c_far_end_ff,
        t_bl_settle_s=t_bl_settle,
        i_bl_leak_a=abs(result.measures.get("i_bl_leak", 0.0)) or None,
    )


def _run_model_decks(
    model_dir: Path,
    model_id: str,
    corner_name: str,
    resolved,
    *,
    include_device: bool = True,
    include_cell: bool = True,
    include_mini_array: bool = True,
) -> tuple[dict[str, SimulationResult], int]:
    """Simulate decks in a model directory, keyed by deck suffix.

    Returns:
        Tuple of (simulation results, number of non-zero exit codes).
    """
    sims: dict[str, SimulationResult] = {}
    warnings = 0
    for deck in sorted(model_dir.glob("*.sp")):
        if deck.stem.endswith("_mini_array"):
            if not include_mini_array:
                continue
            key = "mini_array"
        elif "1t1c" in deck.stem:
            if not include_cell:
                continue
            key = deck.stem.replace(f"{model_id}_{corner_name}_", "")
        else:
            if not include_device:
                continue
            key = deck.stem.replace(f"{model_id}_{corner_name}_", "")
        result = run_simulation(deck, work_dir=model_dir, backend=resolved)
        if result.returncode != 0:
            warnings += 1
            logger.warning(
                "[%s] %s exit %d on %s",
                corner_name,
                resolved.value,
                result.returncode,
                deck.name,
            )
        sims[key] = result
        logger.debug("  sim %s/%s", model_id, key)
    return sims, warnings


def _load_model_sims(
    model_dir: Path,
    model_id: str,
    corner_name: str,
    backend: SimulatorBackend,
    *,
    include_device: bool = True,
    include_cell: bool = True,
    include_mini_array: bool = True,
) -> dict[str, SimulationResult]:
    """Load cached simulation artifacts for a model directory."""
    sims: dict[str, SimulationResult] = {}
    for deck in sorted(model_dir.glob("*.sp")):
        if deck.stem.endswith("_mini_array"):
            if not include_mini_array:
                continue
            key = "mini_array"
        elif "1t1c" in deck.stem:
            if not include_cell:
                continue
            key = deck.stem.replace(f"{model_id}_{corner_name}_", "")
        else:
            if not include_device:
                continue
            key = deck.stem.replace(f"{model_id}_{corner_name}_", "")
        sims[key] = load_simulation_result(deck, backend)
    return sims


def reextract_corner_metrics(
    corner_dir: Path,
    corner_name: str | None = None,
    backend: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Re-collect CSV metrics from existing simulation artifacts without re-simulating.

    Args:
        corner_dir: Corner output directory (e.g. ``results/tt``).
        corner_name: Corner key (defaults to ``corner_dir.name``).
        backend: Simulator backend override.

    Returns:
        Dict with ``device``, ``cell``, and ``mini_array`` DataFrames.
    """
    corner_name = corner_name or corner_dir.name
    deck_root = corner_dir / "decks" / corner_name
    if not deck_root.is_dir():
        raise FileNotFoundError(f"Deck directory not found: {deck_root}")

    resolved = resolve_backend(backend)
    corner = load_corners()[corner_name]
    models = _model_list(None)
    config = _load_bench_config()

    device_rows: list[dict[str, object]] = []
    cell_rows: list[dict[str, object]] = []
    mini_rows: list[dict[str, object]] = []

    for model_id in models:
        model = load_access_model(model_id)
        model_dir = deck_root / model_id
        sims = _load_model_sims(model_dir, model_id, corner_name, resolved)
        device_rows.append(_collect_device_metrics(model, corner, sims).as_dict())
        cell_rows.extend(m.as_dict() for m in _collect_cell_metrics(model, corner, sims))
        if "mini_array" in sims:
            layout = _resolve_mini_array_layout(model, config)
            mini_rows.append(
                _collect_mini_array_metrics(
                    model,
                    corner,
                    sims["mini_array"],
                    layout,
                ).as_dict()
            )

    device_df = pd.DataFrame(device_rows)
    cell_df = pd.DataFrame(cell_rows)
    mini_df = pd.DataFrame(mini_rows)

    corner_dir.mkdir(parents=True, exist_ok=True)
    device_df.to_csv(corner_dir / "device_metrics.csv", index=False)
    cell_df.to_csv(corner_dir / "cell_1t1c_metrics.csv", index=False)
    ref_df = cell_df[cell_df["ccell_ff"] == 20.0] if not cell_df.empty else cell_df
    ref_df.to_csv(corner_dir / "cell_1t1c_metrics_20ff.csv", index=False)
    mini_df.to_csv(corner_dir / "mini_array_metrics.csv", index=False)

    logger.info(
        "Re-extracted %s metrics from %s (%d device rows)",
        corner_name,
        deck_root,
        len(device_df),
    )
    return {"device": device_df, "cell": cell_df, "mini_array": mini_df}


def run_cell_benchmark(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    simulate: bool = True,
    backend: str | None = None,
    reference_ccell_ff: float = 20.0,
    deck_root: Path | None = None,
) -> pd.DataFrame:
    """Run 1T1C macro benchmark for selected models.

    Args:
        output_dir: Directory for decks, logs, and CSV.
        model_ids: Models to benchmark.
        corner_name: Corner name.
        simulate: When False, only generate decks.
        backend: Simulator backend override.
        reference_ccell_ff: Ccell for the golden subset CSV.
        deck_root: Pre-generated deck tree (skips deck generation when set).

    Returns:
        DataFrame of 1T1C metrics (all Ccell values).
    """
    resolved = resolve_backend(backend)
    if deck_root is None:
        deck_root = generate_decks(output_dir, model_ids, corner_name, backend=resolved.value)
    if not simulate:
        return pd.DataFrame()

    if not simulator_available():
        raise RuntimeError("No simulator available.")

    corners = load_corners()
    corner = corners[corner_name]
    models = _model_list(model_ids)
    rows: list[dict[str, object]] = []
    sim_warnings = 0

    for model_id in models:
        model = load_access_model(model_id)
        model_dir = deck_root / model_id
        sims, warns = _run_model_decks(
            model_dir,
            model_id,
            corner_name,
            resolved,
            include_device=False,
            include_cell=True,
            include_mini_array=False,
        )
        sim_warnings += warns
        for metrics in _collect_cell_metrics(model, corner, sims):
            rows.append(metrics.as_dict())

    df = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "cell_1t1c_metrics.csv"
    df.to_csv(csv_path, index=False)
    ref_df = df[df["ccell_ff"] == reference_ccell_ff] if not df.empty else df
    ref_path = output_dir / "cell_1t1c_metrics_20ff.csv"
    ref_df.to_csv(ref_path, index=False)
    warn_note = f", {sim_warnings} sim warnings" if sim_warnings else ""
    logger.info(
        "1T1C:  %d models, %d rows → %s%s",
        len(models),
        len(df),
        csv_path.name,
        warn_note,
    )
    return df


def run_mini_array_benchmark(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    simulate: bool = True,
    backend: str | None = None,
    deck_root: Path | None = None,
) -> pd.DataFrame:
    """Run mini-array benchmark for selected models."""
    resolved = resolve_backend(backend)
    if deck_root is None:
        deck_root = generate_decks(output_dir, model_ids, corner_name, backend=resolved.value)
    if not simulate:
        return pd.DataFrame()

    if not simulator_available():
        raise RuntimeError("No simulator available.")

    config = _load_bench_config()
    corners = load_corners()
    corner = corners[corner_name]
    models = _model_list(model_ids)
    rows: list[dict[str, object]] = []
    sim_warnings = 0

    for model_id in models:
        model = load_access_model(model_id)
        model_dir = deck_root / model_id
        layout = _resolve_mini_array_layout(model, config)
        sims, warns = _run_model_decks(
            model_dir,
            model_id,
            corner_name,
            resolved,
            include_device=False,
            include_cell=False,
            include_mini_array=True,
        )
        sim_warnings += warns
        result = sims.get("mini_array")
        if result is None:
            logger.warning("[%s] No mini-array result for %s", corner_name, model_id)
            continue
        metrics = _collect_mini_array_metrics(model, corner, result, layout)
        rows.append(metrics.as_dict())

    df = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "mini_array_metrics.csv"
    df.to_csv(csv_path, index=False)
    warn_note = f", {sim_warnings} sim warnings" if sim_warnings else ""
    logger.info(
        "Array: %d models → %s%s",
        len(models),
        csv_path.name,
        warn_note,
    )
    return df


def run_device_benchmark(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    simulate: bool = True,
    backend: str | None = None,
    deck_root: Path | None = None,
) -> pd.DataFrame:
    """Run device-level benchmark for selected models.

    Args:
        output_dir: Directory for decks, logs, and CSV.
        model_ids: Models to benchmark.
        corner_name: Corner name.
        simulate: When False, only generate decks and return empty frame.
        backend: Simulator backend override (``spectre``, ``hspice``, or ``ngspice``).
        deck_root: Pre-generated deck tree (skips deck generation when set).

    Returns:
        DataFrame of device metrics.

    Raises:
        RuntimeError: If simulate=True and no simulator is available.
    """
    resolved = resolve_backend(backend)
    if deck_root is None:
        deck_root = generate_decks(output_dir, model_ids, corner_name, backend=resolved.value)
    if not simulate:
        return pd.DataFrame()

    if not simulator_available():
        raise RuntimeError(
            "No simulator available. Source Cadence env for Spectre or use --generate-only."
        )

    corners = load_corners()
    corner = corners[corner_name]
    models = _model_list(model_ids)
    rows: list[dict[str, object]] = []
    sim_warnings = 0

    for model_id in models:
        model = load_access_model(model_id)
        model_dir = deck_root / model_id
        sims, warns = _run_model_decks(
            model_dir,
            model_id,
            corner_name,
            resolved,
            include_device=True,
            include_cell=False,
            include_mini_array=False,
        )
        sim_warnings += warns
        metrics = _collect_device_metrics(model, corner, sims)
        rows.append(metrics.as_dict())

    df = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "device_metrics.csv"
    df.to_csv(csv_path, index=False)
    warn_note = f", {sim_warnings} sim warnings" if sim_warnings else ""
    logger.info(
        "Device: %d models → %s%s",
        len(models),
        csv_path.name,
        warn_note,
    )
    return df


def run_full_benchmark(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    simulate: bool = True,
    backend: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Run device, 1T1C, and mini-array benchmarks for one corner.

    Decks are generated once and shared across all three phases.

    Returns:
        Dict with keys ``device``, ``cell``, ``mini_array``.
    """
    models = _model_list(model_ids)
    t0 = time.monotonic()

    if not simulate:
        generate_decks(output_dir, model_ids, corner_name, backend=backend)
        return {"device": pd.DataFrame(), "cell": pd.DataFrame(), "mini_array": pd.DataFrame()}

    resolved = resolve_backend(backend)
    logger.info(
        "[%s] Starting full benchmark (%d models, %s)",
        corner_name,
        len(models),
        resolved.value,
    )
    deck_root = generate_decks(
        output_dir,
        model_ids,
        corner_name,
        backend=resolved.value,
        quiet=True,
    )
    logger.info("Decks: %d models → %s", len(models), deck_root)

    device_df = run_device_benchmark(
        output_dir,
        model_ids,
        corner_name,
        simulate=True,
        backend=backend,
        deck_root=deck_root,
    )
    cell_df = run_cell_benchmark(
        output_dir,
        model_ids,
        corner_name,
        simulate=True,
        backend=backend,
        deck_root=deck_root,
    )
    mini_df = run_mini_array_benchmark(
        output_dir,
        model_ids,
        corner_name,
        simulate=True,
        backend=backend,
        deck_root=deck_root,
    )

    elapsed = time.monotonic() - t0
    logger.info("[%s] Corner complete in %.0fs", corner_name, elapsed)
    return {"device": device_df, "cell": cell_df, "mini_array": mini_df}


def run_all_corners(
    output_dir: Path,
    model_ids: list[str] | None = None,
    simulate: bool = True,
    backend: str | None = None,
    full: bool = True,
) -> pd.DataFrame:
    """Run benchmark across all defined corners.

    Args:
        output_dir: Base output directory.
        model_ids: Optional model subset.
        simulate: Whether to invoke the circuit simulator.
        backend: Simulator backend override.
        full: When True, run device + 1T1C + mini-array per corner.

    Returns:
        Combined device metrics DataFrame with corner column.
    """
    corner_names = list(load_corners())
    models = _model_list(model_ids)
    t0 = time.monotonic()
    logger.info(
        "Benchmark plan: %d corners × %d models%s",
        len(corner_names),
        len(models),
        " (device + 1T1C + mini-array)" if full else " (device only)",
    )

    frames: list[pd.DataFrame] = []
    for idx, corner_name in enumerate(corner_names, start=1):
        corner_dir = output_dir / corner_name
        logger.info("--- Corner %d/%d: %s ---", idx, len(corner_names), corner_name)
        if full:
            run_full_benchmark(corner_dir, model_ids, corner_name, simulate=simulate, backend=backend)
            df = pd.read_csv(corner_dir / "device_metrics.csv") if simulate else pd.DataFrame()
        else:
            df = run_device_benchmark(
                corner_dir, model_ids, corner_name, simulate=simulate, backend=backend
            )
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(output_dir / "device_metrics_all_corners.csv", index=False)

    cell_frames: list[pd.DataFrame] = []
    mini_frames: list[pd.DataFrame] = []
    for corner_name in corner_names:
        corner_dir = output_dir / corner_name
        cell_path = corner_dir / "cell_1t1c_metrics.csv"
        mini_path = corner_dir / "mini_array_metrics.csv"
        if cell_path.is_file():
            cell_frames.append(pd.read_csv(cell_path))
        if mini_path.is_file():
            mini_frames.append(pd.read_csv(mini_path))
    if cell_frames:
        pd.concat(cell_frames, ignore_index=True).to_csv(
            output_dir / "cell_1t1c_metrics_all_corners.csv", index=False
        )
    if mini_frames:
        pd.concat(mini_frames, ignore_index=True).to_csv(
            output_dir / "mini_array_metrics_all_corners.csv", index=False
        )

    elapsed = time.monotonic() - t0
    logger.info(
        "All corners done in %.0fs → device_metrics_all_corners.csv (%d rows)",
        elapsed,
        len(combined),
    )
    return combined


def run_all_simulators(
    output_dir: Path,
    model_ids: list[str] | None = None,
    corner_name: str = "tt",
    simulate: bool = True,
    full: bool = True,
    backends: list[str] | None = None,
) -> dict[str, dict[str, pd.DataFrame]]:
    """Run the benchmark on every available simulator and write comparison tables.

    Results are stored under ``output_dir/{backend}/{corner}/``. When at least two
    simulators complete, comparison CSVs are written to ``output_dir/simulator_compare/``.

    Args:
        output_dir: Base output directory for all simulator runs.
        model_ids: Optional model subset.
        corner_name: Corner key (single corner; use ``all`` via repeated calls).
        simulate: When False, only generate decks per backend.
        full: When True, run device + 1T1C + mini-array.
        backends: Explicit simulator list; default is all discoverable backends.

    Returns:
        Mapping of backend name to benchmark result dict (``device``, ``cell``, ``mini_array``).
    """
    if backends:
        resolved_backends = [resolve_backend(name) for name in backends]
    else:
        resolved_backends = available_backends()

    if not resolved_backends:
        raise RuntimeError("No simulators available for multi-backend benchmark.")

    names = [b.value for b in resolved_backends]
    logger.info(
        "Multi-simulator benchmark: %s @ %s (%s)",
        ", ".join(names),
        corner_name,
        "full" if full else "device only",
    )

    results: dict[str, dict[str, pd.DataFrame]] = {}
    for backend in resolved_backends:
        sim_dir = output_dir / backend.value / corner_name
        logger.info("--- Backend: %s → %s ---", backend.value, sim_dir)
        if full:
            results[backend.value] = run_full_benchmark(
                sim_dir,
                model_ids,
                corner_name,
                simulate=simulate,
                backend=backend.value,
            )
        else:
            device_df = run_device_benchmark(
                sim_dir,
                model_ids,
                corner_name,
                simulate=simulate,
                backend=backend.value,
            )
            results[backend.value] = {
                "device": device_df,
                "cell": pd.DataFrame(),
                "mini_array": pd.DataFrame(),
            }

    if len(results) >= 2:
        write_simulator_comparison(output_dir, corner=corner_name, backends=list(results))
    else:
        logger.warning("Only one simulator ran; skipping comparison tables.")

    return results


def _aggregate_corner_csvs(backend_dir: Path, corner_names: list[str]) -> None:
    """Combine per-corner CSVs under ``backend_dir/{corner}/`` into all-corners files."""
    device_frames: list[pd.DataFrame] = []
    cell_frames: list[pd.DataFrame] = []
    mini_frames: list[pd.DataFrame] = []
    for corner_name in corner_names:
        corner_dir = backend_dir / corner_name
        device_path = corner_dir / "device_metrics.csv"
        cell_path = corner_dir / "cell_1t1c_metrics.csv"
        mini_path = corner_dir / "mini_array_metrics.csv"
        if device_path.is_file():
            device_frames.append(pd.read_csv(device_path))
        if cell_path.is_file():
            cell_frames.append(pd.read_csv(cell_path))
        if mini_path.is_file():
            mini_frames.append(pd.read_csv(mini_path))
    if device_frames:
        pd.concat(device_frames, ignore_index=True).to_csv(
            backend_dir / "device_metrics_all_corners.csv", index=False
        )
    if cell_frames:
        pd.concat(cell_frames, ignore_index=True).to_csv(
            backend_dir / "cell_1t1c_metrics_all_corners.csv", index=False
        )
    if mini_frames:
        pd.concat(mini_frames, ignore_index=True).to_csv(
            backend_dir / "mini_array_metrics_all_corners.csv", index=False
        )


def run_all_simulators_all_corners(
    output_dir: Path,
    model_ids: list[str] | None = None,
    simulate: bool = True,
    full: bool = True,
    backends: list[str] | None = None,
) -> dict[str, dict[str, pd.DataFrame]]:
    """Run every available simulator across all corners and write comparisons.

    Per-backend results live under ``output_dir/{backend}/{corner}/``. After all
    corners complete, each backend tree also gets ``device_metrics_all_corners.csv``
    (and cell/min-array aggregates when ``full``). Comparison tables are written per
    corner under ``output_dir/simulator_compare/``.
    """
    corner_names = list(load_corners())
    if backends:
        resolved_backends = [resolve_backend(name) for name in backends]
    else:
        resolved_backends = available_backends()
    if not resolved_backends:
        raise RuntimeError("No simulators available for multi-backend benchmark.")

    names = [b.value for b in resolved_backends]
    logger.info(
        "Multi-simulator all-corners: %s × %d corners",
        ", ".join(names),
        len(corner_names),
    )

    results: dict[str, dict[str, pd.DataFrame]] = {}
    for corner_name in corner_names:
        corner_results = run_all_simulators(
            output_dir,
            model_ids,
            corner_name,
            simulate=simulate,
            full=full,
            backends=names,
        )
        for backend_name, frames in corner_results.items():
            results.setdefault(backend_name, frames)

    for backend_name in names:
        _aggregate_corner_csvs(output_dir / backend_name, corner_names)

    return results
