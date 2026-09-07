# DESIGN.md — shared vocabulary

## origin-class
One of: `human` | `deterministic-automation` | `model-assisted` | `autonomous-model`

## evidence-descriptor
- model_id
- model_version
- policy_version
- confidence — float, 0 to 1
- input_ref
- config_binding — digest (bytes)

## verification
- performed — bool
- method
- result — pass | fail | not-run
- verified_at — timestamp

## freshness
- valid_until — timestamp
- nonce — bytes

## provenance-statement (aggregate)
subject_ref, origin_class, evidence, verification, freshness

Full Pydantic types, JSON Schema export, and signing land in Phase 1.