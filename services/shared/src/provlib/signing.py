"""
Signs a ProvenanceStatement as a COSE_Sign1 structure over its CBOR
encoding (RFC 9052), matching the encoding OPSAWG's own yang-provenance
draft uses. ES256 (ECDSA P-256) throughout — pycose's best-supported
algorithm, no reason to pick anything more exotic for a prototype.

Note that ES256 *is* ECDSA-over-P-256 (RFC 9053 s2.1); the curve is not a
free choice alongside the algorithm.

Encoding is canonical CBOR (RFC 8949 s4.2). COSE signs whatever payload
bytes it is handed, so determinism is not required for a signature to
verify -- but it means a decoded statement re-encodes to the exact bytes
that were signed, which is what lets a store compare the two, and it gives
an independent implementation one unambiguous encoding to target.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import cbor2
from pycose.algorithms import Es256
from pycose.headers import Algorithm
from pycose.keys import CoseKey, EC2Key
from pycose.keys.curves import P256
from pycose.messages import Sign1Message

from provlib.models import ProvenanceStatement


class VerificationError(Exception):
    """Raised when a COSE_Sign1 record fails to decode or verify."""


def generate_keypair() -> EC2Key:
    return EC2Key.generate_key(crv="P_256")


def public_key_of(key: EC2Key) -> EC2Key:
    """Return a verify-only copy of `key`, with the private scalar stripped.

    CoseKey.encode() serialises whatever it holds, private scalar included.
    Anything that leaves this process for a verifier should go through here
    first, so a signing key cannot be published by accident.
    """
    return EC2Key(crv=P256, x=key.x, y=key.y)


def save_private_key(key: CoseKey, path: str | Path) -> None:
    """Write a key INCLUDING its private scalar. Treat the file as a secret."""
    Path(path).write_bytes(key.encode())


def save_public_key(key: EC2Key, path: str | Path) -> None:
    """Write only the public half, safe to distribute to verifiers."""
    Path(path).write_bytes(public_key_of(key).encode())


def load_key(path: str | Path) -> CoseKey:
    return CoseKey.decode(Path(path).read_bytes())


def _cbor_safe(obj):
    """Recursively swap Enum members for their .value so cbor2 can encode them."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _cbor_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_cbor_safe(v) for v in obj]
    return obj


def encode_statement(stmt: ProvenanceStatement) -> bytes:
    """Canonical CBOR encoding of a statement -- the COSE_Sign1 payload."""
    return cbor2.dumps(_cbor_safe(stmt.model_dump(mode="python")), canonical=True)


def sign_statement(stmt: ProvenanceStatement, key: EC2Key) -> bytes:
    msg = Sign1Message(phdr={Algorithm: Es256}, payload=encode_statement(stmt))
    msg.key = key
    return msg.encode()


def verify_statement(cose_bytes: bytes, key: CoseKey) -> ProvenanceStatement:
    """Verify a COSE_Sign1 record and return the statement it carries.

    Raises VerificationError on any failure, rather than returning a value a
    caller could ignore. The four failure modes carry distinct messages: they
    are all equally "do not trust this", but a single generic message let a
    decode bug masquerade as a working signature check -- tamper tests passed
    while no cryptography was running at all.
    """
    try:
        msg = Sign1Message.decode(cose_bytes)
    except Exception as exc:
        raise VerificationError(f"COSE decode failed: {exc}") from exc

    alg = msg.phdr.get(Algorithm)
    if alg is not Es256:
        # Checked before verifying, so a record cannot nominate a weaker
        # algorithm and have us verify under it.
        raise VerificationError(f"unexpected algorithm {alg!r}; expected ES256")

    msg.key = key
    try:
        ok = msg.verify_signature()
    except Exception as exc:
        raise VerificationError(f"signature check errored: {exc}") from exc

    if not ok:
        raise VerificationError("signature verification failed")

    try:
        return ProvenanceStatement.model_validate(cbor2.loads(msg.payload))
    except Exception as exc:
        # A good signature over a payload we cannot parse means the signer and
        # this verifier disagree about the schema. Refuse either way.
        raise VerificationError(f"payload is not a valid ProvenanceStatement: {exc}") from exc
