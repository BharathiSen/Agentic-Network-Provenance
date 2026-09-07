"""The committed JSON Schema must not drift from the Pydantic models.

Phase 7 builds an independent verifier from schema/provenance-statement.schema.json
without reading this package's source. That only works if the committed file
is a faithful projection of the models -- so this is checked mechanically
rather than by remembering to run `make schema`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from provenance.models import (
    EvidenceDescriptor,
    Freshness,
    ProvenanceStatement,
    VerificationClaim,
)
from provenance.schema_export import SCHEMA_RELPATH, build_schema, serialise

REPO_ROOT = Path(__file__).resolve().parents[3]
COMMITTED = REPO_ROOT / SCHEMA_RELPATH


def test_committed_schema_exists():
    assert COMMITTED.is_file(), f"{SCHEMA_RELPATH} is missing; run `make schema`"


def test_committed_schema_matches_the_models():
    assert COMMITTED.read_text(encoding="utf-8") == serialise(
        build_schema()
    ), "schema/provenance-statement.schema.json is out of date; run `make schema`"


@pytest.mark.parametrize(
    "model",
    [ProvenanceStatement, EvidenceDescriptor, VerificationClaim, Freshness],
)
def test_every_model_field_appears_in_the_schema(model: type[BaseModel]):
    schema = json.loads(COMMITTED.read_text(encoding="utf-8"))
    definition = (
        schema if model is ProvenanceStatement else schema["$defs"][model.__name__]
    )
    assert set(definition["properties"]) == set(model.model_fields)


@pytest.mark.parametrize(
    "model",
    [ProvenanceStatement, EvidenceDescriptor, VerificationClaim, Freshness],
)
def test_required_fields_agree(model: type[BaseModel]):
    schema = json.loads(COMMITTED.read_text(encoding="utf-8"))
    definition = (
        schema if model is ProvenanceStatement else schema["$defs"][model.__name__]
    )
    expected = {n for n, f in model.model_fields.items() if f.is_required()}
    assert set(definition.get("required", [])) == expected


def test_schema_records_the_kebab_case_draft_names():
    # CLAUDE.md's vocabulary is kebab-case (YANG); the wire format is
    # snake_case. The schema carries both so the mapping is not folklore.
    schema = json.loads(COMMITTED.read_text(encoding="utf-8"))
    evidence = schema["$defs"]["EvidenceDescriptor"]["properties"]
    assert {p["x-yang-name"] for p in evidence.values()} == {
        "model-id",
        "model-version",
        "policy-version",
        "confidence",
        "input-ref",
        "config-binding",
    }
    verification = schema["$defs"]["VerificationClaim"]["properties"]
    assert {p["x-yang-name"] for p in verification.values()} == {
        "performed",
        "method",
        "result",
        "verified-at",
    }
    freshness = schema["$defs"]["Freshness"]["properties"]
    assert {p["x-yang-name"] for p in freshness.values()} == {"valid-until", "nonce"}


def test_schema_documents_the_cbor_binding():
    # Phase 7 gets the schema and prose only, so the encoding rules have to
    # travel with the schema.
    encoding = json.loads(COMMITTED.read_text(encoding="utf-8"))["x-encoding"]
    assert "COSE_Sign1" in encoding["envelope"]
    assert "ES256" in encoding["algorithm"]
    assert "CBOR" in encoding["format"]
    assert encoding["config_binding"]["algorithm"] == "SHA-256"
