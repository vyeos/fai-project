"""Tests for the three coordination algorithms and their interactions."""

import pytest

from traffic_coordination.algorithms import run_greedy, run_uncoordinated
from traffic_coordination.algorithms.csp_optimizer import run_csp
from traffic_coordination.algorithms.greedy import greedy_offsets
from traffic_coordination.config import ScenarioConfig
from traffic_coordination.verification import exhaustive_best


class TestUncoordinated:
    def test_all_offsets_zero(self, medium_config, medium_vehicles) -> None:
        result = run_uncoordinated(medium_vehicles, medium_config)
        assert result.plan.offsets == (0.0, 0.0, 0.0, 0.0, 0.0)
        assert result.algorithm == "uncoordinated"
        assert result.status == "feasible (single deterministic plan)"
        assert result.nodes_expanded == 0
        assert result.best_objective == result.simulation.objective

    def test_uses_common_simulator(self, medium_config, medium_vehicles) -> None:
        # Its simulated metrics must equal a direct simulation of the same plan.
        from traffic_coordination.simulator import simulate_plan

        result = run_uncoordinated(medium_vehicles, medium_config)
        direct = simulate_plan(result.plan, medium_vehicles, medium_config)
        assert result.simulation.summary_dict() == direct.summary_dict()


class TestGreedy:
    def test_offsets_follow_travel_time(self) -> None:
        config = ScenarioConfig(n_intersections=3)
        offsets = greedy_offsets(config)
        # tau = 36 s per link; desired: 36 -> nearest grid 35; 35+36=71 -> 11 -> 10.
        assert offsets == (0.0, 35.0, 10.0)

    def test_tie_break_toward_smaller_offset(self) -> None:
        # Speed such that desired = 2.5 s -> grid values 0 and 5 are equally
        # distant (2.5); the smaller one (0) must be chosen deterministically.
        config = ScenarioConfig(n_intersections=2, link_distance_m=50.0, speed_kmh=72.0)
        # tau = 50 / 20 = 2.5 s
        assert greedy_offsets(config) == (0.0, 0.0)

    def test_wraparound_uses_circular_distance(self) -> None:
        # desired = (0 + 57.5) is not possible on this grid; use tau = 57.5 via
        # distance/speed: 2300 m at 144 km/h -> 57.5 s.
        config = ScenarioConfig(n_intersections=2, link_distance_m=2300.0, speed_kmh=144.0)
        # Grid nearest to 57.5 on the circle: 55 (dist 2.5) and 0 (dist 2.5);
        # the smaller offset 0 must win.
        assert greedy_offsets(config) == (0.0, 0.0)

    def test_no_optimality_guarantee_status(self, medium_config, medium_vehicles) -> None:
        result = run_greedy(medium_vehicles, medium_config)
        assert "heuristic" in result.status
        assert result.complete_assignments_evaluated == 0


