"""Model card parameter parsing and hashing."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from validation.paths import OPEN_DRAMMODEL_V1_ROOT, resolve_model_inc

_FLOAT_RE = re.compile(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")
_PARAM_RE = re.compile(
    rf"^\s*\+?({re.escape('')}|)(\w+)\s*=\s*({_FLOAT_RE.pattern})",
    re.IGNORECASE,
)

# Parameters prioritized for local/global sensitivity screening.
SENSITIVITY_CANDIDATES: tuple[str, ...] = (
    "phig",
    "dvt0",
    "dvt1",
    "u0",
    "vsat",
    "rdsw",
    "agidl",
    "cdsc",
    "cdscd",
    "cit",
    "eot",
    "tfin",
    "nbody",
    "lint",
    "l",
    "nfin",
    "fpitch",
    "vth0",
    "k1",
    "eta0",
)


def parse_model_params(inc_path: Path, model_name: str | None = None) -> dict[str, float]:
    """Parse scalar ``.model`` parameters from an HSPICE card.

    Args:
        inc_path: Path to ``.inc`` model card.
        model_name: Optional ``.model`` identifier to scope parsing (e.g. ``tnmos``).

    Returns:
        Mapping of parameter name to float value.
    """
    text = inc_path.read_text(encoding="utf-8", errors="replace")
    params: dict[str, float] = {}
    active = model_name is None

    for line in text.splitlines():
        model_decl = re.search(r"\.model\s+(\w+)", line, re.IGNORECASE)
        if model_decl:
            active = model_name is None or model_decl.group(1).lower() == model_name.lower()
            continue
        if not active:
            continue
        for match in re.finditer(rf"\b([a-zA-Z_][\w]*)\s*=\s*({_FLOAT_RE.pattern})", line):
            name = match.group(1).lower()
            if name in {"option", "model", "version", "level"}:
                continue
            params[name] = float(match.group(2))
    return params


def parse_card_metrics(model_id: str) -> dict[str, float]:
    """Extract validation metrics directly from a model card.

    Args:
        model_id: Model identifier.

    Returns:
        Card-level metrics for golden validation.
    """
    inc_path = resolve_model_inc(model_id)
    scope = "tnmos" if model_id == "hv_peri_28_32" else None
    params = parse_model_params(inc_path, model_name=scope)
    text = inc_path.read_text(encoding="utf-8", errors="replace")
    metrics: dict[str, float] = {}

    header = re.search(r"Nominal\s+VDD\s*=\s*([0-9.]+)\s*V?", text, re.IGNORECASE)
    if header:
        metrics["nominal_vdd"] = float(header.group(1))
    elif re.search(r"nominal\s+Vdd\s*=\s*([0-9.]+)\s*V?", text, re.IGNORECASE):
        m = re.search(r"nominal\s+Vdd\s*=\s*([0-9.]+)\s*V?", text, re.IGNORECASE)
        if m:
            metrics["nominal_vdd"] = float(m.group(1))

    for key in ("vth0", "rdsw", "u0", "vsat", "fpitch", "l", "nfin"):
        if key in params:
            metrics[key] = params[key]
    return metrics


def file_sha256(path: Path) -> str:
    """Return SHA-256 hex digest for a file."""
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def model_bundle_fingerprint(model_root: Path | None = None) -> str:
    """Return a short content hash for all bundled ``.inc`` model cards.

    Used when models are vendored in-tree (no git submodule).
    """
    root = model_root or OPEN_DRAMMODEL_V1_ROOT
    models_dir = root / "models"
    if not models_dir.is_dir():
        return "unknown"
    digest = hashlib.sha256()
    for path in sorted(models_dir.rglob("*.inc")):
        digest.update(path.relative_to(models_dir).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def model_git_sha(model_root: Path | None = None) -> str | None:
    """Return git commit SHA for the model bundle when available.

    Falls back to :func:`model_bundle_fingerprint` for vendored copies.
    """
    root = model_root or OPEN_DRAMMODEL_V1_ROOT
    git_path = root / ".git"
    if git_path.exists():
        try:
            out = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            return out.strip() or None
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    fp = model_bundle_fingerprint(root)
    return fp if fp != "unknown" else None


def top_sensitivity_params(
    model_id: str,
    *,
    limit: int = 20,
) -> list[tuple[str, float]]:
    """Return ranked sensitivity parameter candidates from a model card.

    Args:
        model_id: Model identifier.
        limit: Maximum parameters to return.

    Returns:
        List of ``(name, nominal_value)`` in default sensitivity priority order.
    """
    params = parse_model_params(resolve_model_inc(model_id))
    ordered: list[tuple[str, float]] = []
    for name in SENSITIVITY_CANDIDATES:
        if name in params:
            ordered.append((name, params[name]))
    for name, value in sorted(params.items()):
        if name not in {n for n, _ in ordered}:
            ordered.append((name, value))
    return ordered[:limit]
