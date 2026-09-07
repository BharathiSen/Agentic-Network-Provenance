"""The config-binding digest.

The architecture note specifies this digest as

    sha256(model_id + model_version + policy_version + sorted manifest)

Plain concatenation of those parts is ambiguous: ``("ab", "c")`` and
``("a", "bc")`` would concatenate to the same byte string and therefore to
the same digest, so two materially different configurations could share a
binding. For a value whose whole job is to bind a decision to the thing that
produced it, that is a real weakness rather than a theoretical one.

We keep the specified inputs and the specified hash (SHA-256) but serialise
them unambiguously first: a domain-separation tag followed by a canonical
CBOR (RFC 8949 section 4.2) array of the four parts, with the manifest as a
key-sorted array of ``[key, value]`` pairs. Canonical CBOR is deterministic
and length-prefixed, so distinct inputs always produce distinct preimages,
and an independent implementation can reproduce the digest exactly from this
description.

``policy_version`` is optional, and CBOR ``null`` keeps a missing policy
version distinguishable from an empty-string one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

import cbor2

__all__ = ["CONFIG_BINDING_DOMAIN", "compute_config_binding"]

#: Domain-separation tag, so this digest can never collide with a SHA-256
#: computed over some other structure elsewhere in the system.
CONFIG_BINDING_DOMAIN = b"anp-config-binding/v1"


def compute_config_binding(
    model_id: str,
    model_version: str,
    policy_version: str | None,
    manifest: Mapping[str, str],
) -> bytes:
    """Return the raw 32-byte SHA-256 config-binding digest.

    Args:
        model_id: Identifier of the model that produced the decision.
        model_version: Version of that model.
        policy_version: Version of the governing policy, or ``None``.
        manifest: Tool/config manifest as name -> version. Sorted by key
            before hashing, so caller ordering never affects the result.

    Returns:
        The raw digest bytes (not hex, not base64) -- this is what is stored
        in ``EvidenceDescriptor.config_binding``.
    """
    preimage = CONFIG_BINDING_DOMAIN + cbor2.dumps(
        [
            model_id,
            model_version,
            policy_version,
            [[k, manifest[k]] for k in sorted(manifest)],
        ],
        canonical=True,
    )
    return hashlib.sha256(preimage).digest()
