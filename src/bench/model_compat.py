"""Spectre-compatible model card patches for OpenDRAM `.inc` files."""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
import subprocess
from pathlib import Path

from bench.models import AccessModel
from bench.paths import PROJECT_ROOT
from bench.simulator import SimulatorBackend, find_ngspice

logger = logging.getLogger(__name__)

# Spectre 24.1 supports BSIM-CMG 105.x; 3D_gaa_Si ships with 112.0.0 (HSPICE-only).
_SPECTRE_BSIM_VERSION = "105.03"
_VERSION_112_RE = re.compile(r"(\+version\s*=\s*)112(?:\.0\.0)?\b", re.IGNORECASE)
_MODEL_HEADER_RE = re.compile(r"\.model\s+nfet\s+nmos\s+level\s*=\s*72", re.IGNORECASE)
_NGSPICE_UNSUPPORTED_PARAMS = frozenset(
    {
        "lmin",
        "lmax",
        "version",
        "coremod",
        "capmod",
        "nseg",
        "ldg",
        "qmtceniv",
        "prwg",
        "pclmgcv",
        "vasat",
        "vasatcv",
        "nigc",
        "alphaii",
    }
)


def needs_spectre_patch(text: str) -> bool:
    """Return True if the card uses a BSIM-CMG version unsupported by Spectre."""
    return bool(_VERSION_112_RE.search(text))


def patch_inc_text_for_spectre(text: str) -> str:
    """Rewrite BSIM-CMG version fields for Spectre compatibility.

    Args:
        text: Original HSPICE model card contents.

    Returns:
        Patched card text (unchanged if no patch required).
    """
    return _VERSION_112_RE.sub(rf"\g<1>{_SPECTRE_BSIM_VERSION}", text)


def spectre_compat_inc_path(
    model: AccessModel,
    cache_dir: Path | None = None,
) -> Path:
    """Return a Spectre-runnable `.inc` path, applying patches and caching if needed.

    Args:
        model: Access model metadata.
        cache_dir: Directory for cached patched cards (default: ``build/spectre_compat``).

    Returns:
        Path to include in SPICE netlists for Spectre runs.
    """
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


