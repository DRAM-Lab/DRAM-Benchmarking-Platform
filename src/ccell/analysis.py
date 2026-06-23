"""Figure generation for Ccell roadmap experiment."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ccell.config import CcellConfig, load_ccell_config
from ccell.read_signal import model_uses_sense_amp, read_pass_threshold_v


def _save_fig(path: Path) -> Path:
    out = path if path.suffix == ".svg" else path.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, format="svg")
    plt.close()
    return out


def plot_t_ret_vs_ccell(
    sweep_df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str,
) -> Path:
    """Log-log retention vs Ccell per architecture."""
    subset = sweep_df[sweep_df["corner"] == corner].copy()
    plt.figure(figsize=(8, 5))
    for model_id, group in subset.groupby("model_id"):
        valid = group.dropna(subset=["t_ret_s"]).sort_values("ccell_ff")
        if valid.empty:
            continue
        plt.loglog(valid["ccell_ff"], valid["t_ret_s"] * 1e3, marker="o", label=model_id)
    plt.xlabel("Ccell (fF)")
    plt.ylabel("t_ret (ms)")
    plt.title(f"Retention vs Ccell @ {corner}")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend(fontsize=8, ncol=2)
    return _save_fig(output_path)


def plot_dv_read_vs_ccell(
    sweep_df: pd.DataFrame,
    output_path: Path,
    *,
    corner: str,
    cfg: CcellConfig | None = None,
) -> Path:
    """Read signal vs Ccell with per-model SA yield budget lines."""
    cfg = cfg or load_ccell_config()
    subset = sweep_df[sweep_df["corner"] == corner].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    for idx, (model_id, group) in enumerate(subset.groupby("model_id")):
        valid = group.dropna(subset=["dv_read_v"]).sort_values("ccell_ff")
        if valid.empty:
            continue
        color = f"C{idx % 10}"
        mid = str(model_id)
        ax.plot(
            valid["ccell_ff"],
            valid["dv_read_v"].astype(float).abs() * 1e3,
            marker="o",
            color=color,
            label=mid,
        )
        uses_sense = model_uses_sense_amp(sweep_df, mid, corner)
        threshold_v = read_pass_threshold_v(cfg, mid, uses_sense_amp=uses_sense)
        ax.axhline(
            threshold_v * 1e3,
            color=color,
            linestyle=":",
            alpha=0.75,
            linewidth=1.4,
        )
    ax.set_xlabel("Ccell (fF)")
    ax.set_ylabel("|ΔV_BL| @ t_en (mV)")
    ax.set_title(f"Read signal vs Ccell @ {corner} (dotted = per-model SA budget)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    out = output_path if output_path.suffix == ".svg" else output_path.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg")
    plt.close(fig)
    return out


def plot_ccell_min_roadmap(
    ccell_min_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """Bar chart of dual-constraint Ccell_min per model."""
    plt.figure(figsize=(9, 5))
    models = ccell_min_df["model_id"].astype(str)
    x = range(len(models))
    width = 0.25
    ret = ccell_min_df["ccell_min_ret_ff"].fillna(0)
    read = ccell_min_df["ccell_min_read_ff"].fillna(0)
    combined = ccell_min_df["ccell_min_ff"].fillna(0)
    plt.bar([i - width for i in x], ret, width=width, label="Ccell_min (retention)")
    plt.bar(x, read, width=width, label="Ccell_min (read)")
    plt.bar([i + width for i in x], combined, width=width, label="Ccell_min (dual)")
    plt.xticks(list(x), models, rotation=30, ha="right")
    plt.ylabel("Ccell (fF)")
    plt.title("Minimum Ccell for 64 ms retention + read yield budget")
    plt.legend()
    plt.grid(True, axis="y", alpha=0.3)
    return _save_fig(output_path)


def plot_feasibility_map(
    feasibility_df: pd.DataFrame,
    output_path: Path,
    *,
    scenario: str,
) -> Path | None:
    """Achievable vs required Ccell under one k scenario."""
    subset = feasibility_df[feasibility_df["scenario"] == scenario].copy()
    if subset.empty:
        return None
    plt.figure(figsize=(8, 5))
    models = subset["model_id"].astype(str)
    x = range(len(models))
    plt.bar([i - 0.2 for i in x], subset["achievable_ccell_ff"], width=0.4, label="Achievable")
    plt.bar([i + 0.2 for i in x], subset["ccell_min_ff"], width=0.4, label="Required")
    plt.xticks(list(x), models, rotation=30, ha="right")
    plt.ylabel("Ccell (fF)")
    plt.title(f"Capacitor feasibility @ {scenario}")
    plt.legend()
    plt.grid(True, axis="y", alpha=0.3)
    return _save_fig(output_path)


def generate_figures(
    sweep_csv: Path,
    ccell_min_csv: Path,
    feasibility_csv: Path | None,
    output_dir: Path,
    *,
    config: CcellConfig | None = None,
) -> list[Path]:
    """Generate all Ccell roadmap summary figures."""
    cfg = config or load_ccell_config()
    sweep_df = pd.read_csv(sweep_csv)
    ccell_min_df = pd.read_csv(ccell_min_csv)
    paths: list[Path] = []

    paths.append(
        plot_t_ret_vs_ccell(
            sweep_df,
            output_dir / "t_ret_vs_ccell_hot",
            corner=cfg.retention_corner,
        )
    )
    paths.append(
        plot_dv_read_vs_ccell(
            sweep_df,
            output_dir / "dv_read_vs_ccell_tt",
            corner=cfg.read_corner,
            cfg=cfg,
        )
    )
    paths.append(plot_ccell_min_roadmap(ccell_min_df, output_dir / "ccell_min_roadmap"))

    if feasibility_csv and feasibility_csv.is_file():
        feas_df = pd.read_csv(feasibility_csv)
        for scenario in cfg.dielectric_scenarios:
            path = plot_feasibility_map(
                feas_df,
                output_dir / f"feasibility_{scenario}",
                scenario=scenario,
            )
            if path is not None:
                paths.append(path)

    return paths
