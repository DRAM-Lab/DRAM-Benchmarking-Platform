"""1T1C differential read-column SPICE netlist generation."""

from __future__ import annotations

from pathlib import Path

from sense_amp.bl_rc import BitlineRC, resolve_bitline_rc
from sense_amp.conditions import BenchConditions
from sense_amp.model_compat import resolve_inc_path
from sense_amp.paths import netlist_include_path
from sense_amp.paths import load_read_path_config
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


def _dv_measure_expr(backend: SimulatorBackend) -> str:
    """Return the differential BL expression used in ``.measure`` statements."""
    expr = "v(bl_sense)-v(blb_sense)"
    if backend is SimulatorBackend.SPECTRE:
        return f"par('{expr}')"
    return expr


def _dv_measures(backend: SimulatorBackend, sample_times_ns: list[float]) -> str:
    """Return backend-specific ``.measure`` statements for ΔV_BL samples."""
    expr = _dv_measure_expr(backend)
    lines: list[str] = []
    for t_ns in sample_times_ns:
        key = f"dv_{int(t_ns)}ns"
        if backend is SimulatorBackend.SPECTRE:
            lines.append(f".measure tran {key} FIND {expr} AT={t_ns}n")
        else:
            lines.append(f".measure tran {key} FIND {expr} AT={t_ns}n")
    return "\n".join(lines) + "\n"


def read_column_netlist(
    conditions: BenchConditions,
    ccell_ff: float,
    bl_rc: BitlineRC,
    backend: SimulatorBackend,
    *,
    config: dict | None = None,
) -> str:
    """Generate differential 1T1C + lumped BL RC read-column deck.

    The victim cell stores logic-0 (``v(cell)=0``). BL and BLB are precharged to
    ``VBL_pre`` with high-Z precharge sources. WL asserts to ``Vdd`` to develop
    a negative differential on BL relative to the reference bitline.

    Args:
        conditions: Resolved bench conditions.
        ccell_ff: Cell capacitance in fF.
        bl_rc: Scaled bitline RC.
        backend: Target simulator for measure syntax.
        config: Optional read-path configuration override.

    Returns:
        SPICE netlist string.
    """
    cfg = config or load_read_path_config()
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
    wl_pwl = (
        f"PWL(0 0 {wl_rise - 0.1:.3f}n 0 {wl_rise:.3f}n {vdd:.6f} "
        f"{wl_fall:.3f}n {vdd:.6f} {wl_fall + 0.1:.3f}n 0 {t_stop:.3f}n 0)"
    )
    measures = _dv_measures(backend, sample_times_ns)

    ic_line = (
        f".ic v(bl)={vbl_pre:.6f} v(blb)={vbl_pre:.6f} "
        f"v(bl_sense)={vbl_pre:.6f} v(blb_sense)={vbl_pre:.6f} v(cell)=0"
    )
    return (
        _header(conditions, f"Read column Ccell={ccell_ff}fF VBL_pre={vbl_pre:.3f}V", backend)
        + f"""
* Differential read column with lumped BL RC
* High-Z precharge (pre -> BL through 100 MΩ); signal at bl_sense / blb_sense
Vpre pre 0 dc {vbl_pre:.6f}
Rpre pre bl 100e6
Vpref pref 0 dc {vbl_pre:.6f}
Rpref pref blb 100e6
Rbl bl bl_int {bl_rc.rbl_ohm:.6f}
Cbl bl_int 0 {bl_rc.cbl_f:.6e}
Rblb blb blb_int {bl_rc.rbl_ohm:.6f}
Cblb blb_int 0 {bl_rc.cbl_f:.6e}
Rseg bl_int bl_sense 0.1
Rseg_b blb_int blb_sense 0.1
Vwl wl 0 {wl_pwl}
Vpl plate 0 dc {vbl_pre:.6f}
{bulk_source}Vs s 0 0
Mn1 bl_sense wl cell b nfet l={model.length_m:.3e} nfin={model.nfin}
Ccell cell plate {ccell_f:.6e}
{ic_line}
.tran 0.05n {t_stop}n
.print tran v(bl_sense) v(blb_sense) v(cell) v(wl)
{measures}.end
"""
    )


def write_read_column_decks(
    output_dir: Path,
    conditions: BenchConditions,
    ccell_values_ff: list[float],
    backend: SimulatorBackend | None = None,
    *,
    config: dict | None = None,
) -> dict[str, Path]:
    """Write read-column decks for multiple Ccell values.

    Args:
        output_dir: Output directory.
        conditions: Bench conditions.
        ccell_values_ff: Cell capacitance sweep in fF.
        backend: Simulator backend override.
        config: Optional read-path configuration.

    Returns:
        Mapping of deck label to path.
    """
    resolved = backend or resolve_backend()
    cfg = config or load_read_path_config()
    bl_rc = resolve_bitline_rc(conditions.model.fpitch_m, cfg)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    model_id = conditions.model.model_id
    corner = conditions.corner.name
    vbl_tag = int(round(conditions.vbl_pre / conditions.vdd * 100))
    for ccell in ccell_values_ff:
        label = f"read_{int(ccell)}ff_vbl{vbl_tag}"
        path = output_dir / f"{model_id}_{corner}_{label}.sp"
        path.write_text(
            read_column_netlist(conditions, ccell, bl_rc, resolved, config=cfg),
            encoding="utf-8",
        )
        paths[label] = path
    return paths
