# Contributing

Thanks for your interest in improving this project. It was built for the
ECSCT24301 Foundation of AI project-based-learning course at Adani University, but
external fixes and suggestions are welcome.

## How to set up a development environment

```bash
git clone <repository-url>
cd traffic-signal-coordination
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Ground rules

- **Reproducibility first.** Any change that alters simulation results, benchmark
  numbers, or search statistics must state this in the pull-request description.
  Benchmark CSV files under `experiments/results/` must always be regenerable from
  committed code and stored seeds.
- **No fabricated results.** Do not commit experimental numbers that were not
  produced by running the benchmark runner, and never present illustrative values
  as measurements.
- **Keep the AI core explicit.** The CSP/backtracking implementation must remain
  hand-written and inspectable; do not replace it with an opaque optimizer library.
- **Tests.** Add or update pytest tests for behaviour changes. Run the whole suite
  with `make test` (or `python -m pytest tests`) before submitting.
- **Style.** The project uses Ruff (`make lint`). Keep the line length at 100
  characters, use type hints on public functions, and write docstrings that explain
  the traffic-engineering semantics, not just the code.
- **Scope.** This is an educational prototype. Changes that claim real-world
  control capability or field validation are out of scope.

## Commit conventions

Use conventional-commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`,
`perf:`, `ci:`, `chore:`. One logical change per commit keeps the history readable.

## Reporting issues

Open a GitHub issue with the scenario settings, the algorithm selection, and the
full error output. For performance problems, include corridor size, offset
resolution, and demand level, since search cost is exponential in several of these.
