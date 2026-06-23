"""Spectre-compatible model card patches for OpenDRAM ``.inc`` files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sense_amp.models import AccessModel
from sense_amp.simulator import SimulatorBackend

_SPECTRE_BSIM_VERSION = "105.03"
_VERSION_112_RE = re.compile(r"(\+version\s*=\s*)112(?:\.0\.0)?\b", re.IGNORECASE)


def needs_spectre_patch(text: str) -> bool:
    """Return True if the card uses a BSIM-CMG version unsupported by Spectre."""
    return bool(_VERSION_112_RE.search(text))


def patch_inc_text_for_spectre(text: str) -> str:
    """Rewrite BSIM-CMG version fields for Spectre compatibility."""
    return _VERSION_112_RE.sub(rf"\g<1>{_SPECTRE_BSIM_VERSION}", text)


def spectre_compat_inc_path(
    model: AccessModel,
    cache_dir: Path | None = None,
) -> Path:
    """Return a Spectre-runnable ``.inc`` path, applying patches and caching if needed."""
    source = model.inc_path
    text = source.read_text(encoding="utf-8", errors="replace")
    if not needs_spectre_patch(text):
        return source

    cache_root = cache_dir or (Path(__file__).resolve().parents[2] / "build" / "spectre_compat")
    cache_root.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    patched_path = cache_root / f"{model.model_id}_spectre_{digest}.inc"
    if patched_path.is_file():
        return patched_path

    patched = patch_inc_text_for_spectre(text)
    header = (
        f"* Spectre compatibility patch for {model.model_id}\n"
        f"* BSIM-CMG version 112.x -> {_SPECTRE_BSIM_VERSION} (Spectre 24.1)\n"
        f"* Source: {source}\n"
    )
    patched_path.write_text(header + patched, encoding="utf-8")
    return patched_path


def resolve_inc_path(
    model: AccessModel,
    backend: SimulatorBackend,
    cache_dir: Path | None = None,
) -> Path:
    """Select the model card path appropriate for the target simulator."""
    if backend is SimulatorBackend.SPECTRE:
        return spectre_compat_inc_path(model, cache_dir)
    return model.inc_path
