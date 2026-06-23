"""Orchestration for read-path SPICE sweeps and signal extraction."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from sense_amp.conditions import load_corners, resolve_conditions
from sense_amp.extract.transient import dv_key_for_time_ns, merge_signal_metrics
from sense_amp.models import READ_MODEL_IDS, load_access_model
from sense_amp.netlist.coupling_read import write_coupling_decks
from sense_amp.netlist.read_column import write_read_column_decks
from sense_amp.paths import load_read_path_config
from sense_amp.simulator import SimulatorBackend, run_simulation

logger = logging.getLogger(__name__)

_MODEL_ID_PATTERN = r"(?:VCT_\d+|BCAT_\d+|3D_gaa_(?:Si|AOS))"
_READ_DECK_RE = re.compile(
    rf"^(?P<model>{_MODEL_ID_PATTERN})_(?P<corner>[a-z]+)_read_(?P<ccell>\d+)ff_vbl(?P<vbl>\d+)$",
    re.IGNORECASE,
)
_COUPLE_DECK_RE = re.compile(
    rf"^(?P<model>{_MODEL_ID_PATTERN})_(?P<corner>[a-z]+)_couple_(?P<ccell>\d+)ff_k(?P<k>\d+)$",
    re.IGNORECASE,
)


def _parse_deck_metadata(deck_path: Path) -> dict[str, str | float]:
    """Extract model, corner, Ccell, and VBL tags from deck filename.

    Expected patterns:
        ``{MODEL}_{corner}_read_{ccell}ff_vbl{pre}`` — e.g. ``VCT_082_tt_read_10ff_vbl40``
        ``{MODEL}_{corner}_couple_{ccell}ff_k{kk}`` — e.g. ``VCT_082_tt_couple_20ff_k05``

    Args:
        deck_path: Path to a generated ``.sp`` deck.

    Returns:
        Parsed metadata fields.

    Raises:
        ValueError: If the filename does not match a known deck pattern.
    """
    stem = deck_path.stem
    read_match = _READ_DECK_RE.match(stem)
    if read_match:
        return {
            "model_id": read_match.group("model"),
            "corner": read_match.group("corner"),
            "ccell_ff": float(read_match.group("ccell")),
            "vbl_pre_fraction": float(read_match.group("vbl")) / 100.0,
        }

    couple_match = _COUPLE_DECK_RE.match(stem)
    if couple_match:
        return {
            "model_id": couple_match.group("model"),
            "corner": couple_match.group("corner"),
            "ccell_ff": float(couple_match.group("ccell")),
            "k_couple": float(couple_match.group("k")) / 100.0,
        }

    msg = f"Cannot parse deck metadata from filename: {deck_path.name}"
    raise ValueError(msg)


def generate_decks(
    output_dir: Path,
    *,
    corner_name: str = "tt",
    model_ids: list[str] | None = None,
    include_coupling: bool = False,
    backend: str | None = None,
    config: dict | None = None,
) -> list[Path]:
    """Generate read-path SPICE decks for selected models.

    Args:
        output_dir: Root output directory for generated decks.
        corner_name: Simulation corner name.
        model_ids: Optional subset of read models.
        include_coupling: When True, also emit multi-BL coupling decks.
        backend: Simulator backend override.
        config: Optional read-path configuration.

    Returns:
        List of generated deck paths.
    """
    cfg = config or load_read_path_config()
    corners = load_corners(cfg)
    corner = corners[corner_name]
    models = model_ids or list(cfg.get("read_models", READ_MODEL_IDS))
    ccell_values = [float(v) for v in cfg["ccell_values_ff"]]
    vbl_fractions = [float(v) for v in cfg["vbl_pre_fractions"]]
    resolved_backend = SimulatorBackend(backend) if backend else None

    deck_paths: list[Path] = []
    deck_root = output_dir / "decks" / corner_name
    for model_id in models:
        model = load_access_model(model_id)
        for vbl_frac in vbl_fractions:
            conditions = resolve_conditions(model, corner, vbl_pre_fraction=vbl_frac)
            model_dir = deck_root / model_id
            paths = write_read_column_decks(
                model_dir,
                conditions,
                ccell_values,
                resolved_backend,
                config=cfg,
            )
            deck_paths.extend(paths.values())

            if include_coupling:
                k_values = [float(v) for v in cfg.get("coupling", {}).get("k_couple_values", [])]
                ref_ccell = 20.0 if 20.0 in ccell_values else ccell_values[0]
                couple_paths = write_coupling_decks(
                    model_dir,
                    conditions,
                    ref_ccell,
                    k_values,
                    resolved_backend,
                    config=cfg,
                )
                deck_paths.extend(couple_paths.values())
    return deck_paths


def run_read_signal_sweep(
    deck_dir: Path,
    *,
    backend: str | None = None,
    config: dict | None = None,
    simulate: bool = True,
) -> pd.DataFrame:
    """Run or parse read-column decks and return ΔV_BL metrics.

    Args:
        deck_dir: Directory containing ``.sp`` decks (possibly nested by model).
        backend: Simulator backend override.
        config: Optional read-path configuration.
        simulate: When False, only parse existing artifacts.

    Returns:
        DataFrame with per-deck signal samples and metadata.
    """
    cfg = config or load_read_path_config()
    sample_times_ns = [float(t) for t in cfg["read_timing"]["sample_times_ns"]]
    rows: list[dict[str, float | str]] = []

    for deck_path in sorted(deck_dir.rglob("*.sp")):
        if "couple_" in deck_path.name:
            continue
        meta = _parse_deck_metadata(deck_path)
        if simulate:
            result = run_simulation(deck_path, backend=backend)
            if result.returncode != 0:
                logger.warning("Simulation failed for %s (rc=%s)", deck_path, result.returncode)
        else:
            from sense_amp.simulator import load_simulation_result

            result = load_simulation_result(deck_path, backend=backend)

        measures = merge_signal_metrics(result.measures, result.print_path, sample_times_ns)
        row: dict[str, float | str] = {
            "deck": deck_path.name,
            "model_id": str(meta["model_id"]),
            "corner": str(meta["corner"]),
            "ccell_ff": float(meta.get("ccell_ff", 20.0)),
            "vbl_pre_fraction": float(meta.get("vbl_pre_fraction", 0.5)),
        }
        for t_ns in sample_times_ns:
            key = dv_key_for_time_ns(t_ns)
            row[key] = float(measures.get(key, float("nan")))
        rows.append(row)

    return pd.DataFrame(rows)


def run_coupling_sweep(
    deck_dir: Path,
    *,
    backend: str | None = None,
    config: dict | None = None,
    simulate: bool = True,
) -> pd.DataFrame:
    """Run or parse coupling decks and return victim ΔV_BL metrics."""
    cfg = config or load_read_path_config()
    sample_times_ns = [float(t) for t in cfg["read_timing"]["sample_times_ns"]]
    rows: list[dict[str, float | str]] = []

    for deck_path in sorted(deck_dir.rglob("*couple_*.sp")):
        meta = _parse_deck_metadata(deck_path)
        if simulate:
            result = run_simulation(deck_path, backend=backend)
            if result.returncode != 0:
                logger.warning("Coupling sim failed for %s", deck_path)
        else:
            from sense_amp.simulator import load_simulation_result

            result = load_simulation_result(deck_path, backend=backend)

        measures = merge_signal_metrics(result.measures, result.print_path, sample_times_ns)
        row: dict[str, float | str] = {
            "deck": deck_path.name,
            "model_id": str(meta["model_id"]),
            "corner": str(meta["corner"]),
            "ccell_ff": float(meta.get("ccell_ff", 20.0)),
            "k_couple": float(meta.get("k_couple", 0.0)),
        }
        for t_ns in sample_times_ns:
            key = dv_key_for_time_ns(t_ns)
            row[key] = float(measures.get(key, float("nan")))
        rows.append(row)

    return pd.DataFrame(rows)


def run_full_read_path(
    output_dir: Path,
    *,
    corner_name: str = "tt",
    model_ids: list[str] | None = None,
    include_coupling: bool = True,
    backend: str | None = None,
    generate_only: bool = False,
    config: dict | None = None,
) -> dict[str, Path]:
    """Generate decks, simulate, and export read-path CSV tables.

    Returns:
        Mapping of artifact name to output path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = config or load_read_path_config()
    generate_decks(
        output_dir,
        corner_name=corner_name,
        model_ids=model_ids,
        include_coupling=include_coupling,
        backend=backend,
        config=cfg,
    )
    deck_dir = output_dir / "decks" / corner_name
    artifacts: dict[str, Path] = {}

    if generate_only:
        return artifacts

    signal_df = run_read_signal_sweep(deck_dir, backend=backend, config=cfg, simulate=True)
    signal_path = output_dir / f"read_signal_{corner_name}.csv"
    signal_df.to_csv(signal_path, index=False)
    artifacts["read_signal"] = signal_path

    if include_coupling:
        coupling_df = run_coupling_sweep(deck_dir, backend=backend, config=cfg, simulate=True)
        coupling_path = output_dir / f"coupling_signal_{corner_name}.csv"
        coupling_df.to_csv(coupling_path, index=False)
        artifacts["coupling_signal"] = coupling_path

    return artifacts
