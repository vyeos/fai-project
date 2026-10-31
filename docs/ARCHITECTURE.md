# Architecture

*(Technical documentation for the traffic signal coordination project.)*

## 1. Repository layout

```
traffic-signal-coordination/
├── app.py                          # Streamlit dashboard (9 tabs)
├── pyproject.toml                  # packaging, ruff and pytest configuration
├── .streamlit/config.toml          # dark theme, Geist fonts, minimal toolbar
├── src/traffic_coordination/
│   ├── models.py                   # Intersection, Link, Vehicle, TimingPlan, SimulationResult
│   ├── config.py                   # ScenarioConfig validation, DEMAND_PRESETS
│   ├── signal_timing.py            # pure timing mathematics (green window, circular distance…)
│   ├── scenario_generator.py       # corridor + vehicle generation from a scenario config
│   ├── simulator.py                # deterministic corridor simulation
│   ├── metrics.py                  # AlgorithmResult and results_dataframe
│   ├── verification.py             # independent exhaustive brute-force verifier
│   ├── algorithms/
│   │   ├── uncoordinated.py        # baseline: all offsets 0
│   │   ├── greedy.py               # baseline: offset = previous + travel time (mod C)
│   │   └── csp_optimizer.py        # backtracking + forward checking + branch & bound
│   ├── visualization/              # plotly figure builders (corridor, timeline, animation, traces)
│   ├── experiments/
│   │   ├── scenarios.py            # registered benchmark scenarios A–E and F/G/H/J
│   │   ├── benchmark_runner.py     # CLI: python -m traffic_coordination.experiments.benchmark_runner
│   │   └── reporting.py            # CSV/JSON/markdown summary writers
│   ├── ui_state.py                 # dashboard run-state helpers (RunBundle, run cache)
│   └── ui_theme.py                 # dashboard CSS and HTML builders (masthead, ledger…)
├── tests/                          # 81 pytest tests (unit + integration)
├── experiments/results/            # measured benchmark outputs (CSV, JSON, summary.md)
├── experiments/figures/            # 7 generated matplotlib figures (fig1–3, fig5–8)
└── docs/                           # this documentation + screenshots/
```

## 2. Simulation model (single source of truth)

Every algorithm's candidate plan is evaluated by **one** deterministic simulator,
so all reported comparisons are apples-to-apples:

- Corridor: N intersections, link distance ℓ (default 400 m), nominal speed
  v (default 40 km/h → travel time τ ≈ 36 s per link by default; τ_i = ℓ_i / v).
- Signals: common cycle C = 60 s, coordinated green G = 30 s, and one offset
  O_i per intersection on the grid {0, r, 2r, …, C−r} (default r = 5 s).
  A vehicle arriving at t sees green iff `((t − O_i) mod C) < G`.
- Departure times: the first signal each vehicle reaches; one stop per red
  arrival (a vehicle waits until the next green window opens); no queue
  interactions (documented simplification — the model has no capacity limit).
- Objective: `J = α·W + β·S` with W = total waiting time (s) and S = total
  stops. Defaults α = 1, β = 2 (one stop "costs" two seconds of delay).

The reference offset is temporal (`O_1 = 0`), not spatial: intersection 1's
green window opens at simulation time 0.

## 3. The three algorithms

| Algorithm | Class | Guarantee | Key statistic |
|---|---|---|---|
| Uncoordinated | no search — single plan O ≡ 0 | "feasible (single deterministic plan)" | — |
| Greedy | local rule `O_{i+1} = (O_i + τ_i) mod C` rounded to the grid | "feasible (heuristic method…)" | — |
| CSP | backtracking search, variable order left→right | "feasible (optimality proven)" when the search completes; "incomplete (budget reached…)" otherwise, honestly | nodes, assignments, FC removals, BB prunes |

### 3.1 CSP formulation

- **Variables:** `O_2 … O_N` (O_1 is fixed at 0 as the time reference).
- **Domains:** grid `{0, r, …, C−r}`.
- **Hard constraints:** domain bounds; `O_1 = 0`; optionally a *progression
  tolerance* ρ — the circular distance between `(O_{i+1} − O_i) mod C` and
  `(τ_i mod C)` must be ≤ ρ. With ρ = None the constraint is vacuous and
  forward checking removes nothing (stated honestly everywhere).
- **Soft objective:** J via the simulator.

### 3.2 Search machinery

- **Static ordering:** variables assigned left to right; values tried in ascending order.
- **Forward checking:** after assigning O_i, values of O_{i+1} that violate the
  pairwise tolerance are deleted from its domain. Because the constraint graph
  is a chain, only one future variable is involved. On scenario C this removed
  10,920 candidate values; on scenario G2 (1 s resolution) 379,236.
