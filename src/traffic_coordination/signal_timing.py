"""Signal-timing and vehicle state calculations used by the simulator.

This module contains the signal-green rule, travel-time computation, and the
per-intersection waiting model, kept separate from the container classes in
:mod:`traffic_coordination.models` so the simulator logic is easy to test and to
explain during a viva.

Timing convention (documented in the project report, Section 2.5):

- Every signal uses a common cycle length ``C`` and coordinated green ``G``.
- The coordinated green window of intersection ``i`` is the half-open interval
  ``[O_i + k*C, O_i + k*C + G)`` for all integers ``k``.
- ``green(t, O_i) == 1`` iff ``((t - O_i) mod C) < G``.
- Because the green window is half-open, a vehicle arriving *exactly* at the end
  of green is treated as arriving on red and must wait for the next window.
  A vehicle arriving exactly at the start of green proceeds immediately.

All times are in seconds and all distances in metres unless stated otherwise.
"""

from __future__ import annotations

KMH_TO_MS = 1000.0 / 3600.0
TOLERANCE = 1e-9

__all__ = [
    "KMH_TO_MS",
    "TOLERANCE",
    "is_green",
    "next_green_start",
    "signal_wait",
    "travel_time_seconds",
]


def _validate_timing(t: float, offset: float, cycle_length: float, green_duration: float) -> float:
    """Validate signal-timing arguments and return the cycle phase of ``t``."""
    if t < 0:
        raise ValueError(f"Time must be non-negative, got {t}")
    if cycle_length <= 0:
        raise ValueError(f"Cycle length must be positive, got {cycle_length}")
    if not 0 < green_duration <= cycle_length:
        raise ValueError(
            f"Green duration must satisfy 0 < G <= C, got G={green_duration}, C={cycle_length}"
        )
    if not 0 <= offset < cycle_length:
        raise ValueError(f"Offset must satisfy 0 <= O < C, got {offset}")
    return (t - offset) % cycle_length


def is_green(t: float, offset: float, cycle_length: float, green_duration: float) -> bool:
    """Return ``green(t, O_i) = 1 iff ((t - O) mod C) < G`` as a bool."""
    return _validate_timing(t, offset, cycle_length, green_duration) < green_duration


def next_green_start(t: float, offset: float, cycle_length: float, green_duration: float) -> float:
    """Return the time (>= t) at which the green window covering ``t`` starts.

    For an arrival inside a green window this is the start of the *current*
    window; for an arrival on red it is the start of the next window.
    """
    phase = _validate_timing(t, offset, cycle_length, green_duration)
    if phase < green_duration:
        return offset + ((t - offset) // cycle_length) * cycle_length
    return t + (cycle_length - phase)


def signal_wait(
    t_arrival: float, offset: float, cycle_length: float, green_duration: float
) -> float:
    """Return the waiting time for a vehicle arriving at time ``t_arrival``.

    A green arrival yields zero wait; a red arrival yields the time until the
    start of the next green window: ``wait = C - ((t_arrival - O) mod C)``.
    """
    phase = _validate_timing(t_arrival, offset, cycle_length, green_duration)
    if phase < green_duration:
        return 0.0
    return cycle_length - phase


def travel_time_seconds(distance_m: float, speed_kmh: float) -> float:
    """Return link travel time in seconds.

    ``tau = d / v`` where ``d`` is the link distance in metres and ``v`` the
    nominal speed converted from km/h to m/s.
    """
    if distance_m < 0:
        raise ValueError(f"Link distance must be non-negative, got {distance_m}")
    if speed_kmh <= 0:
        raise ValueError(f"Speed must be positive, got {speed_kmh}")
    return distance_m / (speed_kmh * KMH_TO_MS)
