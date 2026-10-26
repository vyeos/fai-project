"""Deterministic traffic signal simulation for a full timing plan.

Given a fixed set of vehicles and a timing plan, the simulator walks each
vehicle through the corridor intersection by intersection:

1. The vehicle arrives at the next signal at time ``t``; the coordinated
   movement is green iff ``((t - O_i) mod C) < G``.
2. A green arrival passes immediately with no waiting and no stop.
3. A red arrival waits ``C - ((t - O_i) mod C)`` seconds until the next
   green window, counts one stop, and departs at ``t + wait``.
4. It then travels ``tau = d / v`` seconds along the link to the next signal.
   ``departure_time`` already includes travel from an upstream source, so the
   first arrival time equals the vehicle's departure time.

Simplifications (documented in the report and docs/limitations.md): constant
nominal speed, no acceleration/deceleration profiles, no queue discharge flow or
capacity limits (vehicles never block each other), single shared green phase per
signal, no turning movements, no pedestrians. The simulator is exactly
reproducible: it uses no randomness and produces identical output for identical
inputs ``(plan, vehicles, config)``.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from .config import ScenarioConfig
from .models import (
    SimulationResult,
    TimingPlan,
    VehicleSpec,
    VehicleTrace,
)
from .signal_timing import signal_wait, travel_time_seconds

__all__ = ["evaluate_plan", "simulate_plan"]


def simulate_plan(  # noqa: PLR0912
    plan: TimingPlan,
    vehicles: Sequence[VehicleSpec],
    config: ScenarioConfig,
    *,
    collect_traces: bool = False,
) -> SimulationResult:
    """Simulate ``plan`` over ``vehicles`` and return aggregate metrics.

    Args:
        plan: Complete timing plan (offsets for every intersection).
        vehicles: Vehicle requests (departure times + directions).
        config: Scenario parameters (cycle, green, links, speed, weights).
        collect_traces: Also record per-vehicle trajectories (needed for
            visualizations; disabled during CSP search for speed).

    Returns:
        A :class:`SimulationResult` with totals summed over both directions.

    Raises:
        ValueError: If the plan is shorter than the corridor.

    """
    n = config.n_intersections
    if len(plan) != n:
        raise ValueError(f"Plan defines {len(plan)} offsets but corridor has {n} intersections")

    cycle = config.cycle_length
    green = config.green_duration
    offsets = plan.offsets
    link_times = [
        travel_time_seconds(d, config.speed_kmh) for d in config.effective_link_distances_m
    ]

    total_wait = 0.0
    total_stops = 0
    per_intersection: dict[int, dict[str, float]] = {
        i: {"waiting_time": 0.0, "stops": 0, "arrivals": 0} for i in range(n)
    }
    traces: list[VehicleTrace] | None = None
    if collect_traces:
        traces = [VehicleTrace(v.vehicle_id, v.direction) for v in vehicles]

    for v_idx, vehicle in enumerate(vehicles):
        trace = traces[v_idx] if traces else None
        if trace is not None:
            trace.arrival_at_intersection = {}
            trace.wait_at_intersection = {}
            trace.departure_from_intersection = {}

        if vehicle.direction == "forward":
            stop_seq = range(n)
        else:
            stop_seq = range(n - 1, -1, -1)

        t = vehicle.departure_time
        for seq_pos, i in enumerate(stop_seq):
            wait = signal_wait(t, offsets[i], cycle, green)
            if wait > 1e-9:
                total_wait += wait
                total_stops += 1
                per_intersection[i]["waiting_time"] += wait
                per_intersection[i]["stops"] += 1
            per_intersection[i]["arrivals"] += 1

            if trace is not None:
                trace.arrival_at_intersection[i] = t
                trace.wait_at_intersection[i] = wait
                trace.departure_from_intersection[i] = t + wait

            t += wait
            if seq_pos < n - 1:
                # link between intersection i and the next one on the route
                nxt = i + 1 if vehicle.direction == "forward" else i - 1
                t += link_times[min(i, nxt)]

        if trace is not None:
            trace.total_wait = sum(trace.wait_at_intersection.values())
            trace.stops = sum(1 for w in trace.wait_at_intersection.values() if w > 1e-9)

    n_vehicles = len(vehicles)
    objective = (
        config.objective_weight_wait * total_wait + config.objective_weight_stop * total_stops
    )
    return SimulationResult(
        plan=plan,
        total_waiting_time=total_wait,
        average_waiting_time=total_wait / n_vehicles if n_vehicles else 0.0,
        total_stops=total_stops,
        n_vehicles=n_vehicles,
        objective=objective,
        vehicle_traces=traces or [],
        per_intersections=per_intersection,
    )


def evaluate_plan(
    plan: TimingPlan,
    vehicles: Sequence[VehicleSpec],
    config: ScenarioConfig,
    *,
    timer: Callable[[], float] = time.perf_counter,
) -> tuple[SimulationResult, float]:
    """Evaluate a plan and also return its wall-clock evaluation time (seconds)."""
    start = timer()
    result = simulate_plan(plan, vehicles, config)
    return result, timer() - start
