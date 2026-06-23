# Simulator comparison (ff)

Relative differences use Spectre as reference when present.

## Documented cross-simulator expectations

Full guide: [docs/simulator_cross_check.md](../docs/simulator_cross_check.md)

- **3D_gaa_Si** — `ion_a, ron_ohm, ron_boost_ohm, ron_x_cload` (hspice, ngspice vs spectre): Spectre loads BSIM-CMG 105.03 (112.x compatibility patch); HSPICE/ngspice use native 112.0.0 — Ion and Ron diverge (~40–71% @ tt).
- **BCAT_125** — `i_hold_a` (ngspice vs spectre): ngspice OSDI BSIM-CMG shows higher subthreshold leakage in the 1T1C hold window.
- **all models** — `ion_a, ron_ohm, ron_boost_ohm` (ngspice vs spectre): ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. Directional use only.
- **all models** — `cgg_f, cgd_f, ion_per_cgg` (ngspice vs spectre): Capacitance from transient qg/qd integration on OSDI VA model; stripped HSPICE-only cap flags — often much lower than Spectre.
- **all models** — `t_bl_settle_s` (ngspice vs spectre): Transient timestep and OSDI trajectory vs Spectre (~35–40% @ tt).

## device
- Wide: `device_metrics_wide.csv`
- Rel diff: `device_metrics_rel_diff.csv`

| metric | max |rel diff| |
|--------|-------------|

## cell
- Wide: `cell_1t1c_metrics_wide.csv`
- Rel diff: `cell_1t1c_metrics_rel_diff.csv`

| metric | max |rel diff| |
|--------|-------------|

## mini_array
- Wide: `mini_array_metrics_wide.csv`
- Rel diff: `mini_array_metrics_rel_diff.csv`

| metric | max |rel diff| |
|--------|-------------|

## Known / flagged outliers

No rows exceeded |rel diff| ≥ 0.35 @ ff.
