# Agentic OAM Provenance — Implementation Plan

Prototype for the provenance-and-verification extension described in the
architecture note (extends `draft-ietf-opsawg-yang-provenance-07`; gives a
record format to the verification requirement named in
`draft-zhao-nmop-network-management-agent-05`).

Nine phases, strictly bottom-up — each phase's tests need the previous
phase's code to run against, so build and verify in order.

Stack: Python 3.12 · FastAPI · PostgreSQL (SQLAlchemy + Alembic) · Redis ·
pycose + cbor2 · Docker Compose · pytest · Node/TypeScript (Phase 7 only).

---

## Phase 0 — Repo scaffold and project memory

**Depends on:** nothing
**Produces:** monorepo skeleton, tooling, `CLAUDE.md`, `PROGRESS.md`

1. Create the directory structure:
   - `services/provenance-store/` (FastAPI + Postgres + Redis)
   - `services/evidence-fn/` (decision → evidence → sign → store)
   - `services/controller/` (FastAPI, gate logic)
   - `services/verifier-ts/` (empty until Phase 7)
   - `eval/` (empty until Phase 6)
   - `docs/` (empty until Phase 8)
2. Root `pyproject.toml` with: fastapi, uvicorn, pydantic ≥2, sqlalchemy ≥2,
   alembic, psycopg[binary], redis, pycose, cbor2, httpx, pytest,
   pytest-asyncio, ruff, black.
3. `docker-compose.yml`: postgres:16 (db `provenance`), redis:7, healthchecks,
   named volumes.
4. `Makefile` with targets: `up`, `down`, `test`, `lint`, `fmt`.
5. `.github/workflows/ci.yml` running ruff + pytest on push.
6. `CLAUDE.md` — project summary, the four-role architecture, and the exact
   field lists for origin-class, evidence-descriptor, verification, and
   freshness (see Phase 1) — the shared vocabulary every later phase matches.
7. `PROGRESS.md` — Phases 0–8 as a checklist.
8. A trivial passing test in each service directory so `make test` is green
   on a clean checkout.

**Definition of done:** `make up` starts Postgres+Redis clean; `make test`
and `make lint` pass; `CLAUDE.md` and `PROGRESS.md` exist; one commit.

---

## Phase 1 — Information model & signing

**Depends on:** Phase 0
**Produces:** Pydantic models, JSON Schema export, COSE sign/verify utilities,
config-binding digest, freshness helper

1. Define enums/models:
   - `OriginClass` — human / deterministic-automation / model-assisted /
     autonomous-model (open enum, extensible).
   - `EvidenceDescriptor` — model_id, model_version, policy_version,
     confidence (0–1), input_ref, config_binding (bytes).
   - `VerificationClaim` — performed (bool), method, result
     (pass / fail / not-run), verified_at.
   - `Freshness` — valid_until, nonce.
   - `ProvenanceStatement` — subject_ref, origin_class, evidence,
     verification, freshness.
2. Implement `compute_config_binding(...)` — a digest (e.g. SHA-256) over
   model_id + model_version + policy_version + a sorted tool/config manifest.
3. Export the schema as JSON Schema to
   `schema/provenance-statement.schema.json` — this file, not the Python
   source, is what Phase 7 is allowed to read.
4. Implement COSE signing with pycose + cbor2: CBOR-encode a
   `ProvenanceStatement`, wrap in COSE_Sign1 (ES256, document the key
   choice), expose `sign_statement()` and `verify_statement()`.
5. Implement `is_fresh(statement, now, seen_nonces)` — false if expired,
   false if the nonce has been seen before (replay), true otherwise.
6. Tests: schema validation rejects out-of-range values; CBOR round-trip;
   sign→verify succeeds; a single flipped byte breaks verification;
   `is_fresh` correctly rejects expired and replayed records.

**Definition of done:** tests green including tamper-detection and replay
cases; the JSON Schema file matches the Pydantic models field-for-field.

---

## Phase 2 — Provenance store

