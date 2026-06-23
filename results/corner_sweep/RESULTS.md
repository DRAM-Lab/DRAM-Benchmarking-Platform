# OpenDRAMBench — Results

Reproducible benchmark automation for Open DRAM model cards. This platform extends the Open DRAM Model Part I/II artifacts with push-button reruns, multi-tool comparison, validation, and provenance manifests.

**Models:** 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125

## Run summary

| Field | Value |
|-------|-------|
| Suite | `corner_sweep` |
| Corner | `tt` |
| Simulator | ngspice, spectre |
| Generated | 2026-06-23 13:24 UTC |
| Status | complete |
| Model bundle | OpenDRAMmodelV1 `e692790da857` |

## Contents

- [Device benchmark](#device-benchmark)
- [Executive summary](#executive-summary)
- [Corner matrix summary](#corner-matrix-summary)
- [Architecture highlights (tt)](#architecture-highlights-tt)
- [Device vs cell ranking (tt)](#device-vs-cell-ranking-tt)
- [Metric table (tt)](#metric-table-tt)
- [VCT scaling summary (tt)](#vct-scaling-summary-tt)
- [1T1C macro (20 fF reference)](#1t1c-macro-20-ff-reference)
- [1T1C Ccell sweep (tt)](#1t1c-ccell-sweep-tt)
- [Mini-array (layout BL RC)](#mini-array-layout-bl-rc)
- [Summary figures](#summary-figures)
- [Artifacts](#artifacts)
- [Reproduce](#reproduce)

---
## Device benchmark

**Generated:** 2026-06-23 13:24 UTC  
**Corners:** all (reference: **tt** for tables/plots)  
**Simulator:** spectre  
**Models:** 7 access devices  
**OpenDRAMmodelV1 revision:** `14b3550`

Cross-architecture DRAM access transistor benchmark (BCAT vs VCT vs 3D GAA) using OpenDRAMmodelV1.

## Executive summary

- **Highest Ion:** `BCAT_125` (0.000e+00 A)
- **Lowest Ioff:** `BCAT_125` (0.000e+00 A)

## Corner matrix summary

Primary tables and Pareto/VCT/radar plots use **tt** reference data.

| Corner | Mean Ion (A) | Mean Ioff (A) | Max Ion model |
| --- | --- | --- | --- |
| cold | 0.000e+00 | 0.000e+00 | `BCAT_125` (0.000e+00 A) |
| ff | 0.000e+00 | 0.000e+00 | `BCAT_125` (0.000e+00 A) |
| hot | 0.000e+00 | 0.000e+00 | `BCAT_125` (0.000e+00 A) |
| ss | 0.000e+00 | 0.000e+00 | `BCAT_125` (0.000e+00 A) |
| ss_125 | 0.000e+00 | 0.000e+00 | `BCAT_125` (0.000e+00 A) |
| tt | 0.000e+00 | 0.000e+00 | `BCAT_125` (0.000e+00 A) |

## Architecture highlights (tt)

- **3D_GAA**: highest Ion = `3D_gaa_Si` (0.000e+00 A); lowest Ioff = `3D_gaa_Si` (0.000e+00 A)
- **BCAT**: highest Ion = `BCAT_125` (0.000e+00 A); lowest Ioff = `BCAT_125` (0.000e+00 A)
- **VCT**: highest Ion = `VCT_082` (0.000e+00 A); lowest Ioff = `VCT_082` (0.000e+00 A)

## Device vs cell ranking (tt)

_No valid t_read data._

## Metric table (tt)

| Model | Architecture | Vdd (V) | Ion (A) | Ioff (A) | Vt (V) | SS (mV/dec) | DIBL (mV/V) | Ron (Ω) | Cgg (F) | Cgd (F) | GIDL (A) | Ion/Cgg (1/s) | Ron×Cload (s) | Ioff density (A/m²) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BCAT_125 | BCAT | 0.85 | 0.000e+00 | 0.000e+00 | — | — | — | — | — | — | 0.000e+00 | — | — | 0.000e+00 |
| VCT_082 | VCT | 0.90 | 0.000e+00 | 0.000e+00 | — | — | — | — | — | — | 0.000e+00 | — | — | 0.000e+00 |
| VCT_091 | VCT | 0.90 | 0.000e+00 | 0.000e+00 | — | — | — | — | — | — | 0.000e+00 | — | — | 0.000e+00 |
| VCT_102 | VCT | 0.90 | 0.000e+00 | 0.000e+00 | — | — | — | — | — | — | 0.000e+00 | — | — | 0.000e+00 |
| VCT_125 | VCT | 0.90 | 0.000e+00 | 0.000e+00 | — | — | — | — | — | — | 0.000e+00 | — | — | 0.000e+00 |
| 3D_gaa_Si | 3D_GAA | 0.75 | 0.000e+00 | 0.000e+00 | — | — | — | — | — | — | 0.000e+00 | — | — | 0.000e+00 |
| 3D_gaa_AOS | 3D_GAA | 0.75 | 0.000e+00 | 0.000e+00 | — | — | — | — | — | — | 0.000e+00 | — | — | 0.000e+00 |

## VCT scaling summary (tt)

| Node | Ion (A) | Ioff (A) | Ron (Ω) | vsat |
| --- | --- | --- | --- | --- |
| 082 | 0.000e+00 | 0.000e+00 | nan | 25420 |
| 091 | 0.000e+00 | 0.000e+00 | nan | 26820 |
| 102 | 0.000e+00 | 0.000e+00 | nan | 28720 |
| 125 | 0.000e+00 | 0.000e+00 | nan | 28720 |

- **082 → 125 Ion:** — (0.000e+00 → 0.000e+00 A)
- **082 → 125 Ioff:** — (0.000e+00 → 0.000e+00 A)
- **082 → 125 Ron:** +nan% (nan → nan Ω)
- Drive improves with node; Ioff rises — retention vs drive trade-off in the VCT cards.
- Full step-by-step analysis: [vct_scaling_analysis.md](../docs/vct_scaling_analysis.md)

## 1T1C macro (20 fF reference)

| Model | Ccell (fF) | t_write (s) | t_read (s) | I_hold (A) | Q_read (C) |
| --- | --- | --- | --- | --- | --- |
| BCAT_125 | 20 | — | — | — | — |
| VCT_082 | 20 | — | — | — | — |
| VCT_091 | 20 | — | — | — | — |
| VCT_102 | 20 | — | — | — | — |
| VCT_125 | 20 | — | — | — | — |
| 3D_gaa_Si | 20 | — | — | — | — |
| 3D_gaa_AOS | 20 | — | — | — | — |

## 1T1C Ccell sweep (tt)

Full transient sweep at 10, 20, and 30 fF per model.

| Model | Ccell (fF) | t_write (s) | t_read (s) | I_hold (A) | Q_read (C) |
| --- | --- | --- | --- | --- | --- |
| 3D_gaa_AOS | 10 | — | — | — | — |
| 3D_gaa_AOS | 20 | — | — | — | — |
| 3D_gaa_AOS | 30 | — | — | — | — |
| 3D_gaa_Si | 10 | — | — | — | — |
| 3D_gaa_Si | 20 | — | — | — | — |
| 3D_gaa_Si | 30 | — | — | — | — |
| BCAT_125 | 10 | — | — | — | — |
| BCAT_125 | 20 | — | — | — | — |
| BCAT_125 | 30 | — | — | — | — |
| VCT_082 | 10 | — | — | — | — |
| VCT_082 | 20 | — | — | — | — |
| VCT_082 | 30 | — | — | — | — |
| VCT_091 | 10 | — | — | — | — |
| VCT_091 | 20 | — | — | — | — |
| VCT_091 | 30 | — | — | — | — |
| VCT_102 | 10 | — | — | — | — |
| VCT_102 | 20 | — | — | — | — |
| VCT_102 | 30 | — | — | — | — |
| VCT_125 | 10 | — | — | — | — |
| VCT_125 | 20 | — | — | — | — |
| VCT_125 | 30 | — | — | — | — |

## Mini-array (layout BL RC)

| Model | N cells | BL topology | t_BL settle (s) | I_BL leak (A) | R_metal/pitch (Ω) | R_contact (Ω) | C_SA (fF) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BCAT_125 | 8 | layout | — | — | 3.50 | 2.86 | 21.0 |
| VCT_082 | 8 | layout | — | — | 5.00 | 2.00 | 30.0 |
| VCT_091 | 8 | layout | — | — | 5.00 | 2.00 | 30.0 |
| VCT_102 | 8 | layout | — | — | 5.00 | 2.00 | 30.0 |
| VCT_125 | 8 | layout | — | — | 5.00 | 2.00 | 30.0 |
| 3D_gaa_Si | 8 | layout | — | — | 1.83 | 5.45 | 11.0 |
| 3D_gaa_AOS | 8 | layout | — | — | 5.00 | 2.00 | 30.0 |

## Summary figures

### Pareto: Ion vs Ioff

![Pareto: Ion vs Ioff](figures/pareto_ion_ioff.svg)

### VCT node scaling

![VCT node scaling](figures/vct_scaling.svg)

### Composite figure of merit

![Composite figure of merit](figures/radar_fom.svg)

### Corner Sensitivity Ion

![Corner Sensitivity Ion](figures/corner_sensitivity_ion.svg)

### Corner Sensitivity Ioff

![Corner Sensitivity Ioff](figures/corner_sensitivity_ioff.svg)

### 1T1C read time vs Ccell

![1T1C read time vs Ccell](figures/ccell_scaling.svg)

## Artifacts

| File | Description |
|------|-------------|
| [`MANIFEST.json`](MANIFEST.json) | Provenance manifest with SHA-256 checksums |
| [`figures/`](figures/) | Summary SVG plots |
## Reproduce

```bash
./scripts/run_experiments.sh                    # default: full benchmark bundle
SUITE=corner_sweep ./scripts/run_experiments.sh     # replay this suite
dram-bench run --suite corner_sweep --corner tt --output corner_sweep
```

Metric definitions: [docs/benchmark_spec.md](../docs/benchmark_spec.md)

---
*Report produced by `dram-bench` / `run_experiments.sh`*