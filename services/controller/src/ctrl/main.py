# services/controller/src/ctrl/main.py
# =============================================================================
# THE NETWORK CONTROLLER -- the component that decides which OAM tests to run.
#
# This is the service whose decisions need provenance: in later phases it is the
# thing that consults a model, picks a set of tests, and must then emit a signed
# statement saying who/what made that call (origin-class), on what evidence, and
# how long the claim stays fresh. See DESIGN.md for that vocabulary.
#
# Phase 0 scope: a health endpoint only, mirroring the Provenance Store stub.
#
# RUN IT BY HAND (PowerShell):
#   uv run uvicorn --app-dir services/controller/src ctrl.main:app --port 8002 --reload
# =============================================================================

from fastapi import FastAPI  # ASGI framework; routing + JSON serialisation + OpenAPI

# Module-level ASGI app. The uvicorn target "ctrl.main:app" resolves to this
# object. Note the port convention used across the project: provenance-store on
# 8001, controller on 8002 -- so both can run side by side during development.
app = FastAPI(title="Network Controller")


@app.get("/health")
def health():
    # Same liveness-probe contract as the Provenance Store, differing only in the
    # `service` value. Keeping the shape identical across services means one
    # smoke-test helper can check them all in Phase 6.
    return {"status": "ok", "service": "controller"}
