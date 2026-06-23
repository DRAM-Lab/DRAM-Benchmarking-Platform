# OpenDRAM Model Provenance

Auto-generated confidence tiers and calibration lineage for OpenDRAMmodelV1.
Regenerate with ``dram-validate provenance``.

- **Model bundle fingerprint:** `e692790da857`
- **Bundle path:** `models/OpenDRAMmodelV1`

## Confidence legend

| Tier | Meaning |
|------|---------|
| **H** | High — literature or MATRIX PDK number with ±5–10% band |
| **M** | Medium — inferred from roadmap or cross-architecture scaling |
| **L** | Low — extrapolated beyond published nodes (e.g. D0-class) |

## BCAT_125

- **Architecture:** BCAT
- **Card:** `BCAT_125.inc`
- **Corner:** T=27.0 °C, Vdd=0.85 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| Ion | H | 3.024e-07 | ion_a |
| Ioff | H | 6.143e-14 | ioff_a |
| t_read | H | 2.272e-08 | t_read_s |
| fpitch | H | 4.2e-08 | fpitch_m |
| Ron | M | 2.811e+06 | ron_ohm |
| Cgg | M | 4.726e-17 | cgg_f |

**Sources:** Open DRAM Model Part 1 §III-A (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); Open DRAM Model Part 1 Table timing Fig. 14 (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); 6F² D1b BCAT baseline (Part I §III-A; Part II Table 2)

- **Card nominal Vdd:** 0.85 V
- **Card fpitch:** 42.0 nm

## VCT_082

- **Architecture:** VCT
- **Card:** `VCT_082.inc`
- **Corner:** T=27.0 °C, Vdd=0.9 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| Ion | H | 8.62e-06 | ion_a |
| Ioff | H | [—, 5.43e-18] | ioff_a |
| t_read | M | 1.2e-08 | t_read_s |
| fpitch | H | 6e-08 | fpitch_m |
| Ron | M | 9.693e+05 | ron_ohm |
| Cgg | M | 1.216e-17 | cgg_f |

**Sources:** Open DRAM Model Part 1 Table III Case 3 (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); Open DRAM Model Part 1 Fig. 14 (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); 4F² VCT D/R 12.5 nm, junction-underlap Case 3 (Part I Table III)

- **Card nominal Vdd:** 0.9 V
- **Card fpitch:** 60.0 nm

## VCT_091

- **Architecture:** VCT
- **Card:** `VCT_091.inc`
- **Corner:** T=27.0 °C, Vdd=0.9 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| Ion | H | 9.742e-07 | ion_a |
| Ioff | H | 3.877e-12 | ioff_a |
| t_read | M | 2.282e-08 | t_read_s |
| fpitch | H | 6e-08 | fpitch_m |
| Ron | M | 9.238e+05 | ron_ohm |
| Cgg | M | 1.217e-17 | cgg_f |

**Sources:** Open DRAM Model Part 1 Table III Case 3 (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); Open DRAM Model Part 1 Fig. 14 (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); 4F² VCT D/R 12.5 nm, junction-underlap Case 3 (Part I Table III)

- **Card nominal Vdd:** 0.9 V
- **Card fpitch:** 60.0 nm

## VCT_102

- **Architecture:** VCT
- **Card:** `VCT_102.inc`
- **Corner:** T=27.0 °C, Vdd=0.9 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| Ion | H | 1.035e-06 | ion_a |
| Ioff | H | 4.067e-12 | ioff_a |
| t_read | M | 2.283e-08 | t_read_s |
| fpitch | H | 6e-08 | fpitch_m |
| Ron | M | 8.695e+05 | ron_ohm |
| Cgg | M | 1.219e-17 | cgg_f |

**Sources:** Open DRAM Model Part 1 Table III Case 3 (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); Open DRAM Model Part 1 Fig. 14 (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704358); 4F² VCT D/R 12.5 nm, junction-underlap Case 3 (Part I Table III)

- **Card nominal Vdd:** 0.9 V
- **Card fpitch:** 60.0 nm

## VCT_125

- **Architecture:** VCT
- **Card:** `VCT_125.inc`
- **Corner:** T=27.0 °C, Vdd=0.9 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| fpitch | H | 6e-08 | fpitch_m |
| Ron | M | 6.403e+05 | ron_ohm |
| Cgg | M | 1.244e-17 | cgg_f |

**Sources:** Open DRAM Model Part 2 Table IV (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704508); 4F² VCT D1b+3 generation, D/R 10.2 nm (Part II Table 4)

- **Card nominal Vdd:** 0.9 V
- **Card fpitch:** 60.0 nm

## 3D_gaa_Si

- **Architecture:** 3D_GAA
- **Card:** `3D_gaa_Si.inc`
- **Corner:** T=27.0 °C, Vdd=0.75 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| Ion | H | 1.041e-06 | ion_a |
| Ioff | H | 1.011e-14 | ioff_a |
| fpitch | H | 2.2e-08 | fpitch_m |
| Ron | M | 7.207e+05 | ron_ohm |
| Cgg | M | 1.663e-16 | cgg_f |

**Sources:** Open DRAM Model Part 2 Table II (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704508); 3D DRAM Si channel (Part II Table 2)

- **Card fpitch:** 22.0 nm

## 3D_gaa_AOS

- **Architecture:** 3D_GAA
- **Card:** `3D_gaa_AOS.inc`
- **Corner:** T=27.0 °C, Vdd=0.75 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| Ion | H | 1.885e-06 | ion_a |
| Ioff | H | 8.455e-11 | ioff_a |
| fpitch | H | 6e-08 | fpitch_m |
| Ron | M | 3.978e+05 | ron_ohm |
| Cgg | M | 7.082e-17 | cgg_f |
| I_hold | L | [—, 5e-10] | i_hold_a |

**Sources:** Open DRAM Model Part 2 Table II (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704508); 3D DRAM AOS (IWO) channel (Part II Table 2)

- **Card fpitch:** 60.0 nm

## hv_peri_28_32

- **Architecture:** HV_PERI
- **Card:** `hv_peri_28_32.inc`
- **Corner:** T=27.0 °C, Vdd=1.0 V

| Metric | Confidence | Reference band | Column |
|--------|------------|----------------|--------|
| nominal_vdd | M | 1 | nominal_vdd |
| vth0 | M | 0.63 | vth0 |
| rdsw | M | 190 | rdsw |
| u0 | M | 0.042 | u0 |
| vsat | M | 1.55e+05 | vsat |

**Sources:** Open DRAM Model Part 2 §Open DRAM Model Information (IEEE JxCDC 2026, DOI 10.1109/JXCDC.2026.3704508); HV periphery 28–32 nm class (Part II §Open DRAM Model Information)

- **Card nominal Vdd:** 1.0 V
