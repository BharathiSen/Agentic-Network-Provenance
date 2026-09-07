"""CBOR encoding of statements."""

from __future__ import annotations

import cbor2

from provenance import decode_statement, encode_statement


def test_round_trip_preserves_every_field(statement):
    assert decode_statement(encode_statement(statement)) == statement


def test_encoding_is_deterministic(statement):
    assert encode_statement(statement) == encode_statement(statement)


def test_bytes_stay_byte_strings_and_times_stay_tag_zero(statement):
    # An independent implementation reads these types off the wire, so the
    # choice is part of the contract, not an implementation detail.
    raw = cbor2.loads(encode_statement(statement))
    assert isinstance(raw["evidence"]["config_binding"], bytes)
    assert isinstance(raw["freshness"]["nonce"], bytes)
    assert raw["freshness"]["valid_until"] == statement.freshness.valid_until


def test_enum_encodes_as_a_plain_string(statement):
    raw = cbor2.loads(encode_statement(statement))
    assert raw["origin_class"] == "model-assisted"
    assert type(raw["origin_class"]) is str


def test_optional_nulls_are_present_not_omitted(statement):
    stripped = statement.model_copy(
        update={
            "evidence": statement.evidence.model_copy(update={"policy_version": None})
        }
    )
    raw = cbor2.loads(encode_statement(stripped))
    assert "policy_version" in raw["evidence"]
    assert raw["evidence"]["policy_version"] is None
