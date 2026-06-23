"""1T1C retention hold deck for t_ret extraction."""

from __future__ import annotations

from pathlib import Path

from bench.conditions import BenchConditions
from bench.model_compat import finalize_ngspice_deck, resolve_inc_path
from bench.paths import netlist_include_path
from bench.simulator import SimulatorBackend, resolve_backend, uses_spectre_deck

from pareto.config import RetentionConfig
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


def _retention_measures(
    backend: SimulatorBackend,
    cfg: RetentionConfig,
    vdd: float,
) -> str:
    """Return backend-specific `.measure` statements for retention hold."""
    v_target = vdd - cfg.delta_v_v
    t_stop = cfg.max_hold_s
    dev = fet_name(backend)
    if uses_spectre_deck(backend):
        measures = f""".measure tran v_cell_hold_start FIND v(cell) AT={cfg.hold_start_s:.6e}
.measure tran v_cell_hold_end FIND v(cell) AT={cfg.hold_end_s:.6e}
.measure tran i_leak_hold AVG i(Vpre) FROM={cfg.hold_start_s:.6e} TO={cfg.hold_end_s:.6e}
.measure tran i_leak_cell AVG i({dev}) FROM={cfg.hold_start_s:.6e} TO={cfg.hold_end_s:.6e}
"""
        if cfg.direct_crossing:
            measures += (
                f".measure tran t_ret FIND time WHEN v(cell)={v_target:.6f} "
                f"CROSS=1 FROM={cfg.hold_start_s:.6e} TO={t_stop:.6e}\n"
            )
        return measures
    measures = f""".measure tran v_cell_hold_start FIND v(cell) AT='{cfg.hold_start_s:.6e}'
.measure tran v_cell_hold_end FIND v(cell) AT='{cfg.hold_end_s:.6e}'
.measure tran i_leak_hold AVG i(Vpre) FROM='{cfg.hold_start_s:.6e}' TO='{cfg.hold_end_s:.6e}'
.measure tran i_leak_cell AVG i({dev}) FROM='{cfg.hold_start_s:.6e}' TO='{cfg.hold_end_s:.6e}'
"""
    if cfg.direct_crossing:
        measures += (
            f".measure tran t_ret {time_when('v(cell)', v_target, cfg.hold_start_s, cross=-1)}\n"
        )
    return measures


def retention_hold_netlist(
    conditions: BenchConditions,
    ccell_ff: float,
    cfg: RetentionConfig,
    backend: SimulatorBackend,
) -> str:
    """Generate write-then-hold transient for native retention extraction.

    Writes the cell to Vdd, then holds with WL=0 for up to ``max_hold_s``.
    Direct ``t_ret`` measure fires when Vcell drops by ``delta_v_v`` (JEDEC-style
    50 mV loss proxy). Short-window leakage averages support extrapolation fallback.
    """
    vdd = conditions.vdd
    model = conditions.model
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    instance = access_instance_line(model, backend)
    ccell_f = ccell_ff * 1e-15
    measures = _retention_measures(backend, cfg, vdd)
    t_stop = cfg.max_hold_s
    step = cfg.tran_step_hold_s
    return (
        _header(conditions, f"Retention hold Ccell={ccell_ff}fF", backend)
        + f"""
* Write then long hold: WL=0; BL at Vdd/2 (high-Z)
Vpre pre 0 dc {conditions.vdd_half:.6f}
Rpre pre bl 100e6
Vwl wl 0 PWL(0 0 1n 0 2n {vdd:.6f} 7n {vdd:.6f} 7.1n 0 {t_stop:.6e} 0)
Vpl plate 0 PWL(0 0 1n 0 2n {vdd:.6f} 7n {vdd:.6f} 7.1n {conditions.vdd_half:.6f} {t_stop:.6e} {conditions.vdd_half:.6f})
{bulk_source}Vs s 0 0
{instance}
Ccell cell plate {ccell_f:.6e}
.ic v(bl)={conditions.vdd_half:.6f} v(cell)=0
.tran {step:.6e} {t_stop:.6e}
.print tran v(cell) v(bl) i(Vpre) i(Mn1)
{measures}.end
"""
    )


def write_retention_decks(
    output_dir: Path,
    conditions: BenchConditions,
    ccell_values_ff: list[float],
    cfg: RetentionConfig,
    backend: SimulatorBackend | None = None,
) -> dict[str, Path]:
    """Write retention hold decks for multiple Ccell values."""
    resolved = backend or resolve_backend()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    model_id = conditions.model.model_id
    corner = conditions.corner.name
    for ccell in ccell_values_ff:
        label = f"retention_{int(ccell)}ff"
        path = output_dir / f"{model_id}_{corner}_{label}.sp"
        text = retention_hold_netlist(conditions, ccell, cfg, resolved)
        if resolved == SimulatorBackend.NGSPICE:
            text = finalize_ngspice_deck(text)
        path.write_text(text, encoding="utf-8")
        paths[label] = path
    return paths
