"""Matplotlib style for OpenDRAM benchmark figures (dev-plot skill).

MATLAB-aligned palette, bold typography, and SVG export defaults.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

FIGSIZE = (11, 5)
BAR_COLOR = "#0033cc"
LINE_COLORS = {
    "energy": "#0033cc",
    "dnl": "#0033cc",
    "inl": "#cc0000",
    "sndr": "#0033cc",
    "sfdr": "#cc0000",
    "thd": "#7f3fbf",
    "enob": "#e67300",
    "ion": "#0033cc",
    "ioff": "#cc0000",
    "ron": "#cc0000",
    "vsat": "#e67300",
    "cgg": "#7f3fbf",
}
MULTI_SERIES_COLORS = ("#0033cc", "#cc0000", "#7f3fbf")
PURPLE_CYCLE = ("#7f3fbf", "#9b59b6", "#6a1b9a", "#4a148c")
PROFILE_COLORS = {
    "baseline": "#0033cc",
    "variation_mc_mean": "#cc0000",
    "all_variation_parasitic": "#006400",
}

ARCHITECTURE_COLORS = {
    "BCAT": "#0033cc",
    "VCT": "#cc0000",
    "3D_GAA": "#7f3fbf",
}

# Stable legend / series order for the seven access models.
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
}

MODEL_MARKERS: dict[str, str] = {
    "BCAT_125": "^",
    "VCT_082": "o",
    "VCT_091": "s",
    "VCT_102": "d",
    "VCT_125": "v",
    "3D_gaa_Si": "P",
    "3D_gaa_AOS": "X",
}

LINEWIDTH_MAIN = 4.0
LINEWIDTH_SECONDARY = 3.0
GRID_ALPHA = 0.35
TITLE_SIZE = 17
LABEL_SIZE = 13
TICK_SIZE = 10
LEGEND_SIZE = 9
BAR_EDGE_COLOR = "#002080"
BAR_EDGE_WIDTH = 1.0
SPINE_WIDTH = 2.0
GRID_LINEWIDTH = 1.1
MARKER_SIZE = 5
MARKER_EDGEWIDTH = 1.0

FIGURE_FORMAT = "svg"


def apply_rcparams() -> None:
    """Set global typography once per process."""
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]
    # Avoid global bold weight — Liberation/Arial lack a bold face in many headless envs.
    plt.rcParams["font.weight"] = "normal"
    plt.rcParams["axes.labelweight"] = "normal"
    plt.rcParams["axes.titleweight"] = "normal"


def apply_style(ax: plt.Axes, *, grid_axis: str | None = None) -> None:
    """Apply consistent axis styling to one axes."""
    if grid_axis is None:
        ax.grid(alpha=GRID_ALPHA, linewidth=GRID_LINEWIDTH)
    else:
        ax.grid(axis=grid_axis, alpha=GRID_ALPHA, linewidth=GRID_LINEWIDTH)
    ax.tick_params(axis="both", labelsize=TICK_SIZE)
    for spine in ax.spines.values():
        spine.set_linewidth(SPINE_WIDTH)
    if not hasattr(ax, "name") or ax.name != "polar":
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)


def model_color(model_id: str, index: int = 0) -> str:
    """Resolve plot color for a model id."""
    return MODEL_COLORS.get(model_id, MULTI_SERIES_COLORS[index % len(MULTI_SERIES_COLORS)])


def save_figure(fig: plt.Figure, output_path: Path) -> Path:
    """Save figure using dev-plot conventions (SVG by default)."""
    path = output_path
    if path.suffix.lower() != f".{FIGURE_FORMAT}":
        path = path.with_suffix(f".{FIGURE_FORMAT}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, format=FIGURE_FORMAT)
    plt.close(fig)
    return path
