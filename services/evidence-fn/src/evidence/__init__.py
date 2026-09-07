# services/evidence-fn/src/evidence/__init__.py
# =============================================================================
# THE EVIDENCE FUNCTION -- builds the evidence-descriptor half of a provenance
# statement: model_id, model_version, policy_version, confidence, input_ref and
# the config_binding digest (see DESIGN.md).
#
# Unlike the other two services this is a plain library, not a FastAPI app: it is
# called in-process by the controller rather than over HTTP, so there is no
# main.py and no port. Phase 1/4 replace ping() with the real descriptor builder.
#
# The function lives directly in __init__.py only because the package currently
# has a single trivial symbol; real logic should move to its own module and be
# re-exported here.
# =============================================================================


def ping() -> str:
    # Deliberate placeholder. Its only job is to give Phase 0 a real, importable
    # symbol so that the package layout, the sys.path wiring in conftest.py and
    # the CI test run are all exercised end to end before any real code exists.
    # The `-> str` annotation sets the habit of typing every public function,
    # which matters once pydantic models arrive in Phase 1.
    return "ok"
