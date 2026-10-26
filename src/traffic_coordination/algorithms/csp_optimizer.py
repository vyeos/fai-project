"""CSP optimizer: backtracking + forward checking + branch-and-bound.

Problem formulation (see the project report, Section 4.4):

- **Variables** O_1..O_N: signal offsets. O_1 = 0 is the temporal reference and
  is fixed a priori, so the search assigns O_2..O_N.
- **Domains** D_i: the discrete offset grid {0, r, 2r, ..., C - r}.
- **Hard constraints**: (a) domain membership; (b) the reference constraint
  O_1 = 0; (c) optionally a *progression tolerance*: for every adjacent pair
  (i, i+1) the circular distance between the achieved offset difference
  (O_{i+1} - O_i) mod C and the nominal travel time tau_i (mod C) must be at
  most ``progression_tolerance_s``. With the tolerance set to C/2 (or None) the
  constraint is vacuous — every adjacent pair is allowed; smaller values
  restrict the search space and give forward checking genuine pruning power.
- **Soft objective**: J = alpha*W + beta*S through the deterministic simulator.

Algorithm structure:

- Static variable ordering: left-to-right along the corridor.
- **Forward checking** removes from the domain of the next unassigned variable
  every value inconsistent with the current assignment (the constraint graph
  is a chain, so one neighbour suffices). An empty resulting domain is a dead
  end; state is restored exactly and the search backtracks.
- **Branch-and-bound** keeps the incumbent best complete solution and computes
  a valid lower bound for every partial assignment; a subtree whose bound
  cannot strictly beat the incumbent is pruned. The default bound is

      h(s) = 0

  which is admissible (remaining costs are non-negative) and consistent
  (adding non-negative edge costs cannot violate h(s) <= c(s, a) + h(s')). It
  is safe for every partial state but weak: with non-negative objective costs
  it prunes nothing in practice. ``branch_bound_prunes`` therefore reports the
  *actual* number of prunes (usually 0), and docs/algorithms.md discusses this
  honestly instead of inflating the statistic.
- Each complete feasible assignment is simulated and may improve the incumbent
  (strict improvement only), so ties resolve lexicographically because domain
  values are tried in ascending order.
- ``use_forward_checking=False`` runs the same search as a no-pruning
  ablation: attempts that violate a pair constraint are counted as
  ``constraint_rejections`` instead of never being attempted. This is used in
  tests and sensitivity experiments to quantify the value of forward checking.

Resource limits: a wall-clock time budget and/or a cap on simulated complete
assignments can be supplied. When a limit is hit the result status becomes
``incomplete`` — the returned plan is the best found *so far* and its
optimality is explicitly not claimed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..config import ScenarioConfig
from ..metrics import (
    FEASIBLE_OPTIMAL,
    FEASIBLE_TIME_LIMIT,
    STATUS_NO_SOLUTION,
    AlgorithmResult,
)
from ..models import VehicleSpec, timing_plan
from ..signal_timing import travel_time_seconds
from ..simulator import simulate_plan

__all__ = ["CSPSearchStats", "SearchTrace", "run_csp"]


class _BudgetExceeded(Exception):
    """Internal control-flow exception raised when a search budget is hit."""


@dataclass
class CSPSearchStats:
    """Counters capturing the actual behaviour of one search run.

    Distinguishing the fields matters for the viva:

    - ``search_space_size`` is the theoretical product D^(N-1) before pruning;
    - ``nodes_expanded`` counts partial assignments *extended* by the search;
    - ``complete_assignments_evaluated`` counts complete plans actually
      simulated. These three are different measures and must not be merged.
    """

    search_space_size: int = 0
    nodes_expanded: int = 0
    assignments_attempted: int = 0
    constraint_rejections: int = 0
    backtracks: int = 0
    forward_check_removals: int = 0
    branch_bound_prunes: int = 0
    complete_assignments_evaluated: int = 0
    dead_ends: int = 0
    best_objective: float = float("inf")
    search_time_s: float = 0.0
    lower_bound: str = "h(s) = 0 (admissible and consistent)"

    def as_dict(self) -> dict[str, object]:
        """Return the counters as a plain dict for JSON metadata/export."""
        return {
            "search_space_size": self.search_space_size,
            "nodes_expanded": self.nodes_expanded,
            "assignments_attempted": self.assignments_attempted,
            "constraint_rejections": self.constraint_rejections,
            "backtracks": self.backtracks,
            "forward_check_removals": self.forward_check_removals,
            "branch_bound_prunes": self.branch_bound_prunes,
            "complete_assignments_evaluated": self.complete_assignments_evaluated,
            "dead_ends": self.dead_ends,
            "best_objective": round(self.best_objective, 6),
            "search_time_s": round(self.search_time_s, 4),
            "lower_bound": self.lower_bound,
        }


@dataclass
class SearchTrace:
    """An inspectable record of the search's actual execution.

    Events are capped by ``event_limit`` (kept in chronological order) so that
    huge searches cannot produce unbounded traces; aggregate counters always
    live in :class:`CSPSearchStats`. Event types and fields:

    - ``assign``: ``var``, ``value`` - tentative variable assignment;
    - ``reject``: ``var``, ``value``, ``parent`` - value rejected by the
      pairwise progression constraint (only possible with forward checking
      disabled);
    - ``fc_remove``: ``var``, ``value``, ``next_var``, ``removed`` - forward
      checking narrowed the next variable's domain;
    - ``dead_end``: ``var``, ``value`` - forward checking produced an empty
      domain, so no child value is attempted;
    - ``backtrack``: ``var`` - the assignment of ``var`` was undone;
    - ``evaluate``: ``offsets``, ``objective`` - a complete assignment was
      simulated;
    - ``best``: ``offsets``, ``objective`` - the incumbent improved;
    - ``prune_bb``: ``var``, ``value``, ``lower_bound``, ``incumbent`` - a
      subtree was pruned by the lower bound;
    - ``limit``: ``message`` - a budget stopped the search.
    """

    events: list[dict[str, object]] = field(default_factory=list)
    event_limit: int = 2000
    truncated: bool = False

    def add(self, event_type: str, **payload: object) -> None:
        """Append one event, enforcing the retention cap (chronological)."""
        if len(self.events) >= self.event_limit:
            if not self.truncated:
                self.events.append(
                    {"type": "limit", "message": "trace event cap reached; later events omitted"}
                )
                self.truncated = True
            return
        self.events.append({"type": event_type, **payload})

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable snapshot of the trace."""
        return {"events": list(self.events), "truncated": self.truncated}


