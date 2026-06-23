# Simulator comparison (cold)

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

| metric | max \|rel diff\| |
| --- | --- |
| rel_diff_vt_v_ngspice_vs_spectre | 0 |
| rel_diff_ss_mv_dec_ngspice_vs_spectre | 0.3167 |
| rel_diff_ion_a_ngspice_vs_spectre | 1.385 |
| rel_diff_ioff_a_ngspice_vs_spectre | 2.241 |
| rel_diff_dibl_mv_v_ngspice_vs_spectre | 0.5123 |
| rel_diff_ron_ohm_ngspice_vs_spectre | 0.5807 |
| rel_diff_ron_boost_ohm_ngspice_vs_spectre | 0.5458 |
| rel_diff_cgg_f_ngspice_vs_spectre | 0.9928 |
| rel_diff_cgd_f_ngspice_vs_spectre | 1.474 |
| rel_diff_igidl_a_ngspice_vs_spectre | 2.241 |
| rel_diff_esw_j_ngspice_vs_spectre | 0.2017 |
| rel_diff_ion_per_cgg_ngspice_vs_spectre | 256.3 |
| rel_diff_ron_x_cload_ngspice_vs_spectre | 0.5807 |
| rel_diff_ioff_density_a_m2_ngspice_vs_spectre | 2.241 |

## cell
- Wide: `cell_1t1c_metrics_wide.csv`
- Rel diff: `cell_1t1c_metrics_rel_diff.csv`

| metric | max \|rel diff\| |
| --- | --- |
| rel_diff_t_write_s_ngspice_vs_spectre | 0.0001365 |
| rel_diff_t_read_s_ngspice_vs_spectre | 0.007833 |
| rel_diff_i_hold_a_ngspice_vs_spectre | 97.41 |
| rel_diff_q_read_c_ngspice_vs_spectre | 2.635 |

## mini_array
- Wide: `mini_array_metrics_wide.csv`
- Rel diff: `mini_array_metrics_rel_diff.csv`

| metric | max \|rel diff\| |
| --- | --- |
| rel_diff_t_bl_settle_s_ngspice_vs_spectre | 0.4146 |
| rel_diff_i_bl_leak_a_ngspice_vs_spectre | 0.8695 |

## Known / flagged outliers

Rows with |rel diff| ≥ 0.35 or documented known patterns @ **cold**.
See [docs/simulator_cross_check.md](../docs/simulator_cross_check.md) for full context.

| suite | model | metric | backend | rel diff | known | note |
| --- | --- | --- | --- | --- | --- | --- |
| cell | VCT_125 | i_hold_a | ngspice | -0.4812 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | cgd_f | ngspice | 1.007 | yes | Capacitance from transient qg/qd integration on OSDI VA model; stripped HSPICE-only cap flags — often much lower than... |
| device | VCT_125 | cgg_f | ngspice | -0.9926 | yes | Capacitance from transient qg/qd integration on OSDI VA model; stripped HSPICE-only cap flags — often much lower than... |
| device | VCT_125 | dibl_mv_v | ngspice | -0.352 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | igidl_a | ngspice | -0.9971 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | ioff_a | ngspice | -0.9971 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | ioff_density_a_m2 | ngspice | -0.9971 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | ion_a | ngspice | 0.8935 | yes | ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. Directional use only. |
| device | VCT_125 | ion_per_cgg | ngspice | 256.3 | yes | Capacitance from transient qg/qd integration on OSDI VA model; stripped HSPICE-only cap flags — often much lower than... |
| device | VCT_125 | ron_boost_ohm | ngspice | -0.4694 | yes | ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. Directional use only. |
| device | VCT_125 | ron_ohm | ngspice | -0.4719 | yes | ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. Directional use only. |
| device | VCT_125 | ron_x_cload | ngspice | -0.4719 | auto | Exceeds automatic rel-diff threshold |
| mini_array | VCT_125 | t_bl_settle_s | ngspice | -0.372 | yes | Transient timestep and OSDI trajectory vs Spectre (~35–40% @ tt). |
