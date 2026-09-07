# services/provenance-store/src/pstore/main.py
# =============================================================================
# THE PROVENANCE STORE -- the append-only home for signed provenance statements.
#
# Phase 0 scope: a health endpoint only. This exists to prove the service boots,
# that the import path works, and that CI has something real to test. The actual
# storage API (POST a statement, GET it back, verify a signature) arrives in
# Phase 2 once the Phase 1 information model is defined.
#
# RUN IT BY HAND (PowerShell):
#   uv run uvicorn --app-dir services/provenance-store/src pstore.main:app --port 8001 --reload
#   ^ --app-dir does for uvicorn what conftest.py does for pytest: puts src/ on
#     sys.path. On Windows do NOT use the bash form `PYTHONPATH=... uv run ...`.
# =============================================================================

from fastapi import FastAPI  # ASGI framework; gives routing, validation, OpenAPI docs

# The module-level ASGI application object. The name `app` matters: the uvicorn
# target string "pstore.main:app" means "import pstore.main, then take .app".
# `title` is cosmetic -- it labels the auto-generated docs at /docs and /redoc.
app = FastAPI(title="Provenance Store")


# The decorator registers this function on the app's router: HTTP GET at /health.
# /health is the conventional liveness probe -- used by docker-compose
# healthchecks, Kubernetes, load balancers, and our own smoke tests.
@app.get("/health")
def health():
    # A plain `def` (not `async def`) is intentional. FastAPI runs sync handlers
    # in a threadpool, so a slow one cannot block the event loop. For a handler
    # this trivial either would work; sync is the safer default once real
    # blocking DB calls land here in Phase 2.
    #
    # The returned dict is serialised to JSON automatically. `service` is echoed
    # back so that when several stubs are running on different ports you can tell
    # instantly which one answered. The tests assert on this exact shape, so
    # changing it means updating tests/test_health.py too.
    return {"status": "ok", "service": "provenance-store"}
