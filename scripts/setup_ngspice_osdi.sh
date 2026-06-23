#!/usr/bin/env bash
# Build or refresh ngspice BSIM-CMG OSDI library (bsimcmg.osdi).
#
# Requires: openvaf on PATH
# Optional: OPEN_DRAM_VA_MODELS_ROOT (default: third_party/VA-Models)
#
# Usage:
#   ./scripts/setup_ngspice_osdi.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-}"
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

VA_ROOT="${OPEN_DRAM_VA_MODELS_ROOT:-$REPO_ROOT/third_party/VA-Models}"
VA_SOURCE="$VA_ROOT/code/bsimcmg/vacode111/bsimcmg.va"
OSDI_CACHE="$REPO_ROOT/build/ngspice_osdi/bsimcmg.osdi"

if [[ -f "$OSDI_CACHE" ]]; then
  echo "ngspice OSDI already present: $OSDI_CACHE"
  exit 0
fi

if [[ ! -f "$VA_SOURCE" ]]; then
  echo ">>> Cloning VA-Models into $VA_ROOT"
  mkdir -p "$(dirname "$VA_ROOT")"
  git clone --depth 1 https://github.com/dwarning/VA-Models.git "$VA_ROOT"
fi

if ! command -v openvaf &>/dev/null; then
  echo "ERROR: openvaf not found on PATH (required to build bsimcmg.osdi)" >&2
  exit 1
fi

echo ">>> Building ngspice OSDI library"
"$PYTHON" -c "from bench.model_compat import ensure_ngspice_osdi; p = ensure_ngspice_osdi(); assert p is not None, 'OSDI build failed'; print(p)"
