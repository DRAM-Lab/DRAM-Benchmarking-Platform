"""Markdown table helpers shared across report generators."""

from __future__ import annotations

import pandas as pd


def sanitize_md_cell(text: str) -> str:
    """Escape pipe characters so markdown tables render correctly."""
    return text.replace("|", "\\|")


def join_md_row(cells: list[str]) -> str:
    """Join table cells into one markdown row with escaped delimiters."""
    return "| " + " | ".join(sanitize_md_cell(str(cell)) for cell in cells) + " |"


def df_to_markdown(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavored markdown table."""
    if df.empty:
        return "_No data._"
    headers = join_md_row([str(c) for c in df.columns])
    sep = join_md_row(["---"] * len(df.columns))
    body: list[str] = []
    for row in df.itertuples(index=False):
        cells: list[str] = []
        for value in row:
            if isinstance(value, float):
                if pd.isna(value):
                    cells.append("—")
                else:
                    cells.append(f"{value:.4g}")
            else:
                cells.append(str(value))
        body.append(join_md_row(cells))
    return "\n".join([headers, sep, *body])
