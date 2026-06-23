"""Cross-simulator metric comparison for multi-backend benchmark runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from bench.paths import PROJECT_ROOT
from bench.simulator import SimulatorBackend, available_backends

logger = logging.getLogger(__name__)

_CROSS_CHECK_DOC = PROJECT_ROOT / "docs" / "simulator_cross_check.md"

# Relative-difference thresholds for automatic outlier flagging (vs Spectre).
_REL_DIFF_FLAG_THRESHOLD = 0.35


@dataclass(frozen=True)
class KnownCrossSimulatorNote:
    """Documented expected disagreement (not a pipeline failure)."""

    models: tuple[str, ...]
    metrics: tuple[str, ...]
    backends: tuple[str, ...]
    reason: str
    reference: str = SimulatorBackend.SPECTRE.value


KNOWN_CROSS_SIMULATOR_NOTES: tuple[KnownCrossSimulatorNote, ...] = (
    KnownCrossSimulatorNote(
        models=("3D_gaa_Si",),
        metrics=("ion_a", "ron_ohm", "ron_boost_ohm", "ron_x_cload"),
        backends=(SimulatorBackend.HSPICE.value, SimulatorBackend.NGSPICE.value),
        reason=(
            "Spectre loads BSIM-CMG 105.03 (112.x compatibility patch); "
            "HSPICE/ngspice use native 112.0.0 — Ion and Ron diverge (~40–71% @ tt)."
        ),
    ),
    KnownCrossSimulatorNote(
        models=("BCAT_125",),
        metrics=("i_hold_a",),
        backends=(SimulatorBackend.NGSPICE.value,),
        reason="ngspice OSDI BSIM-CMG shows higher subthreshold leakage in the 1T1C hold window.",
    ),
    KnownCrossSimulatorNote(
        models=tuple(),
        metrics=("ion_a", "ron_ohm", "ron_boost_ohm"),
        backends=(SimulatorBackend.NGSPICE.value,),
        reason=(
            "ngspice OSDI often reports higher Ion than Spectre; Ron follows V/I and is lower. "
            "Directional use only."
        ),
    ),
    KnownCrossSimulatorNote(
        models=tuple(),
        metrics=("cgg_f", "cgd_f", "ion_per_cgg"),
        backends=(SimulatorBackend.NGSPICE.value,),
        reason=(
            "Capacitance from transient qg/qd integration on OSDI VA model; "
            "stripped HSPICE-only cap flags — often much lower than Spectre."
        ),
    ),
    KnownCrossSimulatorNote(
        models=tuple(),
        metrics=("t_bl_settle_s",),
        backends=(SimulatorBackend.NGSPICE.value,),
        reason="Transient timestep and OSDI trajectory vs Spectre (~35–40% @ tt).",
    ),
)

_KEY_COLS_DEVICE = ("model_id", "corner")
_KEY_COLS_CELL = ("model_id", "corner", "ccell_ff")
_KEY_COLS_MINI = ("model_id", "corner")

_DEVICE_METRICS = (
    "vt_v",
    "ss_mv_dec",
    "ion_a",
    "ioff_a",
    "dibl_mv_v",
    "ron_ohm",
    "ron_boost_ohm",
    "cgg_f",
    "cgd_f",
    "igidl_a",
    "esw_j",
    "ion_per_cgg",
    "ron_x_cload",
    "ioff_density_a_m2",
)

_CELL_METRICS = ("t_write_s", "t_read_s", "i_hold_a", "q_read_c")
_MINI_METRICS = ("t_bl_settle_s", "i_bl_leak_a")


def _note_applies(note: KnownCrossSimulatorNote, model_id: str, metric: str, backend: str) -> bool:
    if note.backends and backend not in note.backends:
        return False
    if note.models and model_id not in note.models:
        return False
    return metric in note.metrics


def _find_known_note(model_id: str, metric: str, backend: str, reference: str) -> str | None:
    col_suffix = f"{backend}_vs_{reference}"
    metric_base = metric
    for note in KNOWN_CROSS_SIMULATOR_NOTES:
        if note.reference != reference:
            continue
        if _note_applies(note, model_id, metric_base, backend):
            return note.reason
    return None


def _parse_rel_diff_column(col: str, reference: str) -> tuple[str, str] | None:
    """Parse ``rel_diff_{metric}_{backend}_vs_{reference}`` into metric and backend."""
    suffix = f"_vs_{reference}"
    if not col.startswith("rel_diff_") or not col.endswith(suffix):
        return None
    body = col[len("rel_diff_") : -len(suffix)]
    for backend in (SimulatorBackend.HSPICE.value, SimulatorBackend.NGSPICE.value):
        backend_suffix = f"_{backend}"
        if body.endswith(backend_suffix):
            return body[:-len(backend_suffix)], backend
    return None


def build_known_outliers_table(
    diff_frames: dict[str, pd.DataFrame],
    corner: str,
    reference: str = SimulatorBackend.SPECTRE.value,
) -> pd.DataFrame:
    """Flag rows with large |rel diff| or documented known-outlier patterns."""
    rows: list[dict[str, object]] = []
    kind_labels = {
        "device": _DEVICE_METRICS,
        "cell": _CELL_METRICS,
        "mini_array": _MINI_METRICS,
    }
    for kind, metrics in kind_labels.items():
        diff = diff_frames.get(kind)
        if diff is None or diff.empty:
            continue
        if "corner" in diff.columns:
            subset = diff[diff["corner"] == corner]
            if subset.empty:
                subset = diff
        else:
            subset = diff
        rel_cols = [c for c in subset.columns if c.startswith("rel_diff_")]
        key_cols = [c for c in subset.columns if c in _KEY_COLS_DEVICE + _KEY_COLS_CELL + _KEY_COLS_MINI]
        for _, row in subset.iterrows():
            model_id = str(row.get("model_id", ""))
        for col in rel_cols:
            val = row.get(col)
            if pd.isna(val):
                continue
            parsed = _parse_rel_diff_column(col, reference)
            if parsed is None:
                continue
            metric, backend = parsed
            model_id = str(row.get("model_id", ""))
            known = _find_known_note(model_id, metric, backend, reference)
            flagged = abs(float(val)) >= _REL_DIFF_FLAG_THRESHOLD
            if known or flagged:
                    entry = {k: row.get(k) for k in key_cols}
                    entry.update(
                        {
                            "suite": kind,
                            "metric": metric,
                            "backend": backend,
                            "reference": reference,
                            "rel_diff": float(val),
                            "flag_threshold": _REL_DIFF_FLAG_THRESHOLD,
                            "known_outlier": known is not None,
                            "note": known or "Exceeds automatic rel-diff threshold",
                        }
                    )
                    rows.append(entry)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def format_known_outliers_markdown(outliers: pd.DataFrame, corner: str) -> list[str]:
    """Render outlier table as markdown lines."""
    if outliers.empty:
        return [
            "## Known / flagged outliers",
            "",
            f"No rows exceeded |rel diff| ≥ {_REL_DIFF_FLAG_THRESHOLD} @ {corner}.",
            "",
        ]
    lines = [
        "## Known / flagged outliers",
        "",
        f"Rows with |rel diff| ≥ {_REL_DIFF_FLAG_THRESHOLD} or documented known patterns @ **{corner}**.",
        "See [docs/simulator_cross_check.md](../docs/simulator_cross_check.md) for full context.",
        "",
        "| suite | model | metric | backend | rel diff | known | note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in outliers.sort_values(["suite", "model_id", "metric"]).iterrows():
        rel = row.get("rel_diff")
        rel_s = f"{rel:.4g}" if pd.notna(rel) else "—"
        note = str(row.get("note", "")).replace("|", "\\|")
        if len(note) > 120:
            note = note[:117] + "..."
        lines.append(
            f"| {row.get('suite', '')} | {row.get('model_id', '')} | {row.get('metric', '')} | "
            f"{row.get('backend', '')} | {rel_s} | "
            f"{'yes' if row.get('known_outlier') else 'auto'} | {note} |"
        )
    lines.append("")
    return lines


def format_documented_notes_markdown() -> list[str]:
    """Static summary of documented cross-simulator expectations."""
    lines = [
        "## Documented cross-simulator expectations",
        "",
        "Full guide: [docs/simulator_cross_check.md](../docs/simulator_cross_check.md)",
        "",
    ]
    for note in KNOWN_CROSS_SIMULATOR_NOTES:
        models = ", ".join(note.models) if note.models else "all models"
        metrics = ", ".join(note.metrics)
        backends = ", ".join(note.backends)
        lines.append(f"- **{models}** — `{metrics}` ({backends} vs {note.reference}): {note.reason}")
    lines.append("")
    return lines


def _pick_reference_backend(backends: list[SimulatorBackend]) -> SimulatorBackend:
    """Prefer Spectre as reference, otherwise first listed backend."""
    if SimulatorBackend.SPECTRE in backends:
        return SimulatorBackend.SPECTRE
    return backends[0]


def _numeric_columns(df: pd.DataFrame, metrics: tuple[str, ...]) -> list[str]:
    return [col for col in metrics if col in df.columns]


def compare_metric_frames(
    frames: dict[str, pd.DataFrame],
    key_cols: tuple[str, ...],
    metric_cols: tuple[str, ...],
    reference: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge per-simulator metrics and compute relative differences.

    Args:
        frames: Mapping of simulator name to metrics DataFrame.
        key_cols: Join keys (e.g. model_id, corner).
        metric_cols: Numeric metric columns to compare.
        reference: Reference simulator for rel-diff columns (default: spectre if present).

    Returns:
        Tuple of (wide merged frame, diff frame with rel_diff_{backend} columns).
    """
    if not frames:
        return pd.DataFrame(), pd.DataFrame()

    names = sorted(frames)
    ref_name = reference or (
        SimulatorBackend.SPECTRE.value
        if SimulatorBackend.SPECTRE.value in names
        else names[0]
    )

    merged: pd.DataFrame | None = None
    for name in names:
        df = frames[name].copy()
        metrics = _numeric_columns(df, metric_cols)
        if not metrics:
            continue
        subset = df[list(key_cols) + metrics].copy()
        subset = subset.rename(columns={col: f"{col}_{name}" for col in metrics})
        if merged is None:
            merged = subset
        else:
            merged = merged.merge(subset, on=list(key_cols), how="outer")

    if merged is None or merged.empty:
        return pd.DataFrame(), pd.DataFrame()

    diff = merged[list(key_cols)].copy()
    ref_metrics = _numeric_columns(merged, tuple(f"{m}_{ref_name}" for m in metric_cols))
    for name in names:
        if name == ref_name:
            continue
        for metric in metric_cols:
            ref_col = f"{metric}_{ref_name}"
            other_col = f"{metric}_{name}"
            if ref_col not in merged.columns or other_col not in merged.columns:
                continue
            ref_vals = merged[ref_col]
            other_vals = merged[other_col]
            rel = (other_vals - ref_vals) / ref_vals.replace(0, pd.NA)
            diff[f"rel_diff_{metric}_{name}_vs_{ref_name}"] = rel

    return merged, diff


