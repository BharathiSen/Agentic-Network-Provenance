# Makefile
# ===========================================================================
# Task shortcuts for the five things you do most. Every target is a thin
# wrapper -- nothing here hides real logic, so you can always run the
# underlying command directly.
#
# WINDOWS USERS: `make` is not installed by default and is NOT a PowerShell
# command, so `make lint` fails with CommandNotFoundException. Either run the
# recipe lines below directly, or install make with:
#     winget install GnuWin32.Make
# CI runs on Linux, where make is present.
#
# IMPORTANT: recipe lines MUST be indented with a literal TAB, never spaces.
# A space-indented recipe fails with "missing separator".
# ===========================================================================

# .PHONY tells make these names are commands, not files to build. Without it,
# a file or directory named e.g. `test` in the repo root would make `make test`
# say "nothing to be done" and silently skip the tests.
.PHONY: up down test lint fmt

# Start Postgres + Redis in the background (-d = detached).
# Check readiness with: docker compose ps
up:
	docker compose up -d

# Stop the containers AND DELETE their volumes (-v).
# DESTRUCTIVE: this wipes the provenance database. Omit -v to keep the data.
down:
	docker compose down -v

# Run the full test suite. `uv run` executes inside .venv, so no activation
# is needed. Test discovery is configured by [tool.pytest.ini_options].
test:
	uv run pytest

# Lint + import-order check. This is the same gate CI enforces, so run it
# before pushing. Add --fix to apply the auto-fixable findings.
lint:
	uv run ruff check .

# Auto-format every Python file in place.
# CAVEAT: with no [tool.black] section in pyproject.toml, black infers its
# target from requires-python = ">=3.12" (open-ended), assumes up to py3.15,
# and its AST safety check then warns on a 3.12 interpreter. It also defaults
# to line-length 88 while ruff is set to 100. Add a [tool.black] section
# before relying on this target.
fmt:
	uv run black .
