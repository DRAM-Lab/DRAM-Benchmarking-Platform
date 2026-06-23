"""Golden reference metrics for regression checks."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import yaml

from bench.conditions import load_corners
from bench.paths import PROJECT_ROOT

GOLDEN_ROOT = PROJECT_ROOT / "bench" / "device_benchmark" / "golden"
DEFAULT_RTOL = 0.02

GOLDEN_FILES = (
    "device_metrics.csv",
    "cell_1t1c_metrics_20ff.csv",
    "mini_array_metrics.csv",
)


def golden_corner_dir(corner: str = "tt") -> Path:
    """Return golden artifact directory for a corner."""
    return GOLDEN_ROOT / corner


def all_corner_names() -> list[str]:
    """Return ordered corner names from benchmark config."""
    return list(load_corners())


def publish_golden(results_dir: Path, corner: str = "tt") -> list[Path]:
    """Copy reference CSVs from a benchmark run into the golden tree.

    Args:
        results_dir: Corner results directory (e.g. ``results/tt``).
        corner: Corner label.

    Returns:
        List of published golden file paths.
    """
    src = results_dir if (results_dir / "device_metrics.csv").is_file() else results_dir / corner
    dst = golden_corner_dir(corner)
    dst.mkdir(parents=True, exist_ok=True)
    published: list[Path] = []
    for name in GOLDEN_FILES:
        src_file = src / name
        if src_file.is_file():
            out = dst / name
            shutil.copy2(src_file, out)
            published.append(out)

    manifest = {
        "corner": corner,
        "files": [p.name for p in published],
        "rtol": DEFAULT_RTOL,
    }
    manifest_path = dst / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    published.append(manifest_path)
    return published


def publish_all_golden(results_base: Path, corners: list[str] | None = None) -> list[Path]:
    """Publish golden CSVs for every corner present under ``results_base``."""
    published: list[Path] = []
    for corner in corners or all_corner_names():
        corner_dir = results_base / corner
        if (corner_dir / "device_metrics.csv").is_file():
            published.extend(publish_golden(corner_dir, corner=corner))
    return published


def validate_against_golden(
    results_dir: Path,
    corner: str = "tt",
    rtol: float = DEFAULT_RTOL,
) -> list[str]:
    """Compare run CSVs to golden references within relative tolerance.

    Args:
        results_dir: Corner results directory.
        corner: Corner label.
        rtol: Relative tolerance per metric (default 2%).

    Returns:
        List of validation error messages (empty if all pass).

    Raises:
        FileNotFoundError: If golden references are missing.
    """
    src = results_dir if (results_dir / "device_metrics.csv").is_file() else results_dir / corner
    golden = golden_corner_dir(corner)
    if not golden.is_dir():
        raise FileNotFoundError(f"Golden directory missing: {golden}")

    errors: list[str] = []
    numeric_skip = {"corner", "architecture", "model_id", "temp_c", "bl_topology"}

    for name in GOLDEN_FILES:
        ref_path = golden / name
        run_path = src / name
        if not ref_path.is_file():
            errors.append(f"Missing golden file: {ref_path}")
            continue
        if not run_path.is_file():
            errors.append(f"Missing run file: {run_path}")
            continue
        ref_df = pd.read_csv(ref_path)
        run_df = pd.read_csv(run_path)
        if set(ref_df["model_id"]) != set(run_df["model_id"]):
            errors.append(f"{name}: model_id set mismatch")
            continue
        run_df = run_df.set_index("model_id").loc[ref_df["model_id"]]
        ref_df = ref_df.set_index("model_id")
        for col in ref_df.columns:
            if col in numeric_skip:
                continue
            if col not in run_df.columns:
                continue
            ref_vals = pd.to_numeric(ref_df[col], errors="coerce")
            run_vals = pd.to_numeric(run_df[col], errors="coerce")
            for model_id in ref_vals.index:
                ref_v = ref_vals[model_id]
                run_v = run_vals[model_id]
                if pd.isna(ref_v) and pd.isna(run_v):
                    continue
                if pd.isna(ref_v) or pd.isna(run_v):
                    errors.append(f"{corner}/{name}/{model_id}/{col}: NaN mismatch")
                    continue
                denom = max(abs(ref_v), 1e-30)
                if abs(run_v - ref_v) / denom > rtol:
                    errors.append(
                        f"{corner}/{name}/{model_id}/{col}: {run_v:.4e} vs golden {ref_v:.4e} "
                        f"(>{rtol*100:.0f}% rtol)"
                    )
    return errors


def validate_all_golden(
    results_base: Path,
    corners: list[str] | None = None,
    rtol: float = DEFAULT_RTOL,
) -> dict[str, list[str]]:
    """Validate all corners under ``results_base/{corner}/``.

    Returns:
        Mapping of corner name to error list (empty inner list means pass).

    Raises:
        FileNotFoundError: If any golden tree is missing and ``corners`` is explicit.
    """
    summary: dict[str, list[str]] = {}
    for corner in corners or all_corner_names():
        corner_dir = results_base / corner
        if not (corner_dir / "device_metrics.csv").is_file():
            summary[corner] = [f"Missing run results: {corner_dir / 'device_metrics.csv'}"]
            continue
        try:
            summary[corner] = validate_against_golden(corner_dir, corner=corner, rtol=rtol)
        except FileNotFoundError as exc:
            summary[corner] = [str(exc)]
    return summary