def _load_metrics_csv(base_dir: Path, backend: str, corner: str, filename: str) -> pd.DataFrame | None:
    path = base_dir / backend / corner / filename
    if not path.is_file():
        path = base_dir / backend / filename
    if path.is_file():
        return pd.read_csv(path)
    return None


def collect_simulator_frames(
    base_dir: Path,
    corner: str,
    backends: list[str] | None = None,
) -> dict[str, dict[str, pd.DataFrame]]:
    """Load device/cell/min-array CSVs for each simulator under ``base_dir/{backend}/``."""
    names = backends or [b.value for b in available_backends()]
    result: dict[str, dict[str, pd.DataFrame]] = {
        "device": {},
        "cell": {},
        "mini_array": {},
    }
    for name in names:
        device = _load_metrics_csv(base_dir, name, corner, "device_metrics.csv")
        if device is not None:
            result["device"][name] = device
        cell = _load_metrics_csv(base_dir, name, corner, "cell_1t1c_metrics.csv")
        if cell is not None:
            result["cell"][name] = cell
        mini = _load_metrics_csv(base_dir, name, corner, "mini_array_metrics.csv")
        if mini is not None:
            result["mini_array"][name] = mini
    return result


def write_simulator_comparison(
    base_dir: Path,
    corner: str = "tt",
    backends: list[str] | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Write wide merge + rel-diff CSVs and a markdown summary.

    Args:
        base_dir: Parent directory containing per-simulator result trees.
        corner: Corner subdirectory name.
        backends: Simulator names to include (default: all available).
        output_dir: Comparison output directory (default: ``base_dir/simulator_compare``).

    Returns:
        Path to the markdown summary file.
    """
    out = output_dir or (base_dir / "simulator_compare")
    corner_out = out / corner
    corner_out.mkdir(parents=True, exist_ok=True)

    frames = collect_simulator_frames(base_dir, corner, backends)
    summaries: list[str] = [
        f"# Simulator comparison ({corner})",
        "",
        "Relative differences use Spectre as reference when present.",
        "",
    ]
    summaries.extend(format_documented_notes_markdown())

    comparisons = [
        ("device", _KEY_COLS_DEVICE, _DEVICE_METRICS, "device_metrics"),
        ("cell", _KEY_COLS_CELL, _CELL_METRICS, "cell_1t1c_metrics"),
        ("mini_array", _KEY_COLS_MINI, _MINI_METRICS, "mini_array_metrics"),
    ]
    diff_by_kind: dict[str, pd.DataFrame] = {}

    for kind, keys, metrics, stem in comparisons:
        kind_frames = frames.get(kind, {})
        if len(kind_frames) < 2:
            logger.info("Skip %s compare: need >=2 simulators with data", kind)
            continue
        wide, diff = compare_metric_frames(kind_frames, keys, metrics)
        diff_by_kind[kind] = diff
        wide_path = corner_out / f"{stem}_wide.csv"
        diff_path = corner_out / f"{stem}_rel_diff.csv"
        wide.to_csv(wide_path, index=False)
        diff.to_csv(diff_path, index=False)
        summaries.append(f"## {kind}")
        summaries.append(f"- Wide: `{wide_path.name}`")
        summaries.append(f"- Rel diff: `{diff_path.name}`")
        rel_cols = [c for c in diff.columns if c.startswith("rel_diff_")]
        if rel_cols:
            max_abs = diff[rel_cols].abs().max()
            summaries.append("")
            summaries.append("| metric | max |rel diff| |")
            summaries.append("|--------|-------------|")
            for col in rel_cols:
                val = max_abs[col]
                if pd.notna(val):
                    summaries.append(f"| {col} | {val:.4g} |")
        summaries.append("")

    outliers = build_known_outliers_table(diff_by_kind, corner)
    if not outliers.empty:
        outliers.to_csv(corner_out / "known_outliers.csv", index=False)
        summaries.extend(format_known_outliers_markdown(outliers, corner))
    else:
        summaries.extend(format_known_outliers_markdown(outliers, corner))

    if _CROSS_CHECK_DOC.is_file():
        dest = corner_out / "simulator_cross_check.md"
        if not dest.is_file():
            dest.write_text(_CROSS_CHECK_DOC.read_text(encoding="utf-8"), encoding="utf-8")

    summary_path = corner_out / "SIMULATOR_COMPARE.md"
    summary_path.write_text("\n".join(summaries), encoding="utf-8")

    index_path = out / "SIMULATOR_COMPARE.md"
    index_lines = [
        "# Simulator comparison index",
        "",
        f"Per-corner tables under `simulator_compare/{corner}/`.",
        "",
        f"- [{corner}]({corner}/SIMULATOR_COMPARE.md)",
        "",
    ]
    if index_path.is_file():
        existing = index_path.read_text(encoding="utf-8")
        link = f"- [{corner}]({corner}/SIMULATOR_COMPARE.md)"
        if link not in existing:
            index_path.write_text(existing.rstrip() + "\n" + link + "\n", encoding="utf-8")
    else:
        index_path.write_text("\n".join(index_lines), encoding="utf-8")

    logger.info("Simulator comparison → %s", summary_path)
    return summary_path


def write_simulator_comparison_all_corners(
    base_dir: Path,
    corners: list[str] | None = None,
    backends: list[str] | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """Write comparison tables for every corner under ``base_dir``."""
    from bench.conditions import load_corners

    corner_names = corners or list(load_corners())
    paths: list[Path] = []
    for corner_name in corner_names:
        paths.append(
            write_simulator_comparison(
                base_dir,
                corner=corner_name,
                backends=backends,
                output_dir=output_dir,
            )
        )
    return paths


def list_compared_backends(base_dir: Path) -> list[str]:
    """Return simulator names with result trees under ``base_dir/{backend}/``."""
    names: list[str] = []
    for backend in (SimulatorBackend.SPECTRE, SimulatorBackend.HSPICE, SimulatorBackend.NGSPICE):
        path = base_dir / backend.value
        if path.is_dir() and any(path.rglob("device_metrics.csv")):
            names.append(backend.value)
    return names


def _filter_corner(df: pd.DataFrame, corner: str) -> pd.DataFrame:
    if "corner" in df.columns:
        subset = df[df["corner"] == corner]
        return subset if not subset.empty else df
    return df


def simulator_compare_report_markdown(
    compare_dir: Path,
    reference_corner: str = "tt",
    results_root: Path | None = None,
) -> str:
    """Build a markdown section for embedding in ``RESULTS.md``.

    Args:
        compare_dir: ``simulator_compare/`` root (may contain per-corner subdirs).
        reference_corner: Corner to highlight in per-model tables.
        results_root: Parent results dir to list compared backends (optional).

    Returns:
        Markdown fragment (empty string when no comparison data).
    """
    corner_dir = compare_dir / reference_corner
    if corner_dir.is_dir():
        search_dir = corner_dir
    else:
        search_dir = compare_dir

    wide_path = search_dir / "device_metrics_wide.csv"
    diff_path = search_dir / "device_metrics_rel_diff.csv"
    if not wide_path.is_file() and not diff_path.is_file():
        return ""

    backends = list_compared_backends(results_root) if results_root else []
    if not backends and wide_path.is_file():
        wide_cols = pd.read_csv(wide_path, nrows=0).columns
        backends = sorted(
            {
                col.rsplit("_", 1)[-1]
                for col in wide_cols
                if col.startswith("ion_a_") or col.startswith("ioff_a_")
            }
        )

    lines: list[str] = [
        "## Simulator cross-check",
        "",
        "Relative differences vs **Spectre** when present. No golden baselines for cross-tool agreement.",
        "",
        "Interpretation guide: [docs/simulator_cross_check.md](docs/simulator_cross_check.md)",
        "",
    ]
    if backends:
        lines.append(f"**Compared backends:** {', '.join(backends)}")
        lines.append("")

    if diff_path.is_file():
        diff = _filter_corner(pd.read_csv(diff_path), reference_corner)
        rel_cols = [c for c in diff.columns if c.startswith("rel_diff_")]
        if rel_cols:
            lines.append(f"### Max |relative difference| ({reference_corner}, device metrics)")
            lines.append("")
            lines.append("| Comparison | Max |rel diff| |")
            lines.append("| --- | --- |")
            max_abs = diff[rel_cols].abs().max()
            for col in sorted(rel_cols):
                val = max_abs[col]
                if pd.notna(val):
                    label = col.replace("rel_diff_", "").replace("_", " ")
                    lines.append(f"| {label} | {val:.4g} |")
            lines.append("")

    if wide_path.is_file():
        wide = _filter_corner(pd.read_csv(wide_path), reference_corner)
        ion_cols = [c for c in wide.columns if c.startswith("ion_a_")]
        ioff_cols = [c for c in wide.columns if c.startswith("ioff_a_")]
        if ion_cols:
            lines.append(f"### Ion / Ioff by simulator ({reference_corner})")
            lines.append("")
            header = ["Model"] + [c.replace("ion_a_", "") for c in ion_cols]
            if ioff_cols:
                header += [f"ioff_{c.replace('ioff_a_', '')}" for c in ioff_cols]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("| " + " | ".join(["---"] * len(header)) + " |")
            for _, row in wide.sort_values("model_id").iterrows():
                cells = [str(row.get("model_id", ""))]
                for col in ion_cols:
                    val = row.get(col)
                    cells.append(f"{val:.3e}" if pd.notna(val) else "—")
                for col in ioff_cols:
                    val = row.get(col)
                    cells.append(f"{val:.3e}" if pd.notna(val) else "—")
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")

    outliers_path = search_dir / "known_outliers.csv"
    if outliers_path.is_file():
        outliers = _filter_corner(pd.read_csv(outliers_path), reference_corner)
        flagged = outliers[outliers["known_outlier"] == True]  # noqa: E712
        if not flagged.empty:
            lines.append(f"### Documented outliers ({reference_corner})")
            lines.append("")
            for _, row in flagged.head(8).iterrows():
                lines.append(
                    f"- `{row.get('model_id', '')}` `{row.get('metric', '')}` "
                    f"({row.get('backend', '')}): {row.get('note', '')}"
                )
            if len(flagged) > 8:
                lines.append(f"- … and {len(flagged) - 8} more in `known_outliers.csv`")
            lines.append("")

    rel_link = search_dir / "device_metrics_rel_diff.csv"
    wide_link = search_dir / "device_metrics_wide.csv"
    compare_md = search_dir / "SIMULATOR_COMPARE.md"
    lines.append("### Comparison artifacts")
    lines.append("")
    if compare_md.is_file():
        rel = f"simulator_compare/{reference_corner}/SIMULATOR_COMPARE.md"
        lines.append(f"- [`{rel}`]({rel})")
    if wide_link.is_file():
        lines.append(f"- `simulator_compare/{reference_corner}/device_metrics_wide.csv`")
    if rel_link.is_file():
        lines.append(f"- `simulator_compare/{reference_corner}/device_metrics_rel_diff.csv`")
    lines.append("")
    return "\n".join(lines)
