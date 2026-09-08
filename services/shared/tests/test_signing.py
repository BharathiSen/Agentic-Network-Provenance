from datetime import UTC, datetime, timedelta

import cbor2
import pytest

from provlib import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
    VerificationError,
    VerificationResult,
    encode_statement,
    generate_keypair,
    load_key,
    public_key_of,
    save_private_key,
    save_public_key,
    sign_statement,
    verify_statement,
)


def _statement() -> ProvenanceStatement:
    now = datetime.now(UTC).replace(microsecond=0)
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
            performed=True,
            method="blast-radius-graph-check",
            result=VerificationResult.PASS,
            verified_at=now,
        ),
        freshness=Freshness(valid_until=now + timedelta(minutes=5), nonce=b"\x01" * 16),
    )


def test_sign_then_verify_round_trips():
    key = generate_keypair()
    stmt = _statement()

    signed = sign_statement(stmt, key)
    recovered = verify_statement(signed, key)

    assert recovered == stmt


def test_verifies_with_public_key_alone():
    # This is how Phase 2 will verify: the store holds only the public half.
    key = generate_keypair()
    signed = sign_statement(_statement(), key)
    assert verify_statement(signed, public_key_of(key)) == _statement()


def test_signed_message_is_a_tagged_cose_sign1():
    # CBOR tag 18 is COSE_Sign1 (RFC 9052); Phase 7 decodes on this basis.
    assert cbor2.loads(sign_statement(_statement(), generate_keypair())).tag == 18


def test_encoding_is_canonical_and_deterministic():
    stmt = _statement()
    assert encode_statement(stmt) == encode_statement(stmt)
    # Re-encoding a decoded statement must reproduce the signed bytes exactly.
    key = generate_keypair()
    recovered = verify_statement(sign_statement(stmt, key), key)
    assert encode_statement(recovered) == encode_statement(stmt)


def test_tampering_with_the_payload_breaks_verification():
    # The DoD names the payload specifically, so flip a byte inside the payload
    # rather than in the trailing signature.
    key = generate_keypair()
    stmt = _statement()
    signed = bytearray(sign_statement(stmt, key))

    payload = encode_statement(stmt)
    offset = bytes(signed).find(payload)
    assert offset != -1, "payload should appear verbatim inside the COSE envelope"
    signed[offset] ^= 0x01

    # match= is load-bearing. These tests previously asserted only "some
    # VerificationError", and passed for months-equivalent reasons: under
    # cbor2 >= 6 the decode failed before any signature check ran, so they
    # would have passed even if signing were a no-op. Pinning the message to
    # the signature branch means a regression in decoding fails the test
    # instead of satisfying it.
    with pytest.raises(VerificationError, match="signature verification failed"):
        verify_statement(bytes(signed), key)


def test_tampering_with_the_signature_breaks_verification():
    key = generate_keypair()
    signed = bytearray(sign_statement(_statement(), key))
    signed[-1] ^= 0x01

    with pytest.raises(VerificationError, match="signature verification failed"):
        verify_statement(bytes(signed), key)


def test_wrong_key_fails_verification():
    signed = sign_statement(_statement(), generate_keypair())

    with pytest.raises(VerificationError, match="signature verification failed"):
        verify_statement(signed, generate_keypair())


def test_no_single_byte_edit_survives_verification():
    """Every byte is covered -- protected header, payload, or signature."""
    key = generate_keypair()
    signed = sign_statement(_statement(), key)

    for i in range(len(signed)):
        mutated = bytearray(signed)
        mutated[i] ^= 0x01
        with pytest.raises(VerificationError):
            verify_statement(bytes(mutated), key)


def test_garbage_is_rejected_as_a_decode_failure():
    with pytest.raises(VerificationError, match="COSE decode failed"):
        verify_statement(b"not cbor at all", generate_keypair())


def test_truncated_message_rejected():
    key = generate_keypair()
    signed = sign_statement(_statement(), key)
    with pytest.raises(VerificationError):
        verify_statement(signed[: len(signed) // 2], key)


def test_public_key_of_strips_the_private_scalar():
    key = generate_keypair()
    assert key.d  # the signing key really does carry a private scalar
    pub = public_key_of(key)
    # pycose reports an absent scalar as b"" rather than raising, and omits the
    # EC2KpD parameter from the key entirely.
    assert not pub.d
    assert "EC2KpD" not in str(pub)


def test_save_public_key_does_not_leak_private_material(tmp_path):
    # save_key() used to write whatever it was handed, so exporting "the public
    # key" for a verifier published the signing key. save_public_key strips it.
    key = generate_keypair()
    pub_path = tmp_path / "public.cbor"
    save_public_key(key, pub_path)

    blob = pub_path.read_bytes()
    assert key.d not in blob
    assert not load_key(pub_path).d


def test_saved_public_key_still_verifies(tmp_path):
    key = generate_keypair()
    signed = sign_statement(_statement(), key)
    pub_path = tmp_path / "public.cbor"
    save_public_key(key, pub_path)

    assert verify_statement(signed, load_key(pub_path)) == _statement()


def test_private_key_round_trips(tmp_path):
    key = generate_keypair()
    path = tmp_path / "private.cbor"
    save_private_key(key, path)
    assert load_key(path).encode() == key.encode()
