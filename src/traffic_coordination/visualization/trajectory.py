"""Position mapping shared by the corridor diagram and vehicle animation.

A vehicle's x-position along the corridor at time ``t``:

- before its first signal arrival it holds at the *approach point* 30 m
  upstream of its first signal;
- while waiting at signal ``i`` it holds at that signal's stop bar;
- while travelling between signals ``i`` and ``j`` it interpolates linearly
  along ``[x_i, x_j]`` between the departure and arrival timestamps;
- after the last signal it continues past it at nominal travel speed.

This is a drawing aid for the educational visualization; it does not affect
simulated waiting or stops (which come only from the documented signal model).
"""

from __future__ import annotations

from typing import Literal

from ..config import ScenarioConfig
from ..models import Corridor, VehicleTrace

APPROACH_M = 30.0

__all__ = ["vehicle_position_series"]


def vehicle_position_series(
    trace: VehicleTrace, corridor: Corridor, config: ScenarioConfig
) -> tuple[list[float], list[float]]:
    """Sample ``(times, x_positions)`` for one vehicle from its trace.

    Sampling follows the vehicle's event breakpoints plus one intermediate
    sample per travel segment; downstream consumers build trajectories from
    these piecewise-linear segments.
    """
    direction = trace.direction
    # intersection indices in the order the vehicle reaches them (reverse
    # vehicles visit N-1 first, so sorting by index alone would be wrong)
    visits = sorted(trace.arrival_at_intersection, key=trace.arrival_at_intersection.__getitem__)
    if not visits:
        return [0.0], [0.0]

    # Intersection that the vehicle enters first depends on direction.
    positions = [it.position_m for it in corridor.intersections]
    x_in_approach = (
        positions[visits[0]] - APPROACH_M
        if direction == "forward"
        else positions[visits[0]] + APPROACH_M
    )

    points: list[tuple[float, float]] = [(0.0, x_in_approach)]
    for order, index in enumerate(visits):
        arrival = trace.arrival_at_intersection[index]
        wait = trace.wait_at_intersection[index]
        departure = arrival + wait
        if points[-1][0] < arrival:
            # travelling segment from previous point to the stop bar
            prev_t, prev_x = points[-1]
            if prev_t < arrival:
                points.append((arrival, prev_x))
        points.append((max(points[-1][0], arrival), positions[index]))
        points.append((departure, positions[index]))
        if order < len(visits) - 1:
            nxt = visits[order + 1]
            arr_next = trace.arrival_at_intersection[nxt]
            points.append(((departure + arr_next) / 2, (positions[index] + positions[nxt]) / 2))
            points.append((arr_next, positions[nxt]))

    # after the last signal, drawn continuing beyond the exit
    last_index = visits[-1]
    depart = max(
        trace.arrival_at_intersection[last_index] + trace.wait_at_intersection[last_index],
        points[-1][0],
    )
    exit_x = (
        positions[last_index] + APPROACH_M
        if direction == "forward"
        else positions[last_index] - APPROACH_M
    )
    points.append((depart, exit_x))

    times = [p[0] for p in points]
    xs = [p[1] for p in points]
    return times, xs


def direction_of(traces: list[VehicleTrace]) -> list[Literal["forward", "reverse"]]:
    return [t.direction for t in traces]
