#!/usr/bin/env bash
# Run the VCT_130 sample card through the device suite.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODEL_ROOT="$REPO_ROOT/models/samples/custom_vct_demo"
OUT="$REPO_ROOT/results/custom_demo"
GENERATE_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --generate-only) GENERATE_ONLY=1 ;;
    -h|--help)
      echo "Usage: $0 [--generate-only]"
      echo "  OPEN_DRAM_MODEL_ROOT=$MODEL_ROOT"
      echo "  dram-bench run --suite device --model VCT_130 --skip-golden"
      exit 0
      ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

cd "$REPO_ROOT"
export OPEN_DRAM_MODEL_ROOT="$MODEL_ROOT"

ARGS=(run --suite device --corner tt --model VCT_130 --skip-golden --output "$OUT")
if [[ "$GENERATE_ONLY" -eq 1 ]]; then
  ARGS+=(--generate-only)
fi

echo "Model root: $OPEN_DRAM_MODEL_ROOT"
echo "Output:     $OUT"
dram-bench "${ARGS[@]}"
echo "Wrote: $OUT/RESULTS.md"
echo "       $OUT/MANIFEST.json"
