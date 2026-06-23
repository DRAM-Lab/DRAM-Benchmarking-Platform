"""Matplotlib style for OpenDRAM validation figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

FIGSIZE = (11, 5)
FIGSIZE_SQUARE = (8, 6)
BAR_COLOR = "#0033cc"
PASS_COLOR = "#006400"
FAIL_COLOR = "#cc0000"
WARN_COLOR = "#e67300"

ARCHITECTURE_COLORS = {
    "BCAT": "#0033cc",
    "VCT": "#cc0000",
    "3D_GAA": "#7f3fbf",
    "HV_PERI": "#e67300",
}

MODEL_DISPLAY_ORDER: tuple[str, ...] = (
    "BCAT_125",
    "VCT_082",
    "VCT_091",
    "VCT_102",
    "VCT_125",
    "3D_gaa_Si",
    "3D_gaa_AOS",
)

MODEL_COLORS: dict[str, str] = {
    "BCAT_125": "#0033cc",
    "VCT_082": "#cc0000",
    "VCT_091": "#e67300",
    "VCT_102": "#9b59b6",
    "VCT_125": "#6a1b9a",
    "3D_gaa_Si": "#7f3fbf",
    "3D_gaa_AOS": "#4a148c",
    "hv_peri_28_32": "#e67300",
}

CONFIDENCE_COLORS = {
    "high": "#006400",
    "medium": "#e67300",
    "low": "#cc0000",
}

MATCH_COLORS = {"H": "#006400", "M": "#e67300", "L": "#cc0000", "N": "#888888"}

LINEWIDTH_MAIN = 3.0
GRID_ALPHA = 0.35
TITLE_SIZE = 15
LABEL_SIZE = 12
TICK_SIZE = 10
LEGEND_SIZE = 9
FIGURE_FORMAT = "svg"


def apply_rcparams() -> None:
    """Set global typography once per process."""
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]
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
    return MODEL_COLORS.get(model_id, BAR_COLOR)


def save_figure(fig: plt.Figure, output_path: Path) -> Path:
    """Save figure as SVG."""
    path = output_path
    if path.suffix.lower() != f".{FIGURE_FORMAT}":
        path = path.with_suffix(f".{FIGURE_FORMAT}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, format=FIGURE_FORMAT)
    plt.close(fig)
    return path
