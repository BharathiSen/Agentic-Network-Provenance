# services/provenance-store/tests/test_health.py
from fastapi.testclient import TestClient

from pstore.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "provenance-store"}