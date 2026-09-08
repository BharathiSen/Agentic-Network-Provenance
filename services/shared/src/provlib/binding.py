"""
config_binding: a digest over the exact configuration that produced a
decision, so a signed record becomes invalid the moment that configuration
changes (model swap, policy update, tool-set change).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping


def compute_config_binding(
    model_id: str,
    model_version: str,
    policy_version: str | None,
    tool_manifest: Mapping[str, str] | None = None,
) -> bytes:
    canonical = json.dumps(
        {
            "model_id": model_id,
            "model_version": model_version,
            "policy_version": policy_version,
            "tool_manifest": dict(tool_manifest or {}),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).digest()