class TestCSP:
    def test_matches_exhaustive_small(self, small_config) -> None:
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(small_config)
        csp = run_csp(vehicles, small_config)
        brute = exhaustive_best(small_config, vehicles)
        assert brute.completed
        assert csp.status == "feasible (optimality proven)"
        assert csp.simulation.objective == pytest.approx(brute.best_objective)
        assert csp.plan.offsets == brute.best_offsets

    def test_matches_exhaustive_medium(self, medium_config, medium_vehicles) -> None:
        csp = run_csp(medium_vehicles, medium_config)
        brute = exhaustive_best(medium_config, medium_vehicles)
        assert csp.simulation.objective == pytest.approx(brute.best_objective)
        assert csp.plan.offsets == brute.best_offsets

    def test_at_least_as_good_as_baselines(
        self, small_config: ScenarioConfig
    ) -> None:
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(small_config)
        unc = run_uncoordinated(vehicles, small_config)
        gre = run_greedy(vehicles, small_config)
        csp = run_csp(vehicles, small_config)
        assert csp.simulation.objective <= gre.simulation.objective
        assert csp.simulation.objective <= unc.simulation.objective

    def test_progression_constraint_honoured(self) -> None:
        config = ScenarioConfig(n_intersections=3, progression_tolerance_s=15.0)
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(config)
        result = run_csp(vehicles, config)
        offsets = result.plan.offsets
        tau = 36.0
        for i in range(len(offsets) - 1):
            achieved = (offsets[i + 1] - offsets[i]) % 60.0
            deviation = abs(achieved - tau) % 60.0
            deviation = min(deviation, 60.0 - deviation)
            assert deviation <= 15.0 + 1e-9

    def test_progression_constraint_gives_true_constrained_optimum(self) -> None:
        config = ScenarioConfig(n_intersections=3, progression_tolerance_s=10.0)
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(config)
        csp = run_csp(vehicles, config)
        brute = exhaustive_best(config, vehicles)
        assert brute.completed
        assert csp.simulation.objective == pytest.approx(brute.best_objective)
        assert csp.plan.offsets == brute.best_offsets

    def test_forward_checking_prunes_domains(self) -> None:
        config = ScenarioConfig(n_intersections=3, progression_tolerance_s=10.0)
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(config)
        fc_on = run_csp(vehicles, config)
        assert fc_on.forward_check_removals > 0
        # With forward checking, attempted-but-rejected values cannot occur:
        assert fc_on.constraint_rejections == 0

    def test_no_forward_checking_ablation(self) -> None:
        config = ScenarioConfig(n_intersections=3, progression_tolerance_s=10.0)
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(config)
        ablation = run_csp(vehicles, config, use_forward_checking=False)
        assert ablation.constraint_rejections > 0
        assert ablation.forward_check_removals == 0
        # Same result as the FC run (only bookkeeping differs).
        fc_on = run_csp(vehicles, config, collect_trace=False)
        assert ablation.simulation.objective == fc_on.simulation.objective
        assert ablation.plan.offsets == fc_on.plan.offsets

    def test_evaluation_cap_marks_incomplete(self, small_config) -> None:
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(small_config)
        brute = exhaustive_best(small_config, vehicles)
        capped = run_csp(vehicles, small_config, evaluation_cap=3, collect_trace=False)
        assert capped.status.startswith("incomplete")
        assert capped.complete_assignments_evaluated <= 3 + 64  # budget check granularity
        assert capped.simulation.objective >= brute.best_objective - 1e-9

    def test_evaluation_cap_exact(self, small_config) -> None:
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(small_config)
        capped = run_csp(vehicles, small_config, evaluation_cap=1)
        assert capped.complete_assignments_evaluated == 1

    def test_branch_and_bound_never_loses_optimum(self, small_config) -> None:
        """B&B uses the admissible h(s)=0 bound; it must not remove optima."""
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(small_config)
        csp = run_csp(vehicles, small_config, collect_trace=False)
        brute = exhaustive_best(small_config, vehicles)
        assert csp.simulation.objective == pytest.approx(brute.best_objective)

    def test_stats_internally_consistent(self, medium_config, medium_vehicles) -> None:
        csp = run_csp(medium_vehicles, medium_config, collect_trace=False)
        # attempts == assigned nodes + rejected attempts
        assert csp.assignments_attempted >= csp.nodes_expanded
        assert csp.complete_assignments_evaluated > 0
        assert csp.best_objective == pytest.approx(csp.simulation.objective)
        assert csp.search_time_s > 0

    def test_no_progression_constraint_prunes_nothing(self, small_config) -> None:
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(small_config)
        csp = run_csp(vehicles, small_config, collect_trace=False)
        assert csp.forward_check_removals == 0
        assert csp.branch_bound_prunes == 0
        assert csp.complete_assignments_evaluated == 12 ** (small_config.n_intersections - 1)

    def test_empty_domain_yields_no_solution(self) -> None:
        config = ScenarioConfig(n_intersections=3, progression_tolerance_s=0.5)
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(config)
        result = run_csp(vehicles, config, collect_trace=False)
        # tau = 36 s is not on the grid and the allowed deviation is only 0.5 s;
        # no grid pair satisfies the constraint, so no plan exists.
        assert result.status == "no feasible plan found"

    def test_trace_records_real_events(self, small_config) -> None:
        from traffic_coordination.scenario_generator import generate_vehicles

        vehicles = generate_vehicles(small_config)
        result = run_csp(vehicles, small_config, trace_event_limit=50)
        trace = result.metadata["trace"]
        types = {event["type"] for event in trace["events"]}
        assert "assign" in types
        assert "evaluate" in types
        assert trace["truncated"] or len(trace["events"]) < 50
