"""Distributed, layout-faithful, and lumped mini-array SPICE netlist generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bench.conditions import BenchConditions
from bench.model_compat import finalize_ngspice_deck, resolve_inc_path
from bench.models import osd_instance_name
from bench.paths import netlist_include_path
from bench.simulator import SimulatorBackend, resolve_backend, uses_spectre_deck


@dataclass(frozen=True)
class MiniArrayLayout:
    """Resolved mini-array geometry and bitline RC scaling."""

    n_cells: int
    rbl_ohm: float
    cbl_ff: float
    ccell_ff: float
    topology: str
    r_seg_ohm: float
    c_seg_ff: float
    r_metal_seg_ohm: float = 0.0
    r_contact_ohm: float = 0.0
    c_metal_seg_ff: float = 0.0
    c_wl_coupling_ff: float = 0.0
    c_sa_ff: float = 0.0
    c_far_end_ff: float = 0.0


def resolve_mini_array_layout(model_fpitch_m: float, config: dict) -> MiniArrayLayout:
    """Scale mini-array parameters from reference fpitch to the model fpitch.

    Args:
        model_fpitch_m: Model feature pitch in meters.
        config: Benchmark YAML configuration.

    Returns:
        Layout with total and per-segment bitline RC for the selected topology.
    """
    mini_cfg = config.get("mini_array", {})
    n_cells = int(mini_cfg.get("n_cells", 8))
    ref_fpitch = float(mini_cfg.get("ref_fpitch_m", 6.0e-8))
    topology = str(mini_cfg.get("topology", "layout")).lower()
    pitch_ratio = model_fpitch_m / ref_fpitch

    layout_cfg = mini_cfg.get("layout", {})
    r_metal_at_ref = float(layout_cfg.get("r_metal_ohm_per_pitch_at_60nm", 5.0))
    r_contact_at_ref = float(layout_cfg.get("r_contact_ohm_at_60nm", 2.0))
    c_metal_at_ref = float(layout_cfg.get("c_metal_ff_per_pitch_at_60nm", 20.0))
    c_wl_at_ref = float(layout_cfg.get("c_wl_coupling_ff_at_60nm", 2.0))
    c_sa_at_ref = float(layout_cfg.get("c_sa_ff_at_60nm", 30.0))
    c_far_at_ref = float(layout_cfg.get("c_far_end_ff_at_60nm", 10.0))

    r_metal_seg = r_metal_at_ref * pitch_ratio
    r_contact = r_contact_at_ref / max(pitch_ratio, 1e-6)
    c_metal_seg = c_metal_at_ref * pitch_ratio
    c_wl = c_wl_at_ref * pitch_ratio
    c_sa = c_sa_at_ref * pitch_ratio
    c_far = c_far_at_ref * pitch_ratio

    rbl_at_ref = float(mini_cfg.get("rbl_ohm_at_60nm", 50.0))
    cbl_at_ref = float(mini_cfg.get("cbl_ff_at_60nm", 200.0))
    rbl_ohm = rbl_at_ref / max(pitch_ratio, 1e-6)
    cbl_ff = cbl_at_ref * pitch_ratio

    ccell_values = [float(v) for v in config.get("ccell_values_ff", [20])]
    ccell_ff = 20.0 if 20.0 in ccell_values else ccell_values[len(ccell_values) // 2]

    if topology == "layout":
        r_seg_ohm = r_metal_seg
        c_seg_ff = c_metal_seg
        equiv_r = max(n_cells - 1, 1) * r_metal_seg
        equiv_c = (
            n_cells * c_metal_seg + c_sa + c_far + n_cells * c_wl
        )
        return MiniArrayLayout(
            n_cells=n_cells,
            rbl_ohm=equiv_r,
            cbl_ff=equiv_c,
            ccell_ff=ccell_ff,
            topology=topology,
            r_seg_ohm=r_seg_ohm,
            c_seg_ff=c_seg_ff,
            r_metal_seg_ohm=r_metal_seg,
            r_contact_ohm=r_contact,
            c_metal_seg_ff=c_metal_seg,
            c_wl_coupling_ff=c_wl,
            c_sa_ff=c_sa,
            c_far_end_ff=c_far,
        )

    r_seg_ohm = rbl_ohm / max(n_cells - 1, 1)
    c_seg_ff = cbl_ff / max(n_cells, 1)
    return MiniArrayLayout(
        n_cells=n_cells,
        rbl_ohm=rbl_ohm,
        cbl_ff=cbl_ff,
        ccell_ff=ccell_ff,
        topology=topology,
        r_seg_ohm=r_seg_ohm,
        c_seg_ff=c_seg_ff,
    )


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


def _source_reference_line() -> str:
    """Tie the shared source/bulk node to ground (required for ngspice OP)."""
    return "Vs s 0 0\n"


def _mini_array_measures(
    backend: SimulatorBackend,
    sense_node: str,
    vdd_half: float,
    i_probe: str,
) -> str:
    """Return transient measures for bitline settling and leakage."""
    bl_droop = vdd_half * 0.99
    crossing = f""".measure tran t_bl_settle FIND time WHEN v({sense_node})={bl_droop:.6f} CROSS=1 FROM=2n TO=25n
