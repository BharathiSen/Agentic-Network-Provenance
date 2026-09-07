# services/evidence-fn/tests/test_placeholder.py
# =============================================================================
# Placeholder test for the evidence function package.
#
# It asserts almost nothing about behaviour -- the point is structural: it proves
# `evidence` is importable from services/evidence-fn/src, which is the only part
# of this service Phase 0 actually delivers. Replace it with real tests for the
# evidence-descriptor builder in Phase 4.
# =============================================================================

from evidence import ping  # first-party; resolves via conftest.py's sys.path insert


def test_ping():
    # Smoke assertion: the package imports and its one symbol behaves.
    assert ping() == "ok"