**Depends on:** Phases 0–1
**Produces:** FastAPI app, Alembic migration, write/read endpoints,
Redis-backed freshness cache

1. SQLAlchemy model `provenance_statements` (id, subject_ref indexed,
   payload JSONB, cose_signature, created_at) + Alembic migration.
2. `POST /provenance` — accepts a pre-signed record, verifies the signature
   server-side against a configured trusted key, persists on success,
   returns 422 with a clear reason on failure.
3. `GET /provenance/{id}` — returns a stored record.
4. `GET /provenance?subject_ref=...` — most recent records for a subject,
   newest first.
5. `GET /provenance/{id}/fresh` — recomputes freshness; cache the
   nonce-seen-set in Redis so replay detection survives restarts and works
   across multiple instances; short-TTL cache for the valid-until check.
6. Structured logging on every write (subject_ref, origin_class,
   verification.result) for the Phase 6 evaluation harness.
7. Tests against a real Postgres+Redis: valid record accepted; tampered
   signature rejected; fresh / expired / replayed all correctly reported;
   subject_ref query returns newest first.

**Definition of done:** `make up && make test` green against real
Postgres+Redis; OpenAPI docs render at `/docs`.

---

## Phase 3 — Evidence & verification function

**Depends on:** Phases 0–2
**Produces:** `DecisionEngine` interface, mock implementation, evidence
builder, verifier, CLI runner

1. Define a `DecisionEngine` interface: `propose_next_test(context) →
   Decision` where `Decision` carries model_id, model_version, confidence,
   chosen_test, input_ref, impact_class (low/high).
2. Implement `MockDecisionEngine` — a clearly-labeled stand-in for the real
   ERNET adaptive-OAM agent (weighted-random choice over a small set of OAM
   test types; "high" impact for anything that changes live state).
3. Implement `build_evidence_descriptor(decision)`, computing the
   config-binding digest via Phase 1.
4. Define a `Verifier` interface and implement
   `DryRunSimulationVerifier` — runs a stubbed policy/topology check for
   high-impact decisions and records the outcome; low-impact decisions are
   not required to be verified (performed=False, result=not-run).
5. Set freshness: a short validity window (e.g. 5 minutes) and a fresh
   random nonce per decision.
6. Wire together: sign (Phase 1) → POST to the store (Phase 2).
7. CLI: `run --scenario normal|stale|tamper` — normal runs one clean
   decision end-to-end; stale signs against an old model_version and
   replays after a version bump; tamper flips a byte before submission.
8. Tests: mock engine always returns a valid decision; verifier only
   performs checks for high-impact decisions; one end-to-end test against a
   running store.

**Definition of done:** the normal scenario succeeds against `make up`;
unit tests green.

---

## Phase 4 — Network controller stub

**Depends on:** Phases 0–2
**Produces:** FastAPI controller, gate function, audit log

1. `POST /actions/{subject_ref}/evaluate` — fetches the most recent
   provenance record and applies the gate:
   - no record → deny (`no-provenance-record`)
   - signature invalid → deny (`signature-invalid`)
   - high-impact and verification not performed → deny
     (`unverified-high-impact-action`)
   - high-impact and verification result ≠ pass → deny
     (`verification-failed`)
   - not fresh → deny (`stale-or-replayed`)
   - otherwise → allow
2. Persist every evaluation (subject_ref, decision, reason, timestamp) to
   an audit table or log — feeds Phase 6.
3. `GET /audit` — recent evaluations, newest first.
4. Tests: one per gate branch above, each with a constructed fixture record.

**Definition of done:** every gate branch has an explicit passing test.

---

## Phase 5 — End-to-end demo & adversarial scenarios

**Depends on:** Phases 0–4
**Produces:** full docker-compose wiring, `demo/run_scenarios.py`,
`demo/RESULTS.md`

1. Extend `docker-compose.yml` to bring up store + controller together;
   evidence-fn runs on demand.
