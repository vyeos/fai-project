"""Coordination algorithms for the traffic signal corridor.

Three methods share one simulator and one objective:

- :mod:`traffic_coordination.algorithms.uncoordinated` — all offsets zero.
- :mod:`traffic_coordination.algorithms.greedy` — greedy one-way progression.
- :mod:`traffic_coordination.algorithms.csp_optimizer` — CSP search with
  backtracking, forward checking, and branch-and-bound.
"""

from .csp_optimizer import run_csp
from .greedy import greedy_offsets, run_greedy
from .uncoordinated import run_uncoordinated

__all__ = ["greedy_offsets", "run_csp", "run_greedy", "run_uncoordinated"]
