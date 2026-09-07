"""Freshness and replay checking.

A signature proves a record was authentic when it was made. It says nothing
about *when* -- a correctly signed record stays correctly signed forever, so
an attacker who captures one could re-present it to authorise the same change
again later. The freshness window bounds how long a record is usable, and the
nonce set makes each one single-use.
"""

from __future__ import annotations

from datetime import datetime

from .models import ProvenanceStatement

__all__ = ["is_fresh"]


def is_fresh(
    statement: ProvenanceStatement,
    now: datetime,
    seen_nonces: set[bytes],
) -> bool:
    """Report whether a statement is currently usable, recording its nonce.

    Note that this predicate has a side effect by design: on success it adds
    the statement's nonce to ``seen_nonces``, so a second call with the same
    statement returns ``False``. Checking and recording have to be one step,
    otherwise two concurrent gate checks could both observe an unseen nonce
    and both allow the same record.

    Args:
        statement: The record to check.
        now: Current time; must be timezone-aware, since ``valid_until`` is.
        seen_nonces: Nonces already spent. Mutated on success.

    Returns:
        ``True`` if the record is unexpired and its nonce is unspent.

    Raises:
        ValueError: if ``now`` is naive, which would otherwise raise an
            opaque TypeError when compared against an aware ``valid_until``.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("`now` must be timezone-aware")

    # Expiry is checked first: an expired record must not consume a nonce,
    # or a stale capture could be used to burn a nonce the legitimate holder
    # still needs.
    if now > statement.freshness.valid_until:
        return False

    nonce = statement.freshness.nonce
    if nonce in seen_nonces:
        return False

    seen_nonces.add(nonce)
    return True
