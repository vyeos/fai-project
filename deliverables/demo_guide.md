# Demo Guide — live walkthrough

A page-by-page walkthrough of the Streamlit dashboard. Numbers below are for
the default road (scenario B) and were checked live. Total time ≈ 6–7
minutes; a 4-minute compressed route is marked with (★).

## Setup (do before the audience sits down)

1. Activate the venv: `Set-Location <repo>`; `.\.venv\Scripts\Activate.ps1`.
2. `python -m streamlit run app.py` → opens at http://localhost:8501 on
   **Try it**. The default road runs automatically on the first visit.
3. Defaults: 5 lights, 400 m apart, 40 km/h, moderate traffic (20 cars each
   way, 1 s apart), both ways, in a bunch; cycle 60 s, green 30 s, 5 s step,
   ±10 s green-wave rule, stop cost 2 s.

## 1. Try it (★)

- Read the headline: an average car waits **14 s instead of 86 s** and stops
  **1.0 times instead of 4.0**; badge "Proven best plan for this road".
- Stats: waiting per car 13.5 s (−84%), stops per car 0.97 (−76%), score
  618 vs 3,780 (−84%).
- Point at the animated lights and the table: plan **0 / +40 / +10 / +40 /
  +15 s**; compare "Later than the light before" with the 36 s driving time.
- Scroll to **See the difference** (★): on the left, lines run flat along the
  red bars (cars waiting); on the right, the bunches slide through.
- Strategy cards: No coordination 3,780 · Simple green wave 830 · Optimized
  search 618 (outlined as best).
- Live input (★): set 7 lights, Heavy, One way → **Find the best timings**.
  Waiting per car drops from about 144 s to 10 s.

## 2. How it works

- Walk the steps top to bottom: the problem (why a car meets red at Light 2
  after 36 s), the glossary, the five simulator rules, the greedy rule worked
  through on the current road, then the CSP: 12⁴ = 20,736 plans, the ±10 s
  rule, backtracking, forward checking (680 values crossed out), branch and
  bound (0 skips — "safe but cautious bound, the counter tells the truth").
- Drag the time slider under "Watch the road at any moment".

## 3. Experiments (★)

- Test roads A–E table: optimized beats or ties both baselines everywhere;
  A, B, D are checked by brute force, C and E are proven by the search.
- Press **Run comparison** for "Amount of traffic": five values in a few
  seconds; the callout reports the range of waiting cut against no
  coordination (81–100% on the default road).

## 4. Under the hood

- "Yes, confirmed": brute force over 256 allowed plans gives the same best
  score, 618.
- Search effort: 256 of 20,736 plans scored (1.2%), 341 values tried,
  85 branches, 680 ruled out ahead, 0 skipped by bound.
- Trace charts and the step table; download buttons for results CSV, timing
  plans JSON and search steps CSV; full settings table at the bottom.

## Reset between demos

- Reload the page (new session) or set the form back to the defaults above.
- An invalid road (for example green time longer than the cycle) shows a red
  notice explaining why; the previous valid result stays on screen.

## Known-behaviour notes (say them before they are asked)

- The search stops at 30 s or 250,000 plans; if either trips, the badge says
  "Best plan found before the time limit (not proven best)".
- Brute-force verification runs only when the road has at most 250,000 plans;
  otherwise Under the hood says it was skipped and why.
- All numbers are simulated under the documented simplifications (constant
  speed, no queues, one road, shared cycle).
