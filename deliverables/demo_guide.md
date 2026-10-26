# Demo Guide — live walkthrough

A rehearsed, tab-by-tab walkthrough of the Streamlit dashboard, referencing
behaviour verified live in the delivered screenshots (`docs/screenshots/`).
Total time ≈ 7–8 minutes; a 5-minute compressed route is marked with (★).

## Setup (do before the audience sits down)

1. Activate the venv: `Set-Location <repo>`; `.\.venv\Scripts\Activate.ps1`.
2. `python -m streamlit run app.py` → opens at http://localhost:8501.
3. Confirm the title bar shows the traffic-light emoji and the course caption.
4. Sidebar defaults = scenario B (5 intersections, medium demand, C=60, G=30,
   5 s grid, tolerance ±10 s, budgets 30 s / 250,000-plan cap, verify on).

★ = include even in the 5-minute compressed version.

## 1. Overview tab (★)

- Read the nine KPI cards: N=5, C=60 s, G=30 s, |D|=12, raw space 20,736,
  40 vehicles, tolerance ±10 s, J = 1·W + 2·S, seed 42.
- Press **Run all algorithms** (★): within ~2 s the CSP status shows
  *feasible (optimality proven)* and the "Best objective improvement" metric
  shows **83.7%** (screenshot `01_overview_last_run.png`).
- Point out the honesty caption at the bottom: simulated numbers, not field
  measurements, not the report's illustrative figures.

## 2. Corridor tab

- Drag **View time t** to ≈ 57 s: the corridor figure updates its title to
  "Corridor at t = 57 s" and shows vehicles mid-corridor with some signals on
  green and others red (screenshot `03_corridor_t57_vehicles.png`).
- Scroll to the vehicle animation: press ▶ (play) once in front of the
  audience — platoons sweep left-to-right and right-to-left
  (screenshot `02_corridor_animation.png`).
- If time is short: set t = 0 (★ assets only), skip the animation.

## 3. Signals tab

- The Gantt shows each intersection's green windows shifted by its offset;
  I1 starts at O=0, I2 at 40, I3 at 5 (read from the offset table below).
- One-sentence explanation: "green starts at Oᵢ, lasts G, repeats every C."

## 4. Algorithms tab

- Point at the run buttons; if the audience is technical, click **CSP** under
  single runs — the cached result returns instantly (per-scenario + budget
  cache key).
- Benchmark suite button exists but takes ~1 minute; prefer mentioning the CLI:
  `python -m traffic_coordination.experiments.benchmark_runner --all`.

## 5. Results tab (★)

- Comparison table: uncoordinated J = 3780 (status: single deterministic
  plan), greedy 830 (heuristic, no guarantee), CSP 618 (*optimality proven*).
- Green verification banner: "Independent exhaustive search over 256 feasible
  plans confirms the CSP optimum (J = 618.00)" (screenshot
  `05b_results_verification_plan.png`).
- The two bar charts show waiting time 3460 → 540 and stops 160 → 39.
- Selected timing plan: O = (0, 40, 5, 40, 15).

## 6. Search inspector tab

- Statistics table: search_space_size 20,736; nodes 85; assignments 341;
  forward_check_removals 680 (tolerance ±10 s active); branch_bound_prunes
  **0** — say out loud: "the bound h(s)=0 is admissible but weak; the counter
  reports the truth" (screenshots `06_search_inspector_stats.png`,
  `06b_search_trace_charts.png`, `06c_search_trace_events.png`).
- Scroll to Recorded events: assign / fc_remove / evaluate / best rows in
  chronological order.

## 7. Sensitivity tab

- Keep the default demand sweep and press **Run sweep** (★ in compressed
  route too): five values, per-value progress, then the measured table + the
  "Objective vs traffic demand" line chart with three curves (screenshot
  `07_sensitivity_sweep.png`).
- Mention the cap-skipping warnings: values whose raw space exceeds the cap
  are skipped honestly with a visible notice.

## 8. Export tab

- Four download buttons (screenshot `09_export_tab.png`); click
  **comparison results (CSV)** and open it — columns and values match the
  Results tab exactly.

## 9. Learn tab

- Seven explanations (state space → simulation limitations). Use it as your
  viva quick-reference; screenshot `10_learn_tab.png`.

## Reset between demos

- Press **Defaults** in the sidebar, then the Overview tab.
- If the config ever becomes invalid, the app shows the validation error and
  all tabs fall back to their hint texts — recover via **Defaults**.

## Known-behaviour notes (say them before they are asked)

- Budget slider (30 s) and evaluation cap (250,000) are hard stops; if either
  trips, the status line reports *incomplete* — never a silent lie.
- A reload wipes the session's run bundle (Streamlit session state); re-run
  from the Algorithms tab — by design, not a bug.
- Exhaustive verification runs only when the hard-constraint space fits its
  budget; otherwise the app shows the skip notice, mirroring
  `experiments/results/summary.md`.