def _ngspice_osdi_cache_dir(cache_dir: Path | None = None) -> Path:
    root = cache_dir or (PROJECT_ROOT / "build" / "ngspice_osdi")
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_ngspice_osdi(cache_dir: Path | None = None) -> Path | None:
    """Return path to BSIM-CMG OSDI library for ngspice, building it when possible.

    Requires ``openvaf`` on PATH and the VA-Models BSIM-CMG Verilog-A source tree
  under ``third_party/VA-Models`` or ``OPEN_DRAM_VA_MODELS_ROOT``.
    """
    cache_root = _ngspice_osdi_cache_dir(cache_dir)
    osdi_path = cache_root / "bsimcmg.osdi"
    if osdi_path.is_file():
        return osdi_path

    va_root = Path(
        __import__("os").environ.get(
            "OPEN_DRAM_VA_MODELS_ROOT",
            str(PROJECT_ROOT / "third_party" / "VA-Models"),
        )
    )
    va_source = va_root / "code" / "bsimcmg" / "vacode111" / "bsimcmg.va"
    if not va_source.is_file():
        logger.warning(
            "ngspice OSDI source not found at %s (set OPEN_DRAM_VA_MODELS_ROOT)",
            va_source,
        )
        return None

    openvaf = shutil.which("openvaf")
    if openvaf is None:
        logger.warning("openvaf not found; cannot build ngspice BSIM-CMG OSDI library")
        return None

    build_dir = cache_root / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    staged_va = build_dir / "bsimcmg.va"
    shutil.copy2(va_source, staged_va)
    for include_name in (
        "constants.vams",
        "disciplines.vams",
        "bsimcmg_macros.include",
        "bsimcmg_variables.include",
        "bsimcmg_parameters.include",
        "bsimcmg_noise.include",
        "bsimcmg_checking.include",
        "bsimcmg_initialization.include",
        "bsimcmg_body.include",
    ):
        src = va_source.parent / include_name
        if src.is_file():
            shutil.copy2(src, build_dir / include_name)

    proc = subprocess.run(
        [openvaf, "bsimcmg.va"],
        cwd=build_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    built = build_dir / "bsimcmg.osdi"
    if proc.returncode != 0 or not built.is_file():
        logger.warning("openvaf failed to build BSIM-CMG OSDI: %s", proc.stderr[-500:])
        return None
    shutil.copy2(built, osdi_path)
    return osdi_path


def _strip_ngspice_unsupported_params(text: str) -> str:
    for name in _NGSPICE_UNSUPPORTED_PARAMS:
        text = re.sub(rf"\b{name}\s*=\s*[^\s+]+", "", text, flags=re.IGNORECASE)
    return text


def _upcase_spice_params(text: str) -> str:
    return re.sub(
        r"(?<![A-Za-z0-9_])([a-z][a-z0-9_]*)(\s*=)",
        lambda match: match.group(1).upper() + match.group(2),
        text,
    )


def patch_inc_text_for_ngspice(text: str) -> str:
    """Rewrite HSPICE level-72 cards for ngspice OSDI BSIM-CMG (experimental)."""
    text = re.sub(r"^\.option.*\n", "", text, flags=re.MULTILINE)
    text = _MODEL_HEADER_RE.sub(".model nfet bsimcmg_va\n+ TYPE = 1", text)
    text = _strip_ngspice_unsupported_params(text)
    return _upcase_spice_params(text)


def ngspice_compat_inc_path(
    model: AccessModel,
    cache_dir: Path | None = None,
) -> Path:
    """Return cached ngspice OSDI-compatible `.inc` for a model card."""
    source = model.inc_path
    text = source.read_text(encoding="utf-8", errors="replace")
    cache_root = _ngspice_osdi_cache_dir(cache_dir) / "inc_cache"
    cache_root.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    patched_path = cache_root / f"{model.model_id}_ngspice_{digest}.inc"
    if patched_path.is_file():
        return patched_path

    patched = patch_inc_text_for_ngspice(text)
    header = (
        f"* ngspice OSDI compatibility patch for {model.model_id}\n"
        f"* HSPICE level 72 -> bsimcmg_va (experimental)\n"
        f"* Source: {source}\n"
    )
    patched_path.write_text(header + patched, encoding="utf-8")
    return patched_path


def ngspice_deck_footer(cache_dir: Path | None = None) -> str:
    """Append ngspice ``.control`` block to load OSDI before netlist resolution."""
    osdi = ensure_ngspice_osdi(cache_dir)
    if osdi is None:
        return ""
    return f"""
.control
pre_osdi {osdi.resolve().as_posix()}
.endc
"""


def finalize_ngspice_deck(deck_text: str, cache_dir: Path | None = None) -> str:
    """Insert ngspice OSDI control block before the final ``.end``."""
    footer = ngspice_deck_footer(cache_dir)
    if not footer:
        return deck_text
    if deck_text.rstrip().endswith(".end"):
        body, _ = deck_text.rstrip().rsplit(".end", 1)
        return body + footer + ".end\n"
    return deck_text + footer


def resolve_inc_path(
    model: AccessModel,
    backend: SimulatorBackend,
    cache_dir: Path | None = None,
) -> Path:
    """Select the model card path appropriate for the target simulator.

    Args:
        model: Access model metadata.
        backend: Target simulator.
        cache_dir: Optional cache directory for patched cards.

    Returns:
        Path to `.include` in generated netlists.
    """
    if backend is SimulatorBackend.SPECTRE:
        return spectre_compat_inc_path(model, cache_dir)
    if backend is SimulatorBackend.NGSPICE:
        return ngspice_compat_inc_path(model, cache_dir)
    return model.inc_path
