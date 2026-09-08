# Agentic Network Provenance

This prototype defines a provenance-and-verification extension for AI-driven network-management actions, extending OPSAWG's `draft-ietf-opsawg-yang-provenance-07` (COSE-signed YANG data) and giving a record format to the requirement that `draft-zhao-nmop-network-management-agent-05` names but leaves undefined: simulation and verification before decision-making for high-impact actions. The AI Decision Engine is external and out of scope; this repository focuses on producing, storing, and enforcing signed provenance records.

## Architecture

The system has four roles:

- **AI Decision Engine**: external and out of scope; proposes a network-management action.
- **Evidence & Verification Function**: turns a decision into evidence, performs verification when required, signs the provenance record, and submits it to the store.
- **Provenance Datastore**: persists signed records and serves freshness and retrieval checks.
- **Network Controller**: gates commits on a record that is signed, verified, and fresh.

## Shared Vocabulary

These field lists are normative for later phases and must match exactly.

- **origin-class**: `human`, `deterministic-automation`, `model-assisted`, `autonomous-model`
- **evidence-descriptor**: `model-id`, `model-version`, `policy-version`, `confidence`, `input-ref`, `config-binding`
- **verification**: `performed`, `method`, `result`, `verified-at`
- **freshness**: `valid-until`, `nonce`

The wire format spells these in snake_case (`model_id`, `config_binding`,
`valid_until`); the kebab-case names above are the YANG/Internet-Draft
spelling. `schema/provenance-statement.schema.json` records the mapping.

## Where things live

- `services/shared/src/provlib/` — the information model, config binding, COSE
  signing, and freshness logic. Imported by every other service; there is no
  second copy of the record format anywhere.
- `schema/provenance-statement.schema.json` — generated from the Pydantic
  models by `scripts/export_schema.py`. This file, not the Python source, is
  what Phase 7's independent verifier is allowed to read. A test fails if it
  drifts from the models.

## Pinning note

`cbor2` is capped below 6.0 in `pyproject.toml`. cbor2 6.x returns a tuple
where pycose 1.1.0 expects a list, which makes every signature verification
fail. Do not relax that bound without re-running the signing tests.
