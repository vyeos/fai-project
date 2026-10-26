# Classical AI-Based Traffic Signal Coordination

*(Full README is being written; see `docs/` for technical documentation.)*

An educational simulation and decision-support system for the ECSCT24301
Foundation of AI project (Adani University). It coordinates signal offsets
along an arterial corridor and compares:

1. an **uncoordinated** baseline (all offsets 0),
2. a **greedy one-way progression** baseline (`O_{i+1} ~ O_i + tau_i mod C`),
3. a **CSP optimizer** (backtracking + forward checking + branch-and-bound).

All plans are evaluated with one deterministic corridor simulator using the
objective `J = alpha*W + beta*S` (total waiting time plus a stop penalty).

Status: implementation in progress. Run `pip install -r requirements-dev.txt`
then `pytest tests` for the current test coverage.
