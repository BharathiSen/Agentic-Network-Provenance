"""
Freshness/replay checking. `seen_nonces` is caller-owned so the caller
controls its lifetime — Phase 2 backs it with Redis so replay detection
survives a restart; a test just passes a plain set().
"""

from __future__ import annotations

from collections.abc import MutableSet
from datetime import datetime

from provlib.models import ProvenanceStatement


def is_fresh(stmt: ProvenanceStatement, now: datetime, seen_nonces: MutableSet[bytes]) -> bool:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    if now > stmt.freshness.valid_until:
        return False

    if stmt.freshness.nonce in seen_nonces:
        return False

    seen_nonces.add(stmt.freshness.nonce)
    return True
