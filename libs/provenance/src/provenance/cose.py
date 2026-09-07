"""COSE_Sign1 signing and verification (RFC 9052).

Algorithm choice: **ES256 over NIST P-256**.

The phase brief offered "ES256 over a generated Ed25519 or P-256 test key",
but those are not two options for the same algorithm. ES256 is defined in
RFC 9053 section 2.1 as ECDSA using P-256 and SHA-256; an Ed25519 key is
signed with EdDSA (-8), a different algorithm identifier entirely. Choosing
Ed25519 would mean not using ES256. We therefore use P-256/ES256, which is
also what the independent Phase 7 verifier is specified against, so the two
implementations interoperate.

The signed structure is a tagged COSE_Sign1 (CBOR tag 18) whose payload is
the canonical CBOR encoding of a ProvenanceStatement. The protected header
carries the algorithm, so the algorithm is itself covered by the signature
and cannot be downgraded in transit.
"""

from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pycose.algorithms import Es256
from pycose.headers import Algorithm, KID
from pycose.keys import EC2Key
from pycose.keys.curves import P256
from pycose.messages import Sign1Message

from .cbor import decode_statement, encode_statement
from .models import ProvenanceStatement

__all__ = [
    "VerificationError",
    "generate_key",
    "public_part",
    "sign_statement",
    "verify_statement",
    "private_key_to_pem",
    "public_key_to_pem",
    "private_key_from_pem",
    "public_key_from_pem",
]

_COORD_BYTES = 32  # P-256 field elements are 32 bytes.


class VerificationError(Exception):
    """Raised when a COSE record is not a trustworthy provenance statement.

    Covers every way verification can fail -- malformed CBOR, a broken COSE
    envelope, an unexpected algorithm, a bad signature, or a payload that is
    not a valid statement. They are deliberately one exception type: a caller
    deciding whether to allow a network change needs a single unambiguous
    "do not trust this" signal, and distinguishing failure modes to a
    potential attacker leaks more than it helps. The message says which it
    was, for operators reading logs.
    """


def generate_key(kid: bytes = b"anp-test-key") -> EC2Key:
    """Generate a fresh P-256 keypair for tests and local development."""
    key = EC2Key.generate_key(crv=P256)
    key.kid = kid
    return key


def public_part(key: EC2Key) -> EC2Key:
    """Strip the private scalar, leaving a verify-only key."""
    pub = EC2Key(crv=P256, x=key.x, y=key.y)
    if key.kid:
        pub.kid = key.kid
    return pub


def sign_statement(statement: ProvenanceStatement, key: EC2Key) -> bytes:
    """CBOR-encode a statement and wrap it in a signed COSE_Sign1 envelope.

    Args:
        statement: The record to sign.
        key: A P-256 private key.

    Returns:
        The tagged COSE_Sign1 message as bytes.
    """
    phdr: dict = {Algorithm: Es256}
    if key.kid:
        # A key id in the protected header lets a verifier with several
        # trusted keys pick the right one without trial verification.
        phdr[KID] = key.kid

    message = Sign1Message(phdr=phdr, payload=encode_statement(statement))
    message.key = key
    return message.encode()


def verify_statement(cose_bytes: bytes, pubkey: EC2Key) -> ProvenanceStatement:
    """Verify a COSE_Sign1 record and return the statement it carries.

    Args:
        cose_bytes: A tagged COSE_Sign1 message.
        pubkey: The public key expected to have signed it.

    Returns:
        The validated statement, only if the signature is good.

    Raises:
        VerificationError: on any failure. Nothing is returned on a failed
            signature, so a caller cannot accidentally act on unverified
            content by ignoring a return value.
    """
    try:
        message = Sign1Message.decode(cose_bytes)
    except Exception as exc:
        raise VerificationError(f"not a well-formed COSE_Sign1 message: {exc}") from exc

    algorithm = message.phdr.get(Algorithm)
    if algorithm is not Es256:
        # Checked before verifying so an attacker cannot swap in a weaker
        # algorithm and have us verify under it.
        raise VerificationError(
            f"unexpected signature algorithm {algorithm!r}; expected ES256"
        )

    message.key = pubkey
    try:
        signature_ok = message.verify_signature()
    except Exception as exc:
        raise VerificationError(f"signature could not be verified: {exc}") from exc
    if not signature_ok:
        raise VerificationError("signature does not verify against the supplied key")

    try:
        return decode_statement(message.payload)
    except Exception as exc:
        # A correct signature over a payload we cannot parse means the signer
        # and this verifier disagree about the schema; refuse either way.
        raise VerificationError(
            f"payload is not a valid ProvenanceStatement: {exc}"
        ) from exc


# --- PEM interoperability -------------------------------------------------
# Phase 2 loads a trusted public key from a file and Phase 7's CLI takes
# `--key public.pem`, so keys have to leave this process in a standard format.


def _int(value: bytes) -> int:
    return int.from_bytes(value, "big")


def _bytes(value: int) -> bytes:
    return value.to_bytes(_COORD_BYTES, "big")


def private_key_to_pem(key: EC2Key) -> bytes:
    """Serialise a private P-256 key as unencrypted PKCS#8 PEM."""
    numbers = ec.EllipticCurvePrivateNumbers(
        _int(key.d),
        ec.EllipticCurvePublicNumbers(_int(key.x), _int(key.y), ec.SECP256R1()),
    )
    return numbers.private_key().private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def public_key_to_pem(key: EC2Key) -> bytes:
    """Serialise a public P-256 key as SubjectPublicKeyInfo PEM."""
    numbers = ec.EllipticCurvePublicNumbers(_int(key.x), _int(key.y), ec.SECP256R1())
    return numbers.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def private_key_from_pem(data: bytes, kid: bytes | None = None) -> EC2Key:
    """Load a private P-256 key from PEM."""
    loaded = serialization.load_pem_private_key(data, password=None)
    if not isinstance(loaded, ec.EllipticCurvePrivateKey) or not isinstance(
        loaded.curve, ec.SECP256R1
    ):
        raise ValueError("expected a P-256 (secp256r1) private key")
    numbers = loaded.private_numbers()
    key = EC2Key(
        crv=P256,
        x=_bytes(numbers.public_numbers.x),
        y=_bytes(numbers.public_numbers.y),
        d=_bytes(numbers.private_value),
    )
    if kid:
        key.kid = kid
    return key


def public_key_from_pem(data: bytes, kid: bytes | None = None) -> EC2Key:
    """Load a public P-256 key from PEM."""
    loaded = serialization.load_pem_public_key(data)
    if not isinstance(loaded, ec.EllipticCurvePublicKey) or not isinstance(
        loaded.curve, ec.SECP256R1
    ):
        raise ValueError("expected a P-256 (secp256r1) public key")
    numbers = loaded.public_numbers()
    key = EC2Key(crv=P256, x=_bytes(numbers.x), y=_bytes(numbers.y))
    if kid:
        key.kid = kid
    return key
