"""Tests for metrics aggregation, reproducibility and end-to-end integration."""

import pytest

from traffic_coordination.algorithms import run_csp, run_greedy, run_uncoordinated
from traffic_coordination.config import DEMAND_PRESETS, ScenarioConfig
from traffic_coordination.metrics import results_dataframe
from traffic_coordination.models import timing_plan
from traffic_coordination.scenario_generator import generate_vehicles
from traffic_coordination.signal_timing import travel_time_seconds
from traffic_coordination.simulator import simulate_plan
from traffic_coordination.verification import exhaustive_best


class TestMetrics:
    def test_results_dataframe_rows_sorted_and_complete(
        self, medium_config, medium_vehicles
    ) -> None:
        results = [
            run_uncoordinated(medium_vehicles, medium_config),
            run_csp(medium_vehicles, medium_config, collect_trace=False),
            run_greedy(medium_vehicles, medium_config),
        ]
        frame = results_dataframe(results)
        assert list(frame["algorithm"]) == ["uncoordinated", "greedy", "csp"]
        for column in (
            "total_waiting_time_s",
            "average_waiting_time_s",
            "total_stops",
            "objective",
            "search_time_s",
            "nodes_expanded",
            "status",
        ):
            assert column in frame.columns

    def test_results_dataframe_from_dicts(self) -> None:
        frame = results_dataframe(
            [{"algorithm": "x", "objective": 1}, {"algorithm": "y", "objective": 2}]
        )
        assert len(frame) == 2


class TestReproducibility:
    def test_full_pipeline_bit_identical(self) -> None:
        config = ScenarioConfig(n_intersections=4, vehicles_per_direction=6, jitter_s=0.4, seed=99)
        vehicles_a = generate_vehicles(config)
        vehicles_b = generate_vehicles(config)
        assert [(v.direction, v.departure_time) for v in vehicles_a] == [
            (v.direction, v.departure_time) for v in vehicles_b
        ]
        run_a = run_csp(vehicles_a, config, collect_trace=False)
        run_b = run_csp(vehicles_b, config, collect_trace=False)
        assert run_a.plan.offsets == run_b.plan.offsets
        assert run_a.simulation.summary_dict() == run_b.simulation.summary_dict()

    def test_different_seed_changes_jittered_demand(self) -> None:
        config = ScenarioConfig(n_intersections=3, vehicles_per_direction=8, jitter_s=1.0, seed=1)
        other = ScenarioConfig(n_intersections=3, vehicles_per_direction=8, jitter_s=1.0, seed=2)
        a = generate_vehicles(config)
        b = generate_vehicles(other)
        assert [(v.vehicle_id, v.departure_time) for v in a] != [
            (v.vehicle_id, v.departure_time) for v in b
        ]

    def test_zero_jitter_is_seed_independent(self) -> None:
        a = generate_vehicles(ScenarioConfig(n_intersections=3, seed=1))
        b = generate_vehicles(ScenarioConfig(n_intersections=3, seed=2))
        assert [(v.vehicle_id, v.departure_time) for v in a] == [
            (v.vehicle_id, v.departure_time) for v in b
        ]

    def test_demand_presets_documented_values(self) -> None:
        assert DEMAND_PRESETS["medium"]["vehicles_per_direction"] == 20
        assert DEMAND_PRESETS["medium"]["headway_s"] == 1.0


class TestIntegration:
    def test_end_to_end_three_algorithms_small(self, small_config) -> None:
        corridor_vehicles = generate_vehicles(small_config)
        unc = run_uncoordinated(corridor_vehicles, small_config)
        gre = run_greedy(corridor_vehicles, small_config)
        csp = run_csp(corridor_vehicles, small_config, collect_trace=False)
        for result in (unc, gre, csp):
            offsets = result.plan.offsets
            assert len(offsets) == small_config.n_intersections
            assert offsets[0] == 0.0
            assert all(
                o in small_config.offset_grid() or o == 0.0 for o in offsets
            )
            assert result.simulation.n_vehicles == len(corridor_vehicles)

    def test_verification_exhaustive_equals_csp_multi_scenario(self) -> None:
        for n, tol in ((3, None), (4, 20.0), (3, 25.0)):
            config = ScenarioConfig(
                n_intersections=n,
                progression_tolerance_s=tol,
                vehicles_per_direction=6,
                headway_s=2.0,
            )
            vehicles = generate_vehicles(config)
            csp = run_csp(vehicles, config, collect_trace=False)
            brute = exhaustive_best(config, vehicles)
            assert brute.completed
            assert csp.simulation.objective == pytest.approx(brute.best_objective), (
                f"mismatch for n={n}, tol={tol}"
            )

    def test_documented_report_values_reproduced(self) -> None:
        """Exact reproduction of the report's illustration (Section 5.3 & 7)."""
        config = ScenarioConfig(n_intersections=5)
        vehicles = generate_vehicles(config)
        assert config.cycle_length == 60.0
        assert config.green_duration == 30.0
        assert config.link_distance_m == 400.0
        assert config.speed_kmh == 40.0
        assert travel_time_seconds(config.link_distance_m, config.speed_kmh) == pytest.approx(36.0)
        uncoordinated = simulate_plan(timing_plan([0.0] * 5), vehicles, config)
        # The report's illustrative uncoordinated row: 160 stops / 3,460 s.
        assert uncoordinated.total_stops == 160
        assert uncoordinated.total_waiting_time == pytest.approx(3460.0)
