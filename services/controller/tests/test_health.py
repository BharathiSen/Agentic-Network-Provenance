# services/controller/tests/test_health.py
# =============================================================================
# Smoke test for the Network Controller stub -- the mirror image of the
# provenance-store test, asserting this service's own `service` value.
#
# NOTE ON THE FILENAME: this file and
# services/provenance-store/tests/test_health.py share the basename
# `test_health.py`, and neither tests/ directory has an __init__.py. Under
# pytest's default "prepend" import mode both would be imported as the module
# `test_health` and the second would fail with "import file mismatch". That is
# why pyproject.toml sets `addopts = "--import-mode=importlib"`, which derives
# unique module names from the full path. Do not remove that setting.
# =============================================================================

from fastapi.testclient import TestClient  # third-party group

from ctrl.main import app  # first-party group; ruff's isort keeps the blank line above

# One client for the whole module -- see the provenance-store test for why.
client = TestClient(app)


def test_health():
    resp = client.get("/health")  # in-process ASGI call; no port is bound

    # Status first, so a failure distinguishes "server broke" from "shape changed".
    assert resp.status_code == 200

    # Exact match: `service` must say "controller", which is what makes this test
    # meaningfully different from the provenance-store one. If both apps were
    # accidentally wired to the same module, this assertion is what would catch it.
    assert resp.json() == {"status": "ok", "service": "controller"}
