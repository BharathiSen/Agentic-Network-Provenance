# services/provenance-store/tests/test_health.py
# =============================================================================
# Smoke test for the Provenance Store stub.
#
# It proves three things at once, which is why it is worth having in Phase 0:
#   1. the `pstore` package imports (so conftest.py's sys.path wiring works),
#   2. the FastAPI app object is constructed without error,
#   3. GET /health returns the exact contract other services will rely on.
#
# No server, no network, no ports: TestClient calls the ASGI app in-process, so
# this runs fast in CI and never collides with a port already in use.
# =============================================================================

from fastapi.testclient import TestClient  # third-party import group

from pstore.main import app  # first-party group -- blank line above is ruff's isort rule I001

# Built once at module scope and reused by every test in the file, because
# constructing a TestClient spins up the app's startup machinery. Cheap now;
# meaningfully faster once Phase 2 adds real startup work.
client = TestClient(app)


def test_health():
    # pytest collects any function named test_* inside a test_*.py file.
    resp = client.get("/health")  # in-process request; no socket is opened

    # Assert the status separately from the body so a failure message tells you
    # WHICH half broke -- a 500 and a renamed field are very different bugs.
    assert resp.status_code == 200

    # Exact-equality (not a subset check) is deliberate: this dict is a contract
    # that the eval harness and the Phase 7 verifier will depend on, so an
    # accidental extra or renamed key should fail loudly here.
    assert resp.json() == {"status": "ok", "service": "provenance-store"}
