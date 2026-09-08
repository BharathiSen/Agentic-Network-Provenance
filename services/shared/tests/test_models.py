from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from provlib import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
)


def _valid_statement(**overrides) -> ProvenanceStatement:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    defaults = dict(
        subject_ref="oam-test-42",
        origin_class=OriginClass.AUTONOMOUS_MODEL,
        evidence=EvidenceDescriptor(
            model_id="bandit-v1",
            model_version="1.0.0",
            policy_version="p1",
            confidence=0.87,
            input_ref="telemetry-tick-8831",
            config_binding=b"\x00" * 32,
        ),
        verification=VerificationClaim(
            performed=True, method="blast-radius-graph-check", verified_at=now
        ),
        freshness=Freshness(valid_until=now + timedelta(minutes=5), nonce=b"\x01" * 16),
    )
    defaults.update(overrides)
    return ProvenanceStatement(**defaults)


def test_valid_statement_constructs():
    stmt = _valid_statement()
    assert stmt.origin_class == OriginClass.AUTONOMOUS_MODEL


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        EvidenceDescriptor(
            model_id="m",
            model_version="1",
            policy_version=None,
            confidence=1.5,
            input_ref="x",
            config_binding=b"\x00",
        )


def test_naive_datetime_rejected():
    now_naive = datetime.now()  # no tzinfo
    with pytest.raises(ValidationError):
        Freshness(valid_until=now_naive, nonce=b"\x01")