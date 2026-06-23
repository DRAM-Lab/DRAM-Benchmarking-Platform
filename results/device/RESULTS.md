# OpenDRAMBench — Results

Reproducible benchmark automation for Open DRAM model cards. This platform extends the Open DRAM Model Part I/II artifacts with push-button reruns, multi-tool comparison, validation, and provenance manifests.

**Models:** 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125

## Run summary

| Field | Value |
|-------|-------|
| Suite | `device` |
| Corner | `tt` |
| Simulator | ngspice, spectre |
| Generated | 2026-06-23 16:04 UTC |
| Status | complete |
| Model bundle | OpenDRAMmodelV1 `e692790da857` |

## Contents

- [Device benchmark](#device-benchmark)
- [Executive summary](#executive-summary)
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

**Generated:** 2026-06-23 16:04 UTC  
**Corners:** tt (reference: **tt** for tables/plots)  
**Simulator:** spectre  
**Models:** 7 access devices  
**OpenDRAMmodelV1 revision:** `416f124`

Cross-architecture DRAM access transistor benchmark (BCAT vs VCT vs 3D GAA) using OpenDRAMmodelV1.

## Executive summary

- **Highest Ion:** `3D_gaa_AOS` (1.885e-06 A)
- **Lowest Ioff:** `3D_gaa_Si` (1.011e-14 A)
- **Fastest 1T1C read @ 20 fF:** `3D_gaa_AOS` (2.257e-08 s)

## Architecture highlights (tt)

- **3D_GAA**: highest Ion = `3D_gaa_AOS` (1.885e-06 A); lowest Ioff = `3D_gaa_Si` (1.011e-14 A)
- **BCAT**: highest Ion = `BCAT_125` (3.024e-07 A); lowest Ioff = `BCAT_125` (6.143e-14 A)
- **VCT**: highest Ion = `VCT_125` (1.406e-06 A); lowest Ioff = `VCT_082` (3.731e-12 A)

## Device vs cell ranking (tt)

- **Fastest device Ion:** `3D_gaa_AOS`
- **Fastest 1T1C read (20 fF):** `3D_gaa_AOS`
- Device Ion and 1T1C read leaders align at 20 fF.

## Metric table (tt)

| Model | Architecture | Vdd (V) | Ion (A) | Ioff (A) | Vt (V) | SS (mV/dec) | DIBL (mV/V) | Ron (Ω) | Cgg (F) | Cgd (F) | GIDL (A) | Ion/Cgg (1/s) | Ron×Cload (s) | Ioff density (A/m²) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BCAT_125 | BCAT | 0.85 | 3.024e-07 | 6.143e-14 | 0.850 | 9.0 | 7.8 | 2.811e+06 | 4.726e-17 | 5.495e-13 | 6.143e-14 | 6.398e+09 | 5.622e-08 | 3.482e+01 |
| VCT_082 | VCT | 0.90 | 9.285e-07 | 3.731e-12 | 0.900 | 10.3 | 130.1 | 9.693e+05 | 1.216e-17 | 1.522e-12 | 3.731e-12 | 7.638e+10 | 1.939e-08 | 1.036e+03 |
| VCT_091 | VCT | 0.90 | 9.742e-07 | 3.877e-12 | 0.900 | 10.3 | 130.6 | 9.238e+05 | 1.217e-17 | 1.595e-12 | 3.877e-12 | 8.004e+10 | 1.848e-08 | 1.077e+03 |
| VCT_102 | VCT | 0.90 | 1.035e-06 | 4.067e-12 | 0.900 | 10.3 | 131.3 | 8.695e+05 | 1.219e-17 | 1.691e-12 | 4.067e-12 | 8.493e+10 | 1.739e-08 | 1.130e+03 |
| VCT_125 | VCT | 0.90 | 1.406e-06 | 1.093e-11 | 0.900 | 10.8 | 129.2 | 6.403e+05 | 1.244e-17 | 2.363e-12 | 1.093e-11 | 1.130e+11 | 1.281e-08 | 3.036e+03 |
| 3D_gaa_Si | 3D_GAA | 0.75 | 1.041e-06 | 1.011e-14 | 0.750 | 7.5 | 6.2 | 7.207e+05 | 1.663e-16 | 1.899e-12 | 1.011e-14 | 6.260e+09 | 1.441e-08 | 2.088e+01 |
| 3D_gaa_AOS | 3D_GAA | 0.75 | 1.885e-06 | 8.455e-11 | 0.750 | 13.8 | 18.9 | 3.978e+05 | 7.082e-17 | 3.311e-12 | 8.455e-11 | 2.662e+10 | 7.956e-09 | 2.349e+04 |

## VCT scaling summary (tt)

| Node | Ion (A) | Ioff (A) | Ron (Ω) | vsat |
| --- | --- | --- | --- | --- |
| 082 | 9.285e-07 | 3.731e-12 | 9.693e+05 | 25420 |
| 091 | 9.742e-07 | 3.877e-12 | 9.238e+05 | 26820 |
| 102 | 1.035e-06 | 4.067e-12 | 8.695e+05 | 28720 |
| 125 | 1.406e-06 | 1.093e-11 | 6.403e+05 | 28720 |

- **082 → 125 Ion:** +51.4% (9.285e-07 → 1.406e-06 A)
- **082 → 125 Ioff:** +192.9% (3.731e-12 → 1.093e-11 A)
- **082 → 125 Ron:** -33.9% (9.693e+05 → 6.403e+05 Ω)
- Drive improves with node; Ioff rises — retention vs drive trade-off in the VCT cards.
- Full step-by-step analysis: [vct_scaling_analysis.md](../docs/vct_scaling_analysis.md)

## 1T1C macro (20 fF reference)

| Model | Ccell (fF) | t_write (s) | t_read (s) | I_hold (A) | Q_read (C) |
| --- | --- | --- | --- | --- | --- |
| BCAT_125 | 20 | 1.900e-09 | 2.272e-08 | 8.384e-14 | 1.418e-19 |
| VCT_082 | 20 | 1.900e-09 | 2.282e-08 | 6.021e-11 | 2.138e-18 |
| VCT_091 | 20 | 1.900e-09 | 2.282e-08 | 6.016e-11 | 2.095e-18 |
| VCT_102 | 20 | 1.900e-09 | 2.283e-08 | 6.009e-11 | 2.041e-18 |
| VCT_125 | 20 | 1.900e-09 | 2.293e-08 | 5.757e-11 | 7.505e-19 |
| 3D_gaa_Si | 20 | 1.900e-09 | 2.291e-08 | 1.672e-11 | 3.586e-19 |
| 3D_gaa_AOS | 20 | 1.901e-09 | 2.257e-08 | 3.455e-10 | 1.529e-19 |

## 1T1C Ccell sweep (tt)

Full transient sweep at 10, 20, and 30 fF per model.

| Model | Ccell (fF) | t_write (s) | t_read (s) | I_hold (A) | Q_read (C) |
| --- | --- | --- | --- | --- | --- |
| 3D_gaa_AOS | 10 | 1.902e-09 | 2.278e-08 | 3.454e-10 | 2.749e-19 |
| 3D_gaa_AOS | 20 | 1.901e-09 | 2.257e-08 | 3.455e-10 | 1.529e-19 |
| 3D_gaa_AOS | 30 | 1.901e-09 | 2.238e-08 | 3.455e-10 | 1.119e-19 |
| 3D_gaa_Si | 10 | 1.901e-09 | 2.290e-08 | 1.671e-11 | 3.936e-19 |
| 3D_gaa_Si | 20 | 1.900e-09 | 2.291e-08 | 1.672e-11 | 3.586e-19 |
| 3D_gaa_Si | 30 | 1.900e-09 | 2.291e-08 | 1.672e-11 | 3.468e-19 |
| BCAT_125 | 10 | 1.900e-09 | 2.271e-08 | 8.340e-14 | 1.555e-19 |
| BCAT_125 | 20 | 1.900e-09 | 2.272e-08 | 8.384e-14 | 1.418e-19 |
| BCAT_125 | 30 | 1.900e-09 | 2.272e-08 | 8.399e-14 | 1.372e-19 |
| VCT_082 | 10 | 1.901e-09 | 2.281e-08 | 6.020e-11 | 2.174e-18 |
| VCT_082 | 20 | 1.900e-09 | 2.282e-08 | 6.021e-11 | 2.138e-18 |
| VCT_082 | 30 | 1.900e-09 | 2.282e-08 | 6.021e-11 | 2.125e-18 |
| VCT_091 | 10 | 1.901e-09 | 2.282e-08 | 6.015e-11 | 2.131e-18 |
| VCT_091 | 20 | 1.900e-09 | 2.282e-08 | 6.016e-11 | 2.095e-18 |
| VCT_091 | 30 | 1.900e-09 | 2.282e-08 | 6.016e-11 | 2.082e-18 |
| VCT_102 | 10 | 1.901e-09 | 2.282e-08 | 6.008e-11 | 2.078e-18 |
| VCT_102 | 20 | 1.900e-09 | 2.283e-08 | 6.009e-11 | 2.041e-18 |
| VCT_102 | 30 | 1.900e-09 | 2.283e-08 | 6.009e-11 | 2.029e-18 |
| VCT_125 | 10 | 1.901e-09 | 2.292e-08 | 5.758e-11 | 7.961e-19 |
| VCT_125 | 20 | 1.900e-09 | 2.293e-08 | 5.757e-11 | 7.505e-19 |
| VCT_125 | 30 | 1.900e-09 | 2.293e-08 | 5.760e-11 | 7.350e-19 |

## Mini-array (layout BL RC)

| Model | N cells | BL topology | t_BL settle (s) | I_BL leak (A) | R_metal/pitch (Ω) | R_contact (Ω) | C_SA (fF) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BCAT_125 | 8 | layout | 9.939e-09 | 1.399e-10 | 3.50 | 2.86 | 21.0 |
| VCT_082 | 8 | layout | 7.753e-09 | 1.331e-10 | 5.00 | 2.00 | 30.0 |
| VCT_091 | 8 | layout | 7.498e-09 | 1.362e-10 | 5.00 | 2.00 | 30.0 |
| VCT_102 | 8 | layout | 7.196e-09 | 1.399e-10 | 5.00 | 2.00 | 30.0 |
| VCT_125 | 8 | layout | 5.235e-09 | 1.951e-10 | 5.00 | 2.00 | 30.0 |
| 3D_gaa_Si | 8 | layout | 2.810e-09 | 6.220e-10 | 1.83 | 5.45 | 11.0 |
| 3D_gaa_AOS | 8 | layout | 3.642e-09 | 2.348e-10 | 5.00 | 2.00 | 30.0 |

## Summary figures

### Pareto: Ion vs Ioff

![Pareto: Ion vs Ioff](figures/pareto_ion_ioff.svg)

### VCT node scaling

![VCT node scaling](figures/vct_scaling.svg)

### Composite figure of merit

![Composite figure of merit](figures/radar_fom.svg)

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
SUITE=device ./scripts/run_experiments.sh     # replay this suite
dram-bench run --suite device --corner tt --output device
```

Metric definitions: [docs/benchmark_spec.md](../docs/benchmark_spec.md)

---
*Report produced by `dram-bench` / `run_experiments.sh`*