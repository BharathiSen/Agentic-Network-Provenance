# services/controller/src/ctrl/__init__.py
# =============================================================================
# Package marker for the `ctrl` package (the Network Controller service).
#
# Named `ctrl` rather than `controller` because the directory
# services/controller/ already carries that word -- the import then reads
# `from ctrl.main import app`, not `controller.controller.main`.
#
# Kept empty on purpose so that importing the package has no side effects.
# Phase 3 adds the OAM test-selection logic as sibling modules.
# =============================================================================
