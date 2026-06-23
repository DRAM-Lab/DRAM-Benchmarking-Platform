"""Cross-simulator (Spectre / HSPICE / ngspice) metric comparison for validation reports."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from validation.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

SUPPORTED_BACKENDS: tuple[str, ...] = ("spectre", "hspice", "ngspice")
DEFAULT_REFERENCE = "spectre"
DEFAULT_CORNER = "tt"

KEY_DEVICE_METRICS: tuple[str, ...] = ("ion_a", "ioff_a", "ron_ohm", "cgg_f")
KEY_CELL_METRICS: tuple[str, ...] = ("t_read_s", "t_write_s", "i_hold_a")
KEY_MINI_ARRAY_METRICS: tuple[str, ...] = ("t_bl_settle_s", "i_bl_leak_a")
DEFAULT_CELL_CCELL_FF = 20.0

PINNED_COMPARE_ROOT = PROJECT_ROOT / "bench" / "validation" / "pinned" / "simulator_compare"
MANIFEST_PATH = PINNED_COMPARE_ROOT / "manifest.yaml"


@dataclass(frozen=True)
class SimulatorCompareSnapshot:
    """Pinned or live multi-simulator comparison artifacts."""

    reference: str
    corner: str
    backends: tuple[str, ...]
    device_wide: pd.DataFrame
    device_rel_diff: pd.DataFrame
    cell_wide: pd.DataFrame | None
    cell_rel_diff: pd.DataFrame | None
    mini_array_wide: pd.DataFrame | None
    mini_array_rel_diff: pd.DataFrame | None
    manifest: dict[str, Any]


def default_pinned_compare_dir() -> Path:
    """Return pinned simulator comparison directory."""
    return PINNED_COMPARE_ROOT


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _backend_status(manifest: dict[str, Any]) -> dict[str, str]:
    raw = manifest.get("backend_status", {})
    return {str(k): str(v) for k, v in raw.items()}


def _detect_backend_availability() -> dict[str, bool]:
    """Probe optional dram-device simulator helpers when installed."""
    try:
        from bench.simulator import (  # type: ignore[import-untyped]
            hspice_available,
            ngspice_available,
            spectre_available,
        )
    except ImportError:
        return {name: False for name in SUPPORTED_BACKENDS}
    return {
        "spectre": spectre_available(),
        "hspice": hspice_available(),
        "ngspice": ngspice_available(),
    }


def filter_cell_at_ccell(
    df: pd.DataFrame | None,
    ccell_ff: float = DEFAULT_CELL_CCELL_FF,
) -> pd.DataFrame | None:
    """Keep one 1T1C capacitance row per model when ``ccell_ff`` is present."""
    if df is None or df.empty or "ccell_ff" not in df.columns:
        return df
    subset = df[df["ccell_ff"] == ccell_ff]
    return subset if not subset.empty else df


def load_pinned_simulator_compare(
    compare_dir: Path | None = None,
) -> SimulatorCompareSnapshot | None:
    """Load checked-in simulator comparison CSVs for offline reports.

    Returns:
        Snapshot when manifest and device rel-diff CSV exist, else ``None``.
    """
    root = compare_dir or default_pinned_compare_dir()
    manifest_path = root / "manifest.yaml"
    rel_path = root / "device_metrics_rel_diff.csv"
    wide_path = root / "device_metrics_wide.csv"
    if not manifest_path.is_file() or not rel_path.is_file():
        return None

    manifest = _load_yaml(manifest_path)
    device_rel = pd.read_csv(rel_path)
    device_wide = pd.read_csv(wide_path) if wide_path.is_file() else pd.DataFrame()

    cell_rel_path = root / "cell_1t1c_metrics_rel_diff.csv"
    cell_wide_path = root / "cell_1t1c_metrics_wide.csv"
    cell_rel = pd.read_csv(cell_rel_path) if cell_rel_path.is_file() else None
    cell_wide = pd.read_csv(cell_wide_path) if cell_wide_path.is_file() else None
    cell_rel = filter_cell_at_ccell(cell_rel)
    cell_wide = filter_cell_at_ccell(cell_wide)

    mini_rel_path = root / "mini_array_metrics_rel_diff.csv"
    mini_wide_path = root / "mini_array_metrics_wide.csv"
    mini_rel = pd.read_csv(mini_rel_path) if mini_rel_path.is_file() else None
    mini_wide = pd.read_csv(mini_wide_path) if mini_wide_path.is_file() else None

    backends = tuple(str(b) for b in manifest.get("backends", SUPPORTED_BACKENDS))
    return SimulatorCompareSnapshot(
        reference=str(manifest.get("reference", DEFAULT_REFERENCE)),
        corner=str(manifest.get("corner", DEFAULT_CORNER)),
        backends=backends,
        device_wide=device_wide,
        device_rel_diff=device_rel,
        cell_wide=cell_wide,
        cell_rel_diff=cell_rel,
        mini_array_wide=mini_wide,
        mini_array_rel_diff=mini_rel,
        manifest=manifest,
    )


def _rel_diff_columns(df: pd.DataFrame, metric: str) -> list[str]:
    prefix = f"rel_diff_{metric}_"
    return [col for col in df.columns if col.startswith(prefix)]


def summarize_metric_differences(
    rel_diff: pd.DataFrame,
    metrics: tuple[str, ...],
) -> pd.DataFrame:
    """Summarize max |rel diff| per metric and backend pair."""
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        for col in _rel_diff_columns(rel_diff, metric):
            series = rel_diff[col].abs()
            if series.empty or series.isna().all():
                continue
            backend = col.removeprefix(f"rel_diff_{metric}_").removesuffix(
                f"_vs_{DEFAULT_REFERENCE}"
            )
            rows.append(
                {
                    "metric": metric,
                    "backend": backend,
                    "max_abs_rel_diff": float(series.max(skipna=True)),
                    "mean_abs_rel_diff": float(series.mean(skipna=True)),
                }
            )
    return pd.DataFrame(rows)


def per_model_metric_table(
    rel_diff: pd.DataFrame,
    metrics: tuple[str, ...],
    *,
    reference: str = DEFAULT_REFERENCE,
) -> pd.DataFrame:
    """Build a long table of per-model relative differences for selected metrics."""
    rows: list[dict[str, Any]] = []
    key_cols = [c for c in ("model_id", "corner") if c in rel_diff.columns]
    for _, row in rel_diff.iterrows():
        for metric in metrics:
            for backend in SUPPORTED_BACKENDS:
                if backend == reference:
                    continue
                col = f"rel_diff_{metric}_{backend}_vs_{reference}"
                if col not in rel_diff:
                    continue
                val = row[col]
                if pd.isna(val):
                    continue
                entry: dict[str, Any] = {col_name: row[col_name] for col_name in key_cols}
                entry.update(
                    {
                        "metric": metric,
                        "backend": backend,
                        "rel_diff": float(val),
                        "abs_rel_diff": abs(float(val)),
                    }
                )
                rows.append(entry)
    return pd.DataFrame(rows)


def pin_simulator_compare_artifacts(
    source_dir: Path,
    *,
    output_dir: Path | None = None,
    corner: str = DEFAULT_CORNER,
    reference: str = DEFAULT_REFERENCE,
    backends: tuple[str, ...] = SUPPORTED_BACKENDS,
    notes: str = "",
) -> Path:
    """Copy comparison CSVs from an dram-device multi-simulator run into pinned storage."""
    src = source_dir / "simulator_compare"
    if not src.is_dir():
        raise FileNotFoundError(f"Missing simulator_compare under {source_dir}")

    out = output_dir or default_pinned_compare_dir()
    out.mkdir(parents=True, exist_ok=True)

    corner_src = src / corner
    compare_root = corner_src if corner_src.is_dir() else src

    for name in (
        "device_metrics_wide.csv",
        "device_metrics_rel_diff.csv",
        "cell_1t1c_metrics_wide.csv",
        "cell_1t1c_metrics_rel_diff.csv",
        "mini_array_metrics_wide.csv",
        "mini_array_metrics_rel_diff.csv",
    ):
        path = compare_root / name
        if path.is_file():
            shutil.copy2(path, out / name)

    manifest = {
        "reference": reference,
        "corner": corner,
        "backends": list(backends),
        "source": str(source_dir),
        "notes": notes,
        "backend_status": {
            "spectre": "reference",
            "hspice": "compared",
            "ngspice": "compared",
        },
    }
    (out / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    logger.info("Pinned simulator comparison → %s", out)
    return out


def refresh_simulator_compare(
    *,
    output_dir: Path | None = None,
    corner: str = DEFAULT_CORNER,
    device_only: bool = True,
) -> Path:
    """Run dram-device multi-simulator benchmark and pin comparison CSVs.

    Requires editable ``dram-device`` and at least Spectre on the host.
    """
    try:
        from bench.runner import run_all_simulators  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "dram-device not installed. Install with "
            "pip install -e ../OpenDRAM-device-benchmark"
        ) from exc

    scratch = output_dir or (PROJECT_ROOT / "bench" / "validation" / "simulator_refresh")
    scratch.mkdir(parents=True, exist_ok=True)

    run_all_simulators(
        scratch,
        model_ids=None,
        corner_name=corner,
        simulate=True,
        full=not device_only,
    )

    return pin_simulator_compare_artifacts(
        scratch,
        corner=corner,
        notes="Refreshed via dram-validate simulators --refresh",
    )


def export_simulator_compare_tables(
    snapshot: SimulatorCompareSnapshot,
    data_dir: Path,
) -> dict[str, Path]:
    """Write simulator comparison CSV exports under ``results/data/``."""
    data_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["simulator_device_rel_diff"] = data_dir / "simulator_device_rel_diff.csv"
    snapshot.device_rel_diff.to_csv(paths["simulator_device_rel_diff"], index=False)

    if not snapshot.device_wide.empty:
        paths["simulator_device_wide"] = data_dir / "simulator_device_wide.csv"
        snapshot.device_wide.to_csv(paths["simulator_device_wide"], index=False)

    summary = summarize_metric_differences(snapshot.device_rel_diff, KEY_DEVICE_METRICS)
    paths["simulator_device_summary"] = data_dir / "simulator_device_summary.csv"
    summary.to_csv(paths["simulator_device_summary"], index=False)

    detail = per_model_metric_table(snapshot.device_rel_diff, KEY_DEVICE_METRICS)
    paths["simulator_device_detail"] = data_dir / "simulator_device_detail.csv"
    detail.to_csv(paths["simulator_device_detail"], index=False)

    if snapshot.cell_rel_diff is not None and not snapshot.cell_rel_diff.empty:
        paths["simulator_cell_rel_diff"] = data_dir / "simulator_cell_rel_diff.csv"
        snapshot.cell_rel_diff.to_csv(paths["simulator_cell_rel_diff"], index=False)
        cell_summary = summarize_metric_differences(snapshot.cell_rel_diff, KEY_CELL_METRICS)
        paths["simulator_cell_summary"] = data_dir / "simulator_cell_summary.csv"
        cell_summary.to_csv(paths["simulator_cell_summary"], index=False)
        cell_detail = per_model_metric_table(snapshot.cell_rel_diff, KEY_CELL_METRICS)
        paths["simulator_cell_detail"] = data_dir / "simulator_cell_detail.csv"
        cell_detail.to_csv(paths["simulator_cell_detail"], index=False)
        if snapshot.cell_wide is not None and not snapshot.cell_wide.empty:
            paths["simulator_cell_wide"] = data_dir / "simulator_cell_wide.csv"
            snapshot.cell_wide.to_csv(paths["simulator_cell_wide"], index=False)

    if snapshot.mini_array_rel_diff is not None and not snapshot.mini_array_rel_diff.empty:
        paths["simulator_mini_array_rel_diff"] = data_dir / "simulator_mini_array_rel_diff.csv"
        snapshot.mini_array_rel_diff.to_csv(paths["simulator_mini_array_rel_diff"], index=False)
        mini_summary = summarize_metric_differences(
            snapshot.mini_array_rel_diff, KEY_MINI_ARRAY_METRICS
        )
        paths["simulator_mini_array_summary"] = data_dir / "simulator_mini_array_summary.csv"
        mini_summary.to_csv(paths["simulator_mini_array_summary"], index=False)
        mini_detail = per_model_metric_table(
            snapshot.mini_array_rel_diff, KEY_MINI_ARRAY_METRICS
        )
        paths["simulator_mini_array_detail"] = data_dir / "simulator_mini_array_detail.csv"
        mini_detail.to_csv(paths["simulator_mini_array_detail"], index=False)
        if snapshot.mini_array_wide is not None and not snapshot.mini_array_wide.empty:
            paths["simulator_mini_array_wide"] = data_dir / "simulator_mini_array_wide.csv"
            snapshot.mini_array_wide.to_csv(paths["simulator_mini_array_wide"], index=False)

    return paths


def generate_simulator_compare_markdown(
    snapshot: SimulatorCompareSnapshot | None = None,
    figure_paths: dict[str, Path] | None = None,
) -> list[str]:
    """Return markdown lines for the simulator comparison section in RESULTS.md."""
    if snapshot is None:
        snapshot = load_pinned_simulator_compare()
    if snapshot is None:
        return [
            "## 9. SPICE simulator cross-check (Spectre / HSPICE / ngspice)",
            "",
            "No pinned simulator comparison data found. Refresh with:",
            "",
            "```bash",
            "pip install -e ../OpenDRAM-device-benchmark",
            "dram-validate simulators --refresh",
            "dram-validate report",
            "```",
            "",
        ]

    manifest = snapshot.manifest
    status = _backend_status(manifest)
    availability = _detect_backend_availability()
    lines: list[str] = [
        "## 9. SPICE simulator cross-check (Spectre / HSPICE / ngspice)",
        "",
        f"Reference backend: **{snapshot.reference}** ({snapshot.corner} corner). "
        "Relative Δ = (backend − reference) / reference.",
        "",
        "| Backend | Pinned role | Host available |",
        "| --- | --- | --- |",
    ]
    for backend in SUPPORTED_BACKENDS:
        role = status.get(backend, "—")
        avail = "yes" if availability.get(backend) else "no"
        lines.append(f"| {backend} | {role} | {avail} |")

    notes = manifest.get("notes")
    if notes:
        lines.extend(["", f"*Note:* {notes}", ""])

    summary = summarize_metric_differences(snapshot.device_rel_diff, KEY_DEVICE_METRICS)
    active_backends = [
        b
        for b in SUPPORTED_BACKENDS
        if b != snapshot.reference and "unavailable" not in status.get(b, "").lower()
    ]
    if not summary.empty and active_backends:
        filtered = summary[summary["backend"].isin(active_backends)]
        if not filtered.empty:
            lines.extend(
                [
                    "### Max abs relative difference by metric",
                    "",
                    "| Metric | Backend | max abs Δ | mean abs Δ |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for _, row in filtered.sort_values(["metric", "backend"]).iterrows():
                lines.append(
                    f"| {row['metric']} | {row['backend']} | "
                    f"{row['max_abs_rel_diff']:.4g} | {row['mean_abs_rel_diff']:.4g} |"
                )
            lines.append("")

    figures = figure_paths or {}
    if figures:
        if "simulator_max_rel_diff" in figures:
            lines.extend(
                [
                    "### Simulator agreement summary",
                    "",
                    "![Simulator max abs rel diff](figures/simulator_max_rel_diff.svg)",
                    "",
                    "*Figure: `figures/simulator_max_rel_diff.svg`*",
                    "",
                ]
            )
        if "simulator_rel_diff_heatmap" in figures:
            lines.extend(
                [
                    "### Per-model relative Δ heatmap",
                    "",
                    "![Simulator rel diff heatmap](figures/simulator_rel_diff_heatmap.svg)",
                    "",
                    "*Figure: `figures/simulator_rel_diff_heatmap.svg`*",
                    "",
                ]
            )
        if "simulator_spectre_vs_backend" in figures:
            lines.extend(
                [
                    "### Spectre vs alternate backend scatter",
                    "",
                    "![Spectre vs backend scatter](figures/simulator_spectre_vs_backend.svg)",
                    "",
                    "*Figure: `figures/simulator_spectre_vs_backend.svg`*",
                    "",
                ]
            )

    detail = per_model_metric_table(snapshot.device_rel_diff, KEY_DEVICE_METRICS)
    if not detail.empty and active_backends:
        detail = detail[detail["backend"].isin(active_backends)]
    if not detail.empty:
        lines.extend(
            [
                "### Per-model Ion / Ioff / Ron / Cgg vs Spectre",
                "",
                "| Model | Metric | Backend | Rel Δ |",
                "| --- | --- | --- | --- |",
            ]
        )
        for _, row in detail.sort_values(["model_id", "metric", "backend"]).iterrows():
            lines.append(
                f"| {row['model_id']} | {row['metric']} | {row['backend']} | "
                f"{row['rel_diff']:.4g} |"
            )
        lines.append("")

    if snapshot.cell_rel_diff is not None and not snapshot.cell_rel_diff.empty:
        cell_summary = summarize_metric_differences(snapshot.cell_rel_diff, KEY_CELL_METRICS)
        if not cell_summary.empty and active_backends:
            cell_filtered = cell_summary[cell_summary["backend"].isin(active_backends)]
            if not cell_filtered.empty:
                lines.extend(
                    [
                        f"### 1T1C cell metrics ({DEFAULT_CELL_CCELL_FF:g} fF)",
                        "",
                        "| Metric | Backend | max abs Δ | mean abs Δ |",
                        "| --- | --- | --- | --- |",
                    ]
                )
                for _, row in cell_filtered.sort_values(["metric", "backend"]).iterrows():
                    lines.append(
                        f"| {row['metric']} | {row['backend']} | "
                        f"{row['max_abs_rel_diff']:.4g} | {row['mean_abs_rel_diff']:.4g} |"
                    )
                lines.append("")

        if "simulator_cell_max_rel_diff" in figures:
            lines.extend(
                [
                    "#### 1T1C simulator agreement",
                    "",
                    f"![1T1C simulator max abs rel diff](figures/simulator_cell_max_rel_diff.svg)",
                    "",
                    "*Figure: `figures/simulator_cell_max_rel_diff.svg`*",
                    "",
                ]
            )
        if "simulator_cell_rel_diff_heatmap" in figures:
            lines.extend(
                [
                    f"![1T1C simulator rel diff heatmap](figures/simulator_cell_rel_diff_heatmap.svg)",
                    "",
                    "*Figure: `figures/simulator_cell_rel_diff_heatmap.svg`*",
                    "",
                ]
            )
        if "simulator_cell_spectre_vs_backend" in figures:
            lines.extend(
                [
                    f"![1T1C Spectre vs backend scatter](figures/simulator_cell_spectre_vs_backend.svg)",
                    "",
                    "*Figure: `figures/simulator_cell_spectre_vs_backend.svg`*",
                    "",
                ]
            )

        cell_detail = per_model_metric_table(snapshot.cell_rel_diff, KEY_CELL_METRICS)
        if not cell_detail.empty and active_backends:
            cell_detail = cell_detail[cell_detail["backend"].isin(active_backends)]
        if not cell_detail.empty:
            lines.extend(
                [
                    "#### Per-model 1T1C timing / hold vs Spectre",
                    "",
                    "| Model | Metric | Backend | Rel Δ |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for _, row in cell_detail.sort_values(["model_id", "metric", "backend"]).iterrows():
                lines.append(
                    f"| {row['model_id']} | {row['metric']} | {row['backend']} | "
                    f"{row['rel_diff']:.4g} |"
                )
            lines.append("")

    if snapshot.mini_array_rel_diff is not None and not snapshot.mini_array_rel_diff.empty:
        mini_summary = summarize_metric_differences(
            snapshot.mini_array_rel_diff, KEY_MINI_ARRAY_METRICS
        )
        if not mini_summary.empty and active_backends:
            mini_filtered = mini_summary[mini_summary["backend"].isin(active_backends)]
            if not mini_filtered.empty:
                lines.extend(
                    [
                        "### Mini-array metrics",
                        "",
                        "| Metric | Backend | max abs Δ | mean abs Δ |",
                        "| --- | --- | --- | --- |",
                    ]
                )
                for _, row in mini_filtered.sort_values(["metric", "backend"]).iterrows():
                    lines.append(
                        f"| {row['metric']} | {row['backend']} | "
                        f"{row['max_abs_rel_diff']:.4g} | {row['mean_abs_rel_diff']:.4g} |"
                    )
                lines.append("")

        if "simulator_mini_array_max_rel_diff" in figures:
            lines.extend(
                [
                    "#### Mini-array simulator agreement",
                    "",
                    "![Mini-array simulator max abs rel diff](figures/simulator_mini_array_max_rel_diff.svg)",
                    "",
                    "*Figure: `figures/simulator_mini_array_max_rel_diff.svg`*",
                    "",
                ]
            )
        if "simulator_mini_array_rel_diff_heatmap" in figures:
            lines.extend(
                [
                    "![Mini-array simulator rel diff heatmap](figures/simulator_mini_array_rel_diff_heatmap.svg)",
                    "",
                    "*Figure: `figures/simulator_mini_array_rel_diff_heatmap.svg`*",
                    "",
                ]
            )
        if "simulator_mini_array_spectre_vs_backend" in figures:
            lines.extend(
                [
                    "![Mini-array Spectre vs backend scatter](figures/simulator_mini_array_spectre_vs_backend.svg)",
                    "",
                    "*Figure: `figures/simulator_mini_array_spectre_vs_backend.svg`*",
                    "",
                ]
            )

        mini_detail = per_model_metric_table(
            snapshot.mini_array_rel_diff, KEY_MINI_ARRAY_METRICS
        )
        if not mini_detail.empty and active_backends:
            mini_detail = mini_detail[mini_detail["backend"].isin(active_backends)]
        if not mini_detail.empty:
            lines.extend(
                [
                    "#### Per-model mini-array vs Spectre",
                    "",
                    "| Model | Metric | Backend | Rel Δ |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for _, row in mini_detail.sort_values(["model_id", "metric", "backend"]).iterrows():
                lines.append(
                    f"| {row['model_id']} | {row['metric']} | {row['backend']} | "
                    f"{row['rel_diff']:.4g} |"
                )
            lines.append("")

    lines.extend(
        [
            "Regenerate pinned comparison:",
            "",
            "```bash",
            "dram-validate simulators --refresh",
            "```",
            "",
        ]
    )
    return lines
