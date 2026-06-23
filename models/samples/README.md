# Sample custom access model cards

This folder shows the **minimum inputs** needed to benchmark a new BSIM-CMG access transistor with OpenDRAMBench, without modifying the bundled `models/OpenDRAMmodelV1/` tree.

## What a default run produces

`./scripts/run_experiments.sh` (or `dram-bench run --suite device`) writes a results bundle under `results/`:

| Artifact | Purpose |
|----------|---------|
| `RESULTS.md` | Human-readable report with the OpenDRAMBench platform header, metric tables, figures, and reproduce commands |
| `MANIFEST.json` | Provenance manifest: SHA-256 of every `.inc` in the model root, tool versions, artifact checksums |
| `device_metrics.csv` | Ion, Ioff, Ron, Cgg, Vt, SS, DIBL, GIDL, … per model |
| `cell_1t1c_metrics*.csv` | 1T1C transient metrics (10 / 20 / 30 fF) |
| `mini_array_metrics.csv` | Mini-array bitline RC settle metrics |
| `decks/` | Generated SPICE netlists |
| `figures/*.svg` | Pareto, VCT scaling, radar FOM, Ccell scaling plots |

The opening lines of `RESULTS.md` are injected automatically by `dram-bench`:

```markdown
# OpenDRAMBench — Results

Reproducible benchmark automation for Open DRAM model cards. This platform extends
the Open DRAM Model Part I/II artifacts with push-button reruns, multi-tool comparison,
validation, and provenance manifests.

**Models:** <comma-separated list of every *.inc stem in OPEN_DRAM_MODEL_ROOT>
```

With the default bundled cards, **Models** lists all seven IDs (`BCAT_125`, `VCT_082`, …, `3D_gaa_AOS`).

## What changes when you use a new model

Point `OPEN_DRAM_MODEL_ROOT` at a directory that contains your `.inc` file(s), then pass `--model <ID>` (filename stem without `.inc`).

| Output field | Default (7 bundled cards) | Custom model directory |
|--------------|---------------------------|-------------------------|
| `RESULTS.md` **Models:** line | All seven bundled IDs | Only your `.inc` stems (e.g. `VCT_130`) |
| `MANIFEST.json` `model_root` | `models/OpenDRAMmodelV1/models/access_tx` | Your custom directory path |
| `MANIFEST.json` `model_cards` | SHA-256 of all seven `.inc` files | SHA-256 of your custom `.inc` file(s) only |
| Metric tables / figures | Seven rows, VCT scaling section | One row per model you ran; VCT scaling only if multiple `VCT_*` IDs |
| Golden regression | Checked against Spectre pins (unless ngspice) | Skipped — use `--skip-golden` |
| `dram-bench validate` model inventory | PASS (exactly seven cards) | WARN/FAIL if the directory is not the full bundled set |

The OpenDRAMBench header text is **the same** for default and custom runs; only the model list, metrics, and manifest hashes reflect your cards.

## Minimal card requirements

Each access model is one HSPICE `.inc` file named `<MODEL_ID>.inc`. The platform parser (`bench.models.load_access_model`) requires:

| Item | Where | Example |
|------|-------|---------|
| Model ID | Filename stem | `VCT_130.inc` → `--model VCT_130` |
| BSIM-CMG device | `.model nfet nmos level = 72` | See sample card |
| Nominal Vdd | Header comment `Nominal VDD=…V` | `** Nominal VDD=0.9V` |
| `bulkmod` | Model parameters | `0` (bulk tied to source) or `1` |
| `l` | Channel length (m) | `2.4e-008` |
| `nfin` | Number of fins | `1` |
| `fpitch` | Fin pitch (m) | `6e-008` |
| `vsat` | Saturation velocity proxy | `28720` |

Architecture labels in reports are inferred from the ID prefix:

- `BCAT_*` → BCAT (6F²)
- `VCT_*` → VCT (4F²)
- `3D_gaa_*` → 3D GAA

See [`custom_vct_demo/VCT_130.inc`](custom_vct_demo/VCT_130.inc) — a working copy of the bundled `VCT_125` card with comments marking the fields above.

**Naming tip:** For `VCT_*` IDs, use a numeric node suffix (e.g. `VCT_130`) so VCT scaling tables parse correctly.

## Quick start: run the sample card

From the repository root (deck generation only — no simulator required):

```bash
export OPEN_DRAM_MODEL_ROOT="$PWD/models/samples/custom_vct_demo"
dram-bench run --suite device --corner tt --model VCT_130 \
  --generate-only --skip-golden --output results/custom_demo
```

Full SPICE run (requires Spectre, HSPICE, or ngspice):

```bash
export OPEN_DRAM_MODEL_ROOT="$PWD/models/samples/custom_vct_demo"
dram-bench run --suite device --corner tt --model VCT_130 \
  --skip-golden --output results/custom_demo
```

Or use the helper script:

```bash
./models/samples/run_custom_demo.sh              # simulate if a backend is available
./models/samples/run_custom_demo.sh --generate-only
```

Inspect outputs:

```bash
head -20 results/custom_demo/RESULTS.md   # after a full run
cat results/custom_demo/device_metrics.csv
python -m json.tool results/custom_demo/MANIFEST.json | head -30
```

**Note:** Summary figures (radar FOM) filter on the seven bundled model IDs in `bench/plot_style.py`. A single custom ID such as `VCT_130` still produces CSV metrics and SPICE decks, but `dram-bench` report generation may fail on the radar plot until the ID is registered for plotting. Use the CSVs directly for a quick trial, or add your ID to `MODEL_DISPLAY_ORDER` / `MODEL_COLORS` for full reports.

## Adding your own model

1. Copy `custom_vct_demo/VCT_130.inc` to `my_lab/MyModel_125.inc` (pick a `BCAT_`, `VCT_`, or `3D_gaa_` prefix).
2. Edit BSIM-CMG parameters and the `Nominal VDD` header.
3. Set `OPEN_DRAM_MODEL_ROOT` to the directory containing `MyModel_125.inc`.
4. Run with `--model MyModel_125 --skip-golden`.
5. For full platform integration (validation lane, golden YAML, multi-lane `SUITE=all`), register the ID in `src/bench/models.py` (`ACCESS_MODEL_IDS`) and add golden specs under `models/OpenDRAMmodelV1/validation/golden/` — see `dram-validate provenance` / `CONTRIBUTING_MODELS.md`.

## What you do **not** need to change for a quick device-only trial

- `bench/config/corners.yaml` — shared PVT corners apply to any access card
- SPICE deck templates under `src/bench/netlist/` — they `.include` your card automatically
- The seven bundled cards in `models/OpenDRAMmodelV1/` — leave them untouched; override with `OPEN_DRAM_MODEL_ROOT` only
