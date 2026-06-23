# OpenDRAMBench — Results

Reproducible benchmark automation for Open DRAM model cards. This platform extends the Open DRAM Model Part I/II artifacts with push-button reruns, multi-tool comparison, validation, and provenance manifests.

**Models:** 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125

## Run summary

| Field | Value |
|-------|-------|
| Suite | `validation` |
| Corner | `tt` |
| Simulator | ngspice, spectre |
| Generated | 2026-06-23 16:05 UTC |
| Status | complete |
| Model bundle | OpenDRAMmodelV1 `e692790da857` |

## Contents

- [OpenDRAM Validation Summary](#opendram-validation-summary)
- [Executive summary](#executive-summary)
- [1. Model validation status](#1-model-validation-status)
- [2. Golden metric margins](#2-golden-metric-margins)
- [3. Roadmap trends](#3-roadmap-trends)
- [4. Literature correlation](#4-literature-correlation)
- [5. Confidence tiers](#5-confidence-tiers)
- [6. Local sensitivity (OAT ±5%)](#6-local-sensitivity-oat-5)
- [7. Pinned device metrics (TT)](#7-pinned-device-metrics-tt)
- [8. Pinned 1T1C metrics (20 fF, TT)](#8-pinned-1t1c-metrics-20-ff-tt)
- [9. SPICE simulator cross-check (Spectre / HSPICE / ngspice)](#9-spice-simulator-cross-check-spectre-hspice-ngspice)
- [Data files](#data-files)
- [Artifacts](#artifacts)
- [Reproduce](#reproduce)

---
## OpenDRAM Validation Summary

**Status:** PASS — 8/8 models pass, 0 trend violation(s)

- **Generated:** 2026-06-23 16:04 UTC
- **Model SHA:** `e692790da857`
- **Corner:** TT (27 °C)
- **Pinned metrics:** `bench/validation/pinned/` (TT corner)

## Executive summary

All golden YAML tolerance bands and declared VCT trends are satisfied against pinned SPICE-extracted metrics.

## 1. Model validation status

| Model | Architecture | Status | Errors |
| --- | --- | --- | --- |
| BCAT_125 | BCAT | PASS | 0 |
| VCT_082 | VCT | PASS | 0 |
| VCT_091 | VCT | PASS | 0 |
| VCT_102 | VCT | PASS | 0 |
| VCT_125 | VCT | PASS | 0 |
| 3D_gaa_Si | 3D_GAA | PASS | 0 |
| 3D_gaa_AOS | 3D_GAA | PASS | 0 |
| hv_peri_28_32 | HV_PERI | PASS | 0 |

### Validation error count per model

![Validation error count per model](figures/validation_status.svg)

*Figure: `figures/validation_status.svg`*

## 2. Golden metric margins

Relative margin = (observed − golden) / golden × 100% for metrics with a reference value.

| Model | Metric | Conf. | Golden | Observed | Margin % | Status |
| --- | --- | --- | --- | --- | --- | --- |
| BCAT_125 | Ion | high | 3.024e-07 | 3.024e-07 | 0.0 | PASS |
| BCAT_125 | Ioff | high | 6.143e-14 | 6.143e-14 | 0.0 | PASS |
| BCAT_125 | fpitch | high | 4.200e-08 | 4.200e-08 | 0.0 | PASS |
| BCAT_125 | Ron | medium | 2.811e+06 | 2.811e+06 | 0.0 | PASS |
| BCAT_125 | Cgg | medium | 4.726e-17 | 4.726e-17 | 0.0 | PASS |
| VCT_082 | Ion | high | 8.620e-06 | 9.285e-07 | -89.2 | PASS |
| VCT_082 | Ioff | high | — | 3.731e-12 | — | PASS |
| VCT_082 | fpitch | high | 6.000e-08 | 6.000e-08 | 0.0 | PASS |
| VCT_082 | Ron | medium | 9.693e+05 | 9.693e+05 | 0.0 | PASS |
| VCT_082 | Cgg | medium | 1.216e-17 | 1.216e-17 | 0.0 | PASS |
| VCT_091 | Ion | high | 9.742e-07 | 9.742e-07 | 0.0 | PASS |
| VCT_091 | Ioff | high | 3.877e-12 | 3.877e-12 | 0.0 | PASS |
| VCT_091 | fpitch | high | 6.000e-08 | 6.000e-08 | 0.0 | PASS |
| VCT_091 | Ron | medium | 9.238e+05 | 9.238e+05 | 0.0 | PASS |
| VCT_091 | Cgg | medium | 1.217e-17 | 1.217e-17 | 0.0 | PASS |
| VCT_102 | Ion | high | 1.035e-06 | 1.035e-06 | 0.0 | PASS |
| VCT_102 | Ioff | high | 4.067e-12 | 4.067e-12 | 0.0 | PASS |
| VCT_102 | fpitch | high | 6.000e-08 | 6.000e-08 | 0.0 | PASS |
| VCT_102 | Ron | medium | 8.695e+05 | 8.695e+05 | 0.0 | PASS |
| VCT_102 | Cgg | medium | 1.219e-17 | 1.219e-17 | 0.0 | PASS |
| VCT_125 | fpitch | high | 6.000e-08 | 6.000e-08 | 0.0 | PASS |
| VCT_125 | Ron | medium | 6.403e+05 | 6.403e+05 | 0.0 | PASS |
| VCT_125 | Cgg | medium | 1.244e-17 | 1.244e-17 | 0.0 | PASS |
| 3D_gaa_Si | Ion | high | 1.041e-06 | 1.041e-06 | 0.0 | PASS |
| 3D_gaa_Si | Ioff | high | 1.011e-14 | 1.011e-14 | 0.0 | PASS |
| 3D_gaa_Si | fpitch | high | 2.200e-08 | 2.200e-08 | 0.0 | PASS |
| 3D_gaa_Si | Ron | medium | 7.207e+05 | 7.207e+05 | 0.0 | PASS |
| 3D_gaa_Si | Cgg | medium | 1.663e-16 | 1.663e-16 | 0.0 | PASS |
| 3D_gaa_AOS | Ion | high | 1.885e-06 | 1.885e-06 | 0.0 | PASS |
| 3D_gaa_AOS | Ioff | high | 8.455e-11 | 8.455e-11 | 0.0 | PASS |
| 3D_gaa_AOS | fpitch | high | 6.000e-08 | 6.000e-08 | 0.0 | PASS |
| 3D_gaa_AOS | Ron | medium | 3.978e+05 | 3.978e+05 | 0.0 | PASS |
| 3D_gaa_AOS | Cgg | medium | 7.082e-17 | 7.082e-17 | 0.0 | PASS |

### Signed margin vs golden reference

![Signed margin vs golden reference](figures/golden_margins.svg)

*Figure: `figures/golden_margins.svg`*

## 3. Roadmap trends

| Metric | Direction | Models | Status |
| --- | --- | --- | --- |
| Ion | increasing | VCT_082,VCT_091,VCT_102,VCT_125 | PASS |
| Ioff | non_decreasing | VCT_082,VCT_091,VCT_102,VCT_125 | PASS |

### VCT Ion / Ioff / Ron scaling

![VCT Ion / Ioff / Ron scaling](figures/vct_scaling.svg)

*Figure: `figures/vct_scaling.svg`*

## 4. Literature correlation

| Model | Metric | Open value | Literature band | Dir | Mag |
| --- | --- | --- | --- | --- | --- |
| BCAT_125 | fpitch | 42 | [38.0, 52.0] nm | True | H |
| BCAT_125 | Vdd | 0.85 | [0.85, 1.0] V | True | H |
| BCAT_125 | Ion | 3.024e-07 | directional (VCT Ion increases 082→125) | True | M |
| VCT_082 | fpitch | 60 | [38.0, 52.0] nm | True | L |
| VCT_082 | Vdd | 0.9 | [0.85, 1.0] V | True | H |
| VCT_082 | Ion | 9.285e-07 | directional (VCT Ion increases 082→125) | True | M |
| VCT_091 | fpitch | 60 | [38.0, 52.0] nm | True | L |
| VCT_091 | Vdd | 0.9 | [0.85, 1.0] V | True | H |
| VCT_091 | Ion | 9.742e-07 | directional (VCT Ion increases 082→125) | True | M |
| VCT_102 | fpitch | 60 | [38.0, 52.0] nm | True | L |
| VCT_102 | Vdd | 0.9 | [0.85, 1.0] V | True | H |
| VCT_102 | Ion | 1.035e-06 | directional (VCT Ion increases 082→125) | True | M |
| VCT_125 | fpitch | 60 | [38.0, 52.0] nm | True | L |
| VCT_125 | Vdd | 0.9 | [0.85, 1.0] V | True | H |
| VCT_125 | Ion | 1.406e-06 | directional (VCT Ion increases 082→125) | True | M |
| 3D_gaa_Si | fpitch | 22 | [38.0, 52.0] nm | True | L |
| 3D_gaa_Si | Vdd | 0.75 | [0.85, 1.0] V | True | L |
| 3D_gaa_Si | Ion | 1.041e-06 | directional (VCT Ion increases 082→125) | True | M |
| 3D_gaa_AOS | fpitch | 60 | [38.0, 52.0] nm | True | L |
| 3D_gaa_AOS | Vdd | 0.75 | [0.85, 1.0] V | True | L |
| 3D_gaa_AOS | Ion | 1.885e-06 | directional (VCT Ion increases 082→125) | True | M |

### Pitch and Vdd vs public roadmap

![Pitch and Vdd vs public roadmap](figures/literature_correlation.svg)

*Figure: `figures/literature_correlation.svg`*

## 5. Confidence tiers

| Tier | Meaning |
|------|---------|
| H | High — literature or PDK number, ±5–10% |
| M | Medium — inferred scaling, ±20% envelope |
| L | Low — extrapolated / directional only |

### H/M/L metric count per model

![H/M/L metric count per model](figures/confidence_tiers.svg)

*Figure: `figures/confidence_tiers.svg`*

### Cross-architecture normalized comparison

![Cross-architecture normalized comparison](figures/architecture_radar.svg)

*Figure: `figures/architecture_radar.svg`*

## 6. Local sensitivity (OAT ±5%)

Top parameters by abs Δi_hold from cached local OAT sensitivity screen.

| Model | Parameter | abs Δ | Nominal |
| --- | --- | --- | --- |
| 3D_gaa_AOS | agidl | 0.1500 | 0.001 |
| VCT_125 | agidl | 0.1480 | 0.0002 |
| BCAT_125 | agidl | 0.0860 | 0.0001 |

### OAT sensitivity — i_hold

![OAT sensitivity — i_hold](figures/sensitivity_oat_ihold.svg)

*Figure: `figures/sensitivity_oat_ihold.svg`*

### OAT sensitivity — Ion

![OAT sensitivity — Ion](figures/sensitivity_oat_ion.svg)

*Figure: `figures/sensitivity_oat_ion.svg`*

## 7. Pinned device metrics (TT)

| Model | Arch. | Vdd (V) | Ion (A) | Ioff (A) | Ron (Ω) | fpitch (m) |
| --- | --- | --- | --- | --- | --- | --- |
| BCAT_125 | BCAT | 0.85 | 3.024e-07 | 6.143e-14 | 2.811e+06 | 4.20e-08 |
| VCT_082 | VCT | 0.90 | 9.285e-07 | 3.731e-12 | 9.693e+05 | 6.00e-08 |
| VCT_091 | VCT | 0.90 | 9.742e-07 | 3.877e-12 | 9.238e+05 | 6.00e-08 |
| VCT_102 | VCT | 0.90 | 1.035e-06 | 4.067e-12 | 8.695e+05 | 6.00e-08 |
| VCT_125 | VCT | 0.90 | 1.406e-06 | 1.093e-11 | 6.403e+05 | 6.00e-08 |
| 3D_gaa_Si | 3D_GAA | 0.75 | 1.041e-06 | 1.011e-14 | 7.207e+05 | 2.20e-08 |
| 3D_gaa_AOS | 3D_GAA | 0.75 | 1.885e-06 | 8.455e-11 | 3.978e+05 | 6.00e-08 |

## 8. Pinned 1T1C metrics (20 fF, TT)

| Model | t_read (s) | t_write (s) | I_hold (A) |
| --- | --- | --- | --- |
| BCAT_125 | 2.272e-08 | 1.900e-09 | 8.384e-14 |
| VCT_082 | 2.282e-08 | 1.900e-09 | 6.021e-11 |
| VCT_091 | 2.282e-08 | 1.900e-09 | 6.016e-11 |
| VCT_102 | 2.283e-08 | 1.900e-09 | 6.009e-11 |
| VCT_125 | 2.293e-08 | 1.900e-09 | 5.757e-11 |
| 3D_gaa_Si | 2.291e-08 | 1.900e-09 | 1.672e-11 |
| 3D_gaa_AOS | 2.257e-08 | 1.901e-09 | 3.455e-10 |

## 9. SPICE simulator cross-check (Spectre / HSPICE / ngspice)

Reference backend: **spectre** (tt corner). Relative Δ = (backend − reference) / reference.

| Backend | Pinned role | Host available |
| --- | --- | --- |
| spectre | reference | yes |
| hspice | compared | no |
| ngspice | compared | yes |

*Note:* Post-fix pin: HSPICE -inc, ngspice parser/measures

### Max abs relative difference by metric

| Metric | Backend | max abs Δ | mean abs Δ |
| --- | --- | --- | --- |
| cgg_f | ngspice | 0.9925 | 0.9382 |
| ioff_a | hspice | 1.885 | 0.2693 |
| ioff_a | ngspice | 1.885 | 1.059 |
| ion_a | hspice | 0.7154 | 0.1022 |
| ion_a | ngspice | 1.405 | 0.8461 |
| ron_ohm | ngspice | 0.9781 | 0.8783 |

### Simulator agreement summary

![Simulator max abs rel diff](figures/simulator_max_rel_diff.svg)

*Figure: `figures/simulator_max_rel_diff.svg`*

### Per-model relative Δ heatmap

![Simulator rel diff heatmap](figures/simulator_rel_diff_heatmap.svg)

*Figure: `figures/simulator_rel_diff_heatmap.svg`*

### Spectre vs alternate backend scatter

![Spectre vs backend scatter](figures/simulator_spectre_vs_backend.svg)

*Figure: `figures/simulator_spectre_vs_backend.svg`*

### Per-model Ion / Ioff / Ron / Cgg vs Spectre

| Model | Metric | Backend | Rel Δ |
| --- | --- | --- | --- |
| 3D_gaa_AOS | cgg_f | ngspice | -0.9416 |
| 3D_gaa_AOS | ioff_a | hspice | 1.975e-08 |
| 3D_gaa_AOS | ioff_a | ngspice | -0.7481 |
| 3D_gaa_AOS | ion_a | hspice | 0 |
| 3D_gaa_AOS | ion_a | ngspice | 1.405 |
| 3D_gaa_AOS | ron_ohm | ngspice | -0.9409 |
| 3D_gaa_Si | cgg_f | ngspice | -0.9022 |
| 3D_gaa_Si | ioff_a | hspice | 1.885 |
| 3D_gaa_Si | ioff_a | ngspice | 1.885 |
| 3D_gaa_Si | ion_a | hspice | 0.7154 |
| 3D_gaa_Si | ion_a | ngspice | 0.7154 |
| 3D_gaa_Si | ron_ohm | ngspice | -0.9144 |
| BCAT_125 | cgg_f | ngspice | -0.7556 |
| BCAT_125 | ioff_a | hspice | -1.374e-07 |
| BCAT_125 | ioff_a | ngspice | -0.8586 |
| BCAT_125 | ion_a | hspice | 1.29e-09 |
| BCAT_125 | ion_a | ngspice | 0.8447 |
| BCAT_125 | ron_ohm | ngspice | -0.9415 |
| VCT_082 | cgg_f | ngspice | -0.9914 |
| VCT_082 | ioff_a | hspice | -2.68e-09 |
| VCT_082 | ioff_a | ngspice | -0.9841 |
| VCT_082 | ion_a | hspice | -2.477e-10 |
| VCT_082 | ion_a | ngspice | 0.7182 |
| VCT_082 | ron_ohm | ngspice | -0.7176 |
| VCT_091 | cgg_f | ngspice | -0.992 |
| VCT_091 | ioff_a | hspice | -2.58e-09 |
| VCT_091 | ioff_a | ngspice | -0.984 |
| VCT_091 | ion_a | hspice | -3.901e-10 |
| VCT_091 | ion_a | ngspice | 0.7241 |
| VCT_091 | ron_ohm | ngspice | -0.7901 |
| VCT_102 | cgg_f | ngspice | -0.9925 |
| VCT_102 | ioff_a | hspice | 0 |
| VCT_102 | ioff_a | ngspice | -0.9838 |
| VCT_102 | ion_a | hspice | 0 |
| VCT_102 | ion_a | ngspice | 0.732 |
| VCT_102 | ron_ohm | ngspice | -0.8656 |
| VCT_125 | cgg_f | ngspice | -0.9924 |
| VCT_125 | ioff_a | hspice | 4.575e-09 |
| VCT_125 | ioff_a | ngspice | -0.9693 |
| VCT_125 | ion_a | hspice | 0 |
| VCT_125 | ion_a | ngspice | 0.7834 |
| VCT_125 | ron_ohm | ngspice | -0.9781 |

### 1T1C cell metrics (20 fF)

| Metric | Backend | max abs Δ | mean abs Δ |
| --- | --- | --- | --- |
| i_hold_a | hspice | 0.5638 | 0.1161 |
| i_hold_a | ngspice | 93.13 | 13.73 |
| t_read_s | hspice | 0.003388 | 0.001231 |
| t_read_s | ngspice | 0.007101 | 0.004778 |
| t_write_s | hspice | 2.319e-08 | 1.5e-08 |
| t_write_s | ngspice | 6.726e-05 | 4.359e-05 |

#### 1T1C simulator agreement

![1T1C simulator max abs rel diff](figures/simulator_cell_max_rel_diff.svg)

*Figure: `figures/simulator_cell_max_rel_diff.svg`*

![1T1C simulator rel diff heatmap](figures/simulator_cell_rel_diff_heatmap.svg)

*Figure: `figures/simulator_cell_rel_diff_heatmap.svg`*

![1T1C Spectre vs backend scatter](figures/simulator_cell_spectre_vs_backend.svg)

*Figure: `figures/simulator_cell_spectre_vs_backend.svg`*

#### Per-model 1T1C timing / hold vs Spectre

| Model | Metric | Backend | Rel Δ |
| --- | --- | --- | --- |
| 3D_gaa_AOS | i_hold_a | hspice | -0.01252 |
| 3D_gaa_AOS | i_hold_a | ngspice | 0.304 |
| 3D_gaa_AOS | t_read_s | hspice | 0.002392 |
| 3D_gaa_AOS | t_read_s | ngspice | 0.00304 |
| 3D_gaa_AOS | t_write_s | hspice | -2.301e-08 |
| 3D_gaa_AOS | t_write_s | ngspice | 6.726e-05 |
| 3D_gaa_Si | i_hold_a | hspice | -0.09985 |
| 3D_gaa_Si | i_hold_a | ngspice | 0.766 |
| 3D_gaa_Si | t_read_s | hspice | 0.003388 |
| 3D_gaa_Si | t_read_s | ngspice | 0.001318 |
| 3D_gaa_Si | t_write_s | hspice | 6.923e-09 |
| 3D_gaa_Si | t_write_s | ngspice | 2.654e-05 |
| BCAT_125 | i_hold_a | hspice | -0.5638 |
| BCAT_125 | i_hold_a | ngspice | 93.13 |
| BCAT_125 | t_read_s | hspice | 7.859e-06 |
| BCAT_125 | t_read_s | ngspice | 0.004928 |
| BCAT_125 | t_write_s | hspice | -1.206e-08 |
| BCAT_125 | t_write_s | ngspice | 6.722e-05 |
| VCT_082 | i_hold_a | hspice | -0.03013 |
| VCT_082 | i_hold_a | ngspice | -0.4743 |
| VCT_082 | t_read_s | hspice | 0.000525 |
| VCT_082 | t_read_s | ngspice | -0.007101 |
| VCT_082 | t_write_s | hspice | 1.327e-08 |
| VCT_082 | t_write_s | ngspice | -3.605e-05 |
| VCT_091 | i_hold_a | hspice | -0.02943 |
| VCT_091 | i_hold_a | ngspice | -0.474 |
| VCT_091 | t_read_s | hspice | 0.0005459 |
| VCT_091 | t_read_s | ngspice | -0.007086 |
| VCT_091 | t_write_s | hspice | 1.327e-08 |
| VCT_091 | t_write_s | ngspice | -3.605e-05 |
| VCT_102 | i_hold_a | hspice | -0.02858 |
| VCT_102 | i_hold_a | ngspice | -0.4737 |
| VCT_102 | t_read_s | hspice | 0.0005643 |
| VCT_102 | t_read_s | ngspice | -0.007063 |
| VCT_102 | t_write_s | hspice | 1.327e-08 |
| VCT_102 | t_write_s | ngspice | -3.605e-05 |
| VCT_125 | i_hold_a | hspice | -0.04811 |
| VCT_125 | i_hold_a | ngspice | -0.4674 |
| VCT_125 | t_read_s | hspice | 0.001195 |
| VCT_125 | t_read_s | ngspice | -0.002913 |
| VCT_125 | t_write_s | hspice | 2.319e-08 |
| VCT_125 | t_write_s | ngspice | -3.598e-05 |

### Mini-array metrics

| Metric | Backend | max abs Δ | mean abs Δ |
| --- | --- | --- | --- |
| i_bl_leak_a | hspice | 0.1199 | 0.0182 |
| i_bl_leak_a | ngspice | 20.75 | 12.29 |
| t_bl_settle_s | hspice | 0.1845 | 0.028 |
| t_bl_settle_s | ngspice | 0.3954 | 0.3954 |

#### Mini-array simulator agreement

![Mini-array simulator max abs rel diff](figures/simulator_mini_array_max_rel_diff.svg)

*Figure: `figures/simulator_mini_array_max_rel_diff.svg`*

![Mini-array simulator rel diff heatmap](figures/simulator_mini_array_rel_diff_heatmap.svg)

*Figure: `figures/simulator_mini_array_rel_diff_heatmap.svg`*

![Mini-array Spectre vs backend scatter](figures/simulator_mini_array_spectre_vs_backend.svg)

*Figure: `figures/simulator_mini_array_spectre_vs_backend.svg`*

#### Per-model mini-array vs Spectre

| Model | Metric | Backend | Rel Δ |
| --- | --- | --- | --- |
| 3D_gaa_AOS | i_bl_leak_a | hspice | 0.0003399 |
| 3D_gaa_AOS | i_bl_leak_a | ngspice | 9.233 |
| 3D_gaa_AOS | t_bl_settle_s | hspice | 0.003833 |
| 3D_gaa_Si | i_bl_leak_a | hspice | 0.1199 |
| 3D_gaa_Si | i_bl_leak_a | ngspice | 1.48 |
| 3D_gaa_Si | t_bl_settle_s | hspice | -0.1845 |
| BCAT_125 | i_bl_leak_a | hspice | 0.001944 |
| BCAT_125 | i_bl_leak_a | ngspice | 0.7838 |
| BCAT_125 | t_bl_settle_s | hspice | -0.003557 |
| BCAT_125 | t_bl_settle_s | ngspice | -0.3954 |
| VCT_082 | i_bl_leak_a | hspice | 0.001281 |
| VCT_082 | i_bl_leak_a | ngspice | 20.75 |
| VCT_082 | t_bl_settle_s | hspice | -0.0009534 |
| VCT_091 | i_bl_leak_a | hspice | 0.001276 |
| VCT_091 | i_bl_leak_a | ngspice | 20.26 |
| VCT_091 | t_bl_settle_s | hspice | -0.0003382 |
| VCT_102 | i_bl_leak_a | hspice | 0.00137 |
| VCT_102 | i_bl_leak_a | ngspice | 19.69 |
| VCT_102 | t_bl_settle_s | hspice | -0.001268 |
| VCT_125 | i_bl_leak_a | hspice | 0.001283 |
| VCT_125 | i_bl_leak_a | ngspice | 13.84 |
| VCT_125 | t_bl_settle_s | hspice | -0.001511 |

Regenerate pinned comparison:

```bash
dram-validate simulators --refresh
```

## Data files

| File | Description |
|------|-------------|
| [`data/cell_metrics_tt_20ff.csv`](data/cell_metrics_tt_20ff.csv) | Pinned TT 1T1C metrics at 20 fF |
| [`data/correlation_matrix.csv`](data/correlation_matrix.csv) | Literature alignment scores |
| [`data/device_metrics_tt.csv`](data/device_metrics_tt.csv) | Pinned TT device metrics |
| [`data/metric_detail.csv`](data/metric_detail.csv) | Full golden vs observed detail |
| [`data/model_summary.csv`](data/model_summary.csv) | Per-model pass/fail summary |
| [`data/sensitivity_oat.csv`](data/sensitivity_oat.csv) | Cached local OAT perturbation results |
| [`data/simulator_cell_detail.csv`](data/simulator_cell_detail.csv) | Per-model 1T1C simulator metric deltas |
| [`data/simulator_cell_rel_diff.csv`](data/simulator_cell_rel_diff.csv) | 1T1C cell metric rel differences across simulators (20 fF) |
| [`data/simulator_cell_summary.csv`](data/simulator_cell_summary.csv) | Max abs 1T1C rel diff by metric and backend |
| [`data/simulator_cell_wide.csv`](data/simulator_cell_wide.csv) | Per-simulator 1T1C metrics wide merge (20 fF) |
| [`data/simulator_device_detail.csv`](data/simulator_device_detail.csv) | Per-model simulator metric deltas |
| [`data/simulator_device_rel_diff.csv`](data/simulator_device_rel_diff.csv) | Spectre vs HSPICE/ngspice device rel differences |
| [`data/simulator_device_summary.csv`](data/simulator_device_summary.csv) | Max abs rel diff by metric and backend |
| [`data/simulator_device_wide.csv`](data/simulator_device_wide.csv) | Per-simulator device metrics (wide merge) |
| [`data/simulator_mini_array_detail.csv`](data/simulator_mini_array_detail.csv) | Per-model mini-array simulator metric deltas |
| [`data/simulator_mini_array_rel_diff.csv`](data/simulator_mini_array_rel_diff.csv) | Mini-array metric rel differences across simulators |
| [`data/simulator_mini_array_summary.csv`](data/simulator_mini_array_summary.csv) | Max abs mini-array rel diff by metric and backend |
| [`data/simulator_mini_array_wide.csv`](data/simulator_mini_array_wide.csv) | Per-simulator mini-array metrics wide merge |
| [`data/trend_detail.csv`](data/trend_detail.csv) | Roadmap trend checks |

---

Regenerate: `dram-validate report` or `./run_validation.sh`

Model cards: `models/OpenDRAMmodelV1`

## Artifacts

| File | Description |
|------|-------------|
| [`MANIFEST.json`](MANIFEST.json) | Provenance manifest with SHA-256 checksums |
| [`data/`](data/) | Validation audit CSV exports |
| [`figures/`](figures/) | Summary SVG plots |
## Reproduce

```bash
./scripts/run_experiments.sh                    # default: full benchmark bundle
SUITE=validation ./scripts/run_experiments.sh     # replay this suite
dram-bench run --suite validation --corner tt --output validation
```

Metric definitions: [docs/benchmark_spec.md](../docs/benchmark_spec.md)

---
*Report produced by `dram-bench` / `run_experiments.sh`*