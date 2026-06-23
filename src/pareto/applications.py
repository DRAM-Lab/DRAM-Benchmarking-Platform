"""Application-specific architecture recommendations from Pareto frontiers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pareto.config import ApplicationProfile, ParetoConfig, load_pareto_config
from pareto.pareto import MINIMIZE, filter_pareto_front


@dataclass(frozen=True)
class ApplicationRecommendation:
    """Best architecture pick for one market segment."""

    profile: str
    model_id: str
    architecture: str
    corner: str
    ccell_ff: float
    t_ret_s: float
    target_t_ret_s: float
    retention_gap_s: float
    meets_target: bool
    t_rcd_s: float | None
    e_read_j: float | None
    i_leak_a: float | None
    score: float
    meets_retention: bool


def _normalize(series: pd.Series, *, invert: bool = False) -> pd.Series:
    """Min-max normalize to [0, 1]; lower raw values → higher score when invert."""
    vals = pd.to_numeric(series, errors="coerce")
    if vals.notna().sum() == 0:
        return pd.Series(0.0, index=series.index)
    vmin, vmax = vals.min(), vals.max()
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        norm = pd.Series(1.0, index=series.index)
    else:
        norm = (vals - vmin) / (vmax - vmin)
    return 1.0 - norm if invert else norm


def _score_candidates(front: pd.DataFrame, profile: ApplicationProfile) -> pd.Series:
    """Score Pareto candidates on normalized objectives."""
    scores = pd.Series(0.0, index=front.index)
    for col in profile.optimize:
        if col not in front.columns:
            continue
        invert = col in MINIMIZE
        weight = profile.weight_energy if "e_" in col else 1.0
        if col == "t_ret_s" and "t_ret_s" in MINIMIZE:
            invert = False
        scores = scores + weight * _normalize(front[col], invert=invert)
    return scores


def recommend_for_profile(
    df: pd.DataFrame,
    profile: ApplicationProfile,
    *,
    ccell_ff: float | None = None,
    search_ccell_sweep: bool = False,
    ccell_values: tuple[float, ...] | None = None,
) -> ApplicationRecommendation | None:
    """Select the best architecture for an application anchor.

    When ``search_ccell_sweep`` is True, tries larger Ccell values first so JEDEC
    retention targets can be met via cap scaling.
    """
    if search_ccell_sweep and ccell_ff is None:
        sweep_vals = ccell_values or tuple(sorted(df["ccell_ff"].unique(), reverse=True))
        sweep = tuple(sorted(sweep_vals, reverse=True))
        for ccell in sweep:
            rec = recommend_for_profile(
                df,
                profile,
                ccell_ff=float(ccell),
                search_ccell_sweep=False,
            )
            if rec is not None:
                return rec
        return None

    subset = df[df["corner"] == profile.corner].copy()
    if subset.empty:
        return None

    if ccell_ff is not None:
        subset = subset[subset["ccell_ff"] == ccell_ff]
    else:
        subset = subset.sort_values("ccell_ff").groupby("model_id", as_index=False).first()

    subset = subset[subset["t_ret_s"].notna()]
    qualified = subset[subset["t_ret_s"] >= profile.min_t_ret_s]
    if qualified.empty:
        return None

    objectives = tuple(c for c in profile.optimize if c in qualified.columns)
    if "t_ret_s" not in objectives and "t_ret_s" in qualified.columns:
        objectives = ("t_ret_s",) + objectives

    front = filter_pareto_front(qualified, objectives=objectives, by=("corner",))
    if front.empty:
        front = qualified

    scores = _score_candidates(front, profile)
    if scores.isna().all() or len(scores) == 0:
        best_idx = front.index[0]
    else:
        scores = scores.fillna(scores.min())
        best_idx = scores.idxmax()
    row = front.loc[best_idx]
    t_ret = float(row["t_ret_s"])
    return ApplicationRecommendation(
        profile=profile.name,
        model_id=str(row["model_id"]),
        architecture=str(row["architecture"]),
        corner=str(row["corner"]),
        ccell_ff=float(row["ccell_ff"]),
        t_ret_s=t_ret,
        target_t_ret_s=profile.target_t_ret_s,
        retention_gap_s=t_ret - profile.target_t_ret_s,
        meets_target=t_ret >= profile.target_t_ret_s,
        t_rcd_s=float(row["t_rcd_s"]) if pd.notna(row.get("t_rcd_s")) else None,
        e_read_j=float(row["e_read_j"]) if pd.notna(row.get("e_read_j")) else None,
        i_leak_a=float(row["i_leak_a"]) if pd.notna(row.get("i_leak_a")) else None,
        score=float(scores.loc[best_idx]),
        meets_retention=True,
    )


def recommend_all_profiles(
    df: pd.DataFrame,
    config: ParetoConfig | None = None,
    *,
    ccell_ff: float | None = None,
) -> list[ApplicationRecommendation]:
    """Generate recommendations for all configured application segments."""
    cfg = config or load_pareto_config()
    recs: list[ApplicationRecommendation] = []
    ref_ccell = ccell_ff if ccell_ff is not None else cfg.reference_ccell_ff
    sweep = tuple(sorted(cfg.ccell_values_ff, reverse=True))
    for profile in cfg.applications.values():
        rec = recommend_for_profile(
            df,
            profile,
            search_ccell_sweep=True,
            ccell_values=sweep,
        )
        if rec is not None:
            recs.append(rec)
    return recs


def recommend_best_effort_profiles(
    df: pd.DataFrame,
    config: ParetoConfig | None = None,
    *,
    ccell_ff: float | None = None,
) -> list[ApplicationRecommendation]:
    """Fallback recommendations ignoring JEDEC retention gate (gap still reported)."""
    cfg = config or load_pareto_config()
    recs: list[ApplicationRecommendation] = []
    ref_ccell = ccell_ff if ccell_ff is not None else cfg.reference_ccell_ff
    for profile in cfg.applications.values():
        relaxed = ApplicationProfile(
            name=profile.name,
            min_t_ret_s=0.0,
            target_t_ret_s=profile.target_t_ret_s,
            corner=profile.corner,
            optimize=profile.optimize,
            weight_energy=profile.weight_energy,
        )
        rec = recommend_for_profile(df, relaxed, ccell_ff=ref_ccell)
        if rec is not None:
            recs.append(rec)
    return recs


def jedec_qualification_table(
    df: pd.DataFrame,
    config: ParetoConfig | None = None,
    *,
    ccell_ff: float | None = None,
) -> pd.DataFrame:
    """Build per-model JEDEC retention qualification matrix."""
    cfg = config or load_pareto_config()
    ref_ccell = ccell_ff if ccell_ff is not None else cfg.reference_ccell_ff
    rows: list[dict[str, object]] = []
    for profile in cfg.applications.values():
        for ccell in sorted(set(cfg.ccell_values_ff), reverse=True):
            subset = df[(df["corner"] == profile.corner) & (df["ccell_ff"] == ccell)]
            for _, row in subset.iterrows():
                t_ret = float(row["t_ret_s"]) if pd.notna(row.get("t_ret_s")) else None
                t_ref = float(row["t_refresh_s"]) if pd.notna(row.get("t_refresh_s")) else None
                rows.append(
                    {
                        "profile": profile.name,
                        "model_id": row["model_id"],
                        "corner": row["corner"],
                        "ccell_ff": ccell,
                        "t_ret_ms": t_ret * 1e3 if t_ret else None,
                        "t_refresh_ms": t_ref * 1e3 if t_ref else None,
                        "jedec_target_ms": profile.target_t_ret_s * 1e3,
                        "meets_t_ret": t_ret is not None and t_ret >= profile.min_t_ret_s,
                        "meets_t_refresh": t_ref is not None and t_ref >= profile.min_t_ret_s,
                        "source": row.get("source"),
                    }
                )
    return pd.DataFrame(rows)


def recommendations_to_dataframe(recs: list[ApplicationRecommendation]) -> pd.DataFrame:
    """Convert recommendations to a pandas DataFrame."""
    if not recs:
        return pd.DataFrame()
    return pd.DataFrame([r.__dict__ for r in recs])
