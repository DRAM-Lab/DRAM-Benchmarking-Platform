"""Global Sobol sensitivity analysis (optional SALib)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SobolIndices:
    """First-order Sobol index for one parameter and output."""

    model_id: str
    param: str
    output: str
    s1: float
    s1_conf: float


def run_sobol_screen(
    model_id: str,
    param_names: list[str],
    *,
    n_samples: int = 512,
    outputs: tuple[str, ...] = ("t_read_s", "ron_ohm", "i_hold_a"),
    seed: int = 42,
) -> list[SobolIndices]:
    """Compute Sobol S1 indices using SALib Saltelli sampling.

    Uses a lightweight synthetic response surface when SPICE-in-the-loop is
  unavailable; replace ``_evaluate_surface`` with bench calls for production.

    Args:
        model_id: Model identifier.
        param_names: Top parameters from local OAT screen (5–8 recommended).
        n_samples: Saltelli sample count (N).
        outputs: Output metric names.
        seed: RNG seed for reproducibility.

    Returns:
        List of first-order Sobol indices.

    Raises:
        ImportError: If SALib is not installed.
    """
    from SALib.analyze import sobol as sobol_analyze  # type: ignore[import-untyped]
    from SALib.sample import saltelli  # type: ignore[import-untyped]

    problem = {
        "num_vars": len(param_names),
        "names": param_names,
        "bounds": [[0.95, 1.05] for _ in param_names],
    }
    samples = saltelli.sample(problem, n_samples, calc_second_order=False, seed=seed)
    y_matrix = _evaluate_surface(model_id, param_names, samples, outputs)

    indices: list[SobolIndices] = []
    for out_idx, output in enumerate(outputs):
        analysis = sobol_analyze.analyze(
            problem,
            y_matrix[:, out_idx],
            calc_second_order=False,
            print_to_console=False,
        )
        for p_idx, name in enumerate(param_names):
            indices.append(
                SobolIndices(
                    model_id=model_id,
                    param=name,
                    output=output,
                    s1=float(analysis["S1"][p_idx]),
                    s1_conf=float(analysis["S1_conf"][p_idx]),
                )
            )
    return indices


def _evaluate_surface(
    model_id: str,
    param_names: list[str],
    samples: np.ndarray,
    outputs: tuple[str, ...],
) -> np.ndarray:
    """Synthetic response surface for offline Sobol demonstration.

    Replace with SPICE-in-the-loop evaluation for production studies.
    """
    n = samples.shape[0]
    y = np.zeros((n, len(outputs)), dtype=float)
    weights = np.linspace(0.5, 1.5, len(param_names))
    for i in range(n):
        x = samples[i]
        combo = float(np.dot(x - 1.0, weights))
        y[i, 0] = 2e-8 * (1.0 + 0.3 * combo)  # t_read_s proxy
        y[i, 1] = 8e5 * (1.0 - 0.2 * combo)  # ron_ohm proxy
        y[i, 2] = 5e-11 * (1.0 + 0.5 * combo)  # i_hold_a proxy
    return y


def sobol_dataframe(indices: list[SobolIndices]) -> pd.DataFrame:
    """Convert Sobol indices to a DataFrame."""
    return pd.DataFrame(
        [
            {
                "model_id": s.model_id,
                "param": s.param,
                "output": s.output,
                "S1": s.s1,
                "S1_conf": s.s1_conf,
            }
            for s in indices
        ]
    )


def generate_sobol_report(indices: list[SobolIndices], output_path: Path) -> Path:
    """Write global Sobol sensitivity markdown report.

    Args:
        indices: Sobol index list.
        output_path: Markdown output path.

    Returns:
        Written path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = sobol_dataframe(indices)
    lines = [
        "# Global Sensitivity Report (Sobol S1)",
        "",
        "First-order Sobol indices for top parameters (Saltelli sampling).",
        "",
    ]
    for output in df["output"].unique():
        sub = df[df["output"] == output].sort_values("S1", ascending=False)
        lines.extend([f"## {output}", "", "| Param | S1 | S1_conf |", "|-------|----|---------|"])
        for _, row in sub.iterrows():
            lines.append(f"| {row['param']} | {row['S1']:.4f} | {row['S1_conf']:.4f} |")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
