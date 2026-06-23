# Multi-simulator cross-check notes

Spectre is the **reference backend** for golden regression and relative-difference tables in `results/simulator_compare/`. HSPICE and ngspice are alternate backends using the same netlist topology and measure intent, with backend-specific syntax and post-processing where native measures are unsupported.

This document explains **expected** disagreements that are **not** pipeline failures. After the v0.1.0 HSPICE/ngspice extraction fixes, missing CSV fields and aborted decks should be rare; large relative differences usually trace to model porting or reference-definition choices.

## Summary table (typical @ tt)

| Model / area | Metric | HSPICE vs Spectre | ngspice vs Spectre | Root cause |
|--------------|--------|-------------------|--------------------|------------|
| BCAT–VCT (except 3D_gaa_Si) | `ron_ohm` | **Match** (ratio extraction) | ~40–60% lower Ron | ngspice OSDI higher Ion → lower V/I Ron |
| `3D_gaa_Si` | `ion_a`, `ron_ohm` | HSPICE ≈ ngspice; both **~40–71% above Spectre** | Same as HSPICE | Spectre BSIM **105.03** patch; HSPICE/ngspice use native **112.0.0** card |
| All (ngspice) | `cgg_f`, `cgd_f` | HSPICE transient-step caps (moderate gap) | Often **much lower** | OSDI VA model + stripped HSPICE-only cap flags |
| `BCAT_125` | `i_hold_a` (1T1C) | Close | **~100× higher** | ngspice OSDI subthreshold leakage in hold window |
| Mini-array | `t_bl_settle_s` | ~15–20% | ~35–40% | Transient resolution + ngspice BL settling trajectory |
| Mini-array | `i_bl_leak_a` | ~10–20% | Moderate | Same OSDI / OP differences |

## Backend-specific behavior

### Spectre (reference)

- Primary validated simulator; golden CSVs target Spectre outputs.
- `3D_gaa_Si.inc` uses BSIM-CMG `version = 112.0.0` in the upstream card; Spectre 24.1 cannot load 112.x. The benchmark auto-patches to **105.03** (cached under `build/spectre_compat/`). **Do not compare Spectre Ion/Ron for this model directly to HSPICE without noting the version downgrade.**

### HSPICE

- Loads native HSPICE level-72 BSIM-CMG cards (including 112.x for 3D GAA Si).
- Device decks avoid unsupported `.measure` syntax; Ron/Cgg/GIDL are recovered from `.lis` post-processing.
- Ron uses `|Vd/Ids|` at peak |Ids| (same definition as Spectre `param='abs(v(d)/i(Vd))'`).
- AC capacitance uses transient voltage steps; Cgg/Cgd from integrated gate/drain charge (may differ slightly from Spectre measures).

### ngspice (experimental OSDI)

- Requires `openvaf` and VA-Models BSIM-CMG Verilog-A → `build/ngspice_osdi/bsimcmg.osdi`.
- HSPICE cards are rewritten to `bsimcmg_va` with unsupported parameters stripped (e.g. `version`, `capmod`, `gidlmod`).
- Mini-array decks include **`Vs s 0 0`** so the shared source node has a ground reference (required for correct OP/precharge).
- Ion is often **higher** than Spectre on BCAT/VCT; Ron follows `V/I` and is therefore **lower**.
- `cgg_f` from transient `qg` integration is often much smaller than Spectre.
- Treat ngspice as **directional** for cross-architecture ranking, not bit-exact agreement with Spectre.

## Per-model notes

### `3D_gaa_Si`

- **Expected:** HSPICE and ngspice agree on Ion (~1.78 µA @ tt); Spectre ~1.04 µA (~−42% vs HSPICE).
- **Reason:** Spectre compatibility patch (112 → 105.03), not a failed simulation.
- **Ron:** HSPICE/ngspice Ron tracks their higher Ion; Spectre Ron is higher accordingly.

### `BCAT_125`

- **1T1C `i_hold_a`:** ngspice can report ~10⁻¹¹ A vs Spectre ~10⁻¹³ A in the hold window while read/write timings remain aligned.
- **Device Ion:** ngspice OSDI ~1.5–1.8× Spectre Ion is common; golden regression is Spectre-only.

### VCT family (`VCT_082` … `VCT_125`)

- HSPICE Ion/Ron generally match Spectre after resistive Ron extraction.
- ngspice Ion ~1.5–1.8× Spectre; mini-array `t_bl_settle` populated after source-ground fix.

### `3D_gaa_AOS`

- ngspice Ion can exceed Spectre by a large factor (OSDI + model card); HSPICE usually tracks Spectre on Ron.

## Artifacts

| Path | Content |
|------|---------|
| `results/simulator_compare/{corner}/SIMULATOR_COMPARE.md` | Per-corner max \|rel diff\| + flagged outliers |
| `results/simulator_compare/{corner}/device_metrics_wide.csv` | Side-by-side metrics |
| `results/simulator_compare/{corner}/device_metrics_rel_diff.csv` | Relative differences vs Spectre |
| `results/simulator_compare/{corner}/known_outliers.csv` | Rows exceeding thresholds or on the known-outlier list |

## Regenerating comparison tables

After editing metrics or re-running a subset of simulators:

```bash
# One corner
dram-device compare-simulators --input results --corner tt

# All corners
dram-device compare-simulators --input results --all-corners
```

## References

- [benchmark_spec.md](benchmark_spec.md) — metric definitions and Spectre patch note
- [README.md](../README.md) — tooling and scope
