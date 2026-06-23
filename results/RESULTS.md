# OpenDRAMBench — Aggregate Results

Self-contained benchmark automation for Open DRAM Model cards. This page indexes each benchmark lane; open a suite report for detailed tables.

## Run summary

| Field | Value |
|-------|-------|
| Suite | `all` |
| Corner | `tt` |
| Simulator | ngspice, spectre |
| Generated | 2026-06-23 13:24 UTC |
| Status | complete |
| Model bundle | OpenDRAMmodelV1 `e692790da857` |

## Contents

- [Suite index](#suite-index)
- [Artifacts](#artifacts)
- [Suite layout](#suite-layout)
- [Reproduce](#reproduce)

---
# OpenDRAMBench — Aggregate Results

**Generated:** 2026-06-23 13:24 UTC
**Reference corner:** tt

Self-contained benchmark automation for Open DRAM Model cards. This aggregate indexes each benchmark lane; open a suite report for detailed tables.

| Suite | Role | Primary artifact |
|-------|------|------------------|
| `device` | Full access-device + 1T1C + mini-array @ TT | `device/device_metrics.csv` |
| `corner_sweep` | Six-corner PVT matrix (device + 1T1C + mini-array) | `corner_sweep/device_metrics_all_corners.csv` |
| `multi_tool` | Cross-simulator agreement | `multi_tool/simulator_compare/` |
| `sense_amp` | Read-path ΔV_BL + derived SA requirements | `sense_amp/sa_spec_per_node.csv` |
| `ccell` | Ccell retention vs read binding | `ccell/ccell_sweep.csv` |
| `validation` | Golden + literature + paper audit | `validation/RESULTS.md` |

## Suite index

- **device** [ready] — [device/RESULTS.md](device/RESULTS.md), primary: `device/device_metrics.csv`
- **corner_sweep** [ready] — [corner_sweep/RESULTS.md](corner_sweep/RESULTS.md), primary: `corner_sweep/device_metrics_all_corners.csv`
- **multi_tool** [ready] — [multi_tool/RESULTS.md](multi_tool/RESULTS.md), primary: `multi_tool/simulator_compare/tt/ (spectre, ngspice)`
- **sense_amp** [ready] — [sense_amp/RESULTS.md](sense_amp/RESULTS.md), primary: `sense_amp/sa_spec_per_node.csv (or read_signal_tt.csv / decks/)`
- **ccell** [ready] — [ccell/RESULTS.md](ccell/RESULTS.md), primary: `ccell/ccell_sweep.csv`
- **validation** [ready] — [validation/RESULTS.md](validation/RESULTS.md), primary: `validation/data/`

## Artifacts

| File | Description |
|------|-------------|
| [`MANIFEST.json`](MANIFEST.json) | Provenance manifest with SHA-256 checksums |
## Suite layout

Full benchmark run (`SUITE=all`). Each lane has its own report:

| Suite | Report | Role |
|-------|--------|------|
| `device` | [device/RESULTS.md](device/RESULTS.md) [ready] | Access device + 1T1C + mini-array @ TT |
| `corner_sweep` | [corner_sweep/RESULTS.md](corner_sweep/RESULTS.md) [ready] | Six-corner PVT matrix (device + 1T1C + mini-array) |
| `multi_tool` | [multi_tool/RESULTS.md](multi_tool/RESULTS.md) [ready] | Cross-simulator agreement |
| `sense_amp` | [sense_amp/RESULTS.md](sense_amp/RESULTS.md) [ready] | Read-path ΔV_BL + SA requirements |
| `ccell` | [ccell/RESULTS.md](ccell/RESULTS.md) [ready] | Ccell retention vs read binding |
| `validation` | [validation/RESULTS.md](validation/RESULTS.md) [ready] | Golden + literature + paper audit |
## Reproduce

```bash
./scripts/run_experiments.sh                    # default: full benchmark bundle
SUITE=device ./scripts/run_experiments.sh  # device lane only (faster)
dram-bench run --suite all --corner tt --output results
```

Metric definitions: [docs/benchmark_spec.md](../docs/benchmark_spec.md)

---
*Report produced by `dram-bench` / `run_experiments.sh`*