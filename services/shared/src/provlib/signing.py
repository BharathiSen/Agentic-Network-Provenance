"""
Signs a ProvenanceStatement as a COSE_Sign1 structure over its CBOR
encoding (RFC 9052), matching the encoding OPSAWG's own yang-provenance
draft uses. ES256 (ECDSA P-256) throughout — pycose's best-supported
algorithm, no reason to pick anything more exotic for a prototype.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

import cbor2
from pycose.algorithms import Es256
from pycose.headers import Algorithm
from pycose.keys import CoseKey, EC2Key
from pycose.messages import Sign1Message

from provlib.models import ProvenanceStatement


class VerificationError(Exception):
    """Raised when a COSE_Sign1 record fails to decode or verify."""


def generate_keypair() -> EC2Key:
    return EC2Key.generate_key(crv="P_256")


def save_key(key: CoseKey, path: str | Path) -> None:
    Path(path).write_bytes(key.encode())


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


def sign_statement(stmt: ProvenanceStatement, key: EC2Key) -> bytes:
    payload = cbor2.dumps(_cbor_safe(stmt.model_dump(mode="python")))
    msg = Sign1Message(phdr={Algorithm: Es256}, payload=payload)
    msg.key = key
    return msg.encode()


def verify_statement(cose_bytes: bytes, key: CoseKey) -> ProvenanceStatement:
    try:
        msg = Sign1Message.decode(cose_bytes)
        msg.key = key
        ok = msg.verify_signature()
    except Exception as exc:  # pycose raises different exception types per failure mode
        raise VerificationError(f"COSE decode/verify failed: {exc}") from exc

    if not ok:
        raise VerificationError("signature verification failed")

    payload = cbor2.loads(msg.payload)
    return ProvenanceStatement.model_validate(payload)