from datetime import datetime, timedelta, timezone

import pytest

from provlib import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
    VerificationError,
    generate_keypair,
    sign_statement,
    verify_statement,
)


def _statement() -> ProvenanceStatement:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return ProvenanceStatement(
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


def test_sign_then_verify_round_trips():
    key = generate_keypair()
    stmt = _statement()

    signed = sign_statement(stmt, key)
    recovered = verify_statement(signed, key)

    assert recovered == stmt


def test_tamper_breaks_verification():
    key = generate_keypair()
    signed = bytearray(sign_statement(_statement(), key))
    signed[-1] ^= 0x01  # flip one bit near the end of the COSE structure

    with pytest.raises(VerificationError):
        verify_statement(bytes(signed), key)


def test_wrong_key_fails_verification():
    key = generate_keypair()
    other_key = generate_keypair()
    signed = sign_statement(_statement(), key)

    with pytest.raises(VerificationError):
        verify_statement(signed, other_key)