class _Searcher:
    """One deterministic backtracking search over offset grid indices.

    Grid indices (integers into ``self.grid``) are used internally so that
    forward-checking membership tests are O(1) set lookups.
    """

    def __init__(
        self,
        config: ScenarioConfig,
        vehicles: list[VehicleSpec],
        stats: CSPSearchStats,
        trace: SearchTrace,
        *,
        time_budget_s: float | None = None,
        evaluation_cap: int | None = None,
        use_forward_checking: bool = True,
    ) -> None:
        self.config = config
        self.vehicles = vehicles
        self.stats = stats
        self.trace = trace
        self.time_budget_s = time_budget_s
        self.evaluation_cap = evaluation_cap
        self.use_forward_checking = use_forward_checking

        n = config.n_intersections
        self.n = n
        self.grid = config.offset_grid()
        self.grid_size = len(self.grid)
        cycle = config.cycle_length
        links = config.effective_link_distances_m
        rho = config.progression_tolerance_s

        # Domain of every variable is the full grid; the reference variable O_1
        # is fixed to the single value 0.
        self.domains: list[list[int]] = [list(range(self.grid_size)) for _ in range(n)]
        self.domains[0] = [0]

        # For each adjacent pair (i, i+1) and each parent grid index: the set of
        # legal child grid indices under the progression constraint. Vacuous
        # when ``rho`` is None. Pre-computing this makes individual constraint
        # checks O(1).
        self.allowed_jumps: list[list[set[int]]] = []
        for i in range(n - 1):
            tau = travel_time_seconds(links[i], config.speed_kmh) % cycle
            row: list[set[int]] = []
            for parent in self.grid:
                if rho is None:
                    row.append(set(range(self.grid_size)))
                    continue
                allowed: set[int] = set()
                for child_idx, child in enumerate(self.grid):
                    achieved = (child - parent) % cycle
                    deviation = abs(achieved - tau) % cycle
                    deviation = min(deviation, cycle - deviation)
                    if deviation <= rho + 1e-9:
                        allowed.add(child_idx)
                row.append(allowed)
            self.allowed_jumps.append(row)

        self.assignment: list[int] = [-1] * n  # grid indices
        self.best_cost = float("inf")
        self.best_plan: tuple[float, ...] | None = None
        self._ops = 0
        self._start = 0.0
        stats.search_space_size = self.grid_size ** (n - 1)

    # -- budget handling -------------------------------------------------------

    def _budget_hit(self) -> None:
        """Raise :class:`_BudgetExceeded` when a limit is reached.

        The evaluation cap is checked at every attempt. The time budget is
        checked every 256 attempts: ``perf_counter`` is cheap but its cost is
        not free, and 256 attempts are typically tens of microseconds apart.
        """
        self._ops += 1
        if self.evaluation_cap is not None and (
            self.stats.complete_assignments_evaluated >= self.evaluation_cap
        ):
            raise _BudgetExceeded("simulation cap reached")
        if self.time_budget_s is not None and self._ops % 256 == 0:
            if time.perf_counter() - self._start >= self.time_budget_s:
                raise _BudgetExceeded("time budget reached")

    # -- constraint checking ---------------------------------------------------

    def _pair_consistent(self, parent_var: int, child_idx: int) -> bool:
        """Check the (c) progression constraint between parent and child."""
        return child_idx in self.allowed_jumps[parent_var][self.assignment[parent_var]]

    # -- lower bound (branch and bound) ----------------------------------------

    def _lower_bound(self) -> float:
        """Return a valid lower bound on the cost of any completion of this state.

        By default ``h(s) = 0``: every remaining vehicle-signal interaction
        contributes a non-negative amount to J, hence the bound is admissible
        (never overestimates) and consistent (h(s) <= c(s, a) + h(s') since
        c(s, a) = 0 for assignment steps between simulations). Constant bounds
        cannot overestimate, so pruning with ``bound >= incumbent`` can never
        remove an optimal completion — the tests verify this against exhaustive
        enumeration.
        """
        return 0.0

    # -- forward checking ------------------------------------------------------

    def _forward_check(self, var: int, value_idx: int) -> list[int] | None:
        """Narrow the next variable's domain against (var = value_idx).

        Returns the narrowed domain, or ``None`` when it is empty (dead end).
        Only the next variable can be affected: the progression constraint
        couples adjacent variables and their earlier neighbours were already
        narrowed when those assignments happened. When forward checking is
        disabled this returns the unfiltered domain.
        """
        nxt = var + 1
        if nxt >= self.n:
            return []
        saved = self.domains[nxt]
        if self.use_forward_checking:
            allowed = self.allowed_jumps[var][value_idx]
            keep = [k for k in saved if k in allowed]
            removed = len(saved) - len(keep)
            if removed:
                self.stats.forward_check_removals += removed
                self.trace.add(
                    "fc_remove",
                    var=var,
                    value=self.grid[value_idx],
                    next_var=nxt,
                    removed=removed,
                )
        else:
            keep = saved
        return keep if keep else None

    # -- complete assignment ---------------------------------------------------

    def _current_offsets(self) -> tuple[float, ...]:
        return tuple(self.grid[k] for k in self.assignment)

    def _evaluate_complete(self) -> None:
        offsets = self._current_offsets()
        self.stats.complete_assignments_evaluated += 1
        result = simulate_plan(timing_plan(offsets), self.vehicles, self.config)
        cost = result.objective
        self.trace.add("evaluate", offsets=offsets, objective=cost)
        if cost < self.best_cost:  # strict: keeps the lexicographically first optimum
            self.best_cost = cost
            self.best_plan = offsets
            self.stats.best_objective = cost
            self.trace.add("best", offsets=offsets, objective=cost)

    # -- backtracking search ---------------------------------------------------

    def search(self) -> bool:
        """Run the search. Returns True when it explored the whole space."""
        self._start = time.perf_counter()
        budget_hit = False
        try:
            # O_1 = 0 is the reference constraint: exactly one attempt.
            self.stats.assignments_attempted += 1
            self._assign(0, 0)
        except _BudgetExceeded as exc:
            budget_hit = True
            self.trace.add("limit", message=str(exc))
        self.stats.search_time_s = time.perf_counter() - self._start
        return not budget_hit

    def _assign(self, var: int, value_idx: int) -> None:
        """Assign ``value_idx`` to ``var``, propagate, recurse, and restore."""
        self.assignment[var] = value_idx
        self.trace.add("assign", var=var, value=self.grid[value_idx])
        self.stats.backtracks += 1  # every assignment is eventually undone

        nxt = var + 1
        if nxt >= self.n:
            self._evaluate_complete()
            self.assignment[var] = -1
            return

        narrowed = self._forward_check(var, value_idx)
        if narrowed is None:
            # Forward checking produced an empty domain: dead end.
            self.stats.dead_ends += 1
            self.trace.add("dead_end", var=var, value=self.grid[value_idx])
            self.assignment[var] = -1
            return
        self.domains[nxt] = narrowed

        # Branch and bound: prune the subtree when the lower bound cannot
        # *strictly* beat the incumbent. With the default h(s) = 0 this fires
        # only when the incumbent is already zero (then an equal-cost,
        # lexicographically-later solution is worthless) — otherwise no prune.
        lower_bound = self._lower_bound()
        if lower_bound >= self.best_cost:
            self.stats.branch_bound_prunes += 1
            self.trace.add(
                "prune_bb",
                var=var,
                value=self.grid[value_idx],
                lower_bound=lower_bound,
                incumbent=self.best_cost,
            )
            self.domains[nxt] = list(range(self.grid_size))
            self.assignment[var] = -1
            return

        self.stats.nodes_expanded += 1
        try:
            for child_idx in narrowed:
                self._budget_hit()
                self.stats.assignments_attempted += 1
                if not self.use_forward_checking and not self._pair_consistent(var, child_idx):
                    self.stats.constraint_rejections += 1
                    self.trace.add(
                        "reject",
                        var=nxt,
                        value=self.grid[child_idx],
                        parent=var,
                    )
                    continue
                self._assign(nxt, child_idx)
        finally:
            # Restoration: exactly undo the narrowing and this assignment so
            # sibling branches see pristine state.
            self.domains[nxt] = list(range(self.grid_size))
            self.assignment[var] = -1


