"""Baseline 1 - uncoordinated timing (all offsets zero).

This deliberately ignores progression between signals to establish the
performance cost of *not* coordinating the corridor. It uses the same
simulator and objective as every other method, so the comparison is fair by
construction.
"""

from __future__ import annotations

import time

from ..config import ScenarioConfig
from ..metrics import FEASIBLE_SINGLE, AlgorithmResult
from ..models import VehicleSpec, timing_plan
from ..simulator import simulate_plan

__all__ = ["run_uncoordinated"]


def run_uncoordinated(
    vehicles: list[VehicleSpec],
    config: ScenarioConfig,
) -> AlgorithmResult:
    """Evaluate the all-zero offset plan on ``vehicles``.

    Returns:
        An :class:`AlgorithmResult` with zero search statistics, since this
        baseline performs no search: it evaluates a single fixed plan.

    """
    timer_start = time.perf_counter()
    plan = timing_plan([0.0] * config.n_intersections)
    simulation = simulate_plan(plan, vehicles, config)
    elapsed = time.perf_counter() - timer_start
    return AlgorithmResult(
        algorithm="uncoordinated",
        plan=plan,
        simulation=simulation,
        search_time_s=max(elapsed, 0.0),
        status=FEASIBLE_SINGLE,
        best_objective=simulation.objective,
        metadata={"description": "All offsets are zero (uncoordinated reference plan)"},
    )
