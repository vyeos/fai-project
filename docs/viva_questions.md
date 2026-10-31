# Viva Preparation — 42 Questions and Answers

Answers are grounded in what the repository actually implements and measures.
Numbers marked *"measured"* come from `experiments/results/`; never quote a
number you cannot point to. Good pivots: **"The implementation behaves
honestly — here is the measured table."**

## A. Problem and requirements

1. **What problem does this project solve?**
   Signalized intersections on an arterial corridor are individually timed but
   not coordinated, so platoons stop at every signal. We choose green-window
   offsets O_i per intersection so vehicles release from one signal and arrive
   at the next during its green. We solve it as a classical AI search problem
   and compare an uncoordinated baseline, a greedy progression heuristic, and a
   CSP optimizer.

2. **Why is this an AI problem rather than pure control engineering?**
   The choices interact over a combinatorial offset space (`|D|^(N−1)` plans —
   20,736 for our default N=5 case, *measured*), the objective is evaluated by
   simulation, and classical AI techniques (state space, backtracking, forward
   checking, branch and bound, admissible bounds) are exactly the toolbox for
   such discrete constraint problems.

3. **What is the objective function?**
   `J = α·W + β·S`: W = **total waiting time** (s) summed over all vehicles at
   signals, S = **total number of stops**. Defaults α=1, β=2 — one stop is
   priced like two seconds of waiting. Both weights are user-configurable.

4. **Why weight stops and waiting time rather than travel time?**
   Stops and delay are the subjective costs passengers feel at signals, and
   they respond directly to offset coordination; total travel time is
   dominated by constant link travel time, which offsets cannot change
   in our model (speed is constant).

5. **What are the decision variables?**
   Signal offsets O_1…O_N. O_1 ≡ 0 fixes the temporal reference; the CSP
   assigns O_2…O_N on the discrete grid {0, r, 2r, …, C−r}.

6. **What are the domain and cycle values?**
   Default cycle C=60 s, green G=30 s, resolution r=5 s → |D| = 12 values per
   variable. Scenario E uses a 1 s grid (|D| = 60) to show the cost of finer
   resolutions (*measured*: evaluated space grew from 20,736 to 194,481
   plans, and runtime from ≈1.4 s to ≈12.4 s).

## B. Formulation

7. **State the state space precisely.**
   A state is a partial assignment `(O_2, …, O_k)`; a complete state is a full
   timing plan. Root state = empty assignment with O_1 = 0 fixed. Size =
   |D|^(N−1) e.g. 12^4 = 20,736 (N=5 default).

8. **What are the constraints?**
   Hard: domain bounds; the O_1 = 0 reference; optionally the *progression
   tolerance* ρ — for each adjacent pair, the circular distance between
   `(O_{i+1}−O_i) mod C` and `(τ_i mod C)` ≤ ρ. Soft: minimise J.

9. **Why is O_1 = 0 without loss of generality?**
   Only *differences* of offsets affect green-window overlap (everything is
   `mod C`). Setting one variable to 0 anchors the temporal frame; each plan
   has exactly one representative in the reduced space.

10. **What is the progress/configuration tolerance ρ and why is it needed?**
    It is a hard constraint restricting each adjacent offset difference to lie
    within ρ seconds (circular distance) of the nominal link travel time
    τ mod C. It encodes the engineering intuition that offsets should roughly
    promote progression, and gives forward checking genuine pruning power.
    ρ = None makes it vacuous — the honest baseline case.

11. **Is your graph acyclic / what is the constraint graph?**
    A chain: variable O_{i+1} shares a constraint with O_i only. That is why
    forward checking a single future neighbour is sufficient, and why the
    search never revisits assignments.

12. **What does the simulator model, and what does it not?**
    Constant travel times at nominal speed; a vehicle arriving at a red signal
    waits until the next green window opens; one stop per red arrival;
    half-open green windows `((t−O) mod C) < G`; no queues, capacity limits,
    acceleration profiles, pedestrians or turns. All documented as limitations.

13. **Why one shared simulator instead of per-algorithm evaluation?**
    Fair comparison: every algorithm's plan is scored by the *same*
    deterministic evaluation on the *same* generated demand, so differences in
    J come from the plans, not the evaluator.

14. **Determinism — where could randomness enter, and how is it controlled?**
    Vehicle generation uses a seeded RNG (`seed` in the sidebar/config). With a
    fixed seed the corridor, demand and all metrics are reproducible bit-for-bit;
    `jitter_s` may add seeded arrival jitter but defaults to 0.

## C. Search algorithms

