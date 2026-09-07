"""Shared fixtures for the information-model tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from provenance import (
    EvidenceDescriptor,
    Freshness,
    OriginClass,
    ProvenanceStatement,
    VerificationClaim,
    compute_config_binding,
    generate_key,
)

MANIFEST = {"oam-probe": "2.1.0", "topology-snapshot": "2026-09-01"}


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def binding() -> bytes:
    return compute_config_binding("ernet-oam", "1.4.2", "policy-2026-08", MANIFEST)


@pytest.fixture
def statement(now: datetime, binding: bytes) -> ProvenanceStatement:
    """A well-formed, verified, currently-fresh statement."""
    return ProvenanceStatement(
        subject_ref="oam-test:1a2b3c",
        origin_class=OriginClass.MODEL_ASSISTED,
        evidence=EvidenceDescriptor(
            model_id="ernet-oam",
            model_version="1.4.2",
            policy_version="policy-2026-08",
            confidence=0.93,
            input_ref="s3://telemetry/window/2026-09-07T11:55Z",
            config_binding=binding,
        ),
        verification=VerificationClaim(
            performed=True,
            method="digital-twin-simulation",
            result="pass",
            verified_at=now - timedelta(minutes=2),
        ),
        freshness=Freshness(
            valid_until=now + timedelta(minutes=5),
            nonce=bytes(range(16)),
        ),
    )


@pytest.fixture
def key():
    return generate_key()
