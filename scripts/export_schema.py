"""
Regenerate schema/provenance-statement.schema.json from the Pydantic
models. Run any time models.py changes — Phase 7's independent
implementation is only allowed to read this file, not the Python source,
so it has to stay in sync.

test_schema.py fails if the committed file drifts from the models, so this
being forgotten is caught by the test suite rather than discovered in Phase 7.

Run with plain `uv run python scripts/export_schema.py` -- the sys.path
bootstrap below means no PYTHONPATH is needed, matching how conftest.py
makes the service packages importable during tests.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "services" / "shared" / "src"))

from provlib.schema import SCHEMA_RELPATH, build_schema, serialise


def main() -> None:
    out = ROOT / SCHEMA_RELPATH
    out.parent.mkdir(exist_ok=True)
    out.write_text(serialise(build_schema()), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
