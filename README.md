# DRAM Benchmarking Platform

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-green?logo=creativecommons&logoColor=white)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776ab.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.2.0-blue?logo=semver&logoColor=white)](pyproject.toml)

Self-contained, reproducible DRAM model benchmarking for **Paper A1**. One installable Python product (`dram-benchmark`) bundles six evidence lanes — device SPICE, corner sweep, multi-simulator cross-check, read-path sense-amp, Ccell roadmap, and validation audits — with **vendored model cards** and **paper-derived golden specs**. No sibling `experiments/` checkouts are required.

- **Specification:** [docs/benchmark_spec.md](docs/benchmark_spec.md)
- **Default models:** vendored [OpenDRAMmodelV1](models/OpenDRAMmodelV1/) (upstream [MATRIX-PDK/OpenDRAMmodelV1](https://github.com/MATRIX-PDK/OpenDRAMmodelV1))
- **License:** CC BY 4.0 for this platform (see [LICENSE](LICENSE)); model cards under [MATRIX-PDK terms](models/OpenDRAMmodelV1/LICENSE)

## Table of contents

- [Scope and limitations](#scope-and-limitations)
- [Supported models](#supported-models)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Paper A1 suites](#paper-a1-suites)
- [Environment variables](#environment-variables)
- [CLI reference](#cli-reference)
  - [dram-bench](#dram-bench-orchestrator)
  - [dram-device](#dram-device-device-spice-lane)
  - [dram-validate](#dram-validate-validation-lane)
  - [dram-sense-amp](#dram-sense-amp-read-path-lane)
  - [dram-ccell](#dram-ccell-ccell-roadmap-lane)
  - [dram-pareto](#dram-pareto-pareto-roadmap-lane)
- [Golden and validation workflow](#golden-and-validation-workflow)
- [Repository layout](#repository-layout)
- [Development](#development)
- [License](#license)
- [Citation](#citation)
- [References](#references)

## Scope and limitations

### Purpose

Compare **6F² BCAT**, **4F² VCT**, and **3D GAA** access transistors under a shared SPICE extraction methodology, plus read-path, Ccell, and audit lanes for publication-grade reproducibility. Intended for **research, architecture ranking, and evidence bundles** — not foundry tape-out sign-off.

### In scope

| Lane | Package | Primary outputs |
|------|---------|-----------------|
| Device SPICE | `src/bench/` | Device + 1T1C + mini-array metrics, figures, `RESULTS.md` |
| Corner sweep | `dram-bench run --suite corner_sweep` | All-corner device CSV |
| Multi-tool | `dram-bench run --suite multi_tool` | Per-simulator trees + rel-diff tables |
| Sense-amp | `src/sense_amp/` | Read-path ΔV_BL, SA co-design CSVs, figures |
| Ccell | `src/ccell/` (+ `src/pareto/`) | Ccell sweep, feasibility, roadmap tables |
| Validation | `src/validation/` | Golden check, paper/literature correlation, audit report |

### Limitations

- Vendored `.inc` cards are **compact models**, not GDS layouts or extracted RC netlists.
- Metrics are **research proxies** (see [benchmark spec](docs/benchmark_spec.md)); paper TCAD tables and BSIM SPICE extraction use different definitions — `dram-validate paper` documents gaps.
- **Spectre** is the reference backend for golden CSV regression; **HSPICE** and **ngspice** are supported with documented expected disagreements ([docs/simulator_cross_check.md](docs/simulator_cross_check.md)).
- Sense-amp **SPICE** read-path requires Spectre or HSPICE; without them, decks are generated and reports use deck-only / analytic fallbacks.

## Supported models

Seven access cards ship under `models/OpenDRAMmodelV1/models/access_tx/` (vendored bundle).

| Model ID | Architecture | Nominal Vdd | fpitch |
|----------|--------------|-------------|--------|
| `BCAT_125` | 6F² BCAT | 0.85 V | 42 nm |
| `VCT_082` | 4F² VCT | 0.90 V | 60 nm |
| `VCT_091` | 4F² VCT | 0.90 V | 60 nm |
| `VCT_102` | 4F² VCT | 0.90 V | 60 nm |
| `VCT_125` | 4F² VCT | 0.90 V | 60 nm |
| `3D_gaa_Si` | 3D GAA Si | 0.75 V | 22 nm |
| `3D_gaa_AOS` | 3D GAA AOS | 0.75 V | 60 nm |

Periphery: `hv_peri_28_32.inc` under `models/OpenDRAMmodelV1/models/peri_tx/`.

Override the card directory with `OPEN_DRAM_MODEL_ROOT` if needed.

## Requirements

- **Python 3.10+**
- **At least one** SPICE simulator for device lanes:

| Simulator | Role | Notes |
|-----------|------|--------|
| **Cadence Spectre** | Primary (golden regression) | BSIM-CMG level 72 |
| **Synopsys HSPICE** | Optional | Native `.inc` cards |
| **ngspice** | Optional (experimental) | BSIM-CMG via OSDI under `build/ngspice_osdi/` |

Python dependencies install via `pip` (NumPy, pandas, PyYAML, matplotlib, SciPy, Pillow).

### ngspice setup

ngspice requires a BSIM-CMG OSDI build (cached under `build/ngspice_osdi/` on first run). Optionally set `OPEN_DRAM_VA_MODELS_ROOT` to a [VA-Models](https://github.com/dwarning/VA-Models) checkout. Set `NGSPICE=/path/to/ngspice` if not on `PATH`.

## Installation

```bash
git clone https://github.com/DRAM-Lab/DRAM-Benchmarking-Platform.git
cd DRAM-Benchmarking-Platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

No git submodules — model cards are vendored in-tree.

## Quick start

**Recommended one-shot pipeline** (install, device suite @ TT, offline tests):

```bash
./scripts/run_experiments.sh
```

**Full Paper A1 bundle** (all six suites):

```bash
SUITE=all ./scripts/run_experiments.sh
```

**Regenerate paper-derived golden YAML** (after PDF or pinned metric updates):

```bash
python scripts/extract_paper_refs.py --docs-root /path/to/paper/pdfs
python scripts/publish_golden_from_paper.py
```

`run_experiments.sh` sets model paths, runs `dram-bench run`, then offline `pytest`.

## Paper A1 suites

Use via `dram-bench run --suite <name>` or `SUITE=<name> ./scripts/run_experiments.sh`.

| Suite | Role | Primary artifact |
|-------|------|------------------|
| `device` | Access device + 1T1C + mini-array @ TT | `device/device_metrics.csv` |
| `corner_sweep` | PVT device matrix (all corners) | `corner_sweep/device_metrics_all_corners.csv` |
| `multi_tool` | Cross-simulator agreement | `multi_tool/simulator_compare/` |
| `sense_amp` | Read-path ΔV_BL + SA co-design | `sense_amp/read_signal_tt.csv` |
| `ccell` | Ccell retention vs read binding | `ccell/ccell_sweep.csv` |
| `validation` | Golden + literature + paper audit | `validation/RESULTS.md` |
| `all` | Runs all six suites in order | `results/RESULTS.md` (aggregate) |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_DRAM_MODEL_ROOT` | `models/OpenDRAMmodelV1/models/access_tx` | Access `.inc` card directory |
| `OPEN_DRAM_CORNER_SOURCE` | `local` | `local`, `registry`, or `auto` |
| `OPEN_DRAM_CORNER_REGISTRY` | `bench/registry/corner_registry.yaml` | Corner registry YAML |
| `OPEN_DRAM_SIMULATOR` | auto | Pin `spectre`, `hspice`, or `ngspice` |
| `OPEN_DRAM_BENCH_RESULTS` | — | Device results dir (set by orchestrator for downstream lanes) |
| `OPEN_DRAM_PARETO_RESULTS` | — | Pareto results dir (ccell dependency) |
| `OPEN_DRAM_SENSE_AMP_RESULTS` | — | Sense-amp results dir (ccell overlay) |
| `PAPER_DOCS_ROOT` | auto | Part I/II PDF directory for `extract_paper_refs.py` |
| `SUITE` | `device` | Suite for `run_experiments.sh` |
| `RESULTS_DIR` | `results` | Output root for `run_experiments.sh` |
| `DEVICE_ONLY` | `0` | Skip 1T1C + mini-array |
| `GENERATE_ONLY` | `0` | Deck generation only |
| `SKIP_GOLDEN` | `0` | Skip Spectre CSV golden check on device lane |

## CLI reference

Six commands install from one package. **`dram-bench`** orchestrates full suites; lane tools are also callable directly for development.

### `dram-bench` (orchestrator)

Top-level Paper A1 automation: suite dispatch, manifests, aggregate `RESULTS.md`, artifact validation.

| Command | Description |
|---------|-------------|
| `list-models` | List bundled access model IDs and card file sizes |
| `run` | Run a benchmark suite (see [Paper A1 suites](#paper-a1-suites)) |
| `manifest` | Write `MANIFEST.json` for a results tree |
| `validate` | Validate results artifacts (schema, coverage, file presence) |
| `report` | Regenerate lane `RESULTS.md` with platform header |

```bash
# List models
dram-bench list-models

# Single suite
dram-bench run --suite device --corner tt --output results/device
dram-bench run --suite corner_sweep --output results/corner_sweep
dram-bench run --suite multi_tool --output results/multi_tool
dram-bench run --suite sense_amp --output results/sense_amp
dram-bench run --suite ccell --output results/ccell
dram-bench run --suite validation --output results/validation

# Full Paper A1
dram-bench run --suite all --output results/

# Options
dram-bench run --suite device --device-only --output results/device_only
dram-bench run --suite device --generate-only --output build/device
dram-bench run --suite device --simulator hspice --output results/hspice
dram-bench run --suite device --skip-golden --output results/device

# Post-run
dram-bench validate --suite device --results results/device
dram-bench manifest --suite all --results results/
dram-bench report --suite device --results results/device
```

### `dram-device` (device SPICE lane)

Cross-architecture access transistor benchmark: Id–Vg/Vd, Ron, capacitance, 1T1C, mini-array. Source: `src/bench/`.

| Command | Description |
|---------|-------------|
| `list-models` | Print model registry (architecture, Vdd, fpitch, vsat) |
| `generate` | Write SPICE decks only |
| `run` | Full benchmark (device ± 1T1C ± mini-array) |
| `plot` | Summary figures from `device_metrics.csv` |
| `report` | `RESULTS.md` + figures from existing CSVs |
| `validate-golden` | Compare results to Spectre golden CSVs (±rtol) |
| `compare-simulators` | Build rel-diff tables from per-simulator result trees |

```bash
dram-device list-models

# Single corner, one model
dram-device run --model VCT_125 --corner tt --output results/tt

# All models, all corners
dram-device run --all --corner all --output results

# Simulator pinning
dram-device run --all --corner tt --simulator spectre --output results/spectre/tt
dram-device run --all --corner tt --simulator hspice --output results/hspice/tt
dram-device run --all --corner tt --simulator ngspice --output results/ngspice/tt

# Multi-simulator (auto when >=2 backends on PATH)
dram-device run --all --corner tt --all-simulators --output results
dram-device run --all --corner tt --single-simulator --output results

# Decks only
dram-device generate --all --corner tt --output build

# Golden regression (Spectre reference CSVs under bench/device_benchmark/golden/)
dram-device validate-golden --input results/tt --corner tt
dram-device validate-golden --input results --all-corners

# Regenerate comparison from existing runs
dram-device compare-simulators --input results --corner tt

# Report from CSVs
dram-device report --input results/device_metrics.csv \
  --output results/RESULTS.md --corner tt \
  --cell-input results/cell_1t1c_metrics.csv \
  --mini-input results/mini_array_metrics.csv
```

### `dram-validate` (validation lane)

Golden YAML regression, paper/literature correlation, provenance docs, simulator cross-check pins. Source: `src/validation/`. Golden specs live at `models/OpenDRAMmodelV1/validation/golden/` (paper-derived via `scripts/publish_golden_from_paper.py`).

| Command | Description |
|---------|-------------|
| `check` | Validate golden YAML **spice** bands vs pinned TT CSVs + roadmap trends |
| `report` | Full audit: `RESULTS.md`, figures, `data/` exports |
| `paper` | Part I/II table vs pinned SPICE correlation (`docs/paper_correlation.md`) |
| `correlate` | Literature roadmap correlation (`docs/literature_correlation.md`) |
| `provenance` | Model provenance + `CONTRIBUTING_MODELS.md` |
| `list-golden` | List loaded golden specs per model |
| `sensitivity` | Local OAT report from cache; optional Sobol (`--sobol`, needs `SALib`) |
| `simulators` | Show or `--refresh` pinned multi-simulator comparison CSVs |

```bash
# Offline regression (uses bench/validation/pinned/)
dram-validate check

# Full validation report
dram-validate report --output results/validation

# Paper and literature audits
dram-validate paper
dram-validate correlate
dram-validate provenance

# List golden specs
dram-validate list-golden

# Sensitivity (requires bench/validation/sensitivity/local_oat_cache.json)
dram-validate sensitivity
dram-validate sensitivity --sobol --samples 256

# Refresh simulator comparison pins (needs dram-device + Spectre)
dram-validate simulators --refresh
dram-validate simulators --refresh --full
```

Metrics tagged `validation: paper` in golden YAML are checked via `dram-validate paper`, not `check`.

### `dram-sense-amp` (read-path lane)

Read-path ΔV_BL extraction and sense-amplifier co-design sweeps. Source: `src/sense_amp/`.

| Command | Description |
|---------|-------------|
| `list-models` | Supported read-path model IDs |
| `generate` | Write read-path SPICE decks |
| `run` | Simulate (Spectre/HSPICE) and export signal + co-design CSVs |
| `analyze` | SA co-design on existing signal CSVs |
| `report` | Regenerate `RESULTS.md` and figures from CSVs |

```bash
dram-sense-amp list-models

dram-sense-amp generate --all --corner tt --output build/sense_amp
dram-sense-amp run --all --corner tt --output results/sense_amp
dram-sense-amp run --all --corner tt --generate-only --output results/sense_amp

dram-sense-amp analyze --input results/sense_amp/read_signal_tt.csv \
  --output results/sense_amp

dram-sense-amp report --input results/sense_amp/read_signal_tt.csv \
  --output results/sense_amp --corner tt
```

Without Spectre/HSPICE, `dram-bench run --suite sense_amp` falls back to deck-only mode automatically.

### `dram-ccell` (Ccell roadmap lane)

Cell-capacitance roadmap: retention vs read binding, dielectric feasibility, 3D boost tables. Source: `src/ccell/`. Depends on device + pareto (+ sense-amp overlay) results when deriving.

| Command | Description |
|---------|-------------|
| `derive` | Analytic sweep from upstream CSVs (no SPICE) |
| `run` | Build sweep database (derive + optional SPICE) |
| `report` | Figures + `RESULTS.md` from `ccell_sweep.csv` |

```bash
dram-ccell derive --output results/ccell
dram-ccell run --output results/ccell
dram-ccell run --derive-only --output results/ccell
dram-ccell run --generate-only --output build/ccell
dram-ccell run --simulator spectre --output results/ccell

dram-ccell report --input results/ccell/ccell_sweep.csv \
  --output results/ccell/RESULTS.md
```

### `dram-pareto` (Pareto roadmap lane)

Retention–performance Pareto points from device-benchmark exports; optional native Pareto SPICE. Source: `src/pareto/`. Auto-derived by `dram-bench run --suite ccell` when needed.

| Command | Description |
|---------|-------------|
| `derive` | Build `pareto_roadmap.csv` from device benchmark results |
| `run` | Full roadmap database (derive + sim) |
| `generate` | Pareto SPICE decks only |
| `report` | Figures + markdown atlas |
| `compare-simulators` | Cross-tool Pareto metric comparison |

```bash
dram-pareto derive --bench-input results/device --output results/pareto
dram-pareto run --output results/pareto
dram-pareto run --derive-only --output results/pareto
dram-pareto generate --all --corner tt --output build/pareto

dram-pareto report --input results/pareto/pareto_roadmap.csv \
  --output results/pareto/RESULTS.md

dram-pareto compare-simulators --input results/pareto
```

## Golden and validation workflow

Two golden layers ship with the platform:

| Layer | Location | Checked by |
|-------|----------|------------|
| Paper golden YAML | `models/OpenDRAMmodelV1/validation/golden/` | `dram-validate check` (spice bands) + `dram-validate paper` (TCAD tables) |
| Spectre CSV regression | `bench/device_benchmark/golden/` | `dram-device validate-golden` |
| Pinned TT metrics | `bench/validation/pinned/` | `dram-validate check` input |

Regenerate paper golden from PDFs:

```bash
python scripts/extract_paper_refs.py --docs-root /path/to/part_I_II_pdfs
python scripts/publish_golden_from_paper.py
```

Release manifest (card hashes, extraction SHA): `models/OpenDRAMmodelV1/validation/RELEASE_MANIFEST.yaml`.

## Repository layout

Top-level folders separate **code** (`src/`), **inputs** (`bench/`, `models/`, `data/`), **docs**, **scripts**, and **generated outputs** (`results/`, `build/`).

### Top-level

| Path | Purpose |
|------|---------|
| [`src/`](src/) | Installable Python packages — one lane per subdirectory plus the `dram-bench` orchestrator |
| [`bench/`](bench/) | **Repo data & configs** (YAML, pinned CSVs, golden references) — not Python code; do not confuse with [`src/bench/`](src/bench/) |
| [`models/`](models/) | Vendored SPICE model bundle shipped with the release |
| [`data/`](data/) | Static reference datasets for validation (paper tables, literature roadmap) |
| [`docs/`](docs/) | Human-written specs plus generated audit markdown |
| [`scripts/`](scripts/) | Shell entry points and maintenance utilities (PDF extract, golden publish) |
| [`tests/`](tests/) | Offline pytest — platform helpers, suite wiring, report smoke tests |
| [`results/`](results/) | Benchmark run outputs — CSVs, figures, `RESULTS.md`, `MANIFEST.json` (gitignored) |
| [`build/`](build/) | Rebuildable simulator caches — ngspice OSDI, Spectre card patches (gitignored) |

### `src/` — Python packages

| Path | CLI | Purpose |
|------|-----|---------|
| [`src/dram_benchmark/`](src/dram_benchmark/) | `dram-bench` | Suite orchestration, manifests, aggregate `RESULTS.md`, artifact validation |
| [`src/bench/`](src/bench/) | `dram-device` | Device SPICE decks, simulation, metric extraction, multi-simulator compare |
| [`src/validation/`](src/validation/) | `dram-validate` | Golden regression, paper/literature correlation, provenance reports |
| [`src/sense_amp/`](src/sense_amp/) | `dram-sense-amp` | Read-path ΔV_BL SPICE, SA co-design sweeps, coupling decks |
| [`src/ccell/`](src/ccell/) | `dram-ccell` | Ccell roadmap sweeps, dielectric feasibility, 3D boost tables |
| [`src/pareto/`](src/pareto/) | `dram-pareto` | Retention–performance Pareto points derived from device benchmarks |

### `bench/` — configs and pinned inputs

| Path | Purpose |
|------|---------|
| [`bench/config/corners.yaml`](bench/config/corners.yaml) | PVT corners, Ccell sweep list, mini-array RC topology defaults |
| [`bench/registry/corner_registry.yaml`](bench/registry/corner_registry.yaml) | Canonical corner registry (`OPEN_DRAM_CORNER_REGISTRY`) |
| [`bench/device_benchmark/golden/`](bench/device_benchmark/golden/) | Per-corner Spectre CSV snapshots for `dram-device validate-golden` (±2% rtol) |
| [`bench/validation/pinned/`](bench/validation/pinned/) | TT-corner pinned device/cell metrics — offline input for `dram-validate check` |
| [`bench/validation/pinned/simulator_compare/`](bench/validation/pinned/simulator_compare/) | Pinned Spectre/HSPICE/ngspice rel-diff tables for validation reports |
| [`bench/validation/sensitivity/`](bench/validation/sensitivity/) | Cached local OAT sensitivity results (`local_oat_cache.json`) |
| [`bench/sense_amp_vct/configs/read_path.yaml`](bench/sense_amp_vct/configs/read_path.yaml) | Read-path bias matrix, Ccell list, coupling options for sense-amp lane |
| [`bench/ccell_roadmap/configs/ccell.yaml`](bench/ccell_roadmap/configs/ccell.yaml) | Ccell sweep grid, dielectric scenarios, retention targets |
| [`bench/pareto_roadmap/configs/pareto.yaml`](bench/pareto_roadmap/configs/pareto.yaml) | Pareto corner list, reference Ccell, roadmap derivation knobs |

### `models/OpenDRAMmodelV1/` — vendored model bundle

| Path | Purpose |
|------|---------|
| [`models/access_tx/*.inc`](models/OpenDRAMmodelV1/models/access_tx/) | Seven access transistor BSIM-CMG cards (BCAT, VCT×4, 3D GAA Si/AOS) |
| [`models/peri_tx/`](models/OpenDRAMmodelV1/models/peri_tx/) | High-voltage periphery card (`hv_peri_28_32.inc`) |
| [`validation/golden/`](models/OpenDRAMmodelV1/validation/golden/) | Paper-derived golden YAML per model (auto-generated; do not hand-edit) |
| [`validation/RELEASE_MANIFEST.yaml`](models/OpenDRAMmodelV1/validation/RELEASE_MANIFEST.yaml) | Card SHA256, extraction provenance, bundle fingerprint for releases |
| [`docs/user_guide_V1.0.docx`](models/OpenDRAMmodelV1/docs/user_guide_V1.0.docx) | Upstream model user guide (TCAD calibration workflow) |
| [`models/OpenDRAMmodelV1/bench/`](models/OpenDRAMmodelV1/bench/) | Upstream Cadence OA reference testbench artifacts (not used by Python lanes) |
| [`VENDORED.md`](models/OpenDRAMmodelV1/VENDORED.md) | Vendoring notes and refresh workflow from MATRIX-PDK upstream |
| [`LICENSE`](models/OpenDRAMmodelV1/LICENSE) | MATRIX-PDK academic / non-commercial license for model cards |

### `data/` — reference inputs

| Path | Purpose |
|------|---------|
| [`data/paper/extracted_refs.yaml`](data/paper/extracted_refs.yaml) | Part I/II metrics transcribed from PDFs (`scripts/extract_paper_refs.py`) |
| [`data/paper/model_mapping.yaml`](data/paper/model_mapping.yaml) | Maps each model card ID → paper configuration anchor |
| [`data/paper/docs/`](data/paper/docs/) | Optional local copy of Part I/II PDFs (fallback if `PAPER_DOCS_ROOT` unset) |
| [`data/literature/dram_roadmap.yaml`](data/literature/dram_roadmap.yaml) | Public DRAM roadmap summaries for literature correlation |

### `docs/` — specifications and generated audits

| Path | Purpose |
|------|---------|
| [`docs/benchmark_spec.md`](docs/benchmark_spec.md) | Metric definitions, suite descriptions, scope/limitations |
| [`docs/simulator_cross_check.md`](docs/simulator_cross_check.md) | Expected Spectre vs HSPICE vs ngspice disagreements |
| [`docs/DEFAULT_MODELS.md`](docs/DEFAULT_MODELS.md) | Model inventory and usage notes |
| `docs/paper_correlation.md` | Generated by `dram-validate paper` — SPICE vs Part I/II tables |
| `docs/literature_correlation.md` | Generated by `dram-validate correlate` |
| `docs/model_provenance.md` | Generated by `dram-validate provenance` — confidence tiers per model |

### `scripts/` — entry points

| Path | Purpose |
|------|---------|
| [`scripts/run_experiments.sh`](scripts/run_experiments.sh) | One-command install + `dram-bench run` + offline pytest |
| [`scripts/clean.sh`](scripts/clean.sh) | Remove `results/`, `build/`, caches, and generated docs |
| [`scripts/extract_paper_refs.py`](scripts/extract_paper_refs.py) | PDF → `data/paper/extracted_refs.yaml` |
| [`scripts/publish_golden_from_paper.py`](scripts/publish_golden_from_paper.py) | Extracted refs + pinned CSVs → `models/.../validation/golden/` |

### `tests/` — verification

| Path | Purpose |
|------|---------|
| [`tests/test_platform.py`](tests/test_platform.py) | Model inventory, manifest, validation helpers (offline) |
| [`tests/test_suites.py`](tests/test_suites.py) | Paper A1 suite wiring and path resolution |
| [`tests/test_read_path_report.py`](tests/test_read_path_report.py) | Sense-amp report and SA spec export smoke tests |

### Directory tree (compact)

```text
scripts/          Entry points and golden maintenance
models/           Vendored SPICE cards + paper golden YAML
bench/            Lane configs, pinned CSVs, Spectre golden regression
data/             Paper + literature reference YAML
docs/             Specs and generated audit markdown
src/              Python packages (dram-bench + five lanes)
tests/            Pytest
results/          Run artifacts (gitignored)
build/            Simulator build cache (gitignored)
```

## Development

```bash
pip install -e ".[dev]"
ruff check src
pytest
pytest -m "not integration and not ngspice and not spectre and not hspice"  # offline only
```

## License

This platform is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [LICENSE](LICENSE)).

Vendored model cards in `models/OpenDRAMmodelV1/` remain under the [MATRIX-PDK academic / non-commercial license](models/OpenDRAMmodelV1/LICENSE) (Georgia Institute of Technology).

## Citation

### What to cite

| If you use… | Cite |
|-------------|------|
| This benchmarking platform (Paper A1 automation, suites, validation) | **DRAM Benchmarking Platform** entry below |
| Open DRAM Model `.inc` cards or model-derived results | **Part I and Part II** papers (required by [OpenDRAMmodelV1](models/OpenDRAMmodelV1/README.md)) |
| Both platform reruns and model cards | Platform entry **and** both papers |

Golden specs and pinned metrics trace to Part I/II via `data/paper/extracted_refs.yaml`; model card use still requires the paper citations per upstream license.

### This repository

```bibtex
@misc{dram_benchmarking_platform,
  title        = {DRAM Benchmarking Platform},
  author       = {{DRAM Benchmarking Platform}},
  year         = {2026},
  version      = {0.2.0},
  publisher    = {GitHub},
  howpublished = {\url{https://github.com/DRAM-Lab/DRAM-Benchmarking-Platform}},
  note         = {Self-contained Paper A1 benchmark automation for Open DRAM Model cards}
}
```

### Model bundle (software)

```bibtex
@misc{opendrammodelv1,
  title        = {Open DRAM Model v1 (MATRIX-PDK)},
  author       = {Lee, Kiseok and Lim, Seongkwang and Yu, Shimeng},
  year         = {2026},
  publisher    = {GitHub},
  howpublished = {\url{https://github.com/MATRIX-PDK/OpenDRAMmodelV1}},
  note         = {Vendored in DRAM Benchmarking Platform; cite Part I and Part II papers when using model cards}
}
```

### Publications (required for model cards)

```bibtex
@article{lee2026opendram_part1,
  author  = {Lee, Kiseok and Lim, Seongkwang and Datta, Suman and Yu, Shimeng},
  title   = {{Open DRAM Model Part I: Cross-Layer Device, Array, and Circuit Analysis with BL-to-BL Coupling Mitigation for 4F² VCT DRAM}},
  journal = {IEEE Journal on Exploratory Solid-State Computational Devices and Circuits},
  year    = {2026},
  doi     = {10.1109/JXCDC.2026.3704358}
}

@article{lee2026opendram_part2,
  author  = {Lee, Kiseok and Lim, Seongkwang and Datta, Suman and Yu, Shimeng},
  title   = {{Open DRAM Model Part II: Enabling Processing-in-Memory in 3D DRAM}},
  journal = {IEEE Journal on Exploratory Solid-State Computational Devices and Circuits},
  year    = {2026},
  doi     = {10.1109/JXCDC.2026.3704508}
}
```

## References

### Software

- **[DRAM-Lab/DRAM-Benchmarking-Platform](https://github.com/DRAM-Lab/DRAM-Benchmarking-Platform)** — this repo (Paper A1 suites, validation, vendored models).
- **[MATRIX-PDK/OpenDRAMmodelV1](https://github.com/MATRIX-PDK/OpenDRAMmodelV1)** — TCAD-calibrated BSIM-CMG access and periphery cards (vendored under `models/OpenDRAMmodelV1/`).

### Publications

The underlying Open DRAM models and cross-layer methodology are described in:

1. Kiseok Lee, Seongkwang Lim, Suman Datta, Shimeng Yu, "Open DRAM Model Part I: Cross-Layer Device, Array, and Circuit Analysis with BL-to-BL Coupling Mitigation for 4F² VCT DRAM." *IEEE Journal on Exploratory Solid-State Computational Devices and Circuits* (2026). DOI [10.1109/JXCDC.2026.3704358](https://doi.org/10.1109/JXCDC.2026.3704358).

2. Kiseok Lee, Seongkwang Lim, Suman Datta, Shimeng Yu, "Open DRAM Model Part II: Enabling Processing-in-Memory in 3D DRAM." *IEEE Journal on Exploratory Solid-State Computational Devices and Circuits* (2026). DOI [10.1109/JXCDC.2026.3704508](https://doi.org/10.1109/JXCDC.2026.3704508).
