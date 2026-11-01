"""Vehicle animation: moving vehicles through the corridor over time."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ..config import ScenarioConfig
from ..models import Corridor, SimulationResult
from . import (
    COLOR_BG,
    COLOR_FORWARD,
    COLOR_LINE,
    COLOR_MUTED,
    COLOR_REVERSE,
    COLOR_ROAD,
    COLOR_SURFACE,
    COLOR_TEXT,
    FONT_MONO,
    base_layout,
)
from .corridor import vehicle_position_at
from .trajectory import vehicle_position_series

__all__ = ["vehicle_animation_figure"]


def vehicle_animation_figure(
    corridor: Corridor,
    config: ScenarioConfig,
    offsets: tuple[float, ...],
    simulation: SimulationResult,
    *,
    frames: int = 60,
) -> go.Figure:
    """Build an animated corridor with one plotly animation frame per step.

    :py:meth:`play` on the figure starts the animation in Streamlit.
    """
    positions = [it.position_m for it in corridor.intersections]
    horizon = max(
        [0.0]
        + [
            max(t.arrival_at_intersection.values()) if t.arrival_at_intersection else 0.0
            for t in simulation.vehicle_traces
        ]
    )
    horizon += config.cycle_length
    sample_times = np.linspace(0, horizon, frames)

    ## trajectories pre-computed per vehicle
    series = [vehicle_position_series(t, corridor, config) for t in simulation.vehicle_traces]

    frame_data: list[dict[str, object]] = []
    for t_val in sample_times:
        data = []
        for trace, (times, xs) in zip(simulation.vehicle_traces, series, strict=True):
            x = vehicle_position_at(times, xs, float(t_val))
            data.append(
                go.Scatter(
                    x=[x],
                    y=[0],
                    mode="markers",
                    marker=dict(
                        size=12,
                        color=COLOR_FORWARD if trace.direction == "forward" else COLOR_REVERSE,
                        symbol=(
                            "triangle-right" if trace.direction == "forward" else "triangle-left"
                        ),
                        line={"width": 1, "color": COLOR_BG},
                    ),
                    hovertemplate=f"v{trace.vehicle_id} ({trace.direction})<extra></extra>",
                    showlegend=False,
                )
            )
        frame_data.append(
            {
                "name": f"t={t_val:.0f}",
                "data": data,
                "traces": [1 + i for i in range(len(simulation.vehicle_traces))],
            }
        )

    fig = go.Figure()
    # static base: corridor line
    fig.add_trace(
        go.Scatter(
            x=[min(positions) - 60, max(positions) + 60],
            y=[0, 0],
            mode="lines",
            line={"width": 14, "color": COLOR_ROAD},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    # placeholder trace per vehicle slot (initial frame positions)
    valid_t0 = 0.0
    for trace, (times, xs) in zip(simulation.vehicle_traces, series, strict=True):
        fig.add_trace(
            go.Scatter(
                x=[vehicle_position_at(times, xs, valid_t0)],
                y=[0],
                mode="markers",
                marker=dict(
                    size=12,
                    color=COLOR_FORWARD if trace.direction == "forward" else COLOR_REVERSE,
                    symbol=(
                        "triangle-right" if trace.direction == "forward" else "triangle-left"
                    ),
                    line={"width": 1, "color": COLOR_BG},
                ),
                hovertemplate=f"v{trace.vehicle_id} ({trace.direction})<extra></extra>",
                showlegend=False,
            )
        )

    fig.frames = tuple(
        go.Frame(
            name=str(fd["name"]),
            data=fd["data"],  # type: ignore[arg-type]
            traces=fd["traces"],  # type: ignore[arg-type]
        )
        for fd in frame_data
    )

    from ..signal_timing import is_green

    for i, offset in enumerate(offsets):
        green_at_0 = is_green(0.0, offset, config.cycle_length, config.green_duration)
        state = "green" if green_at_0 else "red"
        fig.add_trace(
            go.Scatter(
                x=[positions[i]],
                y=[6],
                mode="markers+text",
                text=[f"Light {i + 1} (+{offset:g} s)"],
                textposition="top center",
                textfont=dict(family=FONT_MONO, size=11, color=COLOR_MUTED),
                marker=dict(size=14, color=COLOR_LINE, line={"width": 3, "color": COLOR_BG}),
                showlegend=False,
                hovertemplate=f"Light {i + 1} at t=0: {state}<extra></extra>",
            )
        )

    fig.layout.update(
        base_layout(
            showlegend=False,
        )
    )
    fig.update_xaxes(title=None, ticksuffix=" m", showgrid=False)
    fig.update_yaxes(visible=False, range=[-40, 40])
    slider_steps = [
        {
            "method": "animate",
            "label": fd["name"],
            "args": [
                [fd["name"]],
                {"mode": "immediate", "frame": {"duration": 0, "redraw": True}},
            ],
        }
        for fd in frame_data
    ]
    fig.update_layout(
        updatemenus=[
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {"frame": {"duration": 120, "redraw": True}, "fromcurrent": True},
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"mode": "immediate"}],
                    },
                ],
                "x": 1,
                "xanchor": "right",
                "y": 1.18,
                "direction": "left",
                "pad": {"r": 0, "t": 0},
                "showactive": False,
                "bgcolor": COLOR_SURFACE,
                "bordercolor": COLOR_LINE,
                "font": {"color": COLOR_TEXT, "size": 12},
            }
        ],
        sliders=[
            {
                "steps": slider_steps,
                "x": 0,
                "len": 1,
                "pad": {"t": 30},
                "bgcolor": COLOR_SURFACE,
                "bordercolor": COLOR_LINE,
                "activebgcolor": COLOR_REVERSE,
                "tickcolor": COLOR_LINE,
                "font": {"family": FONT_MONO, "size": 10, "color": COLOR_MUTED},
                "currentvalue": {
                    "prefix": "",
                    "font": {"family": FONT_MONO, "size": 11, "color": COLOR_MUTED},
                },
            }
        ],
        height=340,
    )
    return fig
