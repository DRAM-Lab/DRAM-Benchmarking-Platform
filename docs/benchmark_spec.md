# OpenDRAMBench Specification

Benchmark automation for Open DRAM Model cards aligned with **Paper A1** in `papers.md`.

## Relationship to Open DRAM Model Part I/II

Part I/II introduce and demonstrate the Open DRAM Model with flagship device/circuit case studies.
OpenDRAMBench does **not** re-claim those discoveries. It provides:

- Push-button reruns across all seven access models
- Standard metric extraction (`Ion`, `Ioff`, `Ron`, `Cgg`, GIDL proxies, composite FOMs)
- Multi-simulator comparison (Spectre, HSPICE, ngspice)
- Read-path sense-amp, Ccell roadmap, and validation audit lanes
- Provenance manifests for artifact review

## Model scope

| Model ID | Architecture | Nominal use |
|----------|--------------|-------------|
| BCAT_125 | 6F² BCAT | Reference planar access |
| VCT_082–VCT_125 | 4F² VCT | Scaled vertical channel roadmap |
| 3D_gaa_Si | 3D GAA Si | Silicon GAA access |
| 3D_gaa_AOS | 3D GAA AOS | Oxide-semiconductor GAA access |

Cards ship under `models/OpenDRAMmodelV1/models/access_tx/`.

## Suites

| Suite | Command | Description |
|-------|---------|-------------|
| `device` | default | TT device + 1T1C + mini-array for all models |
| `corner_sweep` | `SUITE=corner_sweep` | Device metrics across six PVT corners |
| `multi_tool` | `SUITE=multi_tool` | Per-simulator trees + cross-check report |
| `sense_amp` | `SUITE=sense_amp` | Read-path ΔV_BL (SPICE) + behavioral SA requirement sweep |
| `ccell` | `SUITE=ccell` | Ccell retention sweep vs read binding |
| `validation` | `SUITE=validation` | Golden YAML, literature, paper correlation |
| `all` | `SUITE=all` | Runs all six Paper A1 suites in order |

`SUITE=all` writes:

```
results/
  device/
  corner_sweep/
  multi_tool/
  sense_amp/       # read-path signal + sa_spec_per_node.csv (SA requirements, not SA sizing)
  ccell/
  validation/
  pareto/          # dependency for ccell (auto-derived)
  RESULTS.md       # aggregate index
  MANIFEST.json
```

## Extracted device metrics

| Metric | Unit | Source deck |
|--------|------|-------------|
| `ion_a` | A | Id–Vg @ Vdd/2 and Vdd |
| `ioff_a` | A | Id–Vg @ Vg=0 |
| `ron_ohm` | Ω | Id–Vd @ Vwl |
| `ron_boost_ohm` | Ω | Id–Vd @ boosted WL |
| `cgg_f` | F | AC/transient gate charge |
| `cgd_f` | F | AC gate-drain coupling |
| `igidl_a` | A | GIDL stress deck |
| `vt_v` | V | Constant-current extraction |
| `ss_mv_dec` | mV/dec | Subthreshold slope |
| `dibl_mv_v` | mV/V | DIBL |
| `fpitch_m` | m | Model card metadata |
| `vsat` | m/s | Model card metadata |

Implementation details and deck naming live in the bundled `src/bench/` package.

## Read-path lane (`sense_amp`) — signal + SA requirements

This lane is **not** a sense-amplifier device benchmark. Start with `sense_amp/RESULTS.md` before opening CSVs.

| Layer | What is measured |
|-------|------------------|
| SPICE | ΔV_BL(t) from access device + Ccell + lumped BL RC |
| Sweep | Behavioral G, σ_os, t_en → yield proxy and per-node **SA spec table** |
| Output | `sa_spec_per_node.csv` — min gain, max offset, earliest t_en per model |

Transistor-level SA sizing (W/L, latch netlist) is explicitly out of scope; see `read_path.yaml` behavioral tiers.

## Artifact conventions

Every `./run_experiments.sh` run produces lane-specific `RESULTS.md`, `MANIFEST.json`, and CSV exports under `results/`.

Use `./clean.sh` to remove generated artifacts without touching the vendored model bundle.

## Limitations

- ngspice requires a BSIM-CMG OSDI library under `build/ngspice_osdi/`.
- Golden regression (`bench/device_benchmark/golden/`) is Spectre-pinned; ngspice runs skip golden check by default.
- Sense-amp read-path SPICE requires Spectre or HSPICE; deck-only mode is supported offline.
- Speed-bin grading and JEDEC timing export are out of scope (Paper A2 repos).
