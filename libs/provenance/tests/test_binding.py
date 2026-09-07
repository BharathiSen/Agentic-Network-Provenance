"""The config-binding digest."""

from __future__ import annotations

import hashlib

from provenance import compute_config_binding

BASE = ("ernet-oam", "1.4.2", "policy-2026-08", {"probe": "2.1.0"})


def test_digest_is_a_raw_32_byte_sha256():
    digest = compute_config_binding(*BASE)
    assert isinstance(digest, bytes)
    assert len(digest) == hashlib.sha256().digest_size == 32


def test_digest_is_deterministic():
    assert compute_config_binding(*BASE) == compute_config_binding(*BASE)


def test_manifest_ordering_does_not_affect_the_digest():
    a = compute_config_binding("m", "1", "p", {"x": "1", "y": "2"})
    b = compute_config_binding("m", "1", "p", {"y": "2", "x": "1"})
    assert a == b


def test_every_input_changes_the_digest():
    baseline = compute_config_binding(*BASE)
    assert (
        compute_config_binding("other", "1.4.2", "policy-2026-08", {"probe": "2.1.0"})
        != baseline
    )
    assert (
        compute_config_binding(
            "ernet-oam", "9.9.9", "policy-2026-08", {"probe": "2.1.0"}
        )
        != baseline
    )
    assert (
        compute_config_binding(
            "ernet-oam", "1.4.2", "policy-2027-01", {"probe": "2.1.0"}
        )
        != baseline
    )
    assert (
        compute_config_binding(
            "ernet-oam", "1.4.2", "policy-2026-08", {"probe": "9.9.9"}
        )
        != baseline
    )


def test_absent_policy_version_differs_from_empty_string():
    assert compute_config_binding("m", "1", None, {}) != compute_config_binding(
        "m", "1", "", {}
    )


def test_field_boundaries_are_unambiguous():
    # The reason this digest hashes a canonical CBOR structure rather than a
    # plain concatenation: under concatenation these two distinct
    # configurations would share a preimage, and therefore a binding.
    assert compute_config_binding("ab", "c", None, {}) != compute_config_binding(
        "a", "bc", None, {}
    )
