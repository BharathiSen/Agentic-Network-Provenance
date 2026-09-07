"""Information model for augmented provenance records (architecture section 4).

Field names here are snake_case, matching the wire format the independent
Phase 7 verifier is specified against (``freshness.valid_until``,
``verification.performed``). CLAUDE.md lists the same fields in the
kebab-case spelling that YANG and the Internet-Draft use; each field below
carries its draft name in ``json_schema_extra`` under ``x-yang-name`` so the
exported JSON Schema records the mapping without a second source of truth.

Every ``datetime`` in this model must be timezone-aware. That is not
stylistic: CBOR (RFC 8949 tag 0) has no representation for a naive local
time, and an expiry instant whose timezone is ambiguous is a security
defect, not a formatting one. Aware inputs are normalised to UTC so that
comparisons in :mod:`provenance.freshness` are total.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "OriginClass",
    "EvidenceDescriptor",
    "VerificationClaim",
    "Freshness",
    "ProvenanceStatement",
]


class OriginClass(str, Enum):
    """How much human agency stood behind the proposed action.

    Backed by ``str`` rather than a closed ``Literal`` so the set can gain
    members in a later revision of the draft without changing the wire
    representation: each member serialises as its plain string value, and a
    consumer that does not recognise a newer member still reads a string.
    """

    HUMAN = "human"
    DETERMINISTIC_AUTOMATION = "deterministic-automation"
    MODEL_ASSISTED = "model-assisted"
    AUTONOMOUS_MODEL = "autonomous-model"


def _require_utc(value: datetime) -> datetime:
    """Reject naive datetimes; normalise aware ones to UTC."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(
            "datetime must be timezone-aware; a naive instant cannot be "
            "encoded as CBOR tag 0 and makes expiry checks ambiguous"
        )
    return value.astimezone(timezone.utc)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceDescriptor(_Base):
    """What produced the decision, and what it was bound to."""

    model_id: str = Field(
        min_length=1,
        json_schema_extra={"x-yang-name": "model-id"},
    )
    model_version: str = Field(
        min_length=1,
        json_schema_extra={"x-yang-name": "model-version"},
    )
    policy_version: str | None = Field(
        default=None,
        json_schema_extra={"x-yang-name": "policy-version"},
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        json_schema_extra={"x-yang-name": "confidence"},
    )
    input_ref: str = Field(
        min_length=1,
        json_schema_extra={"x-yang-name": "input-ref"},
    )
    config_binding: bytes = Field(
        min_length=32,
        max_length=32,
        json_schema_extra={
            "x-yang-name": "config-binding",
            "x-cbor-type": "byte string (major type 2)",
            "contentEncoding": "base64",
            "$comment": (
                "Raw 32-byte SHA-256 digest binding the decision to the "
                "model, policy, and tool/config manifest that produced it. "
                "See compute_config_binding in the architecture note."
            ),
        },
    )


class VerificationClaim(_Base):
    """Whether simulation/verification ran before the decision, and its outcome.

    This is the record format for the requirement that
    draft-zhao-nmop-network-management-agent names but leaves undefined.
    """

    performed: bool = Field(json_schema_extra={"x-yang-name": "performed"})
    method: str | None = Field(
        default=None,
        json_schema_extra={"x-yang-name": "method"},
    )
    result: Literal["pass", "fail", "not-run"] = Field(
        json_schema_extra={"x-yang-name": "result"},
    )
    verified_at: datetime | None = Field(
        default=None,
        json_schema_extra={
            "x-yang-name": "verified-at",
            "x-cbor-type": "tag 0 (RFC 3339 date/time string), UTC",
        },
    )

    @field_validator("verified_at")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        return None if v is None else _require_utc(v)


class Freshness(_Base):
    """Bounds replay of an otherwise-valid signed record."""

    valid_until: datetime = Field(
        json_schema_extra={
            "x-yang-name": "valid-until",
            "x-cbor-type": "tag 0 (RFC 3339 date/time string), UTC",
        },
    )
    nonce: bytes = Field(
        min_length=16,
        json_schema_extra={
            "x-yang-name": "nonce",
            "x-cbor-type": "byte string (major type 2)",
            "contentEncoding": "base64",
            "$comment": "At least 16 bytes of unpredictable data.",
        },
    )

    @field_validator("valid_until")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _require_utc(v)


class ProvenanceStatement(_Base):
    """The augmented provenance record.

    This is the payload that gets CBOR-encoded and wrapped in a COSE_Sign1
    envelope. The signature covers this whole structure, so the evidence,
    the verification claim, and the freshness window are all tamper-evident
    together -- a record cannot have its expiry extended or its verification
    result upgraded without invalidating the signature.
    """

    subject_ref: str = Field(
        min_length=1,
        json_schema_extra={
            "x-yang-name": "subject-ref",
            "$comment": "Identifies the action under consideration, e.g. an OAM test id.",
        },
    )
    origin_class: OriginClass = Field(
        json_schema_extra={"x-yang-name": "origin-class"},
    )
    evidence: EvidenceDescriptor
    verification: VerificationClaim
    freshness: Freshness
