"""Canonical CBOR encoding of a ProvenanceStatement.

Encoding rules (these are what an independent implementation must match):

* The statement is a CBOR map keyed by the snake_case field names.
* ``bytes`` fields are CBOR byte strings (major type 2) -- not base64 text.
* ``datetime`` fields are CBOR tag 0, an RFC 3339 string in UTC.
* ``origin_class`` and ``result`` are plain text strings.
* Optional fields that are ``None`` are encoded as CBOR ``null`` rather than
  omitted, so the map shape is stable across records.
* Encoding is canonical (RFC 8949 section 4.2): map keys sorted, shortest
  integer forms, no indefinite-length items.

Canonical encoding is not required for the signature to verify -- COSE signs
whatever payload bytes it is handed -- but it makes a record byte-for-byte
reproducible from its decoded form, which is what lets the store re-encode a
statement and compare it against the signed bytes.
"""

from __future__ import annotations

import cbor2

from .models import ProvenanceStatement

__all__ = ["encode_statement", "decode_statement"]


def encode_statement(statement: ProvenanceStatement) -> bytes:
    """Serialise a statement to canonical CBOR."""
    # mode="python" keeps bytes as bytes and datetimes as datetimes so cbor2
    # can emit native CBOR types; mode="json" would stringify both.
    payload = statement.model_dump(mode="python")
    # Enum members must be reduced to their plain string values.
    payload["origin_class"] = statement.origin_class.value
    return cbor2.dumps(payload, canonical=True, datetime_as_timestamp=False)


def decode_statement(data: bytes) -> ProvenanceStatement:
    """Parse canonical CBOR back into a validated statement.

    Raises:
        cbor2.CBORDecodeError: if ``data`` is not well-formed CBOR.
        pydantic.ValidationError: if it is well-formed but not a valid
            statement.
    """
    return ProvenanceStatement.model_validate(cbor2.loads(data))
