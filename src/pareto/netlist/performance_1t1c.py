"""1T1C performance deck for tRCD, tWR, and energy metrics."""

from __future__ import annotations

from pathlib import Path

from bench.conditions import BenchConditions
from bench.model_compat import finalize_ngspice_deck, resolve_inc_path
from bench.paths import netlist_include_path
from bench.simulator import SimulatorBackend, resolve_backend, uses_spectre_deck

from pareto.config import PerformanceConfig
from pareto.netlist._measures import access_instance_line, fet_name, time_when


def _header(conditions: BenchConditions, title: str, backend: SimulatorBackend) -> str:
    model = conditions.model
    inc_path = resolve_inc_path(model, backend)
    include_path = netlist_include_path(
        inc_path,
        model_id=model.model_id,
        absolute=(backend == SimulatorBackend.NGSPICE),
    )
    return f"""* {title}
* Model: {model.model_id} | Corner: {conditions.corner.name}
.option gmin=1e-20 post=2 measdgt=8
.temp {conditions.temp_c}
.include '{include_path}'
"""


def _performance_measures(
    backend: SimulatorBackend,
    cfg: PerformanceConfig,
    vdd: float,
    vdd_half: float,
) -> str:
    """Return backend-specific `.measure` statements for performance transient."""
    v_write_target = vdd - cfg.write_tol_v
    bl_target = vdd_half + cfg.bl_signal_v
    t_read_start = cfg.wl_read_rise_s
    t_read_end = cfg.wl_read_fall_s
    if uses_spectre_deck(backend):
        return f""".measure tran t_wr FIND time WHEN v(cell)={v_write_target:.6f} CROSS=1 FROM={cfg.write_start_s:.6e} TO={cfg.write_end_s:.6e}
.measure tran t_rcd FIND time WHEN v(bl)={bl_target:.6f} CROSS=1 FROM={t_read_start:.6e} TO={t_read_end:.6e}
.measure tran e_write INTEG 'abs(v(pl)*i(Vpl))' FROM={cfg.write_start_s:.6e} TO={cfg.write_end_s:.6e}
.measure tran e_read INTEG 'abs(v(pre)*i(Vpre))' FROM={t_read_start:.6e} TO={t_read_end:.6e}
.measure tran i_leak AVG i(Vpre) FROM=25e-9 TO=35e-9
"""
    write_integ = (
        "INTEG i(Vpl)"
        if backend is SimulatorBackend.NGSPICE
        else "INTEG 'abs(v(pl)*i(Vpl))'"
    )
    read_integ = (
        "INTEG i(Vpre)"
        if backend is SimulatorBackend.NGSPICE
        else "INTEG 'abs(v(pre)*i(Vpre))'"
    )
    return f""".measure tran t_wr {time_when("v(cell)", v_write_target, cfg.write_start_s, cross=1)}
.measure tran t_rcd {time_when("v(bl)", bl_target, t_read_start, cross=1)}
.measure tran e_write {write_integ} FROM='{cfg.write_start_s:.6e}' TO='{cfg.write_end_s:.6e}'
.measure tran e_read {read_integ} FROM='{t_read_start:.6e}' TO='{t_read_end:.6e}'
.measure tran i_leak AVG i(Vpre) FROM='25e-9' TO='35e-9'
"""


def performance_1t1c_netlist(
    conditions: BenchConditions,
    ccell_ff: float,
    cfg: PerformanceConfig,
    backend: SimulatorBackend,
) -> str:
    """Generate 1T1C write/read transient with Pareto performance measures.

    Metrics:
    - ``t_rcd``: WL rise → BL reaches ``bl_signal_v`` above Vdd/2 precharge.
    - ``t_wr``: write pulse until Vcell within ``write_tol_v`` of Vdd.
    - ``e_read`` / ``e_write``: integrated supply energy on BL and plate.

    Args:
        conditions: Resolved bench conditions.
        ccell_ff: Cell capacitance in fF.
        cfg: Performance configuration.
        backend: Target simulator.

    Returns:
        SPICE netlist string.
    """
    vdd = conditions.vdd
    model = conditions.model
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    instance = access_instance_line(model, backend)
    ccell_f = ccell_ff * 1e-15
    measures = _performance_measures(backend, cfg, vdd, conditions.vdd_half)
    wl_rise = cfg.wl_read_rise_s
    wl_fall = cfg.wl_read_fall_s
    return (
        _header(conditions, f"Performance 1T1C Ccell={ccell_ff}fF", backend)
        + f"""
* High-Z BL precharge; write 2-7 ns; hold; read WL {wl_rise*1e9:.0f}-{wl_fall*1e9:.0f} ns
Vpre pre 0 dc {conditions.vdd_half:.6f}
Rpre pre bl 100e6
Vwl wl 0 PWL(0 0 {wl_rise - 1e-9:.6e} 0 {wl_rise:.6e} {vdd:.6f} {wl_fall:.6e} {vdd:.6f} {(wl_fall + 1e-9):.6e} 0 40n 0)
Vpl plate 0 PWL(0 0 1n 0 2n {vdd:.6f} 7n {vdd:.6f} 7.1n {conditions.vdd_half:.6f} 40n {conditions.vdd_half:.6f})
{bulk_source}Vs s 0 0
{instance}
Ccell cell plate {ccell_f:.6e}
.ic v(bl)={conditions.vdd_half:.6f} v(cell)=0
.tran 0.05n 40n
.print tran v(cell) v(bl) i(Vpre) i(Vpl)
{measures}.end
"""
    )


def write_performance_decks(
    output_dir: Path,
    conditions: BenchConditions,
    ccell_values_ff: list[float],
    cfg: PerformanceConfig,
    backend: SimulatorBackend | None = None,
) -> dict[str, Path]:
    """Write performance 1T1C decks for multiple Ccell values.

    Args:
        output_dir: Output directory.
        conditions: Bench conditions.
        ccell_values_ff: Cell capacitances (fF).
        cfg: Performance configuration.
        backend: Simulator backend override.

    Returns:
        Mapping of deck label to path.
    """
    resolved = backend or resolve_backend()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    model_id = conditions.model.model_id
    corner = conditions.corner.name
    for ccell in ccell_values_ff:
        label = f"perf_{int(ccell)}ff"
        path = output_dir / f"{model_id}_{corner}_{label}.sp"
        text = performance_1t1c_netlist(conditions, ccell, cfg, resolved)
        if resolved == SimulatorBackend.NGSPICE:
            text = finalize_ngspice_deck(text)
        path.write_text(text, encoding="utf-8")
        paths[label] = path
    return paths
