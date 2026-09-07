"""Shared information model and signing utilities for augmented provenance.

Imported by provenance-store, evidence-fn, and controller so that all three
share one definition of the record format. See CLAUDE.md for the vocabulary
and architecture section 4 for the model itself.
"""

from .binding import CONFIG_BINDING_DOMAIN, compute_config_binding
from .cbor import decode_statement, encode_statement
from .cose import (
    VerificationError,
    generate_key,
    private_key_from_pem,
    private_key_to_pem,
    public_key_from_pem,
    public_key_to_pem,
    public_part,
    sign_statement,
    verify_statement,
)
from .freshness import is_fresh
from .models import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
)

__all__ = [
    "CONFIG_BINDING_DOMAIN",
    "EvidenceDescriptor",
    "Freshness",
    "OriginClass",
    "ProvenanceStatement",
    "VerificationClaim",
    "VerificationError",
    "compute_config_binding",
    "decode_statement",
    "encode_statement",
    "generate_key",
    "is_fresh",
    "private_key_from_pem",
    "private_key_to_pem",
    "public_key_from_pem",
    "public_key_to_pem",
    "public_part",
    "sign_statement",
    "verify_statement",
]
