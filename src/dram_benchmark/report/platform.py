"""Platform-specific report header for OpenDRAMBench."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dram_benchmark.paths import model_bundle_revision, resolve_model_root


def prepend_platform_header(
    results_md: Path,
    *,
    suite: str,
    corner: str,
) -> None:
    """Prepend OpenDRAMBench positioning header to an existing RESULTS.md."""
    if not results_md.is_file():
        return

    body = results_md.read_text(encoding="utf-8")
    if body.startswith("# OpenDRAMBench"):
        return

    models = ", ".join(sorted(p.stem for p in resolve_model_root().glob("*.inc")))
    header = f"""# OpenDRAMBench — Platform Results

**Generated:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
**Suite:** {suite}
**Corner scope:** {corner}
**Model bundle:** OpenDRAMmodelV1 `{model_bundle_revision()}`
**Models:** {models}

Reproducible benchmark automation for Open DRAM model cards (Paper A1 positioning).
This platform extends the Open DRAM Model Part I/II artifacts with push-button reruns,
multi-tool comparison, validation, and provenance manifests.
See [benchmark_spec.md](../docs/benchmark_spec.md) for metric definitions.

---

"""
    results_md.write_text(header + body, encoding="utf-8")
