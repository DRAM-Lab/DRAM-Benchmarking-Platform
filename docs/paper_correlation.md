# Paper Correlation (Part I/II vs Pinned SPICE)

Metrics transcribed from Open DRAM Model Part I/II papers and compared
to pinned TT SPICE extraction. Regenerate with `dram-validate paper`.

- **Extracted:** 2026-06-23T01:48:37Z
- **Docs root:** `/home/yongfu/proj/dram-lab/docs`

## Alignment matrix

| Model | Paper config | Metric | Paper | SPICE | Rel err | Mag | Notes |
|-------|--------------|--------|-------|-------|---------|-----|-------|
| BCAT_125 | `bcat_6f2_d1b` | Ion | 2.44 µA @ Vd=VDD | 3.0236e-07 | 87.6% | L | Large gap (88% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM |
| BCAT_125 | `bcat_6f2_d1b` | Ioff | <0.2 fA @ Vd=VDD | 6.1429e-14 | 30614.6% | N | Large gap (30615% rel. error) — expected when TCAD table Ion/Ioff differs from B |
| VCT_082 | `vct_4f2_d1b_dr12p5_case3` | Ion | 8.62 µA @ Vd=VDD (TCAD) | 9.2847e-07 | 89.2% | L | Large gap (89% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM |
| VCT_082 | `vct_4f2_d1b_dr12p5_case3` | Ioff | 0.00543 fA @ Vd=VDD | 3.7310e-12 | 68710578.1% | N | Large gap (68710578% rel. error) — expected when TCAD table Ion/Ioff differs fro |
| VCT_091 | `vct_4f2_d1b_dr12p5_case3` | Ion | 8.62 µA @ Vd=VDD (TCAD) | 9.7420e-07 | 88.7% | L | Large gap (89% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM |
| VCT_091 | `vct_4f2_d1b_dr12p5_case3` | Ioff | 0.00543 fA @ Vd=VDD | 3.8765e-12 | 71390430.9% | N | Large gap (71390431% rel. error) — expected when TCAD table Ion/Ioff differs fro |
| VCT_102 | `vct_4f2_d1b_dr12p5_case3` | Ion | 8.62 µA @ Vd=VDD (TCAD) | 1.0351e-06 | 88.0% | L | Large gap (88% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM |
| VCT_102 | `vct_4f2_d1b_dr12p5_case3` | Ioff | 0.00543 fA @ Vd=VDD | 4.0669e-12 | 74895882.9% | N | Large gap (74895883% rel. error) — expected when TCAD table Ion/Ioff differs fro |
| 3D_gaa_Si | `dram_3d_si` | Ion | 9.03 µA | 1.0407e-06 | 88.5% | L | Large gap (88% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM |
| 3D_gaa_Si | `dram_3d_si` | Ioff | 0.02 fA | 1.0108e-14 | 50440.3% | N | Large gap (50440% rel. error) — expected when TCAD table Ion/Ioff differs from B |
| 3D_gaa_AOS | `dram_3d_aos` | Ion | 10.4 µA | 1.8855e-06 | 81.9% | L | Large gap (82% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM |
| 3D_gaa_AOS | `dram_3d_aos` | Ioff | <0.02 fA | 8.4547e-11 | 422735173.5% | N | Large gap (422735174% rel. error) — expected when TCAD table Ion/Ioff differs fr |

## Extrapolation / metric-definition watchlist

- **BCAT_125** `Ion` — Large gap (88% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 2.44 µA @ Vd=VDD.
- **BCAT_125** `Ioff` — Large gap (30615% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. <0.2 fA @ Vd=V
- **VCT_082** `Ion` — Large gap (89% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 8.62 µA @ Vd=VDD 
- **VCT_082** `Ioff` — Large gap (68710578% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 0.00543 fA 
- **VCT_091** `Ion` — Large gap (89% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 8.62 µA @ Vd=VDD 
- **VCT_091** `Ioff` — Large gap (71390431% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 0.00543 fA 
- **VCT_102** `Ion` — Large gap (88% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 8.62 µA @ Vd=VDD 
- **VCT_102** `Ioff` — Large gap (74895883% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 0.00543 fA 
- **3D_gaa_Si** `Ion` — Large gap (88% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 9.03 µA. Paper Io
- **3D_gaa_Si** `Ioff` — Large gap (50440% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 0.02 fA. Paper
- **3D_gaa_AOS** `Ion` — Large gap (82% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. 10.4 µA. Paper Io
- **3D_gaa_AOS** `Ioff` — Large gap (422735174% rel. error) — expected when TCAD table Ion/Ioff differs from BSIM benchmark extraction. <0.02 fA. 

## Scoring legend

- **Mag H/M/L/N:** high / medium / low / no comparable SPICE column
- Paper Ion/Ioff are TCAD table values; benchmark uses BSIM card extraction
- Re-extract paper tables: `python scripts/extract_paper_refs.py`
