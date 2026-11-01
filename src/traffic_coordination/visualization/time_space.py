"""Time-space diagram: the classic way traffic engineers draw a green wave.

Time runs along the x-axis and distance along the road up the y-axis. Each
signal is a horizontal bar at its position, coloured green or red over time,
and each vehicle is a line. A car driving freely is a straight diagonal; a car
held at a red light draws a flat step at that signal. A good timing plan lets
the diagonals slip through the green parts of every bar.

The lines are built from the simulator's own per-vehicle traces (arrival and
departure at each signal), so the drawing shows exactly what was scored.
"""

from __future__ import annotations

import plotly.graph_objects as go

from ..config import ScenarioConfig
from ..models import Corridor, SimulationResult
from . import COLOR_FORWARD, COLOR_GREEN, COLOR_RED, COLOR_REVERSE, base_layout

__all__ = ["time_space_figure"]

# Seconds of free driving drawn before a car's first signal and after its last.
LEAD_S = 12.0


def _signal_segments(
    offset: float, config: ScenarioConfig, horizon: float
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Green and red windows of one signal clipped to ``[0, horizon]``."""
    cycle, green = config.cycle_length, config.green_duration
    greens: list[tuple[float, float]] = []
    reds: list[tuple[float, float]] = []
    k = int(-(offset // cycle)) - 1
    while offset + k * cycle < horizon:
        start = offset + k * cycle
        windows = ((start, start + green, greens), (start + green, start + cycle, reds))
        for lo, hi, bucket in windows:
            lo, hi = max(lo, 0.0), min(hi, horizon)
            if hi > lo:
                bucket.append((lo, hi))
        k += 1
    return greens, reds


def time_space_figure(
    corridor: Corridor,
    config: ScenarioConfig,
    offsets: tuple[float, ...],
    simulation: SimulationResult,
    *,
    horizon_s: float | None = None,
    title: str | None = None,
    height: int = 420,
    show_legend: bool = True,
) -> go.Figure:
    """Draw signals as coloured bars and every traced vehicle as a line.

    ``simulation`` must have been run with ``collect_traces=True``.
    ``horizon_s`` fixes the time axis so two plans can share a scale.
    """
    positions = [it.position_m for it in corridor.intersections]
    speed_ms = config.speed_kmh / 3.6
    lead_m = speed_ms * LEAD_S
    traces = simulation.vehicle_traces

    if horizon_s is None:
        last = max(
            (
                max(t.departure_from_intersection.values())
                for t in traces
                if t.arrival_at_intersection
            ),
            default=2 * config.cycle_length,
        )
        horizon_s = last + LEAD_S + 4

    fig = go.Figure()

    for colour, name, pick in ((COLOR_GREEN, "Green light", 0), (COLOR_RED, "Red light", 1)):
        xs: list[float | None] = []
        ys: list[float | None] = []
        for pos, offset in zip(positions, offsets, strict=True):
            for lo, hi in _signal_segments(offset, config, horizon_s)[pick]:
                xs += [lo, hi, None]
                ys += [pos, pos, None]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": colour, "width": 6},
                opacity=0.55,
                name=name,
                hoverinfo="skip",
                showlegend=show_legend,
            )
        )

    for direction, colour, label in (
        ("forward", COLOR_FORWARD, "Car heading up the road"),
        ("reverse", COLOR_REVERSE, "Car heading down the road"),
    ):
        xs, ys, text = [], [], []
        sign = 1.0 if direction == "forward" else -1.0
        for trace in traces:
            if trace.direction != direction or not trace.arrival_at_intersection:
                continue
            order = sorted(trace.arrival_at_intersection, key=trace.arrival_at_intersection.get)
            label_text = (
                f"Car {trace.vehicle_id + 1}: {trace.stops} stop(s), "
                f"{trace.total_wait:.0f} s waiting"
            )
            first, last = order[0], order[-1]
            enter = trace.arrival_at_intersection[first] - LEAD_S
            points = [(enter, positions[first] - sign * lead_m)]
            for i in order:
                points.append((trace.arrival_at_intersection[i], positions[i]))
                points.append((trace.departure_from_intersection[i], positions[i]))
            leave = trace.departure_from_intersection[last] + LEAD_S
            points.append((leave, positions[last] + sign * lead_m))
            for t, x in points:
                xs.append(t)
                ys.append(x)
                text.append(label_text)
            xs.append(None)
            ys.append(None)
            text.append("")
        if xs:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line={"color": colour, "width": 1.5},
                    opacity=0.9,
                    name=label,
                    text=text,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=show_legend,
                )
            )

    span = positions[-1] - positions[0]
    pad = max(lead_m, span * 0.06)
    fig.layout.update(
        base_layout(
            title=title,
            height=height,
            hovermode="closest",
            margin={"l": 64, "r": 24, "t": 40 if title else 16, "b": 52},
        )
    )
    fig.update_xaxes(title="Time (seconds)", range=[0, horizon_s], showgrid=False)
    fig.update_yaxes(
        title=None,
        tickmode="array",
        tickvals=positions,
        ticktext=[f"Light {i + 1}" for i in range(len(positions))],
        range=[positions[0] - pad, positions[-1] + pad],
        showgrid=False,
    )
    return fig

