"""Validation rules on the information model."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from provenance import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
)


def _evidence(binding: bytes, **overrides):
    fields = {
        "model_id": "ernet-oam",
        "model_version": "1.4.2",
        "policy_version": "policy-2026-08",
        "confidence": 0.9,
        "input_ref": "s3://telemetry/window",
        "config_binding": binding,
    }
    fields.update(overrides)
    return fields


@pytest.mark.parametrize("bad", [1.5, -0.1, 2.0])
def test_confidence_outside_unit_interval_is_rejected(binding, bad):
    with pytest.raises(ValidationError) as excinfo:
        EvidenceDescriptor(**_evidence(binding, confidence=bad))
    assert "confidence" in str(excinfo.value)


@pytest.mark.parametrize("edge", [0.0, 1.0])
def test_confidence_bounds_are_inclusive(binding, edge):
    assert EvidenceDescriptor(**_evidence(binding, confidence=edge)).confidence == edge


def test_missing_config_binding_is_rejected(binding):
    fields = _evidence(binding)
    del fields["config_binding"]
    with pytest.raises(ValidationError) as excinfo:
        EvidenceDescriptor(**fields)
    assert "config_binding" in str(excinfo.value)


def test_config_binding_must_be_a_full_sha256_digest(binding):
    # A truncated digest would weaken the binding without any visible error.
    with pytest.raises(ValidationError):
        EvidenceDescriptor(**_evidence(binding, config_binding=binding[:16]))


def test_policy_version_is_optional(binding):
    assert (
        EvidenceDescriptor(**_evidence(binding, policy_version=None)).policy_version
        is None
    )


def test_unknown_origin_class_is_rejected(statement):
    with pytest.raises(ValidationError):
        ProvenanceStatement.model_validate(
            {**statement.model_dump(), "origin_class": "vibes"}
        )


def test_origin_class_members_match_the_shared_vocabulary():
    # CLAUDE.md lists these four; every later phase depends on them exactly.
    assert [c.value for c in OriginClass] == [
        "human",
        "deterministic-automation",
        "model-assisted",
        "autonomous-model",
    ]


def test_origin_class_is_a_str_enum_not_a_closed_literal():
    # Backing the enum with str is what keeps the set extensible: members
    # serialise as plain strings, so adding one later is not a wire change.
    assert issubclass(OriginClass, str)
    assert OriginClass.HUMAN == "human"


def test_unexpected_fields_are_rejected(statement):
    # extra="forbid": a record carrying fields we do not understand must not
    # be silently accepted, since the signature covers them but our logic does not.
    with pytest.raises(ValidationError):
        ProvenanceStatement.model_validate({**statement.model_dump(), "escalate": True})


def test_naive_datetimes_are_rejected():
    # A naive expiry is ambiguous and cannot be CBOR-encoded as tag 0.
    with pytest.raises(ValidationError, match="timezone-aware"):
        Freshness(valid_until=datetime(2026, 9, 7, 12, 0, 0), nonce=bytes(16))


def test_aware_datetimes_are_normalised_to_utc():
    ist = timezone(timedelta(hours=5, minutes=30))
    freshness = Freshness(
        valid_until=datetime(2026, 9, 7, 17, 30, 0, tzinfo=ist), nonce=bytes(16)
    )
    assert freshness.valid_until == datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)
    assert freshness.valid_until.tzinfo == timezone.utc


def test_nonce_must_be_long_enough_to_be_unpredictable():
    with pytest.raises(ValidationError):
        Freshness(valid_until=datetime(2026, 9, 7, tzinfo=timezone.utc), nonce=b"short")


@pytest.mark.parametrize("result", ["pass", "fail", "not-run"])
def test_verification_results(result):
    assert VerificationClaim(performed=True, result=result).result == result


def test_unknown_verification_result_is_rejected():
    with pytest.raises(ValidationError):
        VerificationClaim(performed=True, result="probably-fine")