.measure tran i_bl_leak AVG {i_probe} FROM=15n TO=25n"""
    if uses_spectre_deck(backend) or backend == SimulatorBackend.NGSPICE:
        return crossing
    # TRIG/TARG: absolute time of first BL droop crossing (HSPICE rejects bare TRIG VAL=…).
    return f""".measure tran t_bl_settle TRIG AT=0 TARG v({sense_node}) VAL={bl_droop:.6f} FALL=1 TD=2ns
.measure tran i_bl_leak AVG {i_probe} FROM=15n TO=25n"""


def _append_cell_instances(
    lines: list[str],
    conditions: BenchConditions,
    layout: MiniArrayLayout,
    bl_tap_nodes: list[str],
    backend: SimulatorBackend,
) -> None:
    """Append access devices and storage caps for each cell on the bitline."""
    vdd = conditions.vdd
    vdd_half = conditions.vdd_half
    model = conditions.model
    bulk_net = "s" if model.bulk_tied_to_source else "b"
    for idx in range(layout.n_cells):
        wl = f"wl{idx}"
        cell = f"cell{idx}"
        plate = f"plate{idx}"
        bl_tap = bl_tap_nodes[idx]
        if idx == 0:
            lines.append(f"V{wl} {wl} 0 PWL(0 0 1n 0 2n {vdd:.6f} 25n {vdd:.6f})")
            lines.append(f"V{plate} {plate} 0 0")
        else:
            lines.append(f"V{wl} {wl} 0 0")
            lines.append(f"V{plate} {plate} 0 {vdd_half:.6f}")
        if backend == SimulatorBackend.NGSPICE:
            inst = (
                f"{osd_instance_name(f'Mn{idx}')} {bl_tap} {wl} {cell} {bulk_net} nfet "
                f"L={model.length_m:.3e} NFIN={model.nfin}"
            )
        else:
            inst = (
                f"Mn{idx} {bl_tap} {wl} {cell} {bulk_net} nfet "
                f"l={model.length_m:.3e} nfin={model.nfin}"
            )
        lines.append(inst)
        lines.append(f"Ccell{idx} {cell} {plate} {layout.ccell_ff * 1e-15:.6e}")


def mini_array_netlist(
    conditions: BenchConditions,
    layout: MiniArrayLayout,
    backend: SimulatorBackend | None = None,
) -> str:
    """Generate a mini-array deck with layout, distributed, or lumped bitline RC.

    Args:
        conditions: Resolved bench conditions.
        layout: Mini-array geometry and RC layout.
        backend: Simulator backend (default: auto-resolve).

    Returns:
        SPICE netlist string.
    """
    if layout.topology == "lumped":
        return _mini_array_lumped_netlist(conditions, layout, backend)
    if layout.topology == "layout":
        return _mini_array_layout_netlist(conditions, layout, backend)
    return _mini_array_distributed_netlist(conditions, layout, backend)


def _mini_array_layout_netlist(
    conditions: BenchConditions,
    layout: MiniArrayLayout,
    backend: SimulatorBackend | None = None,
) -> str:
    """Full layout array: metal segments, contact R, WL coupling, SA and far-end caps."""
    vdd_half = conditions.vdd_half
    model = conditions.model
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    resolved = backend or resolve_backend()
    bl_nodes = [f"bl{idx}" for idx in range(layout.n_cells)]
    bl_taps = [f"bltap{idx}" for idx in range(layout.n_cells)]

    lines = [
        _header(conditions, f"Mini-array N={layout.n_cells} layout", resolved),
        f"* Layout BL @ fpitch: Rmetal={layout.r_metal_seg_ohm:.4g} Ohm/pitch, "
        f"Rcontact={layout.r_contact_ohm:.4g} Ohm, Cmetal={layout.c_metal_seg_ff:.4g} fF/pitch",
        f"* Csa={layout.c_sa_ff:.4g} fF, Cfar={layout.c_far_end_ff:.4g} fF, "
        f"Cwl={layout.c_wl_coupling_ff:.4g} fF/cell",
        f"Vpre pre 0 dc {vdd_half:.6f}",
        f"Rpre pre {bl_nodes[0]} 100e6",
        f"Csa {bl_nodes[0]} 0 {layout.c_sa_ff * 1e-15:.6e}",
        _source_reference_line(),
        bulk_source,
    ]

    for idx in range(layout.n_cells):
        lines.append(
            f"Cmetal{idx} {bl_nodes[idx]} 0 {layout.c_metal_seg_ff * 1e-15:.6e}"
        )
        lines.append(
            f"Rct{idx} {bl_nodes[idx]} {bl_taps[idx]} {layout.r_contact_ohm:.6g}"
        )
        wl = f"wl{idx}"
        lines.append(
            f"Cwl{idx} {bl_nodes[idx]} {wl} {layout.c_wl_coupling_ff * 1e-15:.6e}"
        )
        if idx < layout.n_cells - 1:
            lines.append(
                f"Rmetal{idx} {bl_nodes[idx]} {bl_nodes[idx + 1]} "
                f"{layout.r_metal_seg_ohm:.6g}"
            )

    lines.append(
        f"Cfar {bl_nodes[-1]} 0 {layout.c_far_end_ff * 1e-15:.6e}"
    )

    _append_cell_instances(lines, conditions, layout, bl_taps, resolved)

    ic_nodes = " ".join(f"v({node})={vdd_half:.6f}" for node in bl_nodes)
    lines.append(f".ic {ic_nodes} v(cell0)=0")
    lines.append(".tran 0.05n 25n")
    lines.append(
        f".print tran v({bl_nodes[0]}) v({bl_nodes[-1]}) i(Vpre)"
    )
    lines.append(_mini_array_measures(resolved, bl_nodes[0], vdd_half, "i(Vpre)"))
    lines.append(".end")
    return "\n".join(lines) + "\n"


def _mini_array_distributed_netlist(
    conditions: BenchConditions,
    layout: MiniArrayLayout,
    backend: SimulatorBackend | None = None,
) -> str:
    """Simplified RC ladder: per-segment R and per-tap C along the bitline."""
    vdd_half = conditions.vdd_half
    model = conditions.model
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    resolved = backend or resolve_backend()
    bl_nodes = [f"bl{idx}" for idx in range(layout.n_cells)]

    lines = [
        _header(conditions, f"Mini-array N={layout.n_cells} distributed", resolved),
        f"* Distributed BL: Rseg={layout.r_seg_ohm:.4g} Ohm, Cseg={layout.c_seg_ff:.4g} fF per tap",
        f"Vpre pre 0 dc {vdd_half:.6f}",
        f"Rpre pre {bl_nodes[0]} 100e6",
        _source_reference_line(),
        bulk_source,
    ]

    for idx in range(layout.n_cells - 1):
        lines.append(
            f"Rseg{idx} {bl_nodes[idx]} {bl_nodes[idx + 1]} {layout.r_seg_ohm:.6g}"
        )
    for idx in range(layout.n_cells):
        lines.append(f"Cseg{idx} {bl_nodes[idx]} 0 {layout.c_seg_ff * 1e-15:.6e}")

    _append_cell_instances(lines, conditions, layout, bl_nodes, resolved)

    ic_nodes = " ".join(f"v({node})={vdd_half:.6f}" for node in bl_nodes)
    lines.append(f".ic {ic_nodes} v(cell0)=0")
    lines.append(".tran 0.05n 25n")
    lines.append(f".print tran v({bl_nodes[0]}) v({bl_nodes[-1]}) i(Vpre)")
    lines.append(_mini_array_measures(resolved, bl_nodes[0], vdd_half, "i(Vpre)"))
    lines.append(".end")
    return "\n".join(lines) + "\n"


def _mini_array_lumped_netlist(
    conditions: BenchConditions,
    layout: MiniArrayLayout,
    backend: SimulatorBackend | None = None,
) -> str:
    """Legacy lumped RBL/CBL mini-array (single internal BL node)."""
    vdd_half = conditions.vdd_half
    model = conditions.model
    bulk_source = "" if model.bulk_tied_to_source else "Vb b 0 0\n"
    resolved = backend or resolve_backend()
    bl_tap = "bl_int"

    lines = [
        _header(conditions, f"Mini-array N={layout.n_cells} lumped", resolved),
        f"Vbl bl 0 {vdd_half:.6f}",
        f"Rbl bl {bl_tap} {layout.rbl_ohm:.6g}",
        f"Cbl {bl_tap} 0 {layout.cbl_ff * 1e-15:.6e}",
        _source_reference_line(),
        bulk_source,
    ]

    _append_cell_instances(lines, conditions, layout, [bl_tap] * layout.n_cells, resolved)
    lines.append(".ic v(cell0)=0")
    lines.append(".tran 0.05n 25n")
    lines.append(f".print tran v({bl_tap}) i(Vbl)")
    lines.append(_mini_array_measures(resolved, bl_tap, vdd_half, "i(Vbl)"))
    lines.append(".end")
    return "\n".join(lines) + "\n"


def write_mini_array_deck(
    output_dir: Path,
    conditions: BenchConditions,
    layout: MiniArrayLayout,
    backend: SimulatorBackend | None = None,
) -> Path:
    """Write one mini-array deck for a model/corner.

    Args:
        output_dir: Output directory.
        conditions: Bench conditions.
        layout: Resolved mini-array layout.
        backend: Simulator backend override.

    Returns:
        Path to the written deck.
    """
    resolved = backend or resolve_backend()
    output_dir.mkdir(parents=True, exist_ok=True)
    model_id = conditions.model.model_id
    corner = conditions.corner.name
    path = output_dir / f"{model_id}_{corner}_mini_array.sp"
    text = mini_array_netlist(conditions, layout, resolved)
    if resolved == SimulatorBackend.NGSPICE:
        text = finalize_ngspice_deck(text)
    path.write_text(text, encoding="utf-8")
    return path
