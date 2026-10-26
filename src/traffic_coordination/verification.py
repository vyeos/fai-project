"""Independent exhaustive-search verification for small instances.

Brute-force enumeration independent of the CSP solver: it walks the full
cartesian product of offset values (first offset fixed to 0), applies the hard
constraints pair by pair, simulates every remaining complete plan, and keeps
the lexicographically-first optimum (strict improvement only, ascending order).

Purpose:

- verify that the CSP optimizer returns the true minimum among feasible plans;
- verify that branch-and-bound lower-bound pruning never removes an optimum;
- verify constraint-filtering behaviour with an independent implementation.

The enumeration is intentionally *not* a search: no backtracking, no pruning,
no shared code with the optimizer beyond the simulator, so agreement between
the two methods is meaningful evidence.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

from .config import ScenarioConfig
from .models import TimingPlan, VehicleSpec
from .signal_timing import travel_time_seconds
from .simulator import simulate_plan

__all__ = ["ExhaustiveResult", "exhaustive_best"]


@dataclass
class ExhaustiveResult:
    """Outcome of an exhaustive enumeration.

    Attributes:
        best_objective: Objective of the best feasible plan (``nan`` when none).
        best_offsets: The best plan (first offset 0) or ``None``.
        feasible_plans: Number of complete plans that satisfied every hard
            constraint (before simulation).
        plans_considered: Number of complete plans seen by the enumeration
            (before constraint filtering).
        completed: False when a time budget stopped the enumeration early —
            in that case the reported best is *not* guaranteed to be optimal.
        elapsed_s: Wall-clock seconds (``time.perf_counter``).
        best_stops / best_waiting_time: performance of the best plan.

    """

    best_objective: float = float("nan")
    best_offsets: tuple[float, ...] | None = None
    feasible_plans: int = 0
    plans_considered: int = 0
    completed: bool = False
    elapsed_s: float = 0.0
    best_stops: int = 0
    best_waiting_time: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


def exhaustive_best(  # noqa: PLR0912
    config: ScenarioConfig,
    vehicles: list[VehicleSpec],
    *,
    time_budget_s: float | None = None,
) -> ExhaustiveResult:
    """Enumerate every feasible timing plan and return the best one.

    Args:
        config: Scenario parameters; hard constraints are taken from
            ``progression_tolerance_s``.
        vehicles: Vehicle demand (identical for all evaluations).
        time_budget_s: Optional wall-clock budget; on expiry ``completed`` is
            False and optimality of the reported best is not claimed.

    Returns:
        An :class:`ExhaustiveResult`.

    """
    grid = config.offset_grid()
    cycle = config.cycle_length
    links = config.effective_link_distances_m
    travel_times = [travel_time_seconds(d, config.speed_kmh) % cycle for d in links]
    rho = config.progression_tolerance_s

    start = time.perf_counter()
    result = ExhaustiveResult()
    best_cost = float("inf")

    def pair_ok(parent: float, child: float, tau_mod: float) -> bool:
        if rho is None:
            return True
        achieved = (child - parent) % cycle
        deviation = abs(achieved - tau_mod) % cycle
        deviation = min(deviation, cycle - deviation)
        return deviation <= rho + 1e-9

    for combo in itertools.product(grid, repeat=config.n_intersections - 1):
        if time_budget_s is not None and (time.perf_counter() - start) >= time_budget_s:
            result.elapsed_s = time.perf_counter() - start
            return result  # completed=False
        result.plans_considered += 1
        offsets = (0.0,) + combo
        ok = True
        for i, tau_mod in enumerate(travel_times):
            if not pair_ok(offsets[i], offsets[i + 1], tau_mod):
                ok = False
                break
        if not ok:
            continue
        result.feasible_plans += 1
        simulation = simulate_plan(TimingPlan(tuple(offsets)), vehicles, config)
        if simulation.objective < best_cost:  # strict: first optimum wins
            best_cost = simulation.objective
            result.best_objective = simulation.objective
            result.best_offsets = tuple(offsets)
            result.best_stops = simulation.total_stops
            result.best_waiting_time = simulation.total_waiting_time

    result.completed = True
    result.elapsed_s = time.perf_counter() - start
    return result
