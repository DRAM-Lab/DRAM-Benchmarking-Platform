#!/usr/bin/env bash
# Remove generated benchmark artifacts (keeps vendored models/OpenDRAMmodelV1).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
rm -rf results build .pytest_cache
find . -type d -name __pycache__ -prune -exec rm -rf {} +
# Validation lane may refresh these under docs/; remove for a clean tree
rm -f docs/literature_correlation.md docs/paper_correlation.md docs/model_provenance.md CONTRIBUTING_MODELS.md
echo "Cleaned generated artifacts under $SCRIPT_DIR"
