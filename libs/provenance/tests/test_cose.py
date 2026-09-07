"""COSE_Sign1 signing, verification, and tamper detection."""

from __future__ import annotations

import cbor2
import pytest

from provenance import (
    VerificationError,
    encode_statement,
    generate_key,
    private_key_from_pem,
    private_key_to_pem,
    public_key_from_pem,
    public_key_to_pem,
    public_part,
    sign_statement,
    verify_statement,
)


def test_sign_then_verify_returns_the_original_statement(statement, key):
    signed = sign_statement(statement, key)
    assert verify_statement(signed, public_part(key)) == statement


def test_signed_message_is_a_tagged_cose_sign1(statement, key):
    # CBOR tag 18 is COSE_Sign1 (RFC 9052); Phase 7 decodes on this basis.
    assert cbor2.loads(sign_statement(statement, key)).tag == 18


def test_verification_fails_against_a_different_key(statement, key):
    signed = sign_statement(statement, key)
    with pytest.raises(VerificationError):
        verify_statement(signed, public_part(generate_key()))


def test_flipping_one_byte_of_the_payload_breaks_verification(statement, key):
    signed = bytearray(sign_statement(statement, key))
    payload = encode_statement(statement)

    offset = bytes(signed).find(payload)
    assert offset != -1, "payload should appear verbatim inside the COSE envelope"

    signed[offset] ^= 0x01  # flip the low bit of the payload's first byte
    with pytest.raises(VerificationError):
        verify_statement(bytes(signed), public_part(key))


def test_no_single_byte_edit_anywhere_survives_verification(statement, key):
    """Every byte of the record is covered -- header, payload, or signature."""
    signed = sign_statement(statement, key)
    pubkey = public_part(key)

    for index in range(len(signed)):
        mutated = bytearray(signed)
        mutated[index] ^= 0x01
        if bytes(mutated) == signed:
            continue
        with pytest.raises(VerificationError):
            verify_statement(bytes(mutated), pubkey)


def test_truncated_message_is_rejected(statement, key):
    signed = sign_statement(statement, key)
    with pytest.raises(VerificationError):
        verify_statement(signed[: len(signed) // 2], public_part(key))


def test_garbage_is_rejected_without_crashing(key):
    with pytest.raises(VerificationError):
        verify_statement(b"not cbor at all", public_part(key))


def test_verification_never_returns_untrusted_content(statement, key):
    # verify_statement raises rather than returning an error value, so a
    # caller cannot act on an unverified statement by ignoring a result.
    with pytest.raises(VerificationError):
        verify_statement(b"\x00" * 32, public_part(key))


def test_public_key_alone_cannot_sign(statement, key):
    with pytest.raises(Exception):
        sign_statement(statement, public_part(key))


def test_keys_round_trip_through_pem(statement, key):
    # Phase 2 loads a trusted key from a file and Phase 7's CLI takes a
    # public.pem, so PEM is part of the contract between phases.
    reloaded_private = private_key_from_pem(private_key_to_pem(key))
    reloaded_public = public_key_from_pem(public_key_to_pem(public_part(key)))

    signed = sign_statement(statement, reloaded_private)
    assert verify_statement(signed, reloaded_public) == statement


def test_pem_rejects_a_non_p256_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    wrong_curve = (
        ec.generate_private_key(ec.SECP384R1())
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    with pytest.raises(ValueError, match="P-256"):
        public_key_from_pem(wrong_curve)
