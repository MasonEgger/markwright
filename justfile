# ABOUTME: Task runner recipes; `just check` is the local gate (no pre-commit).
# ABOUTME: `just test-all` runs the supported Python version matrix locally; docs recipes build and serve the site.

default:
    @just --list

check:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy .
    uv run pytest

fmt:
    uv run ruff format .
    uv run ruff check --fix .

test:
    uv run pytest

test-all:
    #!/usr/bin/env bash
    set -euo pipefail
    for python_version in 3.11 3.12 3.13 3.14 3.15; do
        uv run --python "$python_version" -m pytest
    done

# End-to-end Hugo pipeline and clean-install tests (skip when hugo or mw is not on PATH)
test-integration:
    uv run pytest tests/integration -m integration -v

# Build the docs site (strict mode)
docs-build:
    uv run mkdocs build --strict

# Serve the docs site at localhost:8000
docs-serve:
    uv run mkdocs serve

# Serve the docs site on the Tailscale IP (reachable across your tailnet)
docs-serve-tailnet:
    uv run mkdocs serve -a $(tailscale ip -4):8000
