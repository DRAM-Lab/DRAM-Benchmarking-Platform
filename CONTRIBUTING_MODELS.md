# Contributing OpenDRAM Model Cards

Model pull requests must pass the OpenDRAM validation harness before merge.

## PR checklist

- [ ] Golden YAML regenerated under `models/OpenDRAMmodelV1/validation/golden/<model>.yaml`
- [ ] Confidence tier (H/M/L) assigned per metric with literature citation
- [ ] `pytest` validation suite passes locally
- [ ] Pinned metrics refreshed if SPICE extraction changed (`bench/validation/pinned/`)
- [ ] `docs/model_provenance.md` regenerated (`dram-validate provenance`)
- [ ] Directional trends documented for roadmap-scaling families (VCT, etc.)
- [ ] Model bundle fingerprint noted in `validation/RELEASE_MANIFEST.yaml` when rebasing cards

## Commands

```bash
pip install -e ".[dev]"
python scripts/extract_paper_refs.py --docs-root ~/proj/dram-lab/docs
python scripts/publish_golden_from_paper.py
pytest                          # offline + structure checks
dram-validate check         # golden spice bands vs pinned metrics
dram-validate paper         # paper-transcribed metrics vs pinned SPICE
dram-validate provenance    # refresh provenance doc
```

## Tolerance policy

| Confidence | Numeric band |
|------------|--------------|
| High | ±5% if paper states value; ±10% if inferred |
| Medium | ±20% or min/max envelope from benchmark |
| Low | Directional only (increasing/decreasing across nodes) |

See the tolerance policy table above for band definitions.
