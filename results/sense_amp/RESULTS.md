# OpenDRAMBench — Results

Reproducible benchmark automation for Open DRAM model cards. This platform extends the Open DRAM Model Part I/II artifacts with push-button reruns, multi-tool comparison, validation, and provenance manifests.

**Models:** 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125

## Run summary

| Field | Value |
|-------|-------|
| Suite | `sense_amp` |
| Corner | `tt` |
| Simulator | ngspice, spectre |
| Generated | 2026-06-23 13:24 UTC |
| Status | complete |
| Model bundle | OpenDRAMmodelV1 `e692790da857` |

## Contents

- [Read-Path Signal & SA Requirement Sweep](#read-path-signal-sa-requirement-sweep)
- [Scope (read this first)](#scope-read-this-first)
- [Executive summary](#executive-summary)
- [Behavioral SA assumptions](#behavioral-sa-assumptions)
- [Read signal @ reference point](#read-signal-reference-point)
- [Per-node SA requirements (derived, not sized)](#per-node-sa-requirements-derived-not-sized)
- [Co-design sweep (yield proxy)](#co-design-sweep-yield-proxy)
- [How to analyze the CSVs](#how-to-analyze-the-csvs)
- [Figures](#figures)
- [Artifact index](#artifact-index)
- [Artifacts](#artifacts)
- [Reproduce](#reproduce)

---
## Read-Path Signal & SA Requirement Sweep

**Generated:** 2026-06-23 13:24 UTC  
**Corner:** tt  
**Simulator:** spectre  
**Signal rows:** 84  
**Models:** 7

## Scope (read this first)

| Measured in SPICE | Derived via behavioral SA sweep |
|-------------------|----------------------------------|
| ΔV_BL(t) on the read column | Min gain **G**, max offset **σ_os**, earliest **t_en** |
| Access device from OpenDRAM cards (`l`, `nfin`) | 99.9% yield **proxy** (not foundry MC) |
| Ccell, BL RC (pitch-scaled), WL / precharge timing | Input-referred read **budget** per model |

**Not in scope:** sense-amplifier transistor netlists, W/L sizing, layout mismatch, or SA bench scores.
The lane benchmarks **bitline signal development** and maps it to **SA specification tables** for co-design.

## Executive summary

- **SA closure @ 20 fF:** 0 / 7 access models meet the behavioral yield proxy at the reference point.
- **No closure under swept tiers:** 3D_gaa_AOS, 3D_gaa_Si, BCAT_125, VCT_082, VCT_091, VCT_102, VCT_125 (see SA spec table — may need stronger G, lower σ_os, or later t_en).
- **Co-design pass rate:** 0.0% of G×σ_os×t_en points exceed 99.9% yield proxy.
- **Downstream:** `ccell` consumes `read_signal_*.csv` when present; otherwise analytic read fallback.

## Behavioral SA assumptions

| Parameter | Value |
|-----------|-------|
| Gain sweep G | 5.0, 10.0, 20.0 |
| Offset tiers σ_os | 5, 10, 15, 20 mV |
| Output margin m_min | 50.0 mV |
| Target yield proxy | 99.9% |
| Margin model | M = G·|ΔV_BL| − |V_os|; pass if M > m_min |

## Read signal @ reference point

Reference: **Ccell = 20 fF**, **VBL_pre = 50% × Vdd** (compare access nodes at equal array loading).

|ΔV_BL| is the absolute differential BL voltage sampled from SPICE (access device + lumped BL RC + cell cap).

| model_id |
| --- |
| 3D_gaa_AOS |
| 3D_gaa_Si |
| BCAT_125 |
| VCT_082 |
| VCT_091 |
| VCT_102 |
| VCT_125 |

## Per-node SA requirements (derived, not sized)

These rows answer: *what behavioral SA spec closes read at the reference point?* They are **requirements**, not transistor W/L or a benchmark score for a physical SA.

| model_id | status | read_guidance |
| --- | --- | --- |
| 3D_gaa_AOS | FAIL | No tier in sweep meets target — weaker signal or tighter SA needed |
| 3D_gaa_Si | FAIL | No tier in sweep meets target — weaker signal or tighter SA needed |
| BCAT_125 | FAIL | No tier in sweep meets target — weaker signal or tighter SA needed |
| VCT_082 | FAIL | No tier in sweep meets target — weaker signal or tighter SA needed |
| VCT_091 | FAIL | No tier in sweep meets target — weaker signal or tighter SA needed |
| VCT_102 | FAIL | No tier in sweep meets target — weaker signal or tighter SA needed |
| VCT_125 | FAIL | No tier in sweep meets target — weaker signal or tighter SA needed |

| model_id | ccell_ff | max_sigma_os_mv | min_gain | earliest_t_en_ns | recommended_vbl_pre_fraction | min_delta_v_bl_mv | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3D_gaa_AOS | 20 | — | — | — | — | — | FAIL |
| 3D_gaa_Si | 20 | — | — | — | — | — | FAIL |
| BCAT_125 | 20 | — | — | — | — | — | FAIL |
| VCT_082 | 20 | — | — | — | — | — | FAIL |
| VCT_091 | 20 | — | — | — | — | — | FAIL |
| VCT_102 | 20 | — | — | — | — | — | FAIL |
| VCT_125 | 20 | — | — | — | — | — | FAIL |

## Co-design sweep (yield proxy)

Points meeting 99.9% analytic yield: **0 / 420** across G × σ_os × t_en × model.

Sample of passing combinations (earliest t_en per model preferred):

_No data._

## How to analyze the CSVs

### `read_signal_<corner>.csv`

| Column | Meaning |
|--------|---------|
| `model_id` | OpenDRAM access card |
| `ccell_ff` | Cell capacitance (fF) |
| `vbl_pre_fraction` | BL precharge as fraction of Vdd |
| `dv_<t>ns` | |ΔV_BL| at sample time (V) — **primary SPICE output** |

### `sa_spec_per_node.csv`

| Column | Meaning |
|--------|---------|
| `min_gain` | Smallest G in sweep that passes yield proxy |
| `max_sigma_os_mv` | Largest σ_os tier that still passes |
| `earliest_t_en_ns` | Earliest sense-enable time that passes |
| `min_delta_v_bl_mv` | Input-referred signal budget for target yield |
| `status` | PASS if any sweep point meets target |

### `codesign_sweep.csv`

Full factorial of model × G × σ_os × t_en with `yield_fraction` and `passes_target`.
Use this to explore timing vs offset tradeoffs beyond the per-node summary.

## Figures

### Dv Vs Time

![dv_vs_time](figures/dv_vs_time.svg)

### Dv Vs Ccell

![dv_vs_ccell](figures/dv_vs_ccell.svg)

### Yield Vs Ten

![yield_vs_ten](figures/yield_vs_ten.svg)

### Min Dv Requirement

![min_dv_requirement](figures/min_dv_requirement.svg)

## Artifact index

| File | Contents |
|------|----------|
| `read_signal_tt.csv` | ΔV_BL samples: model × Ccell × VBL_pre |
| `codesign_sweep.csv` | G × σ_os × t_en yield proxy per model |
| `sa_spec_per_node.csv` | Min G, max σ_os, earliest t_en @ reference Ccell |
| `coupling_margin.csv` | ΔV loss vs k_couple (if coupling decks ran) |
| `figures/` | Summary SVG plots |

---
*Produced by `dram-sense-amp` / `dram-bench run --suite sense_amp`*

## Artifacts

| File | Description |
|------|-------------|
| [`MANIFEST.json`](MANIFEST.json) | Provenance manifest with SHA-256 checksums |
| [`read_signal_tt.csv`](read_signal_tt.csv) | Read-path ΔV_BL samples @ TT |
| [`read_signal_all_corners.csv`](read_signal_all_corners.csv) | Read-path ΔV_BL across all PVT corners |
| [`sa_spec_per_node.csv`](sa_spec_per_node.csv) | Derived SA requirements per access node |
| [`decks/`](decks/) | Generated SPICE decks |
| [`figures/`](figures/) | Summary SVG plots |
## Reproduce

```bash
./scripts/run_experiments.sh                    # default: full benchmark bundle
SUITE=sense_amp ./scripts/run_experiments.sh     # replay this suite
dram-bench run --suite sense_amp --corner tt --output sense_amp
```

Metric definitions: [docs/benchmark_spec.md](../docs/benchmark_spec.md)

---
*Report produced by `dram-bench` / `run_experiments.sh`*