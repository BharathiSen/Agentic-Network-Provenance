"""
Provenance information model — see DESIGN.md for the field-level spec.

datetime fields (verified_at, valid_until) must be timezone-aware (UTC).
cbor2 requires a timezone-aware datetime to encode it correctly, so we
reject naive ones here rather than let them silently misbehave later.
Aware values are normalised to UTC so that comparisons in freshness.py are
total and two records that name the same instant compare equal.

Every model sets extra="forbid". These statements are signed: a field we do
not recognise is still covered by the signature, so silently accepting it
would let a producer smuggle content past the consumer's logic while the
record still verifies. Better to refuse the record outright.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A SHA-256 digest is exactly 32 bytes. Pinning the length means a truncated
# or empty digest is rejected at the boundary instead of quietly weakening the
# binding it exists to provide.
CONFIG_BINDING_LEN = 32

# Floor, not an exact length: callers may use a longer nonce. Below 16 bytes a
# nonce stops being meaningfully unpredictable and replay protection weakens.
MIN_NONCE_LEN = 16


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
    # utcoffset() is checked as well as tzinfo, because a tzinfo subclass may
    # be attached yet still return None, which is naive in every way that matters.
    if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
        raise ValueError("datetime must be timezone-aware (use datetime.now(timezone.utc))")
    return v.astimezone(UTC)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceDescriptor(_Base):
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    policy_version: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    input_ref: str = Field(min_length=1)
    config_binding: bytes = Field(min_length=CONFIG_BINDING_LEN, max_length=CONFIG_BINDING_LEN)


class VerificationClaim(_Base):
    performed: bool
    method: str | None = None
    # Required, with no default. DESIGN.md notes that `performed` and `result`
    # are intentionally distinct claims; defaulting result to "not-run" would
    # let a producer that forgot to set it emit a record asserting nobody
    # looked, which is a claim it never actually made.
    result: VerificationResult
    verified_at: datetime | None = None

    @field_validator("verified_at")
    @classmethod
    def _verified_at_aware(cls, v: datetime | None) -> datetime | None:
        return _ensure_aware(v) if v is not None else v


class Freshness(_Base):
    valid_until: datetime
    nonce: bytes = Field(min_length=MIN_NONCE_LEN)

    @field_validator("valid_until")
    @classmethod
    def _valid_until_aware(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class ProvenanceStatement(_Base):
    subject_ref: str = Field(min_length=1)
    origin_class: OriginClass
    evidence: EvidenceDescriptor
    verification: VerificationClaim
    freshness: Freshness
