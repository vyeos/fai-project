# Benchmark Summary

*Generated: 2026-10-26 14:58:10.*
All values are measured from deterministic simulations of documented simplifying assumptions; they are **not** field measurements and not the report's illustrative figures.

**Objective:** J = alpha*W + beta*S (defaults alpha=1, beta=2; per-row alpha/beta recorded in the CSV).

## Main scenarios (report benchmark matrix)

| scenario | algorithm | total_waiting_time_s | average_waiting_time_s | total_stops | objective | search_time_s | nodes_expanded | complete_assignments_evaluated | forward_check_removals | branch_bound_prunes | status | plan_offsets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | uncoordinated | 690.0 | 34.5 | 36 | 762.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0] |
| A | greedy | 124.0 | 6.2 | 8 | 140.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0] |
| A | csp | 124.0 | 6.2 | 8 | 140.0 | 0.0049 | 13 | 144 | 0 | 0 | feasible (optimality proven) | [0.0, 35.0, 10.0] |
| B | uncoordinated | 3460.0 | 86.5 | 160 | 3780.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| B | greedy | 750.0 | 18.75 | 40 | 830.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| B | csp | 540.0 | 13.5 | 39 | 618.0 | 1.4328 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 40.0, 5.0, 40.0, 15.0] |
| C | uncoordinated | 5380.0 | 134.5 | 240 | 5860.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] |
| C | greedy | 1490.0 | 37.25 | 60 | 1610.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0, 55.0, 30.0] |
| C | csp | 576.0 | 14.4 | 49 | 674.0 | 0.3524 | 1365 | 4096 | 10920 | 0 | feasible (optimality proven) | [0.0, 35.0, 20.0, 50.0, 20.0, 50.0, 25.0] |
| D | uncoordinated | 9550.0 | 95.5 | 428 | 10406.0 | 0.0002 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| D | greedy | 2315.0 | 23.15 | 105 | 2525.0 | 0.0002 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| D | csp | 1828.0 | 18.28 | 125 | 2078.0 | 3.3505 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 45.0, 15.0, 55.0, 25.0] |
| E | uncoordinated | 3460.0 | 86.5 | 160 | 3780.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| E | greedy | 770.0 | 19.25 | 40 | 850.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 36.0, 12.0, 48.0, 24.0] |
| E | csp | 533.0 | 13.325 | 36 | 605.0 | 12.3977 | 9724 | 194481 | 379236 | 0 | feasible (optimality proven) | [0.0, 38.0, 4.0, 38.0, 14.0] |

## Sensitivity scenarios

| scenario | algorithm | total_waiting_time_s | average_waiting_time_s | total_stops | objective | search_time_s | nodes_expanded | complete_assignments_evaluated | forward_check_removals | branch_bound_prunes | status | plan_offsets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | uncoordinated | 1650.0 | 82.5 | 76 | 1802.0 | 0.0 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| F1 | greedy | 365.0 | 18.25 | 18 | 401.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| F1 | csp | 264.0 | 13.2 | 22 | 308.0 | 0.7597 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 45.0, 10.0, 50.0, 25.0] |
| F2 | uncoordinated | 3460.0 | 86.5 | 160 | 3780.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| F2 | greedy | 750.0 | 18.75 | 40 | 830.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| F2 | csp | 540.0 | 13.5 | 39 | 618.0 | 1.4463 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 40.0, 5.0, 40.0, 15.0] |
| F3 | uncoordinated | 9550.0 | 95.5 | 428 | 10406.0 | 0.0002 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| F3 | greedy | 2315.0 | 23.15 | 105 | 2525.0 | 0.0002 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| F3 | csp | 1828.0 | 18.28 | 125 | 2078.0 | 3.5515 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 45.0, 15.0, 55.0, 25.0] |
| G1 | uncoordinated | 3460.0 | 86.5 | 160 | 3780.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| G1 | greedy | 750.0 | 18.75 | 40 | 830.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| G1 | csp | 540.0 | 13.5 | 39 | 618.0 | 0.0168 | 85 | 256 | 680 | 0 | feasible (optimality proven) | [0.0, 40.0, 10.0, 40.0, 15.0] |
| G2 | uncoordinated | 3460.0 | 86.5 | 160 | 3780.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| G2 | greedy | 770.0 | 19.25 | 40 | 850.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 36.0, 12.0, 48.0, 24.0] |
| G2 | csp | 533.0 | 13.325 | 36 | 605.0 | 16.134 | 9724 | 194481 | 379236 | 0 | feasible (optimality proven) | [0.0, 38.0, 4.0, 38.0, 14.0] |
| H1 | uncoordinated | 1540.0 | 38.5 | 144 | 1828.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| H1 | greedy | 2006.0 | 50.15 | 120 | 2246.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 50.0, 40.0, 30.0, 20.0] |
| H1 | csp | 331.0 | 8.275 | 39 | 409.0 | 2.202 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 40.0, 30.0, 40.0, 5.0] |
| H2 | uncoordinated | 848.8 | 21.22 | 80 | 1008.8 | 0.0002 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| H2 | greedy | 28.0 | 0.7 | 28 | 84.0 | 0.0002 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 30.0, 0.0, 30.0, 0.0] |
| H2 | csp | 14.0 | 0.35 | 5 | 24.0 | 2.2943 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 20.0, 50.0, 20.0, 50.0] |
| J1 | uncoordinated | 3460.0 | 86.5 | 160 | 3460.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| J1 | greedy | 750.0 | 18.75 | 40 | 750.0 | 0.0001 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| J1 | csp | 540.0 | 13.5 | 39 | 540.0 | 2.0772 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 40.0, 5.0, 40.0, 15.0] |
| J2 | uncoordinated | 3460.0 | 86.5 | 160 | 4100.0 | 0.0005 | 0 | 0 | 0 | 0 | feasible (single deterministic plan) | [0.0, 0.0, 0.0, 0.0, 0.0] |
| J2 | greedy | 750.0 | 18.75 | 40 | 910.0 | 0.0005 | 0 | 0 | 0 | 0 | feasible (heuristic method, no optimality guarantee) | [0.0, 35.0, 10.0, 45.0, 20.0] |
| J2 | csp | 540.0 | 13.5 | 39 | 696.0 | 2.1196 | 1885 | 20736 | 0 | 0 | feasible (optimality proven) | [0.0, 40.0, 5.0, 40.0, 15.0] |

## Exhaustive verification (independent brute force)

- **A**: brute force over 144 feasible plans (of 144), CSP matches best (J=140.0): True.
- **B**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=618.0): True.
- **D**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=2078.0): True.
- **F1**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=308.0): True.
- **F2**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=618.0): True.
- **F3**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=2078.0): True.
- **G1**: brute force over 256 feasible plans (of 20736), CSP matches best (J=618.0): True.
- **G2**: brute force over 194481 feasible plans (of 12960000), CSP matches best (J=605.0): True.
- **H1**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=409.0): True.
- **H2**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=24.0): True.
- **J1**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=540.0): True.
- **J2**: brute force over 20736 feasible plans (of 20736), CSP matches best (J=696.0): True.

## Honestly-incomplete items

- **C**: exhaustive verification skipped (search space 2985984 plans). The CSP search itself completed within its hard-constraint space.
- **E**: exhaustive verification skipped (search space 12960000 plans). The CSP search itself completed within its hard-constraint space.
