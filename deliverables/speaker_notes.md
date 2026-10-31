# Speaker Notes — final presentation (13 slides)

Companion to `deliverables/final_slides.pptx`. The same notes are embedded in
the PPTX file itself. Every quoted number is measured in
`experiments/results/`; when in doubt, open `experiments/results/summary.md`
live during the defence.

**Timing plan:** ~30 s/method slide, ~60 s/results slide, ~25 s/tour slides —
≈ 15 minutes total including questions buffer.

---

## Slide 1 — Title (~40 s)

Good morning. We coordinate the green windows of N signalized intersections on
an arterial corridor using classical AI search. Everything you will see was
measured inside a deterministic, reproducible simulation — no invented numbers,
and honestly-labelled placeholders where course information was not available
(you can see that in the cover metadata of our report and here on the slide).

## Slide 2 — The problem (~45 s)

Independently-timed signals waste platoon progress: a platoon released at one
green arrives at the next during red. The coordination idea is to shift each
signal's green window in time — the offset — so greens "hand" platoons along.
The catch: offsets interact around the cycle, and the cost of any assignment
depends on how platoons actually traverse the corridor. So we defined
`J = α·W + β·S` — α·W total waiting time, β·S total stops — and made choosing
offsets a discrete search problem. Space: |D|^(N−1); on our default case
12⁴ = 20,736 plans — the number we keep returning to, measured, not hand-waved.

## Slide 3 — Simulation model (~35 s)

One shared deterministic simulator: cycle C = 60 s, green G = 30 s, 5 s offset
grid. Green iff `((t−Oᵢ) mod C) < G` — half-open windows. Constant speed
40 km/h → τ ≈ 36 s per 400 m link. Seeded RNG demand, both directions, no
queues or capacity limits. We own these simplifications explicitly — the
deliverable is a controlled test bed for search, not a traffic-engineering
design tool.

## Slide 4 — CSP formulation (~40 s)

Variables O₂…O_N; O₁ = 0 fixes the reference and costs nothing because only
differences mod C matter. Domains: the 12-value grid. Hard constraints: domain
bounds, the reference, and — optionally — a progression tolerance ρ: adjacent
offset differences must stay within ρ = 10 s (circular distance) of nominal
link travel time. That tolerance is our pruning lever: with ρ = None it is
vacuous and forward checking removes nothing (we show exactly that); with
ρ = 10 s scenario C's 2.99 million raw plans collapse to 4,096 evaluated ones.

## Slide 5 — Three comparable strategies (~40 s)

Uncoordinated: all zeros. It also cross-validated our simulator — under the
report's parameters it reproduces the report's illustrative row (3,460 s /
160 stops) exactly. Greedy progression: `Oᵢ₊₁ = round(Oᵢ + τ mod C)`, one pass,
forward only. CSP: backtracking + forward checking + branch and bound, with
hard budget semantics. Key line to deliver: **all three are scored by the same
simulator on identical demand** — any difference in J is attributable to the
plan, not the evaluator.

## Slide 6 — Search machinery + honest counters (~45 s)

Forward checking deletes the next variable's values that violate the pairwise
tolerance; because the constraint graph is a chain, one future neighbour
suffices. Measured: 10,920 eliminations on scenario C; 379,236 on the 1 s grid.
Branch and bound keeps the incumbent and prunes subtrees that cannot beat it
**with a valid lower bound**. Our bound h(s) = 0 is admissible and consistent
but weak — it prunes nothing, and the `branch_bound_prunes` counter truthfully
reads zero in every run. We prefer the honest zero to an inflated number.
Budgets are hard stops: expiry reports "incomplete (best-so-far, optimality
unproven)" verbatim.

## Slide 7 — Independent verification (~40 s)

A separately-written module brute-forces the feasible set and evaluates every
plan through the simulator. Wherever it runs, its best must match the CSP
within 1e-9. Verified: A (144 plans), B, D, F1–F3, H1, H2, J1, J2 (20,736
each), G1 (256), G2 (194,481). Skipped with space sizes stated: C
(2,985,984) and E (12,960,000). Principle: no optimality claim without either
complete search or independent verification.

## Slide 8 — Dashboard tour (screenshot, ~45 s)

Live-verified session at scenario B defaults: the CSP proved optimality, the
banner reports an 83.7% improvement, and the verification alert confirms
J = 618.00 over 256 feasible plans. Nine tabs: overview KPIs, corridor with a
time slider and platoon animation (t = 57 s shows mixed red/green states),
signal-timeline Gantt, algorithm runs, results, search inspector, sensitivity
sweeps, export, and viva-oriented explanations.

## Slide 9 — Search inspector (screenshot, ~30 s)

Event histograms and a depth chart from the retained trace. The trace is a
first-events *window*; the aggregate counters above it always cover the entire
search — the UI says so explicitly so nobody mistakes the window for the whole.

## Slide 10 — Measured results (~60 s)

Read the table row by row (α=1, β=2): A 81.6%, B 83.7%, C 88.5%, D 80.0%,
E 84.0% improvement over uncoordinated. If challenged on any row, walk scenario
B end-to-end: J 3780 → 618 with plan O = (0, 40, 5, 40, 15), all 20,736 plans
evaluated, independent verification agreeing. Also state the greedy contrast:
830 → 618 (25.5% better than greedy) — and note that greedy actively hurt in
scenario H1 before the CSP fixed both directions.

## Slide 11 — Search statistics (~40 s)

Plans evaluated / nodes / FC removals / BB prunes / time. Scenario B:
20,736 plans in ≈1.43 s. C: only 4,096 evaluated (of 2.99M raw) because the
tolerance constraint does the cutting, with 10,920 FC eliminations recorded.
E: resolution is expensive — 194,481 tolerant-space plans, 379,236 removals,
≈12.4 s, about 9× the 5 s grid's work. BB prunes = 0 everywhere (honest).

## Slide 12 — Sensitivity (~35 s)

Demand sweep F1–F3: benefit persists at every demand. H1 (10 s headway):
greedy J = 2246 — worse than doing nothing (1828) — CSP found 409. H2
(5 s headway, tight platoons): J = 24.0 vs 1008.8 — the model's ceiling case.
J-family: same plan optimal at β = 2 and β = 5, because it improves W and S
simultaneously — a robustness result, not a tuning artifact.

## Slide 13 — Wrap-up (~40 s)

Limitations named on the slide are the same ones in the report's §7 — no new
surprises in the viva. Future work: an informative admissible bound, queueing,
min-conflicts for large N, multi-phase timing. Engineering summary: 76 passing
tests, ruff-clean source, lint + tests run locally before every push, one-command reproducible
benchmarks, MIT-licensed clean tree. Final line: *every number traces to a
results file; every optimality claim carries verification or an explicit,
honest skip.*