- **Branch and bound:** the best complete plan found (incumbent) is used to
  prune subtrees whose admissible lower bound cannot beat it. The implemented
  bound `h(s) = 0` is *admissible and consistent but weak* — it prunes nothing
  (all measured `branch_bound_prunes` are 0) and the counter reports the true
  value rather than an inflated one.
- **Budget honesty:** `time_budget_s` and `evaluation_cap` are hard stops; on
  expiry the run status becomes `incomplete (budget reached; best-so-far,
  optimality unproven)` — never presented as optimal.

### 3.3 Measured complexity notes (from `experiments/results/`)

- Scenario B (N = 5, 5 s grid, ρ disabled): full 20,736-plan space evaluated in
  ≈ 1.4 s (≈ 12k plan-evaluations/s) — CSP proven optimal.
- Scenario E (5 s → 1 s grid, ρ = 10 s): 194,481 plans within the tolerant
  space evaluated in ≈ 12.4 s — the resolution change multiplied work by ~11×.
- Scenario C (N = 7, ρ = 10 s): raw space 12^6 = 2,985,984 reduible to 4,096
  plans inside the tolerance band; forward checking removed 10,920 values and
  the search completed in ≈ 0.35 s. Exhaustive verification of the *raw* space
  was skipped honestly (2985984 plans > verification budget).

## 4. Verification (independent)

`verification.exhaustive_best` brute-forces the *hard-constraint feasible set*
with a second, independently written enumeration and simulates each plan. When
its best objective matches the CSP's (within 1e-9) the claim "optimality
proven" is backed by an independent search, not just the solver's own
bookkeeping. In `experiments/results/summary.md` this held for all 12 regions
where verification ran; scenario C (2.99M raw plans) and E (12.96M) were
recorded as skipped rather than faked.

## 5. Data flow

```
ScenarioConfig ──> make_scenario ──> (corridor, vehicles)
                        │
                        ├─> run_uncoordinated(vehicles, config)
                        ├─> run_greedy(vehicles, config)
                        └─> run_csp(vehicles, config, budget, cap)
                                 │  └─ SearchTrace / CSPSearchStats
                                 └─> verification.exhaustive_best (optional)
                                     └─> ExhaustiveResult
                                                       │
                       AlgorithmResult ×3 ─────────────┤
                                                       ▼
                              benchmark_runner → results CSV/JSON/summary
                              streamlit app    → RunBundle (session state)
```

## 6. Dashboard design

`app.py` renders nine tabs driven by one sidebar `ScenarioConfig`:

1. **Overview** — search-space figure, scenario spec sheet, last-run ledger.
2. **Corridor** — corridor diagram at time t (slider) + vehicle animation.
3. **Signals** — green-window Gantt over a horizon slider.
4. **Algorithms** — run all / single runs (cached per scenario+budget) /
   benchmark suite runner.
5. **Results** — objective reduction, verification statement, ledger,
   charts, final plan.
6. **Search inspector** — CSPSearchStats grid, trace summary + depth charts,
   event table (trace retains the first events up to its cap).
7. **Sensitivity** — one-axis sweeps with a fast mode and an evaluation cap;
   values exceeding the cap are skipped with a visible warning.
8. **Export** — CSV/JSON downloads of the current session's real run data.
9. **Learn** — viva-ready explanations (state space, CSP, FC, BB, objective,
   growth, limitations).

**Visual system.** A dark "control room" palette: cool off-black surfaces,
hairline dividers instead of boxed cards, Geist for text and Geist Mono for
every number. Signal amber is the single accent and marks the CSP; green and
red appear only for real signal states. The palette lives in
`visualization/__init__.py` and is shared by `ui_theme.py`, the Plotly figures
and `.streamlit/config.toml`. The masthead runs the current timing plan as a
row of animated signal heads; `tests/test_ui_theme.py` checks that each lamp is
green exactly when `is_green` says so. Custom blocks render through `st.html`,
whose sanitizer strips inline SVG, so the signal row and icons are embedded as
SVG images.

Honesty is first-class in the UI: budgets and caps are configurable, skipped
verifications and incomplete statuses are shown verbatim, and every panel
labels its numbers as simulated, not field-measured.

## 7. Known limitations

- Constant speeds, no acceleration/deceleration profiles, times fixed to
  endpoint arrivals.
- One coordinated green per signal; no pedestrian phases, turns, or per-lane
  geometry.
- No queues/capacity: at very high demand the simulation still lets a stopped
  vehicle depart at the next green, so real-world congestion is understated.
- The objective is unidirectional-friendly, but `direction_mode="both"` is
  supported and reported separately in the dashboard's vehicle-generation
  settings.
