"""Access transistor model registry parsed from OpenDRAM ``.inc`` cards."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sense_amp.paths import resolve_model_root

READ_MODEL_IDS: tuple[str, ...] = (
    "VCT_082",
    "VCT_091",
    "VCT_102",
    "VCT_125",
    "BCAT_125",
    "3D_gaa_Si",
    "3D_gaa_AOS",
)

ACCESS_MODEL_IDS: tuple[str, ...] = READ_MODEL_IDS

_DEFAULT_VDD: dict[str, float] = {
    "3D_gaa_Si": 0.75,
    "3D_gaa_AOS": 0.75,
}

_FLOAT_RE = re.compile(r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")


@dataclass(frozen=True)
class AccessModel:
    """Metadata for one OpenDRAM access transistor model card."""

    model_id: str
    inc_path: Path
    architecture: str
    roadmap_label: str
    nominal_vdd: float
    length_m: float
    nfin: int
    fpitch_m: float
    bulkmod: int
    vsat: float

    @property
    def bulk_tied_to_source(self) -> bool:
        """True when bulk should be shorted to source per BSIM bulkmod."""
        return self.bulkmod == 0


def _parse_float_param(text: str, name: str) -> float | None:
    pattern = re.compile(rf"\b{re.escape(name)}\s*=\s*({_FLOAT_RE.pattern})", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return None
    return float(match.group(1))


def _parse_int_param(text: str, name: str) -> int | None:
    value = _parse_float_param(text, name)
    return int(value) if value is not None else None


def _architecture_from_id(model_id: str) -> str:
    if model_id.startswith("BCAT"):
        return "BCAT"
    if model_id.startswith("VCT"):
        return "VCT"
    if model_id.startswith("3D_gaa"):
        return "3D_GAA"
    return "unknown"


def _roadmap_label(model_id: str) -> str:
    if model_id == "BCAT_125":
        return "125"
    if model_id.startswith("VCT_"):
        return model_id.split("_", 1)[1]
    if model_id == "3D_gaa_Si":
        return "Si"
    if model_id == "3D_gaa_AOS":
        return "AOS"
    return model_id


def _parse_nominal_vdd(text: str, model_id: str) -> float:
    header = re.search(r"Nominal\s+VDD\s*=\s*([0-9.]+)\s*V?", text, re.IGNORECASE)
    if header:
        return float(header.group(1))
    if model_id in _DEFAULT_VDD:
        return _DEFAULT_VDD[model_id]
    raise ValueError(f"Cannot determine nominal Vdd for model {model_id}")


def load_access_model(model_id: str, model_root: Path | None = None) -> AccessModel:
    """Load metadata for a named access model.

    Args:
        model_id: Model identifier (e.g. ``VCT_082``).
        model_root: Optional override for ``.inc`` directory.

    Returns:
        Parsed :class:`AccessModel` instance.

    Raises:
        FileNotFoundError: If the model card file is missing.
        ValueError: If required parameters cannot be parsed.
    """
    root = model_root or resolve_model_root()
    inc_path = root / f"{model_id}.inc"
    if not inc_path.is_file():
        raise FileNotFoundError(f"Model card not found: {inc_path}")

    text = inc_path.read_text(encoding="utf-8", errors="replace")
    length_m = _parse_float_param(text, "l")
    nfin = _parse_int_param(text, "nfin")
    fpitch_m = _parse_float_param(text, "fpitch")
    bulkmod = _parse_int_param(text, "bulkmod")
    vsat = _parse_float_param(text, "vsat")

    missing = [
        name
        for name, val in [
            ("l", length_m),
            ("nfin", nfin),
            ("fpitch", fpitch_m),
            ("bulkmod", bulkmod),
            ("vsat", vsat),
        ]
        if val is None
    ]
    if missing:
        raise ValueError(f"Missing parameters {missing} in {inc_path}")

    return AccessModel(
        model_id=model_id,
        inc_path=inc_path,
        architecture=_architecture_from_id(model_id),
        roadmap_label=_roadmap_label(model_id),
        nominal_vdd=_parse_nominal_vdd(text, model_id),
        length_m=length_m,  # type: ignore[arg-type]
        nfin=nfin,  # type: ignore[arg-type]
        fpitch_m=fpitch_m,  # type: ignore[arg-type]
        bulkmod=bulkmod,  # type: ignore[arg-type]
        vsat=vsat,  # type: ignore[arg-type]
    )


def load_read_models(model_root: Path | None = None) -> dict[str, AccessModel]:
    """Load all models configured for the read-path benchmark.

    Returns:
        Mapping of model_id to :class:`AccessModel`.
    """
    return {mid: load_access_model(mid, model_root) for mid in READ_MODEL_IDS}
