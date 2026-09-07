# DESIGN.md — shared vocabulary

> **Status: Phase 0.** This file fixes the *names and meanings* every later phase
> assumes. It is deliberately not code. The full Pydantic types, the JSON Schema
> export, and COSE signing all land in **Phase 1** — when they do, they must match
> the field names below exactly, because the Phase 7 TypeScript verifier
> re-implements this vocabulary independently and the two have to agree on the
> wire format.

## Why this exists

A network controller that uses a model to choose which OAM tests to run creates a
question that a log line cannot answer: *who or what actually made this decision,
on what basis, and should I still trust it now?* A **provenance statement** is the
signed, structured answer. The four blocks below are its parts.

---

## origin-class

**What kind of agent produced the decision.** Exactly one of:

| Value | Meaning |
|---|---|
| `human` | A person decided, directly. |
| `deterministic-automation` | A fixed rule or script — same input always gives the same output, no model involved. |
| `model-assisted` | A model proposed, a human approved. Accountability stays with the human. |
| `autonomous-model` | A model decided and acted with no human in the loop. |

This is the field that carries the most weight for an auditor, which is why it is
a closed enum and not free text: it must be impossible to write
`"mostly automated"` and leave the reader guessing.

## evidence-descriptor

**What the decision was based on.** Enough to reproduce or challenge it.

| Field | Type | Meaning |
|---|---|---|
| `model_id` | str | Which model. Identity, not version. |
| `model_version` | str | Which build of it — two versions of one model are two different decision-makers. |
| `policy_version` | str | Which governing policy was in force. |
| `confidence` | float, `0.0`–`1.0` | The model's own reported confidence. |
| `input_ref` | str | Reference to the inputs, so the decision can be replayed. |
| `config_binding` | bytes (digest) | Digest of the effective configuration, binding the statement to the exact config in force. A digest rather than the config itself: small, and it does not leak topology. |

## verification

**Whether anyone independently checked the decision** — separate from whether the
decision was *made* well.

| Field | Type | Meaning |
|---|---|---|
| `performed` | bool | Was a check attempted at all? |
| `method` | str | How it was checked. |
| `result` | `pass` \| `fail` \| `not-run` | Outcome. |
| `verified_at` | timestamp | When. |

`performed` and `result` are intentionally distinct: `performed=false` (nobody
looked) is a different claim from `result="fail"` (someone looked and it was
wrong). Collapsing them would hide the difference.

## freshness

**How long the statement may be trusted**, so an old signed claim cannot be
replayed as though it were current.

| Field | Type | Meaning |
|---|---|---|
| `valid_until` | timestamp | After this instant, treat the statement as stale. |
| `nonce` | bytes | Single-use value making each statement unique, defeating replay. |

Redis (see `docker-compose.yml`) is the intended home for nonce tracking.

## provenance-statement (aggregate)

The signed object that ties it together:

```
subject_ref     — what this statement is about
origin_class    — one of the four values above
evidence        — an evidence-descriptor
verification    — a verification block
freshness       — a freshness block
```

`subject_ref` points at the thing being described (the OAM test-selection
decision); everything else answers *who decided*, *on what*, *checked by whom*,
and *for how long*.

---

## What Phase 1 adds

Pydantic v2 models for each block, a JSON Schema exported from them, and
`COSE_Sign1` signing over a CBOR encoding (hence `pycose` + `cbor2` in
`pyproject.toml`). CBOR rather than JSON because COSE is defined over CBOR and
the encoding must be deterministic for a signature to be reproducible.
