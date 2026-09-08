from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from provlib import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
    VerificationResult,
)

# Valid stand-ins, so a test that means to exercise ONE rule is not silently
# satisfied by a second invalid field. (config_binding=b"\x00" used to make the
# confidence test pass on the digest-length rule instead.)
GOOD_BINDING = b"\x00" * 32
GOOD_NONCE = b"\x01" * 16


def _evidence(**overrides) -> dict:
    fields = {
        "model_id": "bandit-v1",
        "model_version": "1.0.0",
        "policy_version": "p1",
        "confidence": 0.87,
        "input_ref": "telemetry-tick-8831",
        "config_binding": GOOD_BINDING,
    }
    fields.update(overrides)
    return fields


def _valid_statement(**overrides) -> ProvenanceStatement:
    now = datetime.now(UTC).replace(microsecond=0)
    defaults = {
        "subject_ref": "oam-test-42",
        "origin_class": OriginClass.AUTONOMOUS_MODEL,
        "evidence": EvidenceDescriptor(**_evidence()),
        "verification": VerificationClaim(
            performed=True,
            method="blast-radius-graph-check",
            result=VerificationResult.PASS,
            verified_at=now,
        ),
        "freshness": Freshness(valid_until=now + timedelta(minutes=5), nonce=GOOD_NONCE),
    }
    defaults.update(overrides)
    return ProvenanceStatement(**defaults)


def test_valid_statement_constructs():
    stmt = _valid_statement()
    assert stmt.origin_class == OriginClass.AUTONOMOUS_MODEL


def test_evidence_fixture_is_itself_valid():
    # Guards every "rejects X" test below: if the baseline were invalid, those
    # tests would pass without exercising the rule they name.
    assert EvidenceDescriptor(**_evidence()).confidence == 0.87


@pytest.mark.parametrize("bad", [1.5, -0.1, 2.0])
def test_confidence_out_of_range_rejected(bad):
    with pytest.raises(ValidationError, match="confidence"):
        EvidenceDescriptor(**_evidence(confidence=bad))


@pytest.mark.parametrize("edge", [0.0, 1.0])
def test_confidence_bounds_are_inclusive(edge):
    assert EvidenceDescriptor(**_evidence(confidence=edge)).confidence == edge


def test_missing_config_binding_rejected():
    fields = _evidence()
    del fields["config_binding"]
    with pytest.raises(ValidationError, match="config_binding"):
        EvidenceDescriptor(**fields)


@pytest.mark.parametrize("bad", [b"", b"\x00", b"\x00" * 31, b"\x00" * 33])
def test_config_binding_must_be_a_full_sha256_digest(bad):
    # A truncated digest would weaken the binding with no visible error.
    with pytest.raises(ValidationError, match="config_binding"):
        EvidenceDescriptor(**_evidence(config_binding=bad))


def test_policy_version_is_optional():
    assert EvidenceDescriptor(**_evidence(policy_version=None)).policy_version is None


@pytest.mark.parametrize("field", ["model_id", "model_version", "input_ref"])
def test_empty_identifier_strings_rejected(field):
    with pytest.raises(ValidationError, match=field):
        EvidenceDescriptor(**_evidence(**{field: ""}))


def test_empty_subject_ref_rejected():
    with pytest.raises(ValidationError, match="subject_ref"):
        _valid_statement(subject_ref="")


def test_naive_datetime_rejected():
    now_naive = datetime.now()  # noqa: DTZ005 -- a naive value is the point
    with pytest.raises(ValidationError, match="timezone-aware"):
        Freshness(valid_until=now_naive, nonce=GOOD_NONCE)


def test_aware_datetime_normalised_to_utc():
    ist = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata"))
    freshness = Freshness(valid_until=ist, nonce=GOOD_NONCE)
    assert freshness.valid_until.tzinfo is UTC
    assert freshness.valid_until == ist


@pytest.mark.parametrize("bad", [b"", b"\x01", b"\x01" * 15])
def test_short_nonce_rejected(bad):
    with pytest.raises(ValidationError, match="nonce"):
        Freshness(valid_until=datetime.now(UTC) + timedelta(minutes=1), nonce=bad)


def test_verification_result_is_required():
    # DESIGN.md: `performed` and `result` are distinct claims. A default would
    # let a producer that forgot `result` assert "nobody looked" by accident.
    with pytest.raises(ValidationError, match="result"):
        VerificationClaim(performed=True)


def test_unknown_verification_result_rejected():
    with pytest.raises(ValidationError, match="result"):
        VerificationClaim(performed=True, result="probably-fine")


def test_unknown_origin_class_rejected():
    with pytest.raises(ValidationError, match="origin_class"):
        _valid_statement(origin_class="vibes")


def test_unknown_fields_rejected():
    # Extras are covered by the signature but not by our logic, so a record
    # carrying them must be refused rather than silently accepted.
    stmt = _valid_statement()
    with pytest.raises(ValidationError):
        ProvenanceStatement.model_validate({**stmt.model_dump(), "escalate": True})


def test_origin_class_matches_shared_vocabulary():
    # CLAUDE.md lists exactly these four; every later phase depends on them.
    assert [c.value for c in OriginClass] == [
        "human",
        "deterministic-automation",
        "model-assisted",
        "autonomous-model",
    ]
