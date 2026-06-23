# Literature Correlation and Gap Analysis

OpenDRAMmodelV1 metrics vs public DRAM roadmap summaries (ISSCC/IRPS/VLSI).
Regenerate with ``dram-validate correlate``.

## Alignment matrix

| Model | Metric | Open value | Literature band | Dir | Mag | Gap notes |
|-------|--------|------------|-----------------|-----|-----|-----------|
| BCAT_125 | fpitch | 42 | [38.0, 52.0] nm | Y | H | D0-class extrapolation if below literature min pitch |
| BCAT_125 | Vdd | 0.85 | [0.85, 1.0] V | Y | H | ULP nodes may sit below mainstream DRAM Vdd band |
| BCAT_125 | Ion | 3.024e-07 | directional (VCT Ion increases 082→125) | Y | M | No public Ion table — simulation projection only |
| VCT_082 | fpitch | 60 | [38.0, 52.0] nm | Y | L | D0-class extrapolation if below literature min pitch |
| VCT_082 | Vdd | 0.9 | [0.85, 1.0] V | Y | H | ULP nodes may sit below mainstream DRAM Vdd band |
| VCT_082 | Ion | 9.285e-07 | directional (VCT Ion increases 082→125) | Y | M | No public Ion table — simulation projection only |
| VCT_091 | fpitch | 60 | [38.0, 52.0] nm | Y | L | D0-class extrapolation if below literature min pitch |
| VCT_091 | Vdd | 0.9 | [0.85, 1.0] V | Y | H | ULP nodes may sit below mainstream DRAM Vdd band |
| VCT_091 | Ion | 9.742e-07 | directional (VCT Ion increases 082→125) | Y | M | No public Ion table — simulation projection only |
| VCT_102 | fpitch | 60 | [38.0, 52.0] nm | Y | L | D0-class extrapolation if below literature min pitch |
| VCT_102 | Vdd | 0.9 | [0.85, 1.0] V | Y | H | ULP nodes may sit below mainstream DRAM Vdd band |
| VCT_102 | Ion | 1.035e-06 | directional (VCT Ion increases 082→125) | Y | M | No public Ion table — simulation projection only |
| VCT_125 | fpitch | 60 | [38.0, 52.0] nm | Y | L | D0-class extrapolation if below literature min pitch |
| VCT_125 | Vdd | 0.9 | [0.85, 1.0] V | Y | H | ULP nodes may sit below mainstream DRAM Vdd band |
| VCT_125 | Ion | 1.406e-06 | directional (VCT Ion increases 082→125) | Y | M | No public Ion table — simulation projection only |
| 3D_gaa_Si | fpitch | 22 | [38.0, 52.0] nm | Y | L | D0-class extrapolation if below literature min pitch |
| 3D_gaa_Si | Vdd | 0.75 | [0.85, 1.0] V | Y | L | ULP nodes may sit below mainstream DRAM Vdd band |
| 3D_gaa_Si | Ion | 1.041e-06 | directional (VCT Ion increases 082→125) | Y | M | No public Ion table — simulation projection only |
| 3D_gaa_AOS | fpitch | 60 | [38.0, 52.0] nm | Y | L | D0-class extrapolation if below literature min pitch |
| 3D_gaa_AOS | Vdd | 0.75 | [0.85, 1.0] V | Y | L | ULP nodes may sit below mainstream DRAM Vdd band |
| 3D_gaa_AOS | Ion | 1.885e-06 | directional (VCT Ion increases 082→125) | Y | M | No public Ion table — simulation projection only |

## Extrapolation watchlist

- **VCT_082** — magnitude outside literature band or low-confidence projection
- **VCT_091** — magnitude outside literature band or low-confidence projection
- **VCT_102** — magnitude outside literature band or low-confidence projection
- **VCT_125** — magnitude outside literature band or low-confidence projection
- **3D_gaa_Si** — magnitude outside literature band or low-confidence projection
- **3D_gaa_AOS** — magnitude outside literature band or low-confidence projection

## Scoring legend

- **Dir Y/N:** directional trend matches public shrink / Vdd reduction narrative
- **Mag H/M/L:** high / medium / low magnitude alignment vs literature envelope