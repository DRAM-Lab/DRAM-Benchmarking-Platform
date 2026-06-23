# Simulator comparison (hot)

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
| rel_diff_ss_mv_dec_ngspice_vs_spectre | 0.2253 |
| rel_diff_ion_a_ngspice_vs_spectre | 1.393 |
| rel_diff_ioff_a_ngspice_vs_spectre | 1.653 |
| rel_diff_dibl_mv_v_ngspice_vs_spectre | 0.3437 |
| rel_diff_ron_ohm_ngspice_vs_spectre | 0.5821 |
| rel_diff_ron_boost_ohm_ngspice_vs_spectre | 0.5512 |
| rel_diff_cgg_f_ngspice_vs_spectre | 0.9923 |
| rel_diff_cgd_f_ngspice_vs_spectre | 1.507 |
| rel_diff_igidl_a_ngspice_vs_spectre | 1.653 |
| rel_diff_esw_j_ngspice_vs_spectre | 0.2162 |
| rel_diff_ion_per_cgg_ngspice_vs_spectre | 217.4 |
| rel_diff_ron_x_cload_ngspice_vs_spectre | 0.5821 |
| rel_diff_ioff_density_a_m2_ngspice_vs_spectre | 1.653 |

## cell
- Wide: `cell_1t1c_metrics_wide.csv`
- Rel diff: `cell_1t1c_metrics_rel_diff.csv`

| metric | max \|rel diff\| |
| --- | --- |
| rel_diff_t_write_s_ngspice_vs_spectre | 0.0001389 |
| rel_diff_t_read_s_ngspice_vs_spectre | 0.02456 |
| rel_diff_i_hold_a_ngspice_vs_spectre | 94.6 |
| rel_diff_q_read_c_ngspice_vs_spectre | 0.7272 |

## mini_array
- Wide: `mini_array_metrics_wide.csv`
- Rel diff: `mini_array_metrics_rel_diff.csv`

| metric | max \|rel diff\| |
| --- | --- |
| rel_diff_t_bl_settle_s_ngspice_vs_spectre | 0.3806 |
| rel_diff_i_bl_leak_a_ngspice_vs_spectre | 0.7111 |

## Known / flagged outliers

Rows with |rel diff| ≥ 0.35 or documented known patterns @ **hot**.
See [docs/simulator_cross_check.md](../docs/simulator_cross_check.md) for full context.

| suite | model | metric | backend | rel diff | known | note |
| --- | --- | --- | --- | --- | --- | --- |
| cell | VCT_125 | i_hold_a | ngspice | -0.4587 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | cgd_f | ngspice | 0.7989 | yes | Capacitance from transient qg/qd integration on OSDI VA model; stripped HSPICE-only cap flags — often much lower than... |
| device | VCT_125 | cgg_f | ngspice | -0.9922 | yes | Capacitance from transient qg/qd integration on OSDI VA model; stripped HSPICE-only cap flags — often much lower than... |
| device | VCT_125 | igidl_a | ngspice | -0.9062 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | ioff_a | ngspice | -0.9062 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | ioff_density_a_m2 | ngspice | -0.9062 | auto | Exceeds automatic rel-diff threshold |
| device | VCT_125 | ion_a | ngspice | 0.7054 | yes | ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. Directional use only. |
| device | VCT_125 | ion_per_cgg | ngspice | 217.4 | yes | Capacitance from transient qg/qd integration on OSDI VA model; stripped HSPICE-only cap flags — often much lower than... |
| device | VCT_125 | ron_boost_ohm | ngspice | -0.4156 | yes | ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. Directional use only. |
| device | VCT_125 | ron_ohm | ngspice | -0.4136 | yes | ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. Directional use only. |
| device | VCT_125 | ron_x_cload | ngspice | -0.4136 | auto | Exceeds automatic rel-diff threshold |
| mini_array | VCT_125 | t_bl_settle_s | ngspice | -0.2557 | yes | Transient timestep and OSDI trajectory vs Spectre (~35–40% @ tt). |
