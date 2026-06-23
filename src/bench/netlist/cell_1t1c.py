"""1T1C SPICE netlist generation."""

from __future__ import annotations

from pathlib import Path

from bench.conditions import BenchConditions
from bench.model_compat import finalize_ngspice_deck, resolve_inc_path
from bench.models import osd_instance_name
from bench.paths import netlist_include_path
from bench.simulator import SimulatorBackend, resolve_backend, uses_spectre_deck


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


def _transient_measures(
    backend: SimulatorBackend,
    vdd: float,
    vdd_half: float,
) -> str:
    """Return backend-specific `.measure` statements for 1T1C transient."""
    v_write = 0.9 * vdd
    # Read after write/hold: cell discharges through access device (CROSS=1 in read window).
    crossing = f""".measure tran t_write FIND time WHEN v(cell)={v_write:.6f} CROSS=1 FROM=1n TO=10n
.measure tran t_read FIND time WHEN v(cell)={vdd_half:.6f} CROSS=1 FROM=12n TO=23n
.measure tran i_hold AVG i(Vpre) FROM=25n TO=35n
.measure tran q_read INTEG i(Vpre) FROM=12n TO=22n
"""
    if uses_spectre_deck(backend) or backend == SimulatorBackend.NGSPICE:
        return crossing
    # HSPICE: TD-qualified crossings (FROM/TO rejected on some builds).
    return f""".measure tran t_write FIND time WHEN v(cell)={v_write:.6f} CROSS=1 TD=1ns
.measure tran t_read FIND time WHEN v(cell)={vdd_half:.6f} CROSS=1 TD=12ns
.measure tran i_hold AVG i(Vpre) FROM=25n TO=35n
.measure tran q_read INTEG i(Vpre) FROM=12n TO=22n
"""


def cell_1t1c_netlist(
    conditions: BenchConditions, ccell_ff: float, backend: SimulatorBackend
) -> str:
    """Generate 1T1C write/read/hold transient deck.

    Args:
        conditions: Resolved bench conditions.
        ccell_ff: Cell capacitance in fF.
        backend: Target simulator for measure syntax.

    Returns:
        SPICE netlist string.
    """
    vdd = conditions.vdd
    model = conditions.model
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    bulk_net = "s" if model.bulk_tied_to_source else "b"
    if backend == SimulatorBackend.NGSPICE:
        instance = (
            f"{osd_instance_name('Mn1')} bl wl cell {bulk_net} nfet "
            f"L={model.length_m:.3e} NFIN={model.nfin}"
        )
    else:
        instance = f"Mn1 bl wl cell {bulk_net} nfet l={model.length_m:.3e} nfin={model.nfin}"
    ccell_f = ccell_ff * 1e-15
    measures = _transient_measures(backend, vdd, conditions.vdd_half)
    return (
        _header(conditions, f"1T1C Ccell={ccell_ff}fF", backend)
        + f"""
* High-Z BL precharge (BL at Vdd/2, floating during read)
* Write 2-7 ns (plate=Vdd), hold with plate=Vdd/2, read WL 12-22 ns
Vpre pre 0 dc {conditions.vdd_half:.6f}
Rpre pre bl 100e6
Vwl wl 0 PWL(0 0 11n 0 12n {vdd:.6f} 22n {vdd:.6f} 23n 0 40n 0)
Vpl plate 0 PWL(0 0 1n 0 2n {vdd:.6f} 7n {vdd:.6f} 7.1n {conditions.vdd_half:.6f} 40n {conditions.vdd_half:.6f})
{bulk_source}Vs s 0 0
{instance}
Ccell cell plate {ccell_f:.6e}
.ic v(bl)={conditions.vdd_half:.6f} v(cell)=0
.tran 0.05n 40n
.print tran v(cell) v(bl) i(Vpre)
{measures}.end
"""
    )


def write_cell_decks(
    output_dir: Path,
    conditions: BenchConditions,
    ccell_values_ff: list[float],
    backend: SimulatorBackend | None = None,
) -> dict[str, Path]:
    """Write 1T1C decks for multiple Ccell values.

    Args:
        output_dir: Output directory.
        conditions: Bench conditions.
        ccell_values_ff: List of cell capacitances (fF).
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
        label = f"1t1c_{int(ccell)}ff"
        text = cell_1t1c_netlist(conditions, ccell, resolved)
        if resolved == SimulatorBackend.NGSPICE:
            text = finalize_ngspice_deck(text)
        path = output_dir / f"{model_id}_{corner}_{label}.sp"
        path.write_text(text, encoding="utf-8")
        paths[label] = path
    return paths
