# services/provenance-store/src/pstore/__init__.py
# =============================================================================
# Package marker for the `pstore` package (the Provenance Store service).
#
# Its presence is what makes `from pstore.main import app` resolve once
# services/provenance-store/src is on sys.path (see the repo-root conftest.py).
#
# Deliberately empty: importing the package should stay free of side effects, so
# nothing here opens a DB connection or reads config. Phase 2 adds the SQLAlchemy
# models and Alembic migrations as sibling modules, not here.
# =============================================================================
