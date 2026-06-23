# DRAM Benchmarking Platform

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-green?logo=creativecommons&logoColor=white)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776ab.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.2.0-blue?logo=semver&logoColor=white)](pyproject.toml)

Reproducible SPICE benchmarking for DRAM access transistors across **6F² BCAT**, **4F² VCT**, and **3D GAA** architectures. A single install (`pip install -e .`) provides suite orchestration, five benchmark lanes, vendored BSIM model cards, pinned regression data, and validation against paper-derived golden specs.

- **Specification:** [docs/benchmark_spec.md](docs/benchmark_spec.md)
- **Model cards:** [models/OpenDRAMmodelV1/](models/OpenDRAMmodelV1/)
- **License:** [CC BY 4.0](LICENSE) (platform code); [models/OpenDRAMmodelV1/LICENSE](models/OpenDRAMmodelV1/LICENSE) (model cards)

## Table of contents

- [Scope and limitations](#scope-and-limitations)
- [Supported models](#supported-models)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Benchmark suites](#benchmark-suites)
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

## Scope and limitations

### Purpose

Compare access transistors under a shared SPICE extraction methodology, with additional lanes for read-path signal, cell-capacitance roadmap, and validation audits. Intended for **research, architecture ranking, and reproducible evidence bundles** — not foundry tape-out sign-off.

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

- Bundled `.inc` cards are **compact models**, not GDS layouts or extracted RC netlists.
- Metrics are **research proxies** (see [benchmark spec](docs/benchmark_spec.md)); published TCAD tables and BSIM SPICE extraction use different definitions — `dram-validate paper` documents the gaps.
- **Spectre** is the reference backend for golden CSV regression; **HSPICE** and **ngspice** are supported with documented expected disagreements ([docs/simulator_cross_check.md](docs/simulator_cross_check.md)).
- Sense-amp **SPICE** read-path requires Spectre or HSPICE; without them, decks are generated and reports use deck-only / analytic fallbacks.

## Supported models

Seven access cards ship under `models/OpenDRAMmodelV1/models/access_tx/`.

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

ngspice requires a BSIM-CMG OSDI build (cached under `build/ngspice_osdi/` on first run). The experiment script runs `scripts/setup_ngspice_osdi.sh` automatically when ngspice is the selected backend; you can also run it manually:

```bash
./scripts/setup_ngspice_osdi.sh
```

This clones [VA-Models](https://github.com/dwarning/VA-Models) into `third_party/VA-Models` (or use `OPEN_DRAM_VA_MODELS_ROOT` for an existing tree) and builds `bsimcmg.osdi` with `openvaf`. Set `NGSPICE=/path/to/ngspice` if not on `PATH`.

**Note:** ngspice uses `/tmp` for internal temp files; ensure the root filesystem has free space.

## Installation

```bash
cd DRAM-Benchmarking-Platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Model cards are included under `models/OpenDRAMmodelV1/` — no submodules or extra checkouts.

## Quick start

**One-shot pipeline** (install, device suite @ TT, offline tests):

```bash
./scripts/run_experiments.sh
```

**Full evidence bundle** (all six suites):

```bash
SUITE=all ./scripts/run_experiments.sh
```

**Regenerate paper-derived golden YAML** (after updating PDFs or pinned metrics):

```bash
python scripts/extract_paper_refs.py --docs-root data/paper/docs
python scripts/publish_golden_from_paper.py
```

Place Part I/II PDFs in `data/paper/docs/`, or pass any directory via `--docs-root` / `PAPER_DOCS_ROOT`.

## Benchmark suites

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
| `PAPER_DOCS_ROOT` | `data/paper/docs` | Part I/II PDF directory for `extract_paper_refs.py` |
| `SUITE` | `device` | Suite for `run_experiments.sh` |
| `RESULTS_DIR` | `results` | Output root for `run_experiments.sh` |
| `DEVICE_ONLY` | `0` | Skip 1T1C + mini-array |
| `GENERATE_ONLY` | `0` | Deck generation only |
| `SKIP_GOLDEN` | `0` | Skip Spectre CSV golden check on device lane |

## CLI reference

Six commands install from one package. **`dram-bench`** orchestrates full suites; lane tools are also callable directly.

### `dram-bench` (orchestrator)

Top-level automation: suite dispatch, manifests, aggregate `RESULTS.md`, artifact validation.

| Command | Description |
|---------|-------------|
| `list-models` | List bundled access model IDs and card file sizes |
| `run` | Run a benchmark suite (see [Benchmark suites](#benchmark-suites)) |
| `manifest` | Write `MANIFEST.json` for a results tree |
| `validate` | Validate results artifacts (schema, coverage, file presence) |
| `report` | Regenerate lane `RESULTS.md` with platform header |

```bash
dram-bench list-models

dram-bench run --suite device --corner tt --output results/device
dram-bench run --suite corner_sweep --output results/corner_sweep
dram-bench run --suite multi_tool --output results/multi_tool
dram-bench run --suite sense_amp --output results/sense_amp
dram-bench run --suite ccell --output results/ccell
dram-bench run --suite validation --output results/validation
dram-bench run --suite all --output results/

dram-bench run --suite device --device-only --output results/device_only
dram-bench run --suite device --generate-only --output build/device
dram-bench run --suite device --simulator hspice --output results/hspice
dram-bench run --suite device --skip-golden --output results/device

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
dram-device run --model VCT_125 --corner tt --output results/tt
dram-device run --all --corner all --output results
dram-device run --all --corner tt --simulator spectre --output results/spectre/tt
dram-device run --all --corner tt --all-simulators --output results
dram-device generate --all --corner tt --output build
dram-device validate-golden --input results/tt --corner tt
dram-device compare-simulators --input results --corner tt
dram-device report --input results/device_metrics.csv \
  --output results/RESULTS.md --corner tt
```

### `dram-validate` (validation lane)

Golden YAML regression, paper/literature correlation, provenance docs, simulator cross-check pins. Source: `src/validation/`.

| Command | Description |
|---------|-------------|
| `check` | Validate golden YAML **spice** bands vs pinned TT CSVs + roadmap trends |
| `report` | Full audit: `RESULTS.md`, figures, `data/` exports |
| `paper` | Published table vs pinned SPICE correlation (`docs/paper_correlation.md`) |
| `correlate` | Literature roadmap correlation (`docs/literature_correlation.md`) |
| `provenance` | Model provenance + `CONTRIBUTING_MODELS.md` |
| `list-golden` | List loaded golden specs per model |
| `sensitivity` | Local OAT report from cache; optional Sobol (`--sobol`, needs `SALib`) |
| `simulators` | Show or `--refresh` pinned multi-simulator comparison CSVs |

```bash
dram-validate check
dram-validate report --output results/validation
dram-validate paper
dram-validate correlate
dram-validate provenance
dram-validate list-golden
dram-validate simulators --refresh
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
dram-sense-amp run --all --corner tt --output results/sense_amp
dram-sense-amp run --all --corner tt --generate-only --output results/sense_amp
dram-sense-amp report --input results/sense_amp/read_signal_tt.csv \
  --output results/sense_amp --corner tt
```

Without Spectre/HSPICE, `dram-bench run --suite sense_amp` falls back to deck-only mode.

### `dram-ccell` (Ccell roadmap lane)

Cell-capacitance roadmap: retention vs read binding, dielectric feasibility, 3D boost tables. Source: `src/ccell/`.

| Command | Description |
|---------|-------------|
| `derive` | Analytic sweep from prior lane CSVs (no SPICE) |
| `run` | Build sweep database (derive + optional SPICE) |
| `report` | Figures + `RESULTS.md` from `ccell_sweep.csv` |

```bash
dram-ccell derive --output results/ccell
dram-ccell run --output results/ccell
dram-ccell report --input results/ccell/ccell_sweep.csv \
  --output results/ccell/RESULTS.md
```

### `dram-pareto` (Pareto roadmap lane)

Retention–performance Pareto points from device exports; optional native Pareto SPICE. Source: `src/pareto/`.

| Command | Description |
|---------|-------------|
| `derive` | Build `pareto_roadmap.csv` from device results |
| `run` | Full roadmap database (derive + sim) |
| `generate` | Pareto SPICE decks only |
| `report` | Figures + markdown atlas |
| `compare-simulators` | Cross-tool Pareto metric comparison |

```bash
dram-pareto derive --bench-input results/device --output results/pareto
dram-pareto run --output results/pareto
dram-pareto report --input results/pareto/pareto_roadmap.csv \
  --output results/pareto/RESULTS.md
```

## Golden and validation workflow

| Layer | Location | Checked by |
|-------|----------|------------|
| Paper golden YAML | `models/OpenDRAMmodelV1/validation/golden/` | `dram-validate check` (spice bands) + `dram-validate paper` (published tables) |
| Spectre CSV regression | `bench/device_benchmark/golden/` | `dram-device validate-golden` |
| Pinned TT metrics | `bench/validation/pinned/` | `dram-validate check` input |

```bash
python scripts/extract_paper_refs.py --docs-root data/paper/docs
python scripts/publish_golden_from_paper.py
```

Release manifest: `models/OpenDRAMmodelV1/validation/RELEASE_MANIFEST.yaml`.

## Repository layout

Top-level folders separate **code** (`src/`), **inputs** (`bench/`, `models/`, `data/`), **docs**, **scripts**, and **generated outputs** (`results/`, `build/`).

### Top-level

| Path | Purpose |
|------|---------|
| [`src/`](src/) | Installable Python packages — one lane per subdirectory plus the `dram-bench` orchestrator |
| [`bench/`](bench/) | Repo configs and pinned CSVs (YAML, golden references) — not Python code |
| [`models/`](models/) | Bundled SPICE model cards and paper golden YAML |
| [`data/`](data/) | Paper tables and literature roadmap inputs for validation |
| [`docs/`](docs/) | Benchmark spec, simulator notes, generated audit markdown |
| [`scripts/`](scripts/) | Entry points and golden maintenance utilities |
| [`tests/`](tests/) | Offline pytest suite |
| [`results/`](results/) | Run outputs (gitignored) |
| [`build/`](build/) | Simulator caches — ngspice OSDI, Spectre card patches (gitignored) |

### `src/` — Python packages

| Path | CLI | Purpose |
|------|-----|---------|
| [`src/dram_benchmark/`](src/dram_benchmark/) | `dram-bench` | Suite orchestration, manifests, aggregate reports |
| [`src/bench/`](src/bench/) | `dram-device` | Device SPICE decks, simulation, extraction |
| [`src/validation/`](src/validation/) | `dram-validate` | Golden regression, correlation, provenance |
| [`src/sense_amp/`](src/sense_amp/) | `dram-sense-amp` | Read-path SPICE and SA co-design |
| [`src/ccell/`](src/ccell/) | `dram-ccell` | Ccell roadmap sweeps |
| [`src/pareto/`](src/pareto/) | `dram-pareto` | Pareto derivation from device results |

### `bench/` — configs and pinned inputs

| Path | Purpose |
|------|---------|
| [`bench/config/corners.yaml`](bench/config/corners.yaml) | PVT corners, Ccell sweep, mini-array RC defaults |
| [`bench/registry/corner_registry.yaml`](bench/registry/corner_registry.yaml) | Corner registry |
| [`bench/device_benchmark/golden/`](bench/device_benchmark/golden/) | Per-corner Spectre CSV snapshots for `dram-device validate-golden` |
| [`bench/validation/pinned/`](bench/validation/pinned/) | TT pinned metrics for `dram-validate check` |
| [`bench/sense_amp_vct/configs/read_path.yaml`](bench/sense_amp_vct/configs/read_path.yaml) | Sense-amp lane configuration |
| [`bench/ccell_roadmap/configs/ccell.yaml`](bench/ccell_roadmap/configs/ccell.yaml) | Ccell sweep configuration |
| [`bench/pareto_roadmap/configs/pareto.yaml`](bench/pareto_roadmap/configs/pareto.yaml) | Pareto derivation configuration |

### `models/OpenDRAMmodelV1/` — model bundle

| Path | Purpose |
|------|---------|
| [`models/access_tx/`](models/OpenDRAMmodelV1/models/access_tx/) | Seven access transistor BSIM-CMG cards |
| [`models/peri_tx/`](models/OpenDRAMmodelV1/models/peri_tx/) | High-voltage periphery card |
| [`validation/golden/`](models/OpenDRAMmodelV1/validation/golden/) | Paper-derived golden YAML (auto-generated) |
| [`validation/RELEASE_MANIFEST.yaml`](models/OpenDRAMmodelV1/validation/RELEASE_MANIFEST.yaml) | Card hashes and extraction provenance |
| [`docs/user_guide_V1.0.docx`](models/OpenDRAMmodelV1/docs/user_guide_V1.0.docx) | Model calibration user guide |
| [`LICENSE`](models/OpenDRAMmodelV1/LICENSE) | Model card license terms |

### `data/`, `docs/`, `scripts/`, `tests/`

| Path | Purpose |
|------|---------|
| [`data/paper/`](data/paper/) | Extracted paper metrics and model-to-paper mapping |
| [`data/literature/`](data/literature/) | Literature roadmap YAML for correlation |
| [`docs/benchmark_spec.md`](docs/benchmark_spec.md) | Metric definitions and suite scope |
| [`scripts/run_experiments.sh`](scripts/run_experiments.sh) | Install, run default suite, offline pytest |
| [`scripts/extract_paper_refs.py`](scripts/extract_paper_refs.py) | PDF → `data/paper/extracted_refs.yaml` |
| [`scripts/publish_golden_from_paper.py`](scripts/publish_golden_from_paper.py) | Extracted refs → golden YAML |
| [`tests/`](tests/) | Platform, suite, and report smoke tests |

## Development

```bash
pip install -e ".[dev]"
ruff check src
pytest -m "not integration and not ngspice and not spectre and not hspice"
```

## License

Platform code: [CC BY 4.0](LICENSE).

Model cards: [models/OpenDRAMmodelV1/LICENSE](models/OpenDRAMmodelV1/LICENSE) (academic / non-commercial terms, Georgia Institute of Technology).

## Citation

### What to cite

| If you use… | Cite |
|-------------|------|
| This platform (suites, validation, automation) | **DRAM Benchmarking Platform** below |
| Bundled `.inc` model cards or model-derived results | **Part I and Part II** papers below (see also `models/OpenDRAMmodelV1/README.md`) |
| Both | Platform entry **and** both papers |

### DRAM Benchmarking Platform

```bibtex
@misc{dram_benchmarking_platform,
  title   = {DRAM Benchmarking Platform},
  author  = {{DRAM Benchmarking Platform}},
  year    = {2026},
  version = {0.2.0},
  note    = {Reproducible DRAM access-transistor SPICE benchmarking with validation lanes}
}
```

### Open DRAM Model publications

When using the bundled model cards, cite:

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
