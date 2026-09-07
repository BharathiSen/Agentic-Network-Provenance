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