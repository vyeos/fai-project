# Development workflow. Detects the venv layout for Windows vs. POSIX.
ifeq ($(OS),Windows_NT)
    PYTHON := .venv/Scripts/python.exe
    PYTEST := .venv/Scripts/pytest.exe
    RUFF   := .venv/Scripts/ruff.exe
else
    PYTHON := .venv/bin/python
    PYTEST := .venv/bin/pytest
    RUFF   := .venv/bin/ruff
endif

.PHONY: setup test lint check benchmarks app clean

setup:
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e .

test:
	$(PYTEST) tests

lint:
	$(RUFF) check src tests app.py tools

# Run before every push (there is no hosted CI).
check: lint test

benchmarks:
	$(PYTHON) -m traffic_coordination.experiments.benchmark_runner --all

app:
	$(PYTHON) -m streamlit run app.py

clean:
	-rm -rf .pytest_cache .ruff_cache
