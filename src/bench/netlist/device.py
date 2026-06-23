"""SPICE netlist generation for device-level benchmarks."""

from __future__ import annotations

from pathlib import Path

from bench.conditions import BenchConditions
from bench.model_compat import finalize_ngspice_deck, resolve_inc_path
from bench.paths import netlist_include_path
from bench.simulator import SimulatorBackend, resolve_backend, uses_hspice_deck, uses_spectre_deck


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


def _device_body(conditions: BenchConditions, backend: SimulatorBackend) -> str:
    model = conditions.model
    bulk_net = "s" if model.bulk_tied_to_source else "b"
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    return f"""{bulk_source}{model.instance_line_for(backend)}
* Bulk reference for bulkmod={model.bulkmod}
* Bulk net tied to: {bulk_net}
"""


def _idvg_measures(vdd: float, backend: SimulatorBackend) -> str:
    """Return backend-specific Ion/Ioff `.measure` statements for Id–Vg sweeps."""
    if backend == SimulatorBackend.NGSPICE:
        # ngspice rejects FIND/WHEN on DC sweeps; MIN/AT forms match HSPICE semantics here.
        return """.measure dc ion MIN i(Vd)
.measure dc ioff FIND i(Vd) AT=0"""
    return f""".measure dc ion FIND i(Vd) WHEN v(g)={vdd:.6f}
.measure dc ioff FIND i(Vd) WHEN v(g)=0"""


def idvg_netlist(conditions: BenchConditions, vds: float, backend: SimulatorBackend) -> str:
    """Generate Id–Vg DC sweep deck at fixed Vds."""
    vdd = conditions.vdd
    return (
        _header(conditions, f"Id-Vg sweep Vds={vds:.4f}V", backend)
        + _device_body(conditions, backend)
        + f"""
Vs s 0 0
Vd d 0 {vds:.6f}
Vg g 0 0
.dc Vg 0 {vdd:.6f} {vdd / 200.0:.6f}
.print dc i(Vd)
{_idvg_measures(vdd, backend)}
.end
"""
    )


def idvd_netlist(conditions: BenchConditions, vgs: float, backend: SimulatorBackend) -> str:
    """Generate Id–Vd DC sweep at fixed Vgs (Ron extraction)."""
    vdd = conditions.vdd
    if uses_spectre_deck(backend):
        ron_measure = ".measure dc ron param='abs(v(d)/i(Vd))'"
    elif uses_hspice_deck(backend):
        ron_measure = "* Ron extracted from DC log in post-processing"
    else:
        ron_measure = "* Ron extracted from DC log in post-processing"
    return (
        _header(conditions, f"Id-Vd sweep Vgs={vgs:.4f}V", backend)
        + _device_body(conditions, backend)
        + f"""
Vs s 0 0
Vd d 0 0
Vg g 0 {vgs:.6f}
.dc Vd 0 {vdd:.6f} {vdd / 100.0:.6f}
.print dc i(Vd) v(d)
{ron_measure}
.end
"""
    )


def ac_cap_netlist(
    conditions: BenchConditions,
    vgs: float,
    vds: float,
    backend: SimulatorBackend,
) -> str:
    """Generate capacitance extraction deck (transient step or Spectre AC measures)."""
    dv = 0.001
    if uses_spectre_deck(backend):
        cap_measures = f""".measure tran qg INTEG i(Vg) FROM=1.01n TO=3n
.measure tran qd INTEG i(Vd) FROM=1.01n TO=3n
.measure tran cgg param='abs(qg)/{dv:.6f}'
.measure tran cgd param='abs(qd)/{dv:.6f}'"""
        return (
            _header(conditions, "Capacitance (transient step)", backend)
            + _device_body(conditions, backend)
            + f"""
Vs s 0 0
Vg g 0 PWL(0 {vgs:.6f} 1n {vgs:.6f} 1.01n {vgs + dv:.6f})
Vd d 0 PWL(0 {vds:.6f} 1n {vds:.6f} 1.01n {vds + dv:.6f})
.tran 0.001n 5n
{cap_measures}
.end
"""
        )

    cap_measures = f""".measure tran qg INTEG i(Vg) FROM=1.01n TO=3n
.measure tran qd INTEG i(Vd) FROM=1.01n TO=3n
* cgg/cgd derived from qg/qd in post-processing (dv={dv:.6f} V)"""
    return (
        _header(conditions, "Capacitance (transient step)", backend)
        + _device_body(conditions, backend)
        + f"""
Vs s 0 0
Vg g 0 PWL(0 {vgs:.6f} 1n {vgs:.6f} 1.01n {vgs + dv:.6f})
Vd d 0 PWL(0 {vds:.6f} 1n {vds:.6f} 1.01n {vds + dv:.6f})
.tran 0.001n 5n
{cap_measures}
.end
"""
    )


def gidl_netlist(conditions: BenchConditions, backend: SimulatorBackend) -> str:
    """Generate GIDL/leakage deck (Vgs=0, Vds=Vdd)."""
    vdd = conditions.vdd
    if uses_hspice_deck(backend):
        measure = "* igidl extracted from .op log in post-processing"
    else:
        measure = ".measure dc igidl FIND i(Vd)"
    return (
        _header(conditions, "GIDL / retention leakage", backend)
        + _device_body(conditions, backend)
        + f"""
Vs s 0 0
Vg g 0 0
Vd d 0 {vdd:.6f}
.op
.print dc i(Vd) i(Vg)
{measure}
.end
"""
    )


def switching_netlist(conditions: BenchConditions, backend: SimulatorBackend) -> str:
    """Generate transient deck for WL switching energy."""
    vdd = conditions.vdd
    if backend == SimulatorBackend.NGSPICE:
        measure = "* esw integrated from transient log in post-processing"
    else:
        measure = ".measure tran esw INTEG 'v(g)*i(Vg)' FROM=0 TO=20n"
    return (
        _header(conditions, "WL switching transient", backend)
        + _device_body(conditions, backend)
        + f"""
Vs s 0 0
Vd d 0 {conditions.vdd_half:.6f}
Vg g 0 PWL(0 0 1n 0 2n {vdd:.6f} 10n {vdd:.6f})
.tran 0.1n 20n
.print tran v(g) i(Vg)
{measure}
.end
"""
    )


def write_device_decks(
    output_dir: Path,
    conditions: BenchConditions,
    backend: SimulatorBackend | None = None,
) -> dict[str, Path]:
    """Write all single-device benchmark decks to disk."""
    resolved = backend or resolve_backend()
    output_dir.mkdir(parents=True, exist_ok=True)
    model_id = conditions.model.model_id
    corner = conditions.corner.name
    decks = {
        "idvg_vds_half": idvg_netlist(conditions, conditions.vdd_half, resolved),
        "idvg_vds_full": idvg_netlist(conditions, conditions.vdd, resolved),
        "idvd_vwl": idvd_netlist(conditions, conditions.vdd, resolved),
        "idvd_vwl_boost": idvd_netlist(conditions, conditions.wl_boost, resolved),
        "ac_read": ac_cap_netlist(conditions, conditions.vdd, conditions.vdd_half, resolved),
        "gidl": gidl_netlist(conditions, resolved),
        "switching": switching_netlist(conditions, resolved),
    }
    paths: dict[str, Path] = {}
    for name, text in decks.items():
        if resolved == SimulatorBackend.NGSPICE:
            text = finalize_ngspice_deck(text)
        path = output_dir / f"{model_id}_{corner}_{name}.sp"
        path.write_text(text, encoding="utf-8")
        paths[name] = path
    return paths
