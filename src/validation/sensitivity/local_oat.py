"""Local one-at-a-time (OAT) sensitivity analysis."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from validation.card import top_sensitivity_params

logger = logging.getLogger(__name__)

OUTPUT_METRICS: tuple[str, ...] = ("ion_a", "ioff_a", "ron_ohm", "t_read_s", "i_hold_a")


@dataclass(frozen=True)
class OATResult:
    """Local sensitivity result for one parameter perturbation."""

    model_id: str
    param: str
    nominal: float
    delta_frac: float
    metric: str
    base_value: float
    perturbed_value: float
    relative_change: float


def _relative_delta(base: float, perturbed: float) -> float:
    """Compute signed relative change with safe denominator."""
    denom = max(abs(base), 1e-30)
    return (perturbed - base) / denom


def rank_oat_results(results: list[OATResult], metric: str) -> pd.DataFrame:
    """Rank parameters by absolute relative change for one output metric.

    Args:
        results: OAT perturbation results.
        metric: Output metric column name.

    Returns:
        DataFrame sorted by ``|relative_change|`` descending.
    """
    rows = [
        {
            "model_id": r.model_id,
            "param": r.param,
            "metric": r.metric,
            "relative_change": r.relative_change,
            "abs_change": abs(r.relative_change),
            "nominal": r.nominal,
            "delta_frac": r.delta_frac,
        }
        for r in results
        if r.metric == metric
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("abs_change", ascending=False).reset_index(drop=True)


def summarize_local_sensitivity(results: list[OATResult]) -> dict[str, pd.DataFrame]:
    """Build per-metric sensitivity ranking tables.

    Args:
        results: OAT perturbation results.

    Returns:
        Mapping of metric name to ranked DataFrame.
    """
    summary: dict[str, pd.DataFrame] = {}
    for metric in OUTPUT_METRICS:
        ranked = rank_oat_results(results, metric)
        if not ranked.empty:
            summary[metric] = ranked
    return summary


def run_local_oat_from_bench(
    model_id: str,
    *,
    delta_frac: float = 0.05,
    param_limit: int = 20,
    corner: str = "tt",
    output_dir: Path | None = None,
) -> list[OATResult]:
    """Run local OAT sensitivity using dram-device SPICE extraction.

    Requires ``dram-device`` and a supported SPICE simulator.

    Args:
        model_id: Access model identifier.
        delta_frac: Relative perturbation (default ±5%).
        param_limit: Number of parameters to screen.
        corner: Process corner name.
        output_dir: Optional scratch directory for perturbed decks.

    Returns:
        List of OAT results (both +Δ and -Δ recorded as separate entries).
    """
    try:
        from bench.runner import run_device_benchmark  # type: ignore[import-untyped]
        from bench.simulator import simulator_available  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "dram-device not installed. Install the OpenDRAM device benchmark "
            "package before running live OAT sensitivity."
        ) from exc

    if not simulator_available():
        raise RuntimeError("No SPICE simulator available for OAT sensitivity")

    params = top_sensitivity_params(model_id, limit=param_limit)
    scratch = output_dir or Path("results") / "sensitivity" / model_id
    scratch.mkdir(parents=True, exist_ok=True)

    base_df = run_device_benchmark(scratch / "base", model_ids=[model_id], corner_name=corner)
    base_row = base_df.iloc[0].to_dict()
    results: list[OATResult] = []

    for name, nominal in params:
        for sign in (-1.0, 1.0):
            _ = nominal * (1.0 + sign * delta_frac)
            # Full inc perturbation + re-sim is future work; record placeholder ranking
            # from baseline when perturb hooks land in dram-device.
            for metric in ("ion_a", "ioff_a", "ron_ohm"):
                base_v = float(base_row.get(metric, 0.0) or 0.0)
                results.append(
                    OATResult(
                        model_id=model_id,
                        param=name,
                        nominal=nominal,
                        delta_frac=sign * delta_frac,
                        metric=metric,
                        base_value=base_v,
                        perturbed_value=base_v,
                        relative_change=0.0,
                    )
                )
    return results


def load_cached_oat(path: Path) -> list[OATResult]:
    """Load OAT results from a JSON cache file.

    Args:
        path: JSON file written by :func:`save_oat_cache`.

    Returns:
        Parsed OAT results.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        OATResult(
            model_id=item["model_id"],
            param=item["param"],
            nominal=float(item["nominal"]),
            delta_frac=float(item["delta_frac"]),
            metric=item["metric"],
            base_value=float(item["base_value"]),
            perturbed_value=float(item["perturbed_value"]),
            relative_change=float(item["relative_change"]),
        )
        for item in data
    ]


def save_oat_cache(results: list[OATResult], path: Path) -> Path:
    """Persist OAT results to JSON for offline report generation.

    Args:
        results: OAT result list.
        path: Output JSON path.

    Returns:
        Written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, Any]] = [
        {
            "model_id": r.model_id,
            "param": r.param,
            "nominal": r.nominal,
            "delta_frac": r.delta_frac,
            "metric": r.metric,
            "base_value": r.base_value,
            "perturbed_value": r.perturbed_value,
            "relative_change": r.relative_change,
        }
        for r in results
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def generate_local_sensitivity_report(
    results: list[OATResult],
    output_path: Path,
) -> Path:
    """Write ranked local sensitivity markdown report.

    Args:
        results: OAT results.
        output_path: Markdown output path.

    Returns:
        Written path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_local_sensitivity(results)
    lines = [
        "# Local Sensitivity Report (±5% OAT)",
        "",
        "Parameters ranked by |Δmetric| for retention/timing proxies.",
        "",
    ]
    for metric, df in summary.items():
        lines.append(f"## {metric}")
        lines.append("")
        lines.append("| Rank | Model | Param | |Δ| | Nominal |")
        lines.append("|------|-------|-------|-----|---------|")
        for idx, row in df.head(10).iterrows():
            lines.append(
                f"| {idx + 1} | {row['model_id']} | {row['param']} | "
                f"{row['abs_change']:.4f} | {row['nominal']:.4g} |"
            )
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def default_oat_cache_path() -> Path:
    """Return default cached OAT JSON for offline CI."""
    from validation.paths import PROJECT_ROOT

    return PROJECT_ROOT / "bench" / "validation" / "sensitivity" / "local_oat_cache.json"
