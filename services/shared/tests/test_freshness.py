from datetime import datetime, timedelta, timezone

from provlib import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
    is_fresh,
)


def _statement(valid_until, nonce=b"\x01" * 16) -> ProvenanceStatement:
    return ProvenanceStatement(
        subject_ref="oam-test-42",
        origin_class=OriginClass.AUTONOMOUS_MODEL,
        evidence=EvidenceDescriptor(
            model_id="bandit-v1",
            model_version="1.0.0",
            policy_version="p1",
            confidence=0.9,
            input_ref="tick-1",
            config_binding=b"\x00" * 32,
        ),
        verification=VerificationClaim(performed=False),
        freshness=Freshness(valid_until=valid_until, nonce=nonce),
    )


def test_fresh_record_accepted():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stmt = _statement(valid_until=now + timedelta(minutes=5))
    assert is_fresh(stmt, now, set()) is True


def test_expired_record_rejected():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stmt = _statement(valid_until=now - timedelta(seconds=1))
    assert is_fresh(stmt, now, set()) is False


def test_replayed_nonce_rejected():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    nonce = b"\x02" * 16
    stmt = _statement(valid_until=now + timedelta(minutes=5), nonce=nonce)
    assert is_fresh(stmt, now, {nonce}) is False  # already in seen set


def test_nonce_recorded_after_acceptance():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    nonce = b"\x03" * 16
    stmt = _statement(valid_until=now + timedelta(minutes=5), nonce=nonce)
    seen: set[bytes] = set()
    assert is_fresh(stmt, now, seen) is True
    assert is_fresh(stmt, now, seen) is False  # second presentation is a replay