# Golden reference metrics

Per-corner CSV snapshots for regression checks (±2% relative tolerance).

| Corner | Files |
|--------|-------|
| `tt`, `ff`, `ss`, `cold`, `hot` | `device_metrics.csv`, `cell_1t1c_metrics_20ff.csv`, `mini_array_metrics.csv` |

Refresh after a validated all-corner run:

```bash
./run_experiments.sh
# or force publish:
PUBLISH_GOLDEN=1 ./run_experiments.sh
```

Validate all corners:

```bash
dram-device validate-golden --input results --all-corners
```

Validate one corner:

```bash
dram-device validate-golden --input results/tt --corner tt
```
