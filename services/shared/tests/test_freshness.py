from datetime import UTC, datetime, timedelta

import pytest

from provlib import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
    VerificationResult,
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
        verification=VerificationClaim(performed=False, result=VerificationResult.NOT_RUN),
        freshness=Freshness(valid_until=valid_until, nonce=nonce),
    )


def test_fresh_record_accepted():
    now = datetime.now(UTC).replace(microsecond=0)
    assert is_fresh(_statement(now + timedelta(minutes=5)), now, set()) is True


def test_expired_record_rejected():
    now = datetime.now(UTC).replace(microsecond=0)
    assert is_fresh(_statement(now - timedelta(seconds=1)), now, set()) is False


def test_expiry_boundary_is_inclusive():
    # The check is `now > valid_until`, so a record is usable at the instant
    # it expires, not one tick earlier.
    now = datetime.now(UTC).replace(microsecond=0)
    assert is_fresh(_statement(now), now, set()) is True


def test_replayed_nonce_rejected():
    now = datetime.now(UTC).replace(microsecond=0)
    nonce = b"\x02" * 16
    assert is_fresh(_statement(now + timedelta(minutes=5), nonce), now, {nonce}) is False


def test_nonce_recorded_after_acceptance():
    now = datetime.now(UTC).replace(microsecond=0)
    nonce = b"\x03" * 16
    stmt = _statement(now + timedelta(minutes=5), nonce)
    seen: set[bytes] = set()

    assert is_fresh(stmt, now, seen) is True
    assert nonce in seen
    assert is_fresh(stmt, now, seen) is False  # second presentation is a replay


def test_expired_record_does_not_consume_its_nonce():
    # Otherwise a captured stale record could be replayed purely to burn a
    # nonce the legitimate holder still needs.
    now = datetime.now(UTC).replace(microsecond=0)
    seen: set[bytes] = set()
    assert is_fresh(_statement(now - timedelta(seconds=1)), now, seen) is False
    assert seen == set()


def test_distinct_nonces_do_not_interfere():
    now = datetime.now(UTC).replace(microsecond=0)
    seen: set[bytes] = set()
    assert is_fresh(_statement(now + timedelta(minutes=5), b"\x04" * 16), now, seen) is True
    assert is_fresh(_statement(now + timedelta(minutes=5), b"\x05" * 16), now, seen) is True


def test_naive_now_rejected():
    now = datetime.now(UTC).replace(microsecond=0)
    stmt = _statement(now + timedelta(minutes=5))
    with pytest.raises(ValueError, match="timezone-aware"):
        is_fresh(stmt, datetime.now(), set())  # noqa: DTZ005 -- naive is the point
