"""Build Ccell sweep database from Pareto roadmap, device-benchmark, and analytics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from bench.models import ACCESS_MODEL_IDS, load_access_model
from pareto.config import load_pareto_config
from pareto.derive import derive_pareto_points
from pareto.extract.retention import t_ret_from_leakage

from ccell.config import CcellConfig, load_ccell_config
from ccell.metrics import CcellSweepPoint
from ccell.paths import (
    load_all_sense_amp_signals,
    resolve_bench_results,
    resolve_pareto_results,
    resolve_sense_amp_csv,
)
from ccell.read_signal import (
    load_sense_amp_dataframe,
    resolve_dv_read,
)

_INTERPOLATE_COLUMNS = ("t_ret_s", "e_read_j", "i_leak_a", "dv_read_v")
_SOURCE_RANK = {
    "simulation": 6,
    "derived_from_pareto": 5,
    "derived_from_device_bench": 5,
    "derived_from_golden_bench": 4,
    "sense_amp_csv": 4,
    "interpolated_ccell": 3,
    "analytic_read": 3,
    "analytic_read_only": 2,
    "scaled_from_leakage": 1,
    "extrapolated_read": 2,
}


def dedupe_sweep_points(points: list[CcellSweepPoint]) -> list[CcellSweepPoint]:
    """Keep the highest-quality row per (model, corner, Ccell)."""
    best: dict[tuple[str, str, float], CcellSweepPoint] = {}
    for pt in points:
        key = (pt.model_id, pt.corner, float(pt.ccell_ff))
        rank = _SOURCE_RANK.get(pt.source, 2)
        prev = best.get(key)
        if prev is None:
            best[key] = pt
            continue
        prev_rank = _SOURCE_RANK.get(prev.source, 2)
        if rank > prev_rank:
            best[key] = pt
            continue
        if rank == prev_rank and pt.t_ret_s is not None and prev.t_ret_s is None:
            best[key] = pt
    return sorted(
        best.values(),
        key=lambda p: (p.model_id, p.corner, p.ccell_ff),
    )


def _pareto_csv_path(pareto_root: Path | None) -> Path | None:
    if pareto_root is None:
        return None
    for candidate in (
        pareto_root / "pareto_roadmap.csv",
        pareto_root / "ngspice" / "pareto_roadmap.csv",
        pareto_root / "spectre" / "pareto_roadmap.csv",
    ):
        if candidate.is_file():
            return candidate
    return None


def _load_pareto_dataframe(pareto_root: Path | None) -> pd.DataFrame:
    csv_path = _pareto_csv_path(pareto_root)
    if csv_path is not None:
        return pd.read_csv(csv_path)
    return pd.DataFrame()


def _expand_ccell_from_leakage(
    model_id: str,
    architecture: str,
    corner: str,
    temp_c: float,
    vdd: float,
    fpitch_m: float,
    i_leak_a: float,
    cfg: CcellConfig,
    *,
    source: str,
) -> list[CcellSweepPoint]:
    """Scale retention linearly with Ccell for fixed leakage current."""
    points: list[CcellSweepPoint] = []
    for ccell in cfg.ccell_values_ff:
        t_ret = t_ret_from_leakage(abs(i_leak_a), ccell, cfg.retention.delta_v_v)
        points.append(
            CcellSweepPoint(
                model_id=model_id,
                architecture=architecture,
                corner=corner,
                ccell_ff=ccell,
                temp_c=temp_c,
                vdd=vdd,
                fpitch_m=fpitch_m,
                t_ret_s=t_ret,
                i_leak_a=abs(i_leak_a),
                source=source,
            )
        )
    return points


def _sense_amp_for_corner(
    sense_amp_df: pd.DataFrame | None,
    corner: str,
) -> pd.DataFrame | None:
    if sense_amp_df is None or sense_amp_df.empty:
        return None
    if "corner" not in sense_amp_df.columns:
        return sense_amp_df
    subset = sense_amp_df[sense_amp_df["corner"].astype(str) == corner]
    return subset if not subset.empty else None


def _attach_dv_read(
    points: list[CcellSweepPoint],
    cfg: CcellConfig,
    sense_amp_df: pd.DataFrame | None,
) -> list[CcellSweepPoint]:
    """Fill read-signal column from sense-amp CSV or analytic model."""
    updated: list[CcellSweepPoint] = []
    for pt in points:
        dv = pt.dv_read_v
        source = pt.source
        corner_sense = _sense_amp_for_corner(sense_amp_df, pt.corner)
        if dv is None and corner_sense is not None:
            model = load_access_model(pt.model_id)
            dv, source = resolve_dv_read(model, pt.ccell_ff, cfg, corner_sense)
        elif dv is None and pt.corner == cfg.read_corner:
            model = load_access_model(pt.model_id)
            dv, source = resolve_dv_read(model, pt.ccell_ff, cfg, sense_amp_df)
        updated.append(
            CcellSweepPoint(
                model_id=pt.model_id,
                architecture=pt.architecture,
                corner=pt.corner,
                ccell_ff=pt.ccell_ff,
                temp_c=pt.temp_c,
                vdd=pt.vdd,
                fpitch_m=pt.fpitch_m,
                t_ret_s=pt.t_ret_s,
                dv_read_v=dv,
                e_read_j=pt.e_read_j,
                i_leak_a=pt.i_leak_a,
                source=source if dv is not None and source != pt.source else pt.source,
                simulator=pt.simulator,
            )
        )
    return updated


def _sweep_corners(cfg: CcellConfig, bench: Path) -> list[str]:
    """Return all PVT corners when multi-corner bench exports exist."""
    if (bench / "device_metrics_all_corners.csv").is_file():
        from bench.conditions import load_corners

        return list(load_corners())
    return [cfg.retention_corner, cfg.read_corner]


def _extend_read_extrapolation(
    points: list[CcellSweepPoint],
    cfg: CcellConfig,
    sense_amp_df: pd.DataFrame | None,
) -> list[CcellSweepPoint]:
    """Add analytic read-corner rows for Ccell values beyond upstream sim range."""
    extras: list[CcellSweepPoint] = []
    existing = {(p.model_id, p.corner, p.ccell_ff) for p in points}
    targets = set(cfg.read_extrapolate_ccell_ff) or {
        c for c in cfg.ccell_values_ff if c > 50.0
    }
    for model_id in ACCESS_MODEL_IDS:
        model = load_access_model(model_id)
        anchor = next(
            (p for p in points if p.model_id == model_id and p.corner == cfg.read_corner),
            None,
        )
        if anchor is None:
            continue
        for ccell in sorted(targets):
            key = (model_id, cfg.read_corner, ccell)
            if key in existing:
                continue
            corner_sense = _sense_amp_for_corner(sense_amp_df, cfg.read_corner)
            dv, source = resolve_dv_read(model, ccell, cfg, corner_sense or sense_amp_df)
            extras.append(
                CcellSweepPoint(
                    model_id=model_id,
                    architecture=model.architecture,
                    corner=cfg.read_corner,
                    ccell_ff=ccell,
                    temp_c=anchor.temp_c,
                    vdd=anchor.vdd,
                    fpitch_m=anchor.fpitch_m,
                    dv_read_v=dv,
                    source="extrapolated_read" if source == "analytic_read" else source,
                )
            )
    return points + extras


def _dual_corner_binding(points: list[CcellSweepPoint], cfg: CcellConfig) -> list[CcellSweepPoint]:
    """Legacy hot-retention + tt-read binding when only dual corners are available."""
    read_points: list[CcellSweepPoint] = []
    for model_id in ACCESS_MODEL_IDS:
        model = load_access_model(model_id)
        existing = [p for p in points if p.model_id == model_id and p.corner == cfg.read_corner]
        if existing:
            read_points.extend(existing)
            continue
        for ccell in cfg.ccell_values_ff:
            read_points.append(
                CcellSweepPoint(
                    model_id=model_id,
                    architecture=model.architecture,
                    corner=cfg.read_corner,
                    ccell_ff=ccell,
                    temp_c=27.0,
                    vdd=model.nominal_vdd,
                    fpitch_m=model.fpitch_m,
                    source="analytic_read_only",
                )
            )
    ret_points = [p for p in points if p.corner == cfg.retention_corner]
    return dedupe_sweep_points(
        ret_points
        + [
            p
            for p in read_points
            if (p.model_id, p.corner, p.ccell_ff)
            not in {(x.model_id, x.corner, x.ccell_ff) for x in ret_points}
        ]
    )


def _interpolate_ccell_sweep(
    points: list[CcellSweepPoint],
    cfg: CcellConfig,
) -> list[CcellSweepPoint]:
    """Linearly interpolate missing Ccell values per (model, corner)."""
    if not points:
        return points

    df = points_to_dataframe(points)
    target = set(cfg.ccell_values_ff)
    extras: list[CcellSweepPoint] = []

    for (model_id, corner), group in df.groupby(["model_id", "corner"], sort=False):
        measured = sorted(set(group["ccell_ff"].astype(float)))
        missing = sorted(target - set(measured))
        if not missing or len(measured) < 2:
            continue
        base = group.iloc[0]
        for ccell in missing:
            row: dict[str, float | str | None] = {
                "model_id": model_id,
                "architecture": base["architecture"],
                "corner": corner,
                "ccell_ff": ccell,
                "temp_c": base["temp_c"],
                "vdd": base["vdd"],
                "fpitch_m": base["fpitch_m"],
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
                row[col] = float(np.interp(ccell, x, y))
            extras.append(CcellSweepPoint(**row))  # type: ignore[arg-type]

    return points + extras


def derive_ccell_sweep(
    bench_root: Path | None = None,
    pareto_root: Path | None = None,
    config: CcellConfig | None = None,
) -> list[CcellSweepPoint]:
    """Build Ccell sweep database without native SPICE."""
    cfg = config or load_ccell_config()
    bench = bench_root or resolve_bench_results()
    pareto_root = pareto_root if pareto_root is not None else resolve_pareto_results()
    pareto_df = _load_pareto_dataframe(pareto_root)
    sweep_corners = _sweep_corners(cfg, bench)
    full_corner_sweep = len(sweep_corners) > 2

    points: list[CcellSweepPoint] = []
    sense_amp_df = load_all_sense_amp_signals()
    if sense_amp_df is None:
        sense_amp_df = load_sense_amp_dataframe(resolve_sense_amp_csv(cfg.read_corner))

    if not pareto_df.empty:
        for corner in sweep_corners:
            subset = pareto_df[pareto_df["corner"] == corner]
            for _, row in subset.iterrows():
                ccell = float(row["ccell_ff"])
                if ccell not in cfg.ccell_values_ff:
                    continue
                points.append(
                    CcellSweepPoint(
                        model_id=str(row["model_id"]),
                        architecture=str(row["architecture"]),
                        corner=corner,
                        ccell_ff=ccell,
                        temp_c=float(row.get("temp_c", 27.0)),
                        vdd=float(row.get("vdd", 0.0)),
                        fpitch_m=float(row.get("fpitch_m", 0.0)),
                        t_ret_s=float(row["t_ret_s"]) if pd.notna(row.get("t_ret_s")) else None,
                        e_read_j=float(row["e_read_j"]) if pd.notna(row.get("e_read_j")) else None,
                        i_leak_a=float(row["i_leak_a"]) if pd.notna(row.get("i_leak_a")) else None,
                        source=str(row.get("source", "derived_from_pareto")),
                        simulator=row.get("simulator"),
                    )
                )

    pareto_cfg = load_pareto_config()
    for corner in sweep_corners:
        derived = derive_pareto_points(bench_root=bench, config=pareto_cfg, corners=[corner])
        for pt in derived:
            if pt.ccell_ff not in cfg.ccell_values_ff:
                continue
            existing = {
                (p.model_id, p.corner, p.ccell_ff)
                for p in points
            }
            key = (pt.model_id, corner, pt.ccell_ff)
            if key in existing:
                continue
            points.append(
                CcellSweepPoint(
                    model_id=pt.model_id,
                    architecture=pt.architecture,
                    corner=corner,
                    ccell_ff=pt.ccell_ff,
                    temp_c=pt.temp_c,
                    vdd=pt.vdd,
                    fpitch_m=pt.fpitch_m,
                    t_ret_s=pt.t_ret_s,
                    e_read_j=pt.e_read_j,
                    i_leak_a=pt.i_leak_a,
                    source=pt.source,
                )
            )

    # Expand retention sweep from leakage only when no simulated hold data exists.
    expanded: list[CcellSweepPoint] = []
    seen_leakage: set[tuple[str, str]] = set()
    sim_retention = {
        (p.model_id, p.corner)
        for p in points
        if p.source == "simulation" and p.t_ret_s is not None
    }
    for pt in points:
        expanded.append(pt)
        if pt.i_leak_a is None or pt.i_leak_a <= 0:
            continue
        key = (pt.model_id, pt.corner)
        if key in seen_leakage or key in sim_retention:
            continue
        seen_leakage.add(key)
        model_ccells = {
            p.ccell_ff for p in points if p.model_id == pt.model_id and p.corner == pt.corner
        }
        if len(model_ccells) >= len(cfg.ccell_values_ff):
            continue
        expanded.extend(
            _expand_ccell_from_leakage(
                pt.model_id,
                pt.architecture,
                pt.corner,
                pt.temp_c,
                pt.vdd,
                pt.fpitch_m,
                pt.i_leak_a,
                cfg,
                source="scaled_from_leakage",
            )
        )

    points = dedupe_sweep_points(_interpolate_ccell_sweep(expanded, cfg))

    if full_corner_sweep:
        merged = _attach_dv_read(points, cfg, sense_amp_df)
    else:
        merged = _dual_corner_binding(points, cfg)
        merged = _attach_dv_read(merged, cfg, sense_amp_df)
    return dedupe_sweep_points(_extend_read_extrapolation(merged, cfg, sense_amp_df))


def dedupe_sweep_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate a sweep CSV dataframe by source quality rank."""
    if df.empty:
        return df
    points: list[CcellSweepPoint] = []
    for row in df.to_dict("records"):
        points.append(
            CcellSweepPoint(
                model_id=str(row["model_id"]),
                architecture=str(row["architecture"]),
                corner=str(row["corner"]),
                ccell_ff=float(row["ccell_ff"]),
                temp_c=float(row.get("temp_c", 27.0)),
                vdd=float(row.get("vdd", 0.0)),
                fpitch_m=float(row.get("fpitch_m", 0.0)),
                t_ret_s=row.get("t_ret_s") if pd.notna(row.get("t_ret_s")) else None,
                dv_read_v=row.get("dv_read_v") if pd.notna(row.get("dv_read_v")) else None,
                e_read_j=row.get("e_read_j") if pd.notna(row.get("e_read_j")) else None,
                i_leak_a=row.get("i_leak_a") if pd.notna(row.get("i_leak_a")) else None,
                source=str(row.get("source", "derived")),
                simulator=row.get("simulator"),
            )
        )
    return points_to_dataframe(dedupe_sweep_points(points))


def points_to_dataframe(points: list[CcellSweepPoint]) -> pd.DataFrame:
    """Convert sweep points to a pandas DataFrame."""
    if not points:
        return pd.DataFrame()
    return pd.DataFrame([p.as_dict() for p in points])