def run_csp(  # noqa: PLR0913
    vehicles: list[VehicleSpec],
    config: ScenarioConfig,
    *,
    time_budget_s: float | None = None,
    evaluation_cap: int | None = None,
    use_forward_checking: bool = True,
    collect_trace: bool = True,
    trace_event_limit: int = 2000,
) -> AlgorithmResult:
    """Optimize the timing plan for ``vehicles`` with the CSP search.

    Args:
        vehicles: Vehicle demand (same set is used by all algorithms).
        config: Scenario parameters (domains, constraints, objective weights).
        time_budget_s: Wall-clock budget for the search (None = unbounded).
        evaluation_cap: Maximum number of complete plans simulated (None =
            unlimited).
        use_forward_checking: When False, run the no-pruning ablation (values
            are attempted and rejected at constraint-check time instead of
            being pre-filtered).
        collect_trace: Whether to keep the inspectable trace events.
        trace_event_limit: Maximum number of trace events retained.

    Returns:
        An :class:`AlgorithmResult`. Its ``status`` is

        - ``feasible (optimality proven)`` when the search completed within its
          budgets (the minimum *within the configured hard-constraint space*);
        - ``incomplete (budget reached; best-so-far, optimality unproven)``
          when a limit stopped the search early;
        - ``no feasible plan found`` when the hard constraints admit no plan.

    """
    stats = CSPSearchStats()
    trace = SearchTrace(event_limit=trace_event_limit)
    searcher = _Searcher(
        config,
        vehicles,
        stats,
        trace,
        time_budget_s=time_budget_s,
        evaluation_cap=evaluation_cap,
        use_forward_checking=use_forward_checking,
    )

    completed = bool(searcher.search())

    if searcher.best_plan is None:
        status = STATUS_NO_SOLUTION
        plan = timing_plan([0.0] * config.n_intersections)
        stats.best_objective = float("nan")
    elif not completed:
        status = FEASIBLE_TIME_LIMIT
        plan = timing_plan(searcher.best_plan)
    else:
        status = FEASIBLE_OPTIMAL
        plan = timing_plan(searcher.best_plan)

    # Final evaluation with traces enabled keeps the returned SimulationResult
    # directly usable by the dashboard visualizations.
    final_simulation = simulate_plan(plan, vehicles, config, collect_traces=True)

    return AlgorithmResult(
        algorithm="csp",
        plan=plan,
        simulation=final_simulation,
        search_time_s=stats.search_time_s,
        status=status,
        nodes_expanded=stats.nodes_expanded,
        assignments_attempted=stats.assignments_attempted,
        constraint_rejections=stats.constraint_rejections,
        backtracks=stats.backtracks,
        forward_check_removals=stats.forward_check_removals,
        branch_bound_prunes=stats.branch_bound_prunes,
        complete_assignments_evaluated=stats.complete_assignments_evaluated,
        best_objective=stats.best_objective,
        search_time_limit_s=time_budget_s,
        maximum_backtracks=None,
        metadata={
            "search_stats": stats.as_dict(),
            "trace": trace.to_dict() if collect_trace else None,
            "use_forward_checking": use_forward_checking,
            "lower_bound": stats.lower_bound,
        },
    )
