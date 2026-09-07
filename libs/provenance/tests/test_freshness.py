"""Freshness window and replay rejection."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from provenance import is_fresh


def test_unexpired_unseen_record_is_fresh(statement, now):
    assert is_fresh(statement, now, set()) is True


def test_expired_record_is_rejected(statement, now):
    after_expiry = statement.freshness.valid_until + timedelta(seconds=1)
    assert is_fresh(statement, after_expiry, set()) is False


def test_expiry_boundary_is_inclusive(statement):
    # `now > valid_until` fails, so a record is still usable at the instant
    # it expires.
    assert is_fresh(statement, statement.freshness.valid_until, set()) is True


def test_replayed_nonce_is_rejected(statement, now):
    seen: set[bytes] = set()
    assert is_fresh(statement, now, seen) is True
    assert is_fresh(statement, now, seen) is False


def test_success_records_the_nonce(statement, now):
    seen: set[bytes] = set()
    is_fresh(statement, now, seen)
    assert statement.freshness.nonce in seen


def test_expired_record_does_not_consume_its_nonce(statement, now):
    # Otherwise a captured stale record could be replayed purely to burn a
    # nonce the legitimate holder still needs.
    seen: set[bytes] = set()
    expired_at = statement.freshness.valid_until + timedelta(hours=1)
    assert is_fresh(statement, expired_at, seen) is False
    assert seen == set()


def test_distinct_nonces_do_not_interfere(statement, now):
    seen: set[bytes] = set()
    other = statement.model_copy(
        update={
            "freshness": statement.freshness.model_copy(
                update={"nonce": bytes(range(16, 32))}
            )
        }
    )
    assert is_fresh(statement, now, seen) is True
    assert is_fresh(other, now, seen) is True


def test_naive_now_is_rejected_with_a_clear_error(statement):
    with pytest.raises(ValueError, match="timezone-aware"):
        is_fresh(statement, datetime(2026, 9, 7, 12, 0, 0), set())