2. `demo/run_scenarios.py` — three scenarios, each with an expected
   outcome:
   - happy path → allow
   - stale replay → deny (`stale-or-replayed`, or a config-binding
     mismatch — pick one and document it)
   - tampered record → deny (`signature-invalid`)
3. Console output as a scenario / expected / actual / pass-fail table;
   mirror it in `demo/RESULTS.md`.
4. Root `README.md`: what this is, quickstart commands, and a pointer to
   `schema/provenance-statement.schema.json` and `demo/RESULTS.md` for
   anyone reviewing it against the draft.

**Definition of done:** all three scenarios pass against a fresh
`make demo-up`.

---

## Phase 6 — Evaluation harness

**Depends on:** Phases 0–5
**Produces:** synthetic-load generator, metrics script, CSV + chart,
results table

1. `eval/generate_load.py` — N synthetic decisions (seeded, reproducible),
   configurable mix of normal / stale / tampered (default 85/10/5); records
   outcome and latency for the full decision-to-gate path.
2. `eval/metrics.py` — detection rate (correctly-denied bad records),
   false-reject rate (normal records wrongly denied), latency p50/p95/p99.
3. A naive-baseline comparison: a policy that trusts any validly-signed
   record regardless of verification/freshness — compute what fraction of
   injected bad records it would have wrongly allowed, versus this
   system's detection rate.
4. Output `eval/results.csv`, one chart (`eval/results.png`: detection
   rate, this system vs. naive baseline), and `eval/RESULTS.md`.
5. Tests: metrics bounded in [0,1]; a hand-built fixture run produces the
   exact expected detection rate.

**Definition of done:** the load generator and metrics script reproducibly
regenerate the CSV, chart, and results table against a fresh `make demo-up`.

---

## Phase 7 — Independent second implementation

**Depends on:** Phase 1's schema file only — **not** its code
**Produces:** `services/verifier-ts` — standalone CLI, fixtures, tests

> Build this without opening `services/provenance-store`,
> `services/evidence-fn`, or `services/controller`. The point is a genuinely
> independent second implementation for the draft's Implementation Status
> section (RFC 7942) — reading the Python source defeats that.

1. New Node/TypeScript project in `services/verifier-ts` with a COSE
   library supporting COSE_Sign1/ES256 verification.
2. `verify-record` CLI: takes a public key and a CBOR record, prints
   ALLOW/REJECT plus a reason, exits 0/1 accordingly.
3. Fixtures: valid, expired, tampered, unverified-high-impact — generated
   with the same COSE library and a throwaway key committed for
   reproducibility, without importing anything from the Python services.
4. Tests asserting the correct verdict and reason for every fixture.
5. A short README in that folder stating it was built from the JSON Schema
   and architecture prose only.

**Definition of done:** `verify-record` correctly classifies all four
fixtures; tests green.

---

## Phase 8 — Docs & draft mapping

**Depends on:** Phases 0–7
**Produces:** `MAPPING.md`, polished root README, exported OpenAPI schemas

1. `MAPPING.md` — table of draft section → architecture-note section →
   code location → covering test(s). This becomes the basis for the
   Implementation Status section of the draft.
2. Export each service's OpenAPI schema to `docs/openapi/*.json`.
3. Polish the root README: summary, architecture reference, full
   quickstart, and a "two implementations" callout linking to Phase 7.
4. Documentation only — no behavior changes in this phase.

**Definition of done:** `MAPPING.md` is accurate against the actual code;
the README reads cleanly for someone who has never seen the repo; all nine
phases checked off in `PROGRESS.md`.

---

## Where each phase lands in the draft

| Phase | Feeds |
|---|---|
| 1 — Information model | YANG module (augment statements); IANA Considerations (origin-class registry) |
| 2–4 — Store, evidence-fn, controller | Architecture section; verification procedure |
| 5 — Demo scenarios | Examples / appendix |
| 6 — Evaluation harness | Motivation (detection-rate delta vs. naive baseline) |
| 7 — Independent verifier | Implementation Status (RFC 7942) |
| 8 — Docs & mapping | Working reference, not draft text directly |
