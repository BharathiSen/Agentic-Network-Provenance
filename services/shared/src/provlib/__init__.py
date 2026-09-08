"""Shared provenance library: information model, config binding, COSE signing,
and freshness/replay checking. Imported by the store, evidence-fn and
controller so all three share one definition of the record format."""

from provlib.binding import compute_config_binding
from provlib.freshness import is_fresh
from provlib.models import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
    VerificationResult,
)
from provlib.signing import (
    VerificationError,
    encode_statement,
    generate_keypair,
    load_key,
    public_key_of,
    save_private_key,
    save_public_key,
    sign_statement,
    verify_statement,
)

__all__ = [
    "EvidenceDescriptor",
    "Freshness",
    "OriginClass",
    "ProvenanceStatement",
    "VerificationClaim",
    "VerificationError",
    "VerificationResult",
    "compute_config_binding",
    "encode_statement",
    "generate_keypair",
    "is_fresh",
    "load_key",
    "public_key_of",
    "save_private_key",
    "save_public_key",
    "sign_statement",
    "verify_statement",
]
