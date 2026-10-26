"""Shared pytest fixtures for the traffic coordination test suite."""

import pytest

from traffic_coordination.config import DEMAND_PRESETS, ScenarioConfig
from traffic_coordination.models import VehicleSpec
from traffic_coordination.scenario_generator import build_corridor, generate_vehicles


@pytest.fixture()
def medium_config() -> ScenarioConfig:
    """The report's illustrative benchmark scenario (5 intersections, medium)."""
    return ScenarioConfig(n_intersections=5)


@pytest.fixture()
def small_config() -> ScenarioConfig:
    """A 3-intersection low-demand scenario for fast exhaustive verification."""
    return ScenarioConfig(
        n_intersections=3,
        demand_level="low",
        vehicles_per_direction=DEMAND_PRESETS["low"]["vehicles_per_direction"],
        headway_s=DEMAND_PRESETS["low"]["headway_s"],
    )


@pytest.fixture()
def medium_vehicles() -> list[VehicleSpec]:
    config = ScenarioConfig(n_intersections=5)
    return generate_vehicles(config)


@pytest.fixture()
def small_corridor():
    return build_corridor(ScenarioConfig(n_intersections=3))
