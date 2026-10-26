"""Timeline chart: green/red windows for every intersection over one horizon."""

from __future__ import annotations

import plotly.graph_objects as go

from ..config import ScenarioConfig
from . import base_layout

GREEN_FILL = "#d6ecd8"
RED_FILL = "#f6d5d3"

__all__ = ["signal_timeline_figure"]


def signal_timeline_figure(
    offsets: tuple[float, ...],
    config: ScenarioConfig,
    horizon_s: float | None = None,
) -> go.Figure:
    """Build the coordinated timeline of green windows.

    The green window of intersection ``i`` is ``[O_i + k*C, O_i + k*C + G)``
    for integer ``k``; windows are drawn beyond the visible horizon so the
    plot edges stay honest. Red is drawn first per row, then green windows on
    top, so no hidden overlaps confuse the reading.
    """
    horizon = horizon_s if horizon_s is not None else 3 * config.cycle_length
    n = len(offsets)
    shapes: list[dict[str, object]] = []

    for i in range(n):
        shapes.append(
            {
                "type": "rect",
                "xref": "x",
                "yref": "y",
                "x0": 0,
                "x1": horizon,
                "y0": i - 0.36,
                "y1": i + 0.36,
                "fillcolor": RED_FILL,
                "line": {"width": 0},
            }
        )
    for i, offset in enumerate(offsets):
        y = n - 1 - i
        first_k = int(-(offset // config.cycle_length)) - 1
        last_k = int((horizon - offset) // config.cycle_length) + 1
        for k in range(first_k, last_k + 1):
            w_start = offset + k * config.cycle_length
            w_end = w_start + config.green_duration
            if w_end <= 0 or w_start >= horizon:
                continue
            shapes.append(
                {
                    "type": "rect",
                    "xref": "x",
                    "yref": "y",
                    "x0": max(w_start, 0),
                    "x1": min(w_end, horizon),
                    "y0": y - 0.36,
                    "y1": y + 0.36,
                    "fillcolor": GREEN_FILL,
                    "line": {"width": 0},
                }
            )

    fig = go.Figure()
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(title="Time (s)", range=[0, horizon], dtick=config.cycle_length),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(n)),
            ticktext=[f"I{k + 1}" for k in reversed(range(n))],
            range=[-0.5, n - 0.5],
        ),
    )
    fig.layout.update(
        base_layout(title="Signal timeline: green windows per intersection")
    )
    note = f"O₁ = 0 reference · C = {config.cycle_length:.0f} s · G = {config.green_duration:.0f} s"
    fig.add_annotation(
        x=0,
        yref="y",
        y=n - 0.62,
        xanchor="left",
        yanchor="top",
        text=note,
        showarrow=False,
        font=dict(size=11, color="#37474f"),
    )
    return fig
