"""
Builds the JSON Schema for a ProvenanceStatement.

This lives in the library rather than in scripts/ so the drift test can
import the same builder the exporter uses, and the committed file can be
compared byte-for-byte against it.

Phase 7 builds an independent verifier from schema/provenance-statement.schema.json
and the architecture prose ONLY -- it is not allowed to read this source. Plain
model_json_schema() output is not sufficient for that: JSON Schema describes a
JSON document, but the wire format here is CBOR inside COSE_Sign1. So an
x-encoding block is added carrying the facts a second implementer cannot infer
from the types alone -- notably that `bytes` fields are CBOR byte strings
rather than base64 text, and how config_binding is computed.
"""

from __future__ import annotations

import json
from typing import Any

from provlib.models import CONFIG_BINDING_LEN, MIN_NONCE_LEN, ProvenanceStatement

SCHEMA_RELPATH = "schema/provenance-statement.schema.json"

_ENCODING: dict[str, Any] = {
    "format": "CBOR (RFC 8949), canonical encoding",
    "envelope": "COSE_Sign1 (RFC 9052), CBOR tag 18",
    "algorithm": "ES256 (ECDSA w/ SHA-256 over NIST P-256), RFC 9053 s2.1",
    "notes": [
        "Wire property names are exactly the snake_case names in this schema.",
        (
            "The Internet-Draft and YANG module spell the same fields in "
            "kebab-case (model-id, config-binding, valid-until, verified-at, "
            "origin-class)."
        ),
        (
            "Properties shown as type 'string' with format 'binary' are CBOR "
            "byte strings (major type 2) on the wire, NOT base64 text."
        ),
        "Date-time properties are CBOR tag 0 (RFC 3339 string), normalised to UTC.",
        "Optional properties are encoded as CBOR null, not omitted.",
        "Unknown properties are rejected: every model forbids extras.",
        (
            f"config_binding is exactly {CONFIG_BINDING_LEN} bytes; nonce is "
            f"at least {MIN_NONCE_LEN} bytes."
        ),
        "The COSE_Sign1 payload is the canonical CBOR encoding of this object.",
    ],
    "config_binding": {
        "algorithm": "SHA-256",
        "preimage": (
            "UTF-8 of json.dumps({model_id, model_version, policy_version, "
            "tool_manifest}, sort_keys=True, separators=(',', ':')) -- a "
            "structurally unambiguous serialisation, so distinct configurations "
            "cannot share a preimage"
        ),
        "output": f"the raw {CONFIG_BINDING_LEN}-byte digest",
    },
}


def build_schema() -> dict[str, Any]:
    schema = ProvenanceStatement.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://example.com/" + SCHEMA_RELPATH
    schema["x-encoding"] = _ENCODING
    return schema


def serialise(schema: dict[str, Any]) -> str:
    """Render exactly as committed, with a trailing newline.

    Deliberately NOT sort_keys=True: model_json_schema() already emits
    properties in field-declaration order and is deterministic for a pinned
    pydantic, so the file is stable for diffing either way -- while keeping
    declaration order makes it much easier to read against models.py.
    """
    return json.dumps(schema, indent=2) + "\n"
