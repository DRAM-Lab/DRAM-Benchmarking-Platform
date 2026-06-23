"""Matplotlib style for OpenDRAM sense-amp figures (dev-plot aligned)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

FIGSIZE = (11, 5)
FIGSIZE_TALL = (8, 6)
MODEL_DISPLAY_ORDER: tuple[str, ...] = (
    "BCAT_125",
    "VCT_082",
    "VCT_091",
    "VCT_102",
    "VCT_125",
)
MODEL_COLORS: dict[str, str] = {
    "BCAT_125": "#0033cc",
    "VCT_082": "#cc0000",
    "VCT_091": "#e67300",
    "VCT_102": "#9b59b6",
    "VCT_125": "#6a1b9a",
}
MODEL_MARKERS: dict[str, str] = {
    "BCAT_125": "^",
    "VCT_082": "o",
    "VCT_091": "s",
    "VCT_102": "d",
    "VCT_125": "v",
}
LINEWIDTH_MAIN = 3.0
GRID_ALPHA = 0.35
TITLE_SIZE = 16
LABEL_SIZE = 12
TICK_SIZE = 10
LEGEND_SIZE = 9
MARKER_SIZE = 7
FIGURE_FORMAT = "svg"


def apply_rcparams() -> None:
    """Set global typography once per process."""
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"
    plt.rcParams["axes.titleweight"] = "bold"


def apply_style(ax: plt.Axes, *, grid_axis: str | None = None) -> None:
    """Apply consistent axis styling."""
    if grid_axis is None:
        ax.grid(alpha=GRID_ALPHA)
    else:
        ax.grid(axis=grid_axis, alpha=GRID_ALPHA)
    ax.tick_params(axis="both", labelsize=TICK_SIZE)
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)


def model_color(model_id: str, index: int = 0) -> str:
    """Resolve plot color for a model id."""
    colors = ("#0033cc", "#cc0000", "#7f3fbf")
    return MODEL_COLORS.get(model_id, colors[index % len(colors)])


def save_figure(fig: plt.Figure, output_path: Path) -> Path:
    """Save figure as SVG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format=FIGURE_FORMAT, bbox_inches="tight")
    plt.close(fig)
    return output_path
