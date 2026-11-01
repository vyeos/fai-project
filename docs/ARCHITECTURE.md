# Architecture

*(Technical documentation for the traffic signal coordination project.)*

## 1. Repository layout

```
traffic-signal-coordination/
├── app.py                          # Streamlit entry: top navigation over four pages
├── pyproject.toml                  # packaging, ruff and pytest configuration
├── .streamlit/config.toml          # light theme, IBM Plex fonts, minimal toolbar
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
│   ├── visualization/              # plotly figure builders (time-space, corridor, timeline, traces)
│   ├── experiments/
│   │   ├── scenarios.py            # registered benchmark scenarios A–E and F/G/H/J
│   │   ├── benchmark_runner.py     # CLI: python -m traffic_coordination.experiments.benchmark_runner
│   │   └── reporting.py            # CSV/JSON/markdown summary writers
│   ├── dashboard/                  # the four pages + shared road state (common.py)
│   ├── ui_state.py                 # dashboard run-state helpers (RunBundle, run cache)
│   └── ui_theme.py                 # design system: CSS tokens and HTML components
├── tests/                          # 86 pytest tests (unit + integration)
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

`app.py` registers four pages with `st.navigation(position="top")`. There is
no sidebar: the only inputs are the road form on the first page, stored as a
plain-language `road` dict in session state and translated to a
`ScenarioConfig` by `dashboard/common.road_to_config`. Every page reads the
latest `RunBundle`; a first visit runs the default road (scenario B) so no
page is ever empty.

1. **Try it** (`dashboard/try_it.py`) — road form (lights, distance, speed,
   traffic preset, directions, arrival pattern; cycle, green, timing step,
   green-wave rule and stop cost in an optional section), a one-sentence
   result, per-car stats against no coordination, the plan as animated
   lights and a table, side-by-side time-space diagrams, and the three
   strategies as cards.
2. **How it works** (`dashboard/how_it_works.py`) — the problem, a glossary,
   the simulator's rules, the strategies (greedy worked through on the
   reader's road), the CSP formulation and search techniques, a corridor
   snapshot with a time slider, and the model's limits.
3. **Experiments** (`dashboard/experiments.py`) — saved A–E results from
   `experiments/results/benchmark_results.csv` and a live one-factor sweep
   (5 s budget, 30,000-plan cap per value; over-cap values are skipped with
   a notice).
4. **Under the hood** (`dashboard/under_the_hood.py`) — brute-force
   verification, every search counter with an explanation, trace charts and
   the recorded steps, CSV/JSON downloads, and the full settings.

**Design system.** One set of tokens in `visualization/__init__.py` drives
`.streamlit/config.toml`, the stylesheet in `ui_theme.py` and every Plotly
figure: a warm light page, white cards with hairline borders, IBM Plex Sans,
and a single accent blue that always means "the optimized plan". Green and
red appear only for signal states; vehicle directions are teal and rust;
strategies step from light grey (no coordination) to slate (greedy) to the
accent. `ui_theme.py` exposes a small component set (page header, section,
summary, stat grid, strategy cards, table, glossary terms, numbered steps,
callout, legend, animated signal row), each rendered through `st.html`.
Because that sanitizer strips inline SVG, the signal row is embedded as an
SVG image; `tests/test_ui_theme.py` checks each lamp is green exactly when
`is_green` says so. All reader-facing wording uses one vocabulary (light,
cycle, green time, offset, driving time, stop, waiting time, score).

Honesty is first-class in the UI: incomplete searches, skipped verifications
and the weak branch-and-bound are stated in words, and every page labels its
numbers as simulated, not measured on a street.

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
