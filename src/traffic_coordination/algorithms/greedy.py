"""Baseline 2 - greedy one-way progression coordination.

For consecutive intersections the greedy strategy assigns the downstream
offset from the nominal link travel time ``tau_i = d_i / v``:

    O_{i+1} ~ (O_i + tau_i)  (mod C)

Because offsets belong to a discrete domain, the strategy selects the *legal*
offset whose circular distance to ``desired = (O_i + tau_i) mod C`` is minimal;
ties are broken deterministically by taking the smaller offset.

Engineered properties (documented here and in the report):

- it builds a "green wave" that optimizes progression in the **forward**
  direction only, because it considers no demand and no reverse direction;
- it never reconsiders an earlier assignment, so errors accumulate downstream;
- it provides no optimality guarantee - the CSP optimizer exists to quantify
  what a global search can add over this cheap heuristic.
"""

from __future__ import annotations

import time

from ..config import ScenarioConfig
from ..metrics import FEASIBLE_SUBOPTIMAL, AlgorithmResult
from ..models import VehicleSpec, timing_plan
from ..signal_timing import travel_time_seconds
from ..simulator import simulate_plan

__all__ = ["greedy_offsets", "run_greedy"]


def _circular_distance(a: float, b: float, cycle_length: float) -> float:
    """Shortest distance between two phases on a circle of length ``C``."""
    diff = abs(a - b) % cycle_length
    return min(diff, cycle_length - diff)


def greedy_offsets(config: ScenarioConfig) -> tuple[float, ...]:
    """Return the greedy one-way progression offsets for ``config``.

    The first intersection keeps the reference offset 0; each downstream offset
    is the legal grid value nearest (on the cycle) to ``(O_i + tau_i) mod C``.
    """
    cycle = config.cycle_length
    grid = config.offset_grid()
    if not grid:
        raise ValueError("Offset domain is empty; check offset resolution")

    offsets = [0.0]
    for i in range(config.n_intersections - 1):
        tau = travel_time_seconds(config.effective_link_distances_m[i], config.speed_kmh)
        desired = (offsets[-1] + tau) % cycle
        # min() with tuple keys is deterministic: distance first, then smaller
        # offset wins ties (lexicographic tie-breaking).
        best = min(grid, key=lambda o: (_circular_distance(o, desired, cycle), o))
        offsets.append(best)
    return tuple(offsets)


def run_greedy(
    vehicles: list[VehicleSpec],
    config: ScenarioConfig,
) -> AlgorithmResult:
    """Compute the greedy plan and evaluate it on ``vehicles``.

    Returns:
        An :class:`AlgorithmResult` with zero search statistics; the greedy
        method is a constructive heuristic, not a search.

    """
    timer_start = time.perf_counter()
    offsets = greedy_offsets(config)
    plan = timing_plan(offsets)
    simulation = simulate_plan(plan, vehicles, config)
    elapsed = time.perf_counter() - timer_start
    return AlgorithmResult(
        algorithm="greedy",
        plan=plan,
        simulation=simulation,
        search_time_s=max(elapsed, 0.0),
        status=FEASIBLE_SUBOPTIMAL,
        best_objective=simulation.objective,
        metadata={
            "description": "Greedy one-way progression: downstream offsets follow "
            "upstream offset + nominal link travel time, rounded to the legal grid",
        },
    )
