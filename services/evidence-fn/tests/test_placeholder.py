# services/evidence-fn/tests/test_placeholder.py
from evidence import ping


def test_ping():
    assert ping() == "ok"