15. **Why backtracking (DFS) rather than BFS/IDA*/A\*?**
    Complete plans are the only useful nodes (every full assignment is
    evaluable), the tree has bounded depth N−1 and moderate branching, and
    memory for DFS is O(depth) vs O(breadth) for BFS. A* would need an
    admissible heuristic over partial plans; our objective is only defined by
    simulated *complete* plans, so we use branch and bound instead (which is
    A\*'s spirit applied at the complete-plan frontier with h=0).

16. **Walk through your CSP algorithm.**
    Fix O_1=0. Order variables left→right. At each level try each value of the
    next variable in ascending order: check the hard pairwise tolerance
    (forward-check removals already shrink the domain), recurse; a leaf
    (complete plan) is simulated; if J < incumbent J, update the incumbent and
    record a `best` trace event. Undo on dead ends. Budget/cap checks abort
    and mark the run incomplete.

17. **Explain forward checking concretely.**
    After assigning O_i, delete from O_{i+1}'s domain every value whose
    pairwise circular distance from `O_i + τ_i` exceeds ρ. Because constraints
    are pairwise between chain neighbours, this is sound. *Measured*: on
    scenario C (ρ=10 s) it removed 10,920 candidate values; scenario G2
    (ρ=10 s, 1 s grid) removed 379,236.

18. **When does forward checking do nothing?**
    When ρ is None the pairwise tolerance is vacuous — every domain value
    survives — so `forward_check_removals = 0` exactly as our scenario-B run
    shows (*measured*). We say this everywhere rather than implying pruning
    that never happened.

19. **What is branch and bound and what is your bound?**
    B&B prunes subtrees that cannot contain a better-than-incumbent plan,
    using a *lower bound* on the subtree's best J. Our bound h(s) = 0 is
    admissible (0 ≤ any J) and consistent but weak: it never beats a real
    incumbent, so `branch_bound_prunes` is honestly 0 in every measured run.
    The framework is real; the bound is a documented limitation/extension
    point.

20. **Admissible heuristic — define and defend h(s)=0.**
    Admissible: never overestimates the true remaining cost from a partial
    assignment (all J ≥ 0). Consistent: |h(s)−h(s′)|=0 ≤ cost(s,s′). Consequence:
    no invalid pruning — correctness is preserved — but no speedup either. An
    over-optimistic bound (e.g. subtracting an unachieved "perfect" wait)
    could prune the optimum; we chose correctness over aggressive pruning.

21. **What guarantees does the CSP result carry when it completes?**
    "feasible (optimality proven)" — it evaluated every feasible complete plan
    in its constraint space, so no plan in that space has lower J. When the
    budget/cap cuts it, status honestly reads "incomplete (budget reached;
    best-so-far, optimality unproven)".

22. **Why does a completed CSP on scenario C count only 4,096 of 2,985,984
    raw plans?**
    The raw space |D|^(N−1) = 12^6 counts every combination; the hard
    progression tolerance (ρ=10 s) restricts feasible plans to
    combinations whose adjacent differences are near τ. The solver only ever
    enumerates feasible assignments (4,096), plus it tracks removed values
    (10,920) — this is space reduction by constraints, not a solver shortcut.

23. **How do the two baselines work?**
    Uncoordinated: O_i ≡ 0 for all i (signals identical to the template clock).
    Greedy: round `(O_i + τ_i) mod C` to the grid for the next intersection —
    it "aimed" platoons at each next green, one direction only, with no search
    or re-optimisation.

24. **Why keep the baselines if the CSP exists?**
    They are the reference points that measure coordination's benefit and the
    sanity checks for the simulator: identical demand and simulator, so the
    delta is attributable to the algorithm.

25. **Where did greedy fail, in measured numbers?**
    Scenario B: greedy J=830 vs CSP 618 (*measured*); scenario H1 (10 s
    headway platoon at 40 km/h): greedy J=2246 — *worse* than uncoordinated's
    1828 — because its one-direction progression mis-times the reverse
    direction, while the CSP found J=409. Coordination tuned per-direction is
    what wins; blind progression can backfire.

26. **Complexity of each approach?**
    Uncoordinated O(N); greedy O(N); CSP worst-case O(|D|^(N−1) · sim cost)
    — exponential, but constraint propagation (ρ) and B&B (when a strong bound
    is added) cut the *effective* space: C reduced 2.99M raw → 4,096 evaluated
    plans (*measured*).

27. **What was the measured improvement of CSP over uncoordinated?**
    Scenario B: J 3780 → 618 = **83.7%** (*measured*). Scenario A: 762 → 140 =
    81.6%. Scenario D (high demand): 10406 → 2078 = 80.0%.

28. **And versus greedy?**
    Scenario B: 830 → 618 (25.5% better); C: 1610 → 674; E: 850 → 605
    (*measured*, from `summary.md`).

## D. Implementation and engineering

29. **Why Python, and what libraries?**
    numpy/pandas for data plumbing, matplotlib for static figures, plotly for
    interactive dashboard charts, streamlit for the app, pytest/ruff for
    quality, python-docx/python-pptx for deliverables. Simplicity and
    reproducibility outranked speed; 1.4 s for a 20,736-plan exact search is
    fast enough for a classroom demo.

