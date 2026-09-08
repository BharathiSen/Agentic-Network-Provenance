"""
Regenerate schema/provenance-statement.schema.json from the Pydantic
models. Run any time models.py changes — Phase 7's independent
implementation is only allowed to read this file, not the Python source,
so it has to stay in sync.
"""
import json
from pathlib import Path

from provlib.models import ProvenanceStatement

ROOT = Path(__file__).parent.parent
OUT = ROOT / "schema" / "provenance-statement.schema.json"


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    schema = ProvenanceStatement.model_json_schema()
    OUT.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()