# conftest.py
# =============================================================================
# WHAT THIS FILE IS
# -----------------------------------------------------------------------------
# pytest automatically imports the conftest.py sitting at the rootdir BEFORE it
# collects any test files. That makes it the one reliable place to adjust the
# import path for the whole test run.
#
# WHY WE NEED IT
# -----------------------------------------------------------------------------
# This is a monorepo: each service keeps its code under services/<name>/src/,
# and pyproject.toml sets `[tool.uv] package = false`, so uv never pip-installs
# those service packages into the virtualenv. Without help, a test doing
# `from pstore.main import app` would raise ModuleNotFoundError, because
# services/provenance-store/src is not on sys.path.
#
# This file fixes that by appending every services/*/src directory to sys.path
# at test-collection time. It is the test-time equivalent of the --app-dir flag
# we pass to uvicorn when running a service by hand.
# =============================================================================

import sys  # sys.path is the list of directories Python searches on import
from pathlib import Path  # pathlib gives OS-independent path handling (Windows + Linux CI)

# __file__ is this conftest.py; .parent is the repo root, since this file lives
# at the top level. Everything below is resolved relative to that, so the tests
# work no matter which directory pytest is invoked from.
ROOT = Path(__file__).parent

# Walk every immediate child of services/ -- controller, evidence-fn,
# provenance-store, verifier-ts -- in one pass. Using iterdir() rather than a
# hardcoded list means a new service is picked up automatically with no edit here.
for svc in (ROOT / "services").iterdir():
    src = svc / "src"  # by convention each Python service exposes its packages under src/

    # Guard: services/verifier-ts is TypeScript and has no src/ directory (and in
    # a fresh clone may hold only .gitkeep), so skip anything that is not a real
    # directory instead of poisoning sys.path with a nonexistent path.
    if src.is_dir():
        # insert(0, ...) puts the repo's own code ahead of site-packages, so a
        # local package always wins over a same-named third-party one.
        # str() is required: older sys.path handling expects str, not Path.
        sys.path.insert(0, str(src))
