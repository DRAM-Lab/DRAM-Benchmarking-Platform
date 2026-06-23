# Default SPICE Models

The platform uses OpenDRAMmodelV1 as the default model source.

## Access Transistor Models

Location: `models/OpenDRAMmodelV1/models/access_tx/`

| Model | Architecture | Description |
|-------|--------------|-------------|
| BCAT_125.inc | 6F² BCAT | Boundary-controlled access transistor |
| VCT_082.inc | 4F² VCT | Vertical channel transistor |
| VCT_091.inc | 4F² VCT | Vertical channel transistor |
| VCT_102.inc | 4F² VCT | Vertical channel transistor |
| VCT_125.inc | 4F² VCT | Vertical channel transistor |
| 3D_gaa_Si.inc | 3D GAA | Silicon gate-all-around |
| 3D_gaa_AOS.inc | 3D GAA | Amorphous oxide semiconductor |

## Periphery Models

Location: `models/OpenDRAMmodelV1/models/peri_tx/`

| Model | Architecture | Description |
|-------|--------------|-------------|
| ... | ... | ... |

## Usage

```bash
# Use default model (VCT_082.inc)
./scripts/run_experiments.sh

# Use specific model
./scripts/run_experiments.sh models/OpenDRAMmodelV1/models/access_tx/VCT_125.inc

# Multi-tool benchmark
./scripts/run_experiments.sh models/OpenDRAMmodelV1/models/access_tx/VCT_082.inc --tools ngspice,hspice
```

## Model Documentation

See `models/OpenDRAMmodelV1/README.md` for detailed model information.
