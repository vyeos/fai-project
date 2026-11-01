"""Corridor diagram: signals, links and vehicles at a moment in time."""

from __future__ import annotations

import plotly.graph_objects as go

from ..config import ScenarioConfig
from ..models import Corridor, SimulationResult
from . import (
    COLOR_FAINT,
    COLOR_FORWARD,
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_RED,
    COLOR_REVERSE,
    COLOR_ROAD,
    COLOR_SURFACE,
    base_layout,
)
from .trajectory import vehicle_position_series

__all__ = ["corridor_figure", "vehicle_position_at"]


def vehicle_position_at(times: list[float], xs: list[float], t: float) -> float:
    """Interpolate the piecewise-linear trajectory ``(times, xs)`` at ``t``."""
    if not times:
        return 0.0
    if t <= times[0]:
        return xs[0]
    if t >= times[-1]:
        return xs[-1]
    for i in range(1, len(times)):
        if t <= times[i]:
            t0, t1 = times[i - 1], times[i]
            if t1 == t0:
                return xs[i]
            frac = (t - t0) / (t1 - t0)
            return xs[i - 1] + frac * (xs[i] - xs[i - 1])
    return xs[-1]


def corridor_figure(
    corridor: Corridor,
    config: ScenarioConfig,
    offsets: tuple[float, ...],
    simulation: SimulationResult,
    time_s: float = 0.0,
) -> go.Figure:
    """Draw the corridor at ``time_s``: signal states, vehicles, distances."""
    fig = go.Figure()
    positions = [it.position_m for it in corridor.intersections]

    # link line
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
    # links with distances
    for i, d in enumerate(corridor.link_distances_m):
        mid = (positions[i] + positions[i + 1]) / 2
        fig.add_annotation(
            x=mid,
            y=-24,
            text=f"{d:.0f} m",
            showarrow=False,
            font=dict(size=10, color=COLOR_FAINT),
        )

    # signals as markers colored by state at time_s
    from ..signal_timing import is_green

    for i, offset in enumerate(offsets):
        green = is_green(time_s, offset, config.cycle_length, config.green_duration)
        fig.add_trace(
            go.Scatter(
                x=[positions[i]],
                y=[0],
                mode="markers+text",
                text=[f"Light {i + 1}<br>+{offset:g} s"],
                textposition="top center",
                textfont=dict(size=11, color=COLOR_MUTED),
                marker=dict(
                    size=22,
                    color=COLOR_GREEN if green else COLOR_RED,
                    line={"width": 4, "color": COLOR_SURFACE},
                ),
                name=f"Light {i + 1}",
                hovertemplate=(
                    f"Light {i + 1} · green starts +{offset:g} s<br>"
                    f"{('green' if green else 'red')} at t={time_s:.1f} s<extra></extra>"
                ),
                showlegend=False,
            )
        )

    # vehicles at time_s
    for trace in simulation.vehicle_traces:
        times, xs = vehicle_position_series(trace, corridor, config)
        x = vehicle_position_at(times, xs, time_s)
        fig.add_trace(
            go.Scatter(
                x=[x],
                y=[0],
                mode="markers",
                marker=dict(
                    size=12,
                    color=COLOR_FORWARD if trace.direction == "forward" else COLOR_REVERSE,
                    symbol="triangle-right" if trace.direction == "forward" else "triangle-left",
                    line={"width": 1, "color": COLOR_SURFACE},
                ),
                name=f"vehicle {trace.vehicle_id}",
                hovertemplate=(
                    f"Car {trace.vehicle_id + 1}: {trace.stops} stop(s), "
                    f"{trace.total_wait:.0f} s waiting<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.layout.update(
        base_layout(
            title=None,
            margin={"l": 24, "r": 24, "t": 16, "b": 36},
            showlegend=False,
        )
    )
    fig.update_xaxes(title=None, ticksuffix=" m", showgrid=False, zeroline=False)
    fig.update_yaxes(visible=False, range=[-50, 50])
    fig.update_layout(height=240)
    return fig
