"""Plotly-based visualizations for the coordination dashboard.

Design tokens (restrained palette, consistent with the dashboard CSS):

- green signal window: ``#2e7d32`` (fill ``#d6ecd8``)
- red state: ``#c62828`` (fill ``#f6d5d3``)
- forward vehicles: ``#1565c0``; reverse vehicles: ``#6a1b9a``
- neutral text: ``#37474f``; grid: light grey
"""

from __future__ import annotations

COLOR_GREEN = "#2e7d32"
COLOR_GREEN_FILL = "#d6ecd8"
COLOR_RED = "#c62828"
COLOR_RED_FILL = "#f6d5d3"
COLOR_FORWARD = "#1565c0"
COLOR_REVERSE = "#6a1b9a"
COLOR_TEXT = "#37474f"
FONT = "Segoe UI, Roboto, Helvetica, Arial, sans-serif"

__all__ = [
    "COLOR_FORWARD",
    "COLOR_GREEN",
    "COLOR_GREEN_FILL",
    "COLOR_RED",
    "COLOR_RED_FILL",
    "COLOR_REVERSE",
    "COLOR_TEXT",
    "FONT",
    "base_layout",
]


def base_layout(**overrides: object) -> object:
    """Build the common Plotly layout for all dashboard figures."""
    import plotly.graph_objects as go

    layout = {
        "font": {"family": FONT, "color": COLOR_TEXT},
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "margin": {"l": 60, "r": 30, "t": 50, "b": 40},
        "title_font": {"size": 16},
    }
    layout.update(overrides)
    return go.Layout(**layout)
