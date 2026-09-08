from provlib import compute_config_binding


def test_deterministic():
    a = compute_config_binding("m1", "1.0", "p1", {"tool": "1"})
    b = compute_config_binding("m1", "1.0", "p1", {"tool": "1"})
    assert a == b
    assert len(a) == 32  # sha256 digest


def test_changes_with_version():
    a = compute_config_binding("m1", "1.0", "p1")
    b = compute_config_binding("m1", "1.1", "p1")
    assert a != b


def test_manifest_order_does_not_matter():
    a = compute_config_binding("m1", "1.0", "p1", {"x": "1", "y": "2"})
    b = compute_config_binding("m1", "1.0", "p1", {"y": "2", "x": "1"})
    assert a == b