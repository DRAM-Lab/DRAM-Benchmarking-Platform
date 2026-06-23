# OpenDRAMBench — Results

Reproducible benchmark automation for Open DRAM model cards. This platform extends the Open DRAM Model Part I/II artifacts with push-button reruns, multi-tool comparison, validation, and provenance manifests.

**Models:** 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125

## Run summary

| Field | Value |
|-------|-------|
| Suite | `ccell` |
| Corner | `tt` |
| Simulator | ngspice, spectre |
| Generated | 2026-06-23 13:24 UTC |
| Status | complete |
| Model bundle | OpenDRAMmodelV1 `e692790da857` |

## Contents

- [OpenDRAM Cell Capacitance Roadmap](#opendram-cell-capacitance-roadmap)
- [Executive summary](#executive-summary)
- [Ccell_min table (dual constraint)](#ccell_min-table-dual-constraint)
- [Binding classification](#binding-classification)
- [Dielectric k scenario feasibility](#dielectric-k-scenario-feasibility)
- [3D vertical capacitor boost](#3d-vertical-capacitor-boost)
- [Device leakage what-if](#device-leakage-what-if)
- [Figures](#figures)
- [Methodology](#methodology)
- [Artifacts](#artifacts)
- [Reproduce](#reproduce)

---
## OpenDRAM Cell Capacitance Roadmap

_Generated: 2026-06-23 13:24 UTC · revision `14b3550`_

## Executive summary

- **Ccell sweep:** 420 rows across 7 models, Ccell ∈ {5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80} fF.
- **Retention corner:** hot @ 64 ms target (ΔV = 50 mV loss).
- **Read corner:** tt @ BL swing target (100 mV), t_en = 10 ns.

## Ccell_min table (dual constraint)

| Model | Arch | Ccell_min ret (fF) | Ccell_min read (fF) | Ccell_min (fF) | Binding | Cap-limited |
| --- | --- | --- | --- | --- | --- | --- |
| 3D_gaa_AOS | 3D_GAA | — | 72.8 | 72.8 | read-limited | True |
| 3D_gaa_Si | 3D_GAA | — | 26.7 | 26.7 | read-limited | True |
| BCAT_125 | BCAT | 103.0 | 43.2 | 103.0 | retention-limited | True |
| VCT_082 | VCT | — | 57.2 | 57.2 | read-limited | True |
| VCT_091 | VCT | — | 57.2 | 57.2 | read-limited | True |
| VCT_102 | VCT | — | 57.2 | 57.2 | read-limited | True |
| VCT_125 | VCT | — | 57.2 | 57.2 | read-limited | True |

## Binding classification

- **read-limited:** 6 models (3D_gaa_AOS, 3D_gaa_Si, VCT_082, VCT_091, VCT_102, VCT_125)
- **retention-limited:** 1 models (BCAT_125)

## Dielectric k scenario feasibility

### S-aggressive

| Model | k | Achievable (fF) | Required (fF) | Cap-limited |
| --- | --- | --- | --- | --- |
| 3D_gaa_AOS | 40 | 42.5 | 72.8 | True |
| 3D_gaa_Si | 40 | 5.7 | 26.7 | True |
| BCAT_125 | 40 | 28.1 | 103.0 | True |
| VCT_082 | 22 | 18.7 | 57.2 | True |
| VCT_091 | 28 | 23.8 | 57.2 | True |
| VCT_102 | 34 | 28.9 | 57.2 | True |
| VCT_125 | 40 | 34.0 | 57.2 | True |
_Cap-limited under S-aggressive: 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125_

### S-base

| Model | k | Achievable (fF) | Required (fF) | Cap-limited |
| --- | --- | --- | --- | --- |
| 3D_gaa_AOS | 25 | 26.6 | 72.8 | True |
| 3D_gaa_Si | 25 | 3.6 | 26.7 | True |
| BCAT_125 | 25 | 17.6 | 103.0 | True |
| VCT_082 | 18 | 15.3 | 57.2 | True |
| VCT_091 | 20 | 17.0 | 57.2 | True |
| VCT_102 | 22 | 18.7 | 57.2 | True |
| VCT_125 | 25 | 21.3 | 57.2 | True |
_Cap-limited under S-base: 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125_

### S-conservative

| Model | k | Achievable (fF) | Required (fF) | Cap-limited |
| --- | --- | --- | --- | --- |
| 3D_gaa_AOS | 18 | 19.1 | 72.8 | True |
| 3D_gaa_Si | 18 | 2.6 | 26.7 | True |
| BCAT_125 | 18 | 12.7 | 103.0 | True |
| VCT_082 | 15 | 12.8 | 57.2 | True |
| VCT_091 | 16 | 13.6 | 57.2 | True |
| VCT_102 | 17 | 14.5 | 57.2 | True |
| VCT_125 | 18 | 15.3 | 57.2 | True |
_Cap-limited under S-conservative: 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125_


## 3D vertical capacitor boost

| Model | β | Effective Ccell (fF) | Required (fF) | Feasible |
| --- | --- | --- | --- | --- |
| 3D_gaa_Si | 1.0 | 3.6 | 26.7 | False |
| 3D_gaa_Si | 1.5 | 5.4 | 26.7 | False |
| 3D_gaa_Si | 2.0 | 7.1 | 26.7 | False |
| 3D_gaa_Si | 2.5 | 8.9 | 26.7 | False |
| 3D_gaa_AOS | 1.0 | 26.6 | 72.8 | False |
| 3D_gaa_AOS | 1.5 | 39.8 | 72.8 | False |
| 3D_gaa_AOS | 2.0 | 53.1 | 72.8 | False |
| 3D_gaa_AOS | 2.5 | 66.4 | 72.8 | False |

## Device leakage what-if

| Model | Ioff scale | Ccell_min (fF) | ΔCcell_min (fF) |
| --- | --- | --- | --- |
| 3D_gaa_AOS | 1.00 | 72.8 | 0.0 |
| 3D_gaa_AOS | 0.50 | 72.8 | 0.0 |
| 3D_gaa_Si | 1.00 | 26.7 | 0.0 |
| 3D_gaa_Si | 0.50 | 26.7 | 0.0 |
| BCAT_125 | 1.00 | 103.0 | 0.0 |
| BCAT_125 | 0.50 | 51.5 | 51.5 |
| VCT_082 | 1.00 | 57.2 | 0.0 |
| VCT_082 | 0.50 | 57.2 | 0.0 |
| VCT_091 | 1.00 | 57.2 | 0.0 |
| VCT_091 | 0.50 | 57.2 | 0.0 |
| VCT_102 | 1.00 | 57.2 | 0.0 |
| VCT_102 | 0.50 | 57.2 | 0.0 |
| VCT_125 | 1.00 | 57.2 | 0.0 |
| VCT_125 | 0.50 | 57.2 | 0.0 |

## Figures

### ccell min roadmap

![ccell min roadmap](figures/ccell_min_roadmap.svg)

### dv read vs ccell tt

![dv read vs ccell tt](figures/dv_read_vs_ccell_tt.svg)

### feasibility S-aggressive

![feasibility S-aggressive](figures/feasibility_S-aggressive.svg)

### feasibility S-base

![feasibility S-base](figures/feasibility_S-base.svg)

### feasibility S-conservative

![feasibility S-conservative](figures/feasibility_S-conservative.svg)

### t ret vs ccell hot

![t ret vs ccell hot](figures/t_ret_vs_ccell_hot.svg)

## Methodology

- Retention and read decks reuse OpenDRAM-pareto-roadmap and OpenDRAM-sense-amp-vct pipelines.
- Geometric capacitor model: Ccell = k·ε₀·α·structure·fpitch² / t_EOT · β with t_EOT = 1.5 nm.
- See [docs/ccell_metric_spec.md](../docs/ccell_metric_spec.md).

## Artifacts

| File | Description |
|------|-------------|
| [`MANIFEST.json`](MANIFEST.json) | Provenance manifest with SHA-256 checksums |
| [`ccell_sweep.csv`](ccell_sweep.csv) | Ccell retention vs read binding sweep |
| [`figures/`](figures/) | Summary SVG plots |
## Reproduce

```bash
./scripts/run_experiments.sh                    # default: full benchmark bundle
SUITE=ccell ./scripts/run_experiments.sh     # replay this suite
dram-bench run --suite ccell --corner tt --output ccell
```

Metric definitions: [docs/benchmark_spec.md](../docs/benchmark_spec.md)

---
*Report produced by `dram-bench` / `run_experiments.sh`*