"""Structured validation result tables for reporting and plots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from validation.golden import (
    ACCESS_MODEL_IDS,
    ALL_MODEL_IDS,
    CELL_ONLY_COLUMNS,
    GoldenSpec,
    load_all_golden_specs,
    validate_all_golden,
    validate_trends,
)


@dataclass(frozen=True)
class ValidationRun:
    """Aggregated outcome of one validation pass."""

    model_summary: pd.DataFrame
    metric_detail: pd.DataFrame
    trend_detail: pd.DataFrame
    errors_by_model: dict[str, list[str]]
    trend_errors: list[str]

    @property
    def all_passed(self) -> bool:
        """True when every model and trend check passed."""
        return (
            self.model_summary["status"].eq("PASS").all()
            and not self.trend_errors
        )

    @property
    def pass_count(self) -> int:
        """Number of models with PASS status."""
        return int(self.model_summary["status"].eq("PASS").sum())

    @property
    def fail_count(self) -> int:
        """Number of models with FAIL status."""
        return int(self.model_summary["status"].eq("FAIL").sum())


def _observed_value(
    spec: GoldenSpec,
    band_name: str,
    device_row: dict[str, Any] | None,
    cell_row: dict[str, Any] | None,
    card_row: dict[str, Any] | None,
) -> float | None:
    """Look up observed metric for one golden band."""
    band = spec.metrics[band_name]
    row = card_row if spec.model_id not in ACCESS_MODEL_IDS else None
    if row is None:
        row = cell_row if band.column in CELL_ONLY_COLUMNS else device_row
    if row is None:
        return None
    val = row.get(band.column)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return float(val)


def build_metric_detail(
    device_df: pd.DataFrame,
    cell_df: pd.DataFrame | None,
    card_metrics: dict[str, dict[str, float]] | None,
    errors_by_model: dict[str, list[str]],
) -> pd.DataFrame:
    """Build per-metric validation detail table.

    Args:
        device_df: Device metrics CSV data.
        cell_df: Optional 1T1C metrics.
        card_metrics: Optional card-level metrics for periphery models.
        errors_by_model: Validation errors keyed by model_id.

    Returns:
        DataFrame with one row per model/metric check.
    """
    specs = load_all_golden_specs()
    rows: list[dict[str, Any]] = []

    for model_id, spec in specs.items():
        device_row = None
        subset = device_df[device_df["model_id"] == model_id]
        if not subset.empty:
            device_row = subset.iloc[0].to_dict()

        cell_row = None
        if cell_df is not None:
            csub = cell_df[cell_df["model_id"] == model_id]
            if not csub.empty:
                cell_row = csub.iloc[0].to_dict()

        card_row = (card_metrics or {}).get(model_id)
        model_errors = errors_by_model.get(model_id, [])

        for metric_name, band in spec.metrics.items():
            observed = _observed_value(spec, metric_name, device_row, cell_row, card_row)
            metric_errors = [e for e in model_errors if e.startswith(f"{metric_name}:")]
            status = "PASS" if not metric_errors else "FAIL"

            rel_margin_pct: float | None = None
            if observed is not None and band.value is not None:
                ref = float(band.value)
                rel_margin_pct = 100.0 * (observed - ref) / max(abs(ref), 1e-30)

            rows.append(
                {
                    "model_id": model_id,
                    "architecture": spec.architecture,
                    "metric": metric_name,
                    "column": band.column,
                    "confidence": band.confidence,
                    "golden_value": band.value,
                    "golden_min": band.min,
                    "golden_max": band.max,
                    "observed": observed,
                    "rel_margin_pct": rel_margin_pct,
                    "status": status,
                    "error": "; ".join(metric_errors) if metric_errors else "",
                }
            )

    return pd.DataFrame(rows)


def build_model_summary(
    errors_by_model: dict[str, list[str]],
) -> pd.DataFrame:
    """Summarize pass/fail per model."""
    specs = load_all_golden_specs()
    rows: list[dict[str, Any]] = []
    for model_id in ALL_MODEL_IDS:
        errors = errors_by_model.get(model_id, [])
        rows.append(
            {
                "model_id": model_id,
                "architecture": specs[model_id].architecture,
                "status": "PASS" if not errors else "FAIL",
                "n_errors": len(errors),
                "errors": "; ".join(errors),
            }
        )
    return pd.DataFrame(rows)


def build_trend_detail(device_df: pd.DataFrame) -> pd.DataFrame:
    """Evaluate declared golden trends and return a detail table."""
    specs = load_all_golden_specs()
    from validation.golden import METRIC_ALIASES

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for model_id in ACCESS_MODEL_IDS:
        for trend in specs[model_id].trends:
            key = (trend.metric, ",".join(trend.models))
            if key in seen:
                continue
            seen.add(key)

            col = METRIC_ALIASES.get(trend.metric, trend.metric)
            values: list[float] = []
            for mid in trend.models:
                row = device_df[device_df["model_id"] == mid]
                if row.empty:
                    continue
                val = row.iloc[0].get(col)
                if val is not None and not pd.isna(val):
                    values.append(float(val))

            ok = len(values) == len(trend.models)
            if ok:
                if trend.direction == "increasing":
                    ok = all(a < b for a, b in zip(values, values[1:]))
                elif trend.direction == "decreasing":
                    ok = all(a > b for a, b in zip(values, values[1:]))
                elif trend.direction == "non_decreasing":
                    ok = all(a <= b for a, b in zip(values, values[1:]))
                elif trend.direction == "non_increasing":
                    ok = all(a >= b for a, b in zip(values, values[1:]))

            rows.append(
                {
                    "metric": trend.metric,
                    "direction": trend.direction,
                    "models": ",".join(trend.models),
                    "values": ",".join(f"{v:.4e}" for v in values),
                    "confidence": trend.confidence,
                    "status": "PASS" if ok else "FAIL",
                }
            )
    return pd.DataFrame(rows)


def run_validation(
    device_df: pd.DataFrame,
    cell_df: pd.DataFrame | None = None,
    card_metrics: dict[str, dict[str, float]] | None = None,
) -> ValidationRun:
    """Execute full validation and return structured results.

    Args:
        device_df: Device-level metrics.
        cell_df: Optional 1T1C metrics.
        card_metrics: Optional card-parsed periphery metrics.

    Returns:
        :class:`ValidationRun` with summary tables and error lists.
    """
    errors_by_model = validate_all_golden(
        device_df, cell_df=cell_df, card_metrics=card_metrics
    )
    trend_errors = validate_trends(device_df)
    model_summary = build_model_summary(errors_by_model)
    metric_detail = build_metric_detail(
        device_df, cell_df, card_metrics, errors_by_model
    )
    trend_detail = build_trend_detail(device_df)
    if trend_errors:
        for err in trend_errors:
            trend_detail = pd.concat(
                [
                    trend_detail,
                    pd.DataFrame(
                        [
                            {
                                "metric": "trend",
                                "direction": "",
                                "models": "",
                                "values": "",
                                "confidence": "",
                                "status": "FAIL",
                                "error": err,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
    return ValidationRun(
        model_summary=model_summary,
        metric_detail=metric_detail,
        trend_detail=trend_detail,
        errors_by_model=errors_by_model,
        trend_errors=trend_errors,
    )
