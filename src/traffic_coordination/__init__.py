"""Classical AI-based traffic signal coordination for an arterial corridor.

This package implements:
- a deterministic corridor traffic simulator,
- an uncoordinated baseline and a greedy one-way progression baseline,
- a constraint-satisfaction optimizer (backtracking + forward checking +
  branch-and-bound) for signal offsets,
- benchmark experiments, visualizations, and reporting utilities.

The package is an educational prototype for the ECSCT24301 Foundation of AI
project-based-learning course at Adani University. It is not a certified
traffic-control system.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
