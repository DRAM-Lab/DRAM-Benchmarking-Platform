"""Multi-objective Pareto filtering for roadmap points."""

from __future__ import annotations

import pandas as pd

# Objectives: higher is better for retention; lower is better for the rest.
MAXIMIZE = ("t_ret_s", "t_refresh_s")
MINIMIZE = ("t_rcd_s", "t_wr_s", "e_read_j", "e_write_j", "i_leak_a", "i_leak_density_a_m2")


def _valid_row(row: pd.Series, cols: tuple[str, ...]) -> bool:
    return all(pd.notna(row.get(c)) and row.get(c) is not None for c in cols)


def dominates(a: pd.Series, b: pd.Series, objectives: tuple[str, ...]) -> bool:
    """Return True if point ``a`` Pareto-dominates point ``b``.

    Args:
        a: First point as a pandas Series.
        b: Second point.
        objectives: Metric columns to compare.

    Returns:
        True when ``a`` is at least as good on all objectives and strictly
        better on at least one.
    """
    if not _valid_row(a, objectives) or not _valid_row(b, objectives):
        return False

    at_least_as_good = True
    strictly_better = False
    for col in objectives:
        av, bv = float(a[col]), float(b[col])
        if col in MAXIMIZE:
            if av < bv:
                at_least_as_good = False
                break
            if av > bv:
                strictly_better = True
        elif col in MINIMIZE:
            if av > bv:
                at_least_as_good = False
                break
            if av < bv:
                strictly_better = True
    return at_least_as_good and strictly_better


def pareto_mask(df: pd.DataFrame, objectives: tuple[str, ...]) -> pd.Series:
    """Compute non-dominated mask for a set of roadmap points.

    Args:
        df: Input dataframe with metric columns.
        objectives: Columns participating in dominance.

    Returns:
        Boolean Series — True for Pareto-optimal rows.
    """
    valid = df[list(objectives)].notna().all(axis=1)
    indices = df.index[valid].tolist()
    is_pareto = {idx: True for idx in indices}

    for i, idx_i in enumerate(indices):
        if not is_pareto[idx_i]:
            continue
        row_i = df.loc[idx_i]
        for idx_j in indices[i + 1 :]:
            if not is_pareto.get(idx_j, True):
                continue
            row_j = df.loc[idx_j]
            if dominates(row_i, row_j, objectives):
                is_pareto[idx_j] = False
            elif dominates(row_j, row_i, objectives):
                is_pareto[idx_i] = False
                break

    return pd.Series({idx: is_pareto.get(idx, False) for idx in df.index})


def filter_pareto_front(
    df: pd.DataFrame,
    objectives: tuple[str, ...] = ("t_ret_s", "t_rcd_s", "e_read_j", "i_leak_a"),
    *,
    by: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Return non-dominated subset, optionally per group.

    Args:
        df: Full roadmap database.
        objectives: Metrics for dominance (defaults to core retention/performance triple + leak).
        by: Optional group columns (e.g. ``("corner", "ccell_ff")``).

    Returns:
        Filtered dataframe with ``pareActive`` column removed; only Pareto points.
    """
    present = tuple(c for c in objectives if c in df.columns)
    if not present:
        raise ValueError(f"No objective columns found in dataframe: {objectives}")

    if by:
        parts: list[pd.DataFrame] = []
        for _, group in df.groupby(list(by), sort=False):
            mask = pareto_mask(group, present)
            parts.append(group.loc[mask])
        return pd.concat(parts, ignore_index=True)

    mask = pareto_mask(df, present)
    return df.loc[mask].copy()


def rank_by_objective(
    df: pd.DataFrame,
    objective: str,
    *,
    ascending: bool | None = None,
) -> pd.DataFrame:
    """Sort points by a single objective.

    Args:
        df: Input dataframe.
        objective: Column to sort by.
        ascending: Sort direction; inferred from MAXIMIZE/MINIMIZE when None.

    Returns:
        Sorted copy.
    """
    if ascending is None:
        ascending = objective not in MAXIMIZE
    return df.sort_values(objective, ascending=ascending, na_position="last").copy()
