"""Golden metric specification loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from validation.paths import GOLDEN_ROOT

Confidence = Literal["high", "medium", "low"]
ACCESS_MODEL_IDS: tuple[str, ...] = (
    "BCAT_125",
    "VCT_082",
    "VCT_091",
    "VCT_102",
    "VCT_125",
    "3D_gaa_Si",
    "3D_gaa_AOS",
)
ALL_MODEL_IDS: tuple[str, ...] = (*ACCESS_MODEL_IDS, "hv_peri_28_32")

CELL_ONLY_COLUMNS: frozenset[str] = frozenset(
    {"t_read_s", "t_write_s", "i_hold_a", "q_read_c"}
)

METRIC_ALIASES: dict[str, str] = {
    "Ion": "ion_a",
    "Ioff": "ioff_a",
    "Ron": "ron_ohm",
    "fpitch": "fpitch_m",
    "Cgg": "cgg_f",
    "Vt": "vt_v",
    "SS": "ss_mv_dec",
    "t_read": "t_read_s",
    "t_write": "t_write_s",
    "I_hold": "i_hold_a",
    "vth0": "vth0",
    "rdsw": "rdsw",
    "u0": "u0",
    "vsat": "vsat",
    "nominal_vdd": "nominal_vdd",
}


ValidationMode = Literal["spice", "paper"]


@dataclass(frozen=True)
class MetricBand:
    """Tolerance band for one golden metric."""

    name: str
    column: str
    value: float | None = None
    min: float | None = None
    max: float | None = None
    tol: float | None = None
    rtol: float | None = None
    confidence: Confidence = "medium"
    direction: str | None = None
    validation: ValidationMode = "spice"

    def check(self, observed: float | None) -> list[str]:
        """Validate one observed value against this band.

        Args:
            observed: Measured or extracted metric value.

        Returns:
            List of validation error messages (empty if pass).
        """
        if self.validation == "paper":
            return []
        errors: list[str] = []
        if observed is None or (isinstance(observed, float) and pd.isna(observed)):
            if self.value is not None or self.min is not None or self.max is not None:
                errors.append(f"{self.name}: missing observed value")
            return errors

        obs = float(observed)
        if self.value is not None:
            ref = float(self.value)
            rel_tol = self.rtol if self.rtol is not None else (self.tol or 0.10)
            denom = max(abs(ref), 1e-30)
            if abs(obs - ref) / denom > rel_tol:
                errors.append(
                    f"{self.name}: {obs:.4e} vs golden {ref:.4e} (>{rel_tol * 100:.0f}% tol)"
                )
        if self.min is not None and obs < float(self.min):
            errors.append(f"{self.name}: {obs:.4e} < min {float(self.min):.4e}")
        if self.max is not None and obs > float(self.max):
            errors.append(f"{self.name}: {obs:.4e} > max {float(self.max):.4e}")
        return errors


@dataclass
class TrendSpec:
    """Directional trend across multiple models."""

    metric: str
    models: list[str]
    direction: Literal["increasing", "decreasing", "non_decreasing", "non_increasing"]
    confidence: Confidence = "medium"


@dataclass
class GoldenSpec:
    """Parsed golden YAML for one model card."""

    model_id: str
    model_file: str
    architecture: str
    corner: dict[str, float]
    metrics: dict[str, MetricBand]
    trends: list[TrendSpec] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    model_git_pin: str | None = None
    paper_config: str | None = None

    @property
    def yaml_path(self) -> Path:
        """Return canonical golden YAML path for this model."""
        return GOLDEN_ROOT / f"{self.model_id.lower()}.yaml"


def _metric_band(name: str, raw: dict[str, Any]) -> MetricBand:
    """Build a :class:`MetricBand` from YAML mapping."""
    column = METRIC_ALIASES.get(name, name)
    validation = raw.get("validation", "spice")
    if validation not in ("spice", "paper"):
        validation = "spice"
    return MetricBand(
        name=name,
        column=column,
        value=raw.get("value"),
        min=raw.get("min"),
        max=raw.get("max"),
        tol=raw.get("tol"),
        rtol=raw.get("rtol"),
        confidence=raw.get("confidence", "medium"),
        direction=raw.get("direction"),
        validation=validation,
    )


def load_golden_spec(model_id: str, golden_root: Path | None = None) -> GoldenSpec:
    """Load golden specification for one model.

    Args:
        model_id: Model identifier (e.g. ``VCT_125``).
        golden_root: Optional override for golden YAML directory.

    Returns:
        Parsed :class:`GoldenSpec`.

    Raises:
        FileNotFoundError: If the YAML spec is missing.
        ValueError: If the YAML is malformed.
    """
    root = golden_root or GOLDEN_ROOT
    path = root / f"{model_id.lower()}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Golden spec missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid golden YAML: {path}")

    metrics_raw = data.get("metrics", {})
    metrics = {name: _metric_band(name, spec) for name, spec in metrics_raw.items()}
    trends: list[TrendSpec] = []
    for item in data.get("trends", []):
        trends.append(
            TrendSpec(
                metric=item["metric"],
                models=list(item["models"]),
                direction=item["direction"],
                confidence=item.get("confidence", "medium"),
            )
        )

    model_file = str(data.get("model", f"{model_id}.inc"))
    return GoldenSpec(
        model_id=model_id,
        model_file=model_file,
        architecture=str(data.get("architecture", "unknown")),
        corner=dict(data.get("corner", {})),
        metrics=metrics,
        trends=trends,
        sources=list(data.get("sources", [])),
        model_git_pin=data.get("model_git_pin"),
        paper_config=data.get("paper_config"),
    )


def load_all_golden_specs(golden_root: Path | None = None) -> dict[str, GoldenSpec]:
    """Load golden specs for all eight OpenDRAMmodelV1 cards.

    Returns:
        Mapping of model_id to :class:`GoldenSpec`.
    """
    return {mid: load_golden_spec(mid, golden_root=golden_root) for mid in ALL_MODEL_IDS}


def validate_metrics_row(
    spec: GoldenSpec,
    row: dict[str, Any],
    *,
    skip_columns: frozenset[str] | None = None,
) -> list[str]:
    """Validate one metrics row against a golden spec.

    Args:
        spec: Golden specification.
        row: Flat metrics dictionary (CSV row or bench output).
        skip_columns: Optional column names to omit.

    Returns:
        List of validation errors.
    """
    errors: list[str] = []
    skip = skip_columns or frozenset()
    for band in spec.metrics.values():
        if band.column in skip:
            continue
        observed = row.get(band.column)
        if observed is None:
            observed = row.get(band.name)
        errors.extend(band.check(observed if observed is None else float(observed)))
    return errors


def validate_against_dataframe(
    spec: GoldenSpec,
    df: pd.DataFrame,
    *,
    model_col: str = "model_id",
    skip_columns: frozenset[str] | None = None,
) -> list[str]:
    """Validate golden spec against a metrics DataFrame.

    Args:
        spec: Golden specification.
        df: Metrics table containing one row for ``spec.model_id``.
        model_col: Column holding model identifiers.

    Returns:
        List of validation errors.
    """
    subset = df[df[model_col] == spec.model_id]
    if subset.empty:
        return [f"{spec.model_id}: no row in metrics table"]
    row = subset.iloc[0].to_dict()
    return validate_metrics_row(spec, row, skip_columns=skip_columns)


def validate_all_golden(
    device_df: pd.DataFrame,
    cell_df: pd.DataFrame | None = None,
    card_metrics: dict[str, dict[str, float]] | None = None,
    golden_root: Path | None = None,
) -> dict[str, list[str]]:
    """Validate all golden specs against benchmark outputs.

    Args:
        device_df: Device-level metrics (``device_metrics.csv`` from device benchmark).
        cell_df: Optional 1T1C metrics at 20 fF.
        card_metrics: Optional card-parsed metrics (periphery models).
        golden_root: Optional golden YAML directory override.

    Returns:
        Mapping of model_id to error list (empty means pass).
    """
    specs = load_all_golden_specs(golden_root=golden_root)
    summary: dict[str, list[str]] = {}
    for model_id, spec in specs.items():
        errors: list[str] = []
        if model_id in ACCESS_MODEL_IDS:
            errors.extend(
                validate_against_dataframe(
                    spec, device_df, skip_columns=CELL_ONLY_COLUMNS
                )
            )
            if cell_df is not None:
                cell_subset = cell_df[cell_df["model_id"] == model_id]
                if not cell_subset.empty:
                    cell_row = cell_subset.iloc[0].to_dict()
                    for band in spec.metrics.values():
                        if band.column not in CELL_ONLY_COLUMNS:
                            continue
                        observed = cell_row.get(band.column)
                        if observed is None or pd.isna(observed):
                            errors.extend(band.check(None))
                        else:
                            errors.extend(band.check(float(observed)))
                else:
                    cell_metrics = [
                        b.name
                        for b in spec.metrics.values()
                        if b.column in CELL_ONLY_COLUMNS
                        and (b.value is not None or b.min is not None or b.max is not None)
                    ]
                    if cell_metrics:
                        errors.append(f"{model_id}: no row in cell metrics")
        elif card_metrics and model_id in card_metrics:
            errors.extend(validate_metrics_row(spec, card_metrics[model_id]))
        else:
            errors.append(f"{model_id}: no metrics source available")
        summary[model_id] = errors
    return summary


def validate_trends(device_df: pd.DataFrame) -> list[str]:
    """Validate directional trends declared in golden YAML files.

    Args:
        device_df: Device metrics table indexed by model_id column.

    Returns:
        List of trend violation messages.
    """
    errors: list[str] = []
    for model_id in ACCESS_MODEL_IDS:
        spec = load_golden_spec(model_id)
        for trend in spec.trends:
            col = METRIC_ALIASES.get(trend.metric, trend.metric)
            values: list[float] = []
            for mid in trend.models:
                row = device_df[device_df["model_id"] == mid]
                if row.empty:
                    errors.append(f"Trend {trend.metric}: missing model {mid}")
                    continue
                val = row.iloc[0].get(col)
                if val is None or pd.isna(val):
                    errors.append(f"Trend {trend.metric}: NaN for {mid}")
                    continue
                values.append(float(val))
            if len(values) != len(trend.models):
                continue
            ok = True
            if trend.direction == "increasing":
                ok = all(a < b for a, b in zip(values, values[1:]))
            elif trend.direction == "decreasing":
                ok = all(a > b for a, b in zip(values, values[1:]))
            elif trend.direction == "non_decreasing":
                ok = all(a <= b for a, b in zip(values, values[1:]))
            elif trend.direction == "non_increasing":
                ok = all(a >= b for a, b in zip(values, values[1:]))
            if not ok:
                errors.append(
                    f"Trend {trend.metric} ({trend.direction}) failed for {trend.models}: "
                    f"{values}"
                )
    return errors
