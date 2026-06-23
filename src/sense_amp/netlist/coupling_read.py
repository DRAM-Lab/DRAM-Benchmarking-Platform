"""Multi-BL coupling read netlist."""

from __future__ import annotations

from pathlib import Path

from sense_amp.bl_rc import BitlineRC, resolve_bitline_rc
from sense_amp.conditions import BenchConditions
from sense_amp.model_compat import resolve_inc_path
from sense_amp.netlist.read_column import _dv_measures
from sense_amp.paths import load_read_path_config, netlist_include_path
from sense_amp.simulator import SimulatorBackend, resolve_backend


def _header(conditions: BenchConditions, title: str, backend: SimulatorBackend) -> str:
    model = conditions.model
    inc_path = resolve_inc_path(model, backend)
    include_path = netlist_include_path(inc_path, model_id=model.model_id)
    return f"""* {title}
* Model: {model.model_id} | Corner: {conditions.corner.name}
.option gmin=1e-20 post=2 measdgt=8
.temp {conditions.temp_c}
.include '{include_path}'
"""


def _precharged_column(
    name: str,
    sense_node: str,
    bl_rc: BitlineRC,
    vbl_pre: float,
) -> list[str]:
    """High-Z precharged column; ``sense_node`` is the access-device attachment."""
    return [
        f"Vpre_{name} pre_{name} 0 dc {vbl_pre:.6f}",
        f"Rpre_{name} pre_{name} n_{name} 100e6",
        f"Rbl_{name} n_{name} n_{name}_mid {bl_rc.rbl_ohm:.6f}",
        f"Cbl_{name} n_{name}_mid 0 {bl_rc.cbl_f:.6e}",
        f"Rseg_{name} n_{name}_mid {sense_node} 0.1",
    ]


def coupling_read_netlist(
    conditions: BenchConditions,
    ccell_ff: float,
    bl_rc: BitlineRC,
    backend: SimulatorBackend,
    *,
    k_couple: float,
    config: dict | None = None,
) -> str:
    """Generate a three-column BL coupling deck with victim read on center BL."""
    cfg = config or load_read_path_config()
    coupling_cfg = cfg.get("coupling", {})
    aggressor_frac = float(coupling_cfg.get("aggressor_swing_fraction", 0.5))
    timing = cfg["read_timing"]
    wl_rise = float(timing["wl_rise_ns"])
    wl_fall = float(timing["wl_fall_ns"])
    t_stop = float(timing["t_stop_ns"])
    sample_times_ns = [float(t) for t in timing["sample_times_ns"]]

    vdd = conditions.vdd
    vbl_pre = conditions.vbl_pre
    model = conditions.model
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    ccell_f = ccell_ff * 1e-15
    c_couple = k_couple * bl_rc.cbl_f
    aggressor_delta = aggressor_frac * vbl_pre
    wl_victim_pwl = (
        f"PWL(0 0 {wl_rise - 0.1:.3f}n 0 {wl_rise:.3f}n {vdd:.6f} "
        f"{wl_fall:.3f}n {vdd:.6f} {wl_fall + 0.1:.3f}n 0 {t_stop:.3f}n 0)"
    )
    aggr_drive = (
        f"PWL(0 0 {wl_rise + 0.5:.3f}n 0 {wl_rise + 0.6:.3f}n {aggressor_delta:.6f} "
        f"{wl_fall:.3f}n {aggressor_delta:.6f} {wl_fall + 0.1:.3f}n 0 {t_stop:.3f}n 0)"
    )
    measures = _dv_measures(backend, sample_times_ns)

    body = []
    body.extend(_precharged_column("left", "bl_left", bl_rc, vbl_pre))
    body.extend(_precharged_column("victim", "bl_sense", bl_rc, vbl_pre))
    body.extend(_precharged_column("right", "bl_right", bl_rc, vbl_pre))
    body.extend(
        [
            f"Ccouple0 bl_left bl_sense {c_couple:.6e}",
            f"Ccouple1 bl_sense bl_right {c_couple:.6e}",
        ]
    )

    return (
        _header(conditions, f"Coupling read k={k_couple:.3f} Ccell={ccell_ff}fF", backend)
        + f"""
* Multi-BL coupling victim read (victim = bl_sense, ref = blb_sense)
{chr(10).join(body)}
Vpref pref 0 dc {vbl_pre:.6f}
Rpref pref blb 100e6
Rblb blb blb_int {bl_rc.rbl_ohm:.6f}
Cblb blb_int 0 {bl_rc.cbl_f:.6e}
Rseg_b blb_int blb_sense 0.1
Vwl wl 0 {wl_victim_pwl}
Vaggr aggr_drv 0 {aggr_drive}
Raggr aggr_drv bl_left 50
Vpl plate 0 dc {vbl_pre:.6f}
{bulk_source}Vs s 0 0
Mn1 bl_sense wl cell b nfet l={model.length_m:.3e} nfin={model.nfin}
Ccell cell plate {ccell_f:.6e}
.ic v(bl_sense)={vbl_pre:.6f} v(blb_sense)={vbl_pre:.6f} v(cell)=0
.tran 0.05n {t_stop}n
.print tran v(bl_sense) v(blb_sense) v(bl_left) v(bl_right)
{measures}.end
"""
    )


def write_coupling_decks(
    output_dir: Path,
    conditions: BenchConditions,
    ccell_ff: float,
    k_couple_values: list[float],
    backend: SimulatorBackend | None = None,
    *,
    config: dict | None = None,
) -> dict[str, Path]:
    """Write coupling read decks for multiple ``k_couple`` values."""
    resolved = backend or resolve_backend()
    cfg = config or load_read_path_config()
    bl_rc = resolve_bitline_rc(conditions.model.fpitch_m, cfg)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    model_id = conditions.model.model_id
    corner = conditions.corner.name
    for k_couple in k_couple_values:
        label = f"couple_{int(ccell_ff)}ff_k{int(k_couple * 100):02d}"
        path = output_dir / f"{model_id}_{corner}_{label}.sp"
        netlist = coupling_read_netlist(
            conditions, ccell_ff, bl_rc, resolved, k_couple=k_couple, config=cfg
        )
        path.write_text(netlist, encoding="utf-8")
        paths[label] = path
    return paths