30. **How is the code kept correct?**
    81 pytest tests (models, timing arithmetic, simulator edge cases, CSP
    status semantics, cross-algorithm integration), ruff linting (line length
    100), type hints and docstrings throughout, and an independent exhaustive
    verifier cross-checking the CSP's claimed optimum wherever the space is
    small enough.

31. **How is reproducibility ensured?**
    Fixed seeds per scenario, deterministic simulator, one-command benchmark
    runner (`python -m traffic_coordination.experiments.benchmark_runner
    --all`) writing CSV/JSON/markdown artefacts, configuration JSONs archived
    with results, and lint (ruff) + the full test suite run locally before
    every push to GitHub.

32. **How does the dashboard avoid freezing?**
    CSP budget (s) and evaluation cap sliders; streamlit spinner with
    per-step progress for sweeps; single runs cached by
    `config_fingerprint(algorithm, budget, cap)`; verification only runs when
    the space is small; the app warns when a configuration likely exceeds
    budgets instead of lying about progress.

33. **What is in the search trace inspector?**
    Chronologically recorded first events (assign / fc_remove / evaluate /
    best) with variable, value, next variable and removed count, plus the
    aggregate histogram and depth chart. The trace remembers it is a *window*
    (first events until a cap) while the counters above always cover the whole
    search — stated in the app.

34. **Why skip exhaustive verification for scenarios C and E?**
    Their raw (tolerance-free) spaces are 2,985,984 and 12,960,000 plans;
    brute-forcing at ~12k plans/s would exceed the verification budget. Rather
    than fake it, `summary.md` records "skipped (search space … plans)" and
    the app shows the appropriate message.

35. **What happens if a scenario finds no feasible plan?**
    Status becomes "no feasible plan found"; the results tab shows an error
    telling the user to widen ρ. This is exercisable by setting an extreme
    tolerance with a tiny grid.

## E. Results interpretation

36. **Which scenario numbers should I quote in the viva?**
    The ones in `experiments/results/summary.md` — e.g. B: 3780 → 618
    (83.7%); the illustrative numbers from the original report are labelled
    illustrative there and are *not* quoted as measured anywhere.

37. **What did the sensitivity analyses show?**
    Demand sweep F1–F3 (10/20/40 veh/dir): CSP relative benefit stays large; H1
    (10 s headway): greedy *hurts* the reverse direction; H2 (5 s headway,
    tighter platoon): near-perfect progression — CSP J=24.0 vs 1008.8
    uncoordinated (97.6% better, *measured*). Weights (J1/J2: β 2→5): the same
    plan remains best at both weightings on scenario B — a robustness finding.
    Scenarios J1 and J2 reuse the scenario-B demand with β = 2 and β = 5: the
    CSP plan is identical at both weightings (O = (0,40,5,40,15), *measured*)
    because it simultaneously improves W *and* S — the ranking is robust to
    this weight change; only the arithmetic scale moves.

38. **What is the honest headline?**
    On the documented synthetic model, coordination via CSP reduces the targeted
    cost by ≥80% versus uncoordinated timing across scenarios A/B/D, and
    exhaustive verification (where feasible) always matched the CSP plan.
    These are simulation results of a simplified model — not field-validated
    traffic engineering.

39. **If a professor challenges your 83.7% figure, what do you say?**
    Give the trace: objective definition, identical vehicles & simulator for
    all algorithms, plan O = (0,40,5,40,15) at scenario B (*measured* in
    summary.md and CSV), exhaustive verification over 20,736 plans agreeing
    (J=618.0), plus the model's simplifications. Every step is reproducible
    via the repository commands.

40. **What would you do differently with more time?**
    Queueing/capacity in the simulator (M/G/1-style Greenberg or cell
    transmission), a real admissible lower bound for B&B (e.g. remaining-link
    minimum-wait estimates), min-conflicts local search for large N, and
    multi-cycle (per-phase) timing.

41. **How does this connect to what the course taught?**
    Uninformed search (DFS/backtracking) → CSPs (formulation, forward
    checking) → informed search (branch and bound with an admissible, if weak,
    bound) → evaluation methodology (deterministic experiments, honest
    counters) — a compact end-to-end application of the classical-AI toolbox.

42. **Demonstration plan in 5 minutes?**
    (a) Load scenario B in the sidebar; (b) run all — CSP proves optimality,
    83.7% banner; (c) Corridor tab: slide t to 57 s, watch platoons;
    (d) Search inspector: show 20,736 evaluations, 0 FC removals (ρ disabled),
    0 BB prunes honest; (e) Sensitivity: run the demand sweep, show the gap
    widening; (f) Export CSV to prove data leaves the app. Each step ~45 s.
