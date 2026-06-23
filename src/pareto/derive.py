"""Derive Pareto points from OpenDRAM-device-benchmark CSV exports."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from bench.models import load_access_model
from pareto.config import ParetoConfig, load_pareto_config
from pareto.metrics import ParetoPoint, compute_t_refresh
from pareto.paths import DEFAULT_BENCH_RESULTS, PROJECT_ROOT, resolve_bench_results

_GOLDEN_BENCH_ROOT = PROJECT_ROOT / "bench" / "device_benchmark" / "golden"

_INTERPOLATE_COLUMNS = (
    "t_ret_s",
    "t_refresh_s",
    "t_rcd_s",
    "t_wr_s",
    "e_read_j",
    "e_write_j",
    "i_leak_a",
    "i_leak_density_a_m2",
)


def _device_csv_has_leakage(device_df: pd.DataFrame) -> bool:
    """Return True when device export has non-zero off-state leakage."""
    if "ioff_a" in device_df.columns and device_df["ioff_a"].notna().any():
        return bool((device_df["ioff_a"].fillna(0.0) != 0.0).any())
    return False


def _cell_csv_has_hold_data(cell_df: pd.DataFrame) -> bool:
    """Return True when at least one row has usable hold leakage."""
    if "i_hold_a" in cell_df.columns and cell_df["i_hold_a"].notna().any():
        return True
    return False


def _expand_cell_ccell_sweep(cell_df: pd.DataFrame, ccells: tuple[float, ...]) -> pd.DataFrame:
    """Duplicate reference rows across configured Ccell values."""
    if cell_df.empty:
        return cell_df
    rows: list[dict[str, object]] = []
    for _, base in cell_df.iterrows():
        for ccell in ccells:
            row = base.to_dict()
            row["ccell_ff"] = float(ccell)
            rows.append(row)
    return pd.DataFrame(rows)


def _load_corner_tables(
    bench_root: Path,
    corner: str,
    cfg: ParetoConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, str] | None:
    """Load merged device + 1T1C tables, falling back to golden references."""
    device_path, cell_path = _resolve_metrics_paths(bench_root, corner)
    if not device_path.is_file():
        return None

    device_df = pd.read_csv(device_path)
    if "corner" in device_df.columns:
        device_df = device_df[device_df["corner"] == corner]

    cell_df = pd.read_csv(cell_path) if cell_path.is_file() else pd.DataFrame()
    if "corner" in cell_df.columns and not cell_df.empty:
        cell_df = cell_df[cell_df["corner"] == corner]

    source = "derived_from_device_bench"
    use_golden = cell_df.empty or not _cell_csv_has_hold_data(cell_df) or not _device_csv_has_leakage(device_df)
    if use_golden:
        golden_dir = _GOLDEN_BENCH_ROOT / corner
        g_device = golden_dir / "device_metrics.csv"
        g_cell = golden_dir / "cell_1t1c_metrics_20ff.csv"
        if g_device.is_file() and g_cell.is_file():
            device_df = pd.read_csv(g_device)
            cell_df = _expand_cell_ccell_sweep(pd.read_csv(g_cell), cfg.ccell_values_ff)
            if "corner" in device_df.columns:
                device_df = device_df[device_df["corner"] == corner]
            if "corner" in cell_df.columns:
                cell_df = cell_df[cell_df["corner"] == corner]
            source = "derived_from_golden_bench"
        elif cell_df.empty:
            return None

    return device_df, cell_df, source


def _resolve_metrics_paths(bench_root: Path, corner: str) -> tuple[Path, Path]:
    """Locate device and 1T1C CSV files for a corner."""
    if corner == "all":
        device = bench_root / "device_metrics_all_corners.csv"
        cell = bench_root / "cell_1t1c_metrics_all_corners.csv"
        return device, cell

    device = bench_root / corner / "device_metrics.csv"
    cell = bench_root / corner / "cell_1t1c_metrics.csv"
    if device.is_file():
        return device, cell

    flat_device = bench_root / "device_metrics.csv"
    flat_cell = bench_root / "cell_1t1c_metrics.csv"
    if flat_device.is_file():
        return flat_device, flat_cell

    return (
        bench_root / "device_metrics_all_corners.csv",
        bench_root / "cell_1t1c_metrics_all_corners.csv",
    )


def _append_merged_rows(
    merged: pd.DataFrame,
    cfg: ParetoConfig,
    points: list[ParetoPoint],
    *,
    source: str,
) -> None:
    """Append Pareto points from a merged device + 1T1C dataframe."""
    for _, row in merged.iterrows():
        ccell = float(row["ccell_ff"])
        if ccell not in cfg.ccell_values_ff and ccell not in (10.0, 20.0, 30.0):
            continue
        model_id = str(row["model_id"])
        try:
            fpitch = load_access_model(model_id).fpitch_m
        except (FileNotFoundError, ValueError):
            fpitch = float(row.get("fpitch_m", 0.0) or 0.0)
        point = _row_to_point(row, cfg, fpitch, source)
        if point.t_ret_s is None and point.t_rcd_s is None:
            continue
        points.append(point)


def _row_to_point(row: pd.Series, cfg: ParetoConfig, fpitch: float, source: str) -> ParetoPoint:
    """Convert one merged benchmark row to a ParetoPoint."""
    delta_v = cfg.retention.delta_v_v
    ccell = float(row["ccell_ff"])
    i_hold = row.get("i_hold_a")
    if pd.notna(i_hold) and float(i_hold) != 0.0:
        i_leak = abs(float(i_hold))
    else:
        ioff = row.get("ioff_a")
        i_leak = abs(float(ioff)) if pd.notna(ioff) and float(ioff) != 0.0 else None
    t_ret = None
    if i_leak is not None and float(i_leak) > 0:
        t_ret = (delta_v * ccell * 1e-15) / abs(float(i_leak))

    t_read = row.get("t_read_s")
    t_write = row.get("t_write_s")
    t_rcd = float(t_read) - cfg.performance.wl_read_rise_s if pd.notna(t_read) else None
    t_wr = float(t_write) - cfg.performance.write_start_s if pd.notna(t_write) else None

    q_read = row.get("q_read_c")
    vdd = float(row.get("vdd", 0.0) or 0.0)
    e_read = float(q_read) * vdd if pd.notna(q_read) and vdd else row.get("esw_j")
    e_write = row.get("esw_j")

    i_leak_f = float(i_leak) if i_leak is not None and pd.notna(i_leak) else None
    i_leak_density = i_leak_f / (fpitch**2) if i_leak_f and fpitch > 0 else None

    return ParetoPoint(
        model_id=str(row["model_id"]),
        architecture=str(row["architecture"]),
        corner=str(row["corner"]),
        ccell_ff=ccell,
        temp_c=float(row.get("temp_c", 27.0)),
        vdd=vdd,
        fpitch_m=fpitch,
        t_ret_s=t_ret,
        t_refresh_s=compute_t_refresh(t_ret),
        t_rcd_s=t_rcd,
        t_wr_s=t_wr,
        e_read_j=float(e_read) if e_read is not None and pd.notna(e_read) else None,
        e_write_j=float(e_write) if e_write is not None and pd.notna(e_write) else None,
        i_leak_a=i_leak_f,
        i_leak_density_a_m2=i_leak_density,
        source=source,
    )


def _interpolate_ccell_points(points: list[ParetoPoint], cfg: ParetoConfig) -> list[ParetoPoint]:
    """Linearly interpolate missing Ccell sweep values from measured rows."""
    if not points:
        return points

    df = points_to_dataframe(points)
    target_ccells = set(cfg.ccell_values_ff)
    extras: list[ParetoPoint] = []

    for (model_id, corner), group in df.groupby(["model_id", "corner"], sort=False):
        measured = sorted(set(group["ccell_ff"].astype(float)))
        missing = sorted(target_ccells - set(measured))
        if not missing or len(measured) < 2:
            continue

        base_row = group.iloc[0]
        for ccell in missing:
            interp: dict[str, float | str | None] = {
                "model_id": model_id,
                "architecture": base_row["architecture"],
                "corner": corner,
                "ccell_ff": ccell,
                "temp_c": base_row["temp_c"],
                "vdd": base_row["vdd"],
                "fpitch_m": base_row["fpitch_m"],
                "source": "interpolated_ccell",
            }
            for col in _INTERPOLATE_COLUMNS:
                if col not in group.columns:
                    continue
                series = group.set_index("ccell_ff")[col].astype(float)
                values = series.reindex(measured).dropna()
                if len(values) < 2:
                    continue
                x = values.index.to_numpy(dtype=float)
                y = values.to_numpy(dtype=float)
                interp[col] = float(np.interp(ccell, x, y))
            if interp.get("t_ret_s") is not None and interp.get("t_refresh_s") is None:
                interp["t_refresh_s"] = compute_t_refresh(float(interp["t_ret_s"]))
            extras.append(ParetoPoint(**interp))  # type: ignore[arg-type]

    return points + extras


def derive_pareto_points(
    bench_root: Path | None = None,
    config: ParetoConfig | None = None,
    corners: list[str] | None = None,
) -> list[ParetoPoint]:
    """Build roadmap points from device-benchmark CSVs (fast path without Spectre).

    Prefers ``*_all_corners.csv`` when available (includes hot @ 85 °C). Missing
    Ccell values (15 fF, 50 fF) are linearly interpolated from measured 10/20/30 fF
    sweeps.
    """
    root = bench_root or resolve_bench_results()
    cfg = config or load_pareto_config()
    corner_list = corners or list(cfg.pareto_corners)
    points: list[ParetoPoint] = []

    for corner in corner_list:
        loaded = _load_corner_tables(root, corner, cfg)
        if loaded is None:
            continue
        device_df, cell_df, source = loaded
        merged = cell_df.merge(
            device_df[
                ["model_id", "corner", "temp_c", "vdd", "fpitch_m", "ioff_a", "esw_j"]
            ],
            on=["model_id", "corner"],
            how="left",
        )
        _append_merged_rows(merged, cfg, points, source=source)

    return _interpolate_ccell_points(points, cfg)


def points_to_dataframe(points: list[ParetoPoint]) -> pd.DataFrame:
    """Convert Pareto points to a pandas DataFrame."""
    if not points:
        return pd.DataFrame()
    return pd.DataFrame([p.as_dict() for p in points])
