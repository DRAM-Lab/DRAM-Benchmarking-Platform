# Bundled bench assets

Runtime data shipped inside **DRAM-Benchmarking-Platform** — no external repo checkout required.

| Path | Role |
|------|------|
| `bench/validation/pinned/` | Pinned TT regression CSVs (device, cell, simulator compare) |
| `bench/registry/` | Corner registry YAML |
| `bench/config/` | Lane configs (corners, sense-amp, etc.) |
| `models/OpenDRAMmodelV1/` | Access/peri `.inc` cards + validation golden YAML |
| `data/literature/` | Literature roadmap for validation audits |
| `data/paper/` | Paper extraction inputs and `extracted_refs.yaml` |

Python packages (same repository):

| Package | Lane |
|---------|------|
| `src/bench/` | Device SPICE (`dram-device`) |
| `src/validation/` | Golden, paper, literature audits |
| `src/sense_amp/` | Read-path sense-amp |
| `src/ccell/` | Cell-capacitance roadmap |
| `src/pareto/` | Pareto retention/speed |
| `src/dram_benchmark/` | Suite orchestrator (`dram-bench`) |

Install once: `pip install -e ".[dev]"`.
