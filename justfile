# Prism BI developer task runner

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# Create/sync the virtualenv and install the package with dev extras.
bootstrap:
    uv sync --extra dev

# Run the desktop application.
run:
    uv run prism-bi

# Headless startup smoke.
run-headless:
    uv run prism-bi --headless

# Unit/smoke/UI tests (offscreen Qt for CI/headless).
test:
    $env:QT_QPA_PLATFORM='offscreen'; uv run pytest

# Lint (ruff).
lint:
    uv run ruff check src tests plugins
    uv run ruff format --check src tests plugins

# Typecheck.
typecheck:
    uv run mypy

# Architecture fitness (package boundaries).
contract:
    uv run lint-imports --config importlinter_contracts.ini

# Full verification gate.
check:
    uv run ruff check src tests plugins
    uv run ruff format --check src tests plugins
    uv run mypy
    uv run lint-imports --config importlinter_contracts.ini
    uv run pytest

# Capture docs screenshots (offscreen).
screenshots:
    $env:QT_QPA_PLATFORM='offscreen'; uv run python scripts/capture_screenshots.py

# Milestone 5 benchmark harness (default 100k rows).
bench:
    uv run python benchmarks/run_bench.py --rows 100000

# Windows portable (+ optional installer via scripts/build_windows.ps1 -InnoSetup).
package-windows:
    powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
