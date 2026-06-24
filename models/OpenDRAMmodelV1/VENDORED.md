# Vendored OpenDRAMmodelV1 bundle

This directory is a **vendored copy** of [MATRIX-PDK/OpenDRAMmodelV1](https://github.com/MATRIX-PDK/OpenDRAMmodelV1) at upstream snapshot `c53ccc9`. It is shipped in-tree with the DRAM Benchmarking Platform (no git submodule).

## Contents

| Path | Description |
|------|-------------|
| `models/access_tx/*.inc` | Access transistor BSIM-CMG cards |
| `models/peri_tx/*.inc` | Periphery transistor cards |
| `validation/golden/` | Paper-derived golden YAML (auto-generated) |
| `validation/RELEASE_MANIFEST.yaml` | Card hashes + extraction provenance |

## Refresh workflow

When upstream model cards change:

1. Copy updated `.inc` files from MATRIX-PDK/OpenDRAMmodelV1.
2. Re-run device benchmark and refresh `bench/validation/pinned/`.
3. Re-extract paper tables: `python scripts/extract_paper_refs.py --docs-root data/paper/docs`
4. Regenerate golden: `python scripts/publish_golden_from_paper.py`
5. Update `upstream_snapshot` in `validation/RELEASE_MANIFEST.yaml`.

## License

See `LICENSE` — MATRIX-PDK academic / non-commercial terms (Georgia Institute of Technology).
