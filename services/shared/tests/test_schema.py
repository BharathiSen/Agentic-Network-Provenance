"""The committed JSON Schema must not drift from the Pydantic models.

Phase 7 builds its verifier from schema/provenance-statement.schema.json without
reading provlib. That only holds if the committed file is a faithful projection
of the models, so it is checked mechanically rather than by remembering to run
scripts/export_schema.py.
"""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from provlib.models import (
    EvidenceDescriptor,
    Freshness,
    ProvenanceStatement,
    VerificationClaim,
)
from provlib.schema import SCHEMA_RELPATH, build_schema, serialise

ROOT = Path(__file__).resolve().parents[3]
COMMITTED = ROOT / SCHEMA_RELPATH

MODELS = [ProvenanceStatement, EvidenceDescriptor, VerificationClaim, Freshness]


def _committed() -> dict:
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


def _definition(schema: dict, model: type[BaseModel]) -> dict:
    return schema if model is ProvenanceStatement else schema["$defs"][model.__name__]


def test_committed_schema_exists():
    assert COMMITTED.is_file(), f"{SCHEMA_RELPATH} missing; run scripts/export_schema.py"


def test_committed_schema_matches_the_models():
    assert COMMITTED.read_text(encoding="utf-8") == serialise(
        build_schema()
    ), f"{SCHEMA_RELPATH} is stale; run `uv run python scripts/export_schema.py`"


def test_top_level_properties():
    assert list(_committed()["properties"]) == [
        "subject_ref",
        "origin_class",
        "evidence",
        "verification",
        "freshness",
    ]


@pytest.mark.parametrize("model", MODELS)
def test_every_model_field_appears(model: type[BaseModel]):
    assert set(_definition(_committed(), model)["properties"]) == set(model.model_fields)


@pytest.mark.parametrize("model", MODELS)
def test_required_fields_agree(model: type[BaseModel]):
    definition = _definition(_committed(), model)
    expected = {n for n, f in model.model_fields.items() if f.is_required()}
    assert set(definition.get("required", [])) == expected


def test_schema_documents_the_cbor_binding():
    # Phase 7 gets this file and the prose only, so the encoding rules have to
    # travel with the schema -- JSON Schema alone would imply a JSON document.
    enc = _committed()["x-encoding"]
    assert "COSE_Sign1" in enc["envelope"]
    assert "ES256" in enc["algorithm"]
    assert "CBOR" in enc["format"]
    assert enc["config_binding"]["algorithm"] == "SHA-256"
    assert any("byte string" in n for n in enc["notes"])
