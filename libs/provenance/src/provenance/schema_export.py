"""Export the information model as JSON Schema.

``schema/provenance-statement.schema.json`` at the repo root is the contract
the independent Phase 7 verifier is built against -- that implementation is
allowed to read the schema file but not this Python source, so anything a
second implementer needs must survive the export. That is why the models
carry ``x-cbor-type`` annotations and why this module adds a top-level
``x-encoding`` block: JSON Schema on its own describes a JSON document, and
the wire format here is CBOR.

Run ``make schema`` to regenerate. ``test_schema_export.py`` fails if the
committed file drifts from the models, so the two cannot diverge silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .binding import CONFIG_BINDING_DOMAIN
from .models import ProvenanceStatement

__all__ = ["SCHEMA_RELPATH", "build_schema", "serialise", "write_schema"]

#: Where the exported schema lives, relative to the repo root. The library
#: deliberately does not try to locate the repo root itself -- it may be
#: installed anywhere -- so callers pass an explicit destination.
SCHEMA_RELPATH = Path("schema") / "provenance-statement.schema.json"

_ENCODING_NOTE: dict[str, Any] = {
    "format": "CBOR (RFC 8949), canonical encoding",
    "envelope": "COSE_Sign1 (RFC 9052), CBOR tag 18",
    "algorithm": "ES256 (ECDSA w/ SHA-256 over NIST P-256), RFC 9053 section 2.1",
    "notes": [
        "Property names on the wire are exactly the snake_case names in this schema.",
        "Each property also carries x-yang-name, the kebab-case spelling used by the YANG module and the Internet-Draft.",
        "Properties typed 'string' with contentEncoding 'base64' are CBOR byte strings (major type 2) on the wire; base64 is only how this JSON Schema can describe them.",
        "Properties with x-cbor-type 'tag 0' are CBOR tag 0 RFC 3339 date/time strings, normalised to UTC.",
        "Optional properties are present and null rather than omitted.",
        "The COSE_Sign1 payload is the canonical CBOR encoding of this object.",
    ],
    "config_binding": {
        "algorithm": "SHA-256",
        "preimage": (
            f"the ASCII domain tag {CONFIG_BINDING_DOMAIN.decode()!r} followed by the "
            "canonical CBOR encoding of the array "
            "[model_id, model_version, policy_version_or_null, "
            "[[key, value], ...] manifest entries sorted by key]"
        ),
        "output": "the raw 32-byte digest",
    },
}


def build_schema() -> dict[str, Any]:
    """Return the JSON Schema document for a ProvenanceStatement."""
    schema = ProvenanceStatement.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://example.com/schema/provenance-statement.schema.json"
    schema["x-encoding"] = _ENCODING_NOTE
    return schema


def write_schema(path: Path) -> Path:
    """Write the schema to ``path``, returning where it went."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialise(build_schema()), encoding="utf-8")
    return path


def serialise(schema: dict[str, Any]) -> str:
    """Render the schema exactly as it is committed (stable, diff-friendly)."""
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"
