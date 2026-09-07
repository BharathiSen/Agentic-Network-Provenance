"""Regenerate schema/provenance-statement.schema.json from the Pydantic models.

Run via `make schema`. The committed schema is the contract the independent
Phase 7 verifier builds against, so it is checked in rather than generated at
build time -- and test_schema_export.py fails if it drifts from the models.
"""

from __future__ import annotations

from pathlib import Path

from provenance.schema_export import SCHEMA_RELPATH, write_schema

REPO_ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    print(f"wrote {write_schema(REPO_ROOT / SCHEMA_RELPATH)}")
