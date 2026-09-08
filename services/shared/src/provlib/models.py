"""
Provenance information model — see DESIGN.md for the field-level spec.

datetime fields (verified_at, valid_until) must be timezone-aware (UTC).
cbor2 requires a timezone-aware datetime to encode it correctly, so we
reject naive ones here rather than let them silently misbehave later.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OriginClass(str, Enum):
    HUMAN = "human"
    DETERMINISTIC_AUTOMATION = "deterministic-automation"
    MODEL_ASSISTED = "model-assisted"
    AUTONOMOUS_MODEL = "autonomous-model"


class VerificationResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_RUN = "not-run"


def _ensure_aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (use datetime.now(timezone.utc))")
    return v


class EvidenceDescriptor(BaseModel):
    model_id: str
    model_version: str
    policy_version: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    input_ref: str
    config_binding: bytes


class VerificationClaim(BaseModel):
    performed: bool
    method: str | None = None
    result: VerificationResult = VerificationResult.NOT_RUN
    verified_at: datetime | None = None

    @field_validator("verified_at")
    @classmethod
    def _verified_at_aware(cls, v: datetime | None) -> datetime | None:
        return _ensure_aware(v) if v is not None else v


class Freshness(BaseModel):
    valid_until: datetime
    nonce: bytes

    @field_validator("valid_until")
    @classmethod
    def _valid_until_aware(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class ProvenanceStatement(BaseModel):
    subject_ref: str
    origin_class: OriginClass
    evidence: EvidenceDescriptor
    verification: VerificationClaim
    freshness: Freshness