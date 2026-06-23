#!/usr/bin/env bash
# OpenDRAMBench — Paper A1 full benchmark verification pipeline (self-contained)
#
# Usage:
#   ./run_experiments.sh                     # device suite @ tt (full: device+1T1C+mini-array)
#   SUITE=all ./run_experiments.sh           # full Paper A1 evidence bundle
#   SUITE=validation ./run_experiments.sh    # golden/literature/paper audit only
#   DEVICE_ONLY=1 ./run_experiments.sh       # skip 1T1C + mini-array
#   GENERATE_ONLY=1 ./run_experiments.sh     # deck generation only
#
# Requires: Python 3.10+, bundled models/OpenDRAMmodelV1
# Optional: ngspice (device), Spectre/HSPICE (sense-amp read-path SPICE)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-}"
SUITE="${SUITE:-device}"
CORNER="${CORNER:-tt}"
RESULTS_DIR="${RESULTS_DIR:-results}"
GENERATE_ONLY="${GENERATE_ONLY:-0}"
DEVICE_ONLY="${DEVICE_ONLY:-0}"
SIMULATOR="${OPEN_DRAM_SIMULATOR:-}"
SKIP_GOLDEN="${SKIP_GOLDEN:-0}"

if [[ -z "$PYTHON" ]]; then
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
      ver="$("$candidate" -c 'import sys; print(sys.version_info >= (3, 10))')"
      if [[ "$ver" == "True" ]]; then
        PYTHON="$candidate"
        break
      fi
    fi
  done
fi
if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python 3.10+ required" >&2
  exit 1
fi

if [[ ! -d "models/OpenDRAMmodelV1/models/access_tx" ]]; then
  echo "ERROR: Bundled model cards missing under models/OpenDRAMmodelV1/models/access_tx" >&2
  exit 1
fi

export OPEN_DRAM_MODEL_ROOT="$REPO_ROOT/models/OpenDRAMmodelV1/models/access_tx"
export OPEN_DRAM_CORNER_SOURCE="${OPEN_DRAM_CORNER_SOURCE:-local}"
export OPEN_DRAM_CORNER_REGISTRY="${OPEN_DRAM_CORNER_REGISTRY:-$REPO_ROOT/bench/registry/corner_registry.yaml}"

echo "=== OpenDRAMBench (Paper A1) ==="
echo "Python:     $("$PYTHON" --version)"
echo "Suite:      $SUITE"
echo "Corner:     $CORNER"
echo "Models:     $OPEN_DRAM_MODEL_ROOT"
echo "Engine:     $REPO_ROOT (bundled)"
echo "Results:    $RESULTS_DIR"
echo ""

echo ">>> Installing package"
"$PYTHON" -m pip install -q -e ".[dev]"

RUN_ARGS=(run --suite "$SUITE" --corner "$CORNER" --output "$RESULTS_DIR")
if [[ "$GENERATE_ONLY" == "1" ]]; then
  RUN_ARGS+=(--generate-only)
fi
if [[ "$DEVICE_ONLY" == "1" ]]; then
  RUN_ARGS+=(--device-only)
fi
if [[ -n "$SIMULATOR" ]]; then
  RUN_ARGS+=(--simulator "$SIMULATOR")
fi
if [[ "$SKIP_GOLDEN" == "1" ]]; then
  RUN_ARGS+=(--skip-golden)
fi

echo ">>> Benchmark"
"$PYTHON" -m dram_benchmark.cli "${RUN_ARGS[@]}"

echo ">>> Tests (offline)"
"$PYTHON" -m pytest -q -m "not integration and not ngspice and not spectre and not hspice"

echo ""
echo "Done."
echo "  Report: $RESULTS_DIR/RESULTS.md"
