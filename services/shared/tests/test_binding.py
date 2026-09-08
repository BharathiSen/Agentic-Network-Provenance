import hashlib

from provlib import compute_config_binding


def test_deterministic():
    a = compute_config_binding("m1", "1.0", "p1", {"tool": "1"})
    b = compute_config_binding("m1", "1.0", "p1", {"tool": "1"})
    assert a == b
    assert len(a) == hashlib.sha256().digest_size == 32


def test_changes_with_version():
    assert compute_config_binding("m1", "1.0", "p1") != compute_config_binding("m1", "1.1", "p1")


def test_changes_with_model_id():
    assert compute_config_binding("m1", "1.0", "p1") != compute_config_binding("m2", "1.0", "p1")


def test_changes_with_policy_version():
    assert compute_config_binding("m1", "1.0", "p1") != compute_config_binding("m1", "1.0", "p2")


def test_changes_with_manifest():
    a = compute_config_binding("m1", "1.0", "p1", {"tool": "1"})
    b = compute_config_binding("m1", "1.0", "p1", {"tool": "2"})
    assert a != b


def test_manifest_order_does_not_matter():
    a = compute_config_binding("m1", "1.0", "p1", {"x": "1", "y": "2"})
    b = compute_config_binding("m1", "1.0", "p1", {"y": "2", "x": "1"})
    assert a == b


def test_absent_policy_version_differs_from_empty_string():
    assert compute_config_binding("m1", "1.0", None) != compute_config_binding("m1", "1.0", "")


def test_absent_manifest_differs_from_empty_manifest_only_if_content_differs():
    # None and {} are both "no tools", so they are deliberately the same digest.
    assert compute_config_binding("m1", "1.0", "p1", None) == compute_config_binding(
        "m1", "1.0", "p1", {}
    )


def test_field_boundaries_are_unambiguous():
    # Structured JSON rather than plain concatenation: under naive concatenation
    # these two distinct configurations would share a preimage, and so a binding.
    a = compute_config_binding("ab", "c", None)
    b = compute_config_binding("a", "bc", None)
    assert a != b
