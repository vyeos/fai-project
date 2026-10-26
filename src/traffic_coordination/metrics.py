"""Aggregated algorithm metrics, comparison tables and export structures.

Every algorithm returns a :class:`AlgorithmResult`. Search-only statistics
(nodes expanded, backtracks, forward-check removals, branch-and-bound prunes)
are zero for the non-searching baselines, which lets a single comparison table
fairly display all three methods.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from .models import SimulationResult, TimingPlan

FEASIBLE_OPTIMAL = "feasible (optimality proven)"
FEASIBLE_TIME_LIMIT = "incomplete (budget reached; best-so-far, optimality unproven)"
FEASIBLE_SUBOPTIMAL = "feasible (heuristic method, no optimality guarantee)"
FEASIBLE_SINGLE = "feasible (single deterministic plan)"
STATUS_NO_SOLUTION = "no feasible plan found"

__all__ = [
    "FEASIBLE_OPTIMAL",
    "FEASIBLE_SINGLE",
    "FEASIBLE_SUBOPTIMAL",
    "FEASIBLE_TIME_LIMIT",
    "STATUS_NO_SOLUTION",
    "AlgorithmResult",
    "results_dataframe",
]


@dataclass
class AlgorithmResult:
    """The outcome of one algorithm run on one scenario.

    Attributes:
        algorithm: ``"uncoordinated"``, ``"greedy"`` or ``"csp"``.
        plan: The selected timing plan; all offsets are within the legal domain
            and the first offset is 0 by construction.
        simulation: Simulated performance of ``plan`` on the scenario's traffic.
        search_time_s: Wall-clock seconds (monotonic high-resolution timer) spent
            by the algorithm, including simulation of evaluated candidate plans.
        status: One of the FEASIBLE_*/STATUS_NO_SOLUTION constants above.
        nodes_expanded: Partial assignments extended by the search.
        assignments_attempted: Individual (variable, value) assignment attempts.
        constraint_rejections: Attempts rejected by constraint checks.
        backtracks: Occasions the search undid an assignment after a dead end.
        forward_check_removals: Domain values removed by forward checking.
        branch_bound_prunes: Subtrees skipped because their lower bound could
            not beat the incumbent best objective.
        complete_assignments_evaluated: Number of complete plans simulated.
        best_objective: Objective value of the returned plan.
        search_time_limit_s: Budget configured for the search (None = none).
        backtrack_count_limit: Budget on backtracking nodes (None = no limit).
        metadata: Free-form extras (e.g. verifier results).

    """

    algorithm: str
    plan: TimingPlan
    simulation: SimulationResult
    search_time_s: float
    status: str = FEASIBLE_SINGLE

    nodes_expanded: int = 0
    assignments_attempted: int = 0
    constraint_rejections: int = 0
    backtracks: int = 0
    forward_check_removals: int = 0
    branch_bound_prunes: int = 0
    complete_assignments_evaluated: int = 0
    best_objective: float = 0.0

    search_time_limit_s: float | None = None
    maximum_backtracks: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def summary_dict(self) -> dict[str, object]:
        """Flat record for tables, CSV exports and Streamlit display."""
        data = asdict(self)
        data.pop("plan", None)
        data.pop("simulation", None)
        data.pop("metadata", None)
        return {
            **{
                "algorithm": self.algorithm,
                "status": self.status,
                "search_time_s": round(self.search_time_s, 4),
                "nodes_expanded": self.nodes_expanded,
                "assignments_attempted": self.assignments_attempted,
                "constraint_rejections": self.constraint_rejections,
                "backtracks": self.backtracks,
                "forward_check_removals": self.forward_check_removals,
                "branch_bound_prunes": self.branch_bound_prunes,
                "complete_assignments_evaluated": self.complete_assignments_evaluated,
                "best_objective": round(self.best_objective, 4),
                **self.simulation.summary_dict(),
            },
            "offsets": list(self.plan.offsets),
        }


def results_dataframe(results: list[AlgorithmResult] | list[dict[str, object]]) -> pd.DataFrame:
    """Build the comparison table used by the dashboard and experiments."""
    rows = [r.summary_dict if isinstance(r, AlgorithmResult) else r for r in results]
    frame = pd.DataFrame(rows)
    if "algorithm" in frame.columns:
        order = {"uncoordinated": 0, "greedy": 1, "csp": 2}
        frame = frame.assign(
            _order=frame["algorithm"].map(order).fillna(9).astype(int)
        ).sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return frame


def improvement_percent(baseline: float, improved: float) -> float | None:
    """Relative reduction from ``baseline`` to ``improved`` in percent.

    Returns None when the baseline is zero (improvement undefined).
    """
    if baseline == 0:
        return None
    return (baseline - improved) / baseline * 100.0
