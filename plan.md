Nine phases, bottom-up
Each phase below is a self-contained prompt: paste it into Claude Code in VS Code, let it build and test that phase, review the diff, commit, then move on. The order matters — each phase's tests need the previous phase's code to actually run against.

Python 3.12 · FastAPI
PostgreSQL · SQLAlchemy · Alembic
Redis
pycose + cbor2
Docker Compose
pytest
Node/TS (Phase 7 only)
How to run this
New empty repo, opened in VS Code with Claude Code active. Nothing pre-existing — Phase 0 creates the skeleton.
Paste phases in order, one per Claude Code turn. Phase 0 writes CLAUDE.md and PROGRESS.md; every later prompt tells Claude to read those first, so you never have to re-explain the project.
Don't advance until tests pass. Each prompt ends with a definition of done — hold Claude to it before starting the next phase.
Skim every diff yourself. This code gets cited as your draft's Implementation Status — treat review as part of the phase, not cleanup after it.
Phase 7 is deliberately blindfolded — it must not read the Python source, only the JSON Schema and this plan's prose. That's what makes it count as a second, independent implementation.
Progress
0 / 9
Phase 0
Repo scaffold and project memory
~1 session
Bootstrap: structure, tooling, CLAUDE.md
Done
Nothing here is novel — it's the scaffolding every later phase assumes. The one thing worth getting right is CLAUDE.md: it carries the architecture's vocabulary (origin-class, evidence descriptor, verification claim, freshness) so that every later phase's prompt can stay short.

Produces
Monorepo skeleton, docker-compose, CI, CLAUDE.md, PROGRESS.md
Depends on
Nothing
Paste into Claude Code
Copy
Context. I'm building a prototype for an IETF Internet-Draft: a provenance-and-verification extension for AI-driven network-management actions, extending OPSAWG's draft-ietf-opsawg-yang-provenance-07 (COSE-signed YANG data) and giving a record format to a requirement that draft-zhao-nmop-network-management-agent-05 names but leaves undefined ("simulation and verification before decision-making" for high-impact actions). The system has four roles: an AI Decision Engine (external, out of scope), an Evidence & Verification Function (the one genuinely new component), a Provenance Datastore, and a Network Controller that gates commits on a signed+verified+fresh record. This is a fresh, empty repo.

Do:
1. Create this structure:
   services/provenance-store/   (FastAPI + Postgres + Redis)
   services/evidence-fn/        (Python, decision -> evidence -> sign -> store)
   services/controller/         (FastAPI, gate logic)
   services/verifier-ts/        (empty for now — Phase 7)
   eval/                        (evaluation harness, empty for now)
   docs/                        (empty for now)
2. Root pyproject.toml (uv or poetry, your call) with: fastapi, uvicorn, pydantic>=2, sqlalchemy>=2, alembic, psycopg[binary], redis, pycose, cbor2, httpx, pytest, pytest-asyncio, ruff, black. Pin reasonable current versions.
3. docker-compose.yml with postgres:16 (db `provenance`) and redis:7, healthchecks, and named volumes.
4. A Makefile (or justfile) with targets: up, down, test, lint, fmt.
5. .github/workflows/ci.yml running ruff + pytest on push.
6. Write CLAUDE.md at the repo root containing: a one-paragraph project summary (above), the four-role architecture, and the exact field lists for origin-class (human / deterministic-automation / model-assisted / autonomous-model), evidence-descriptor (model-id, model-version, policy-version, confidence, input-ref, config-binding), verification (performed, method, result, verified-at), and freshness (valid-until, nonce) — this is the shared vocabulary every later phase must match exactly.
7. Write PROGRESS.md listing Phases 0–8 as an unchecked list; check off Phase 0 when this is done.
8. Empty-but-passing test in each service directory (e.g. test_health.py) so `make test` succeeds green on a clean checkout.

Definition of done: `make up` starts Postgres+Redis clean; `make test` and `make lint` both pass; CLAUDE.md and PROGRESS.md exist and read correctly; one commit, message: "scaffold: repo structure, tooling, project memory".
Phase 1
Information model & signing
~1 session
Pydantic schema + COSE sign/verify
Done
This is architecture §4 made real: the augmented provenance record as a typed model, plus the signing mechanism it rides on. Everything downstream — the store, the emitter, the controller, even the independent Phase 7 build — treats this schema as ground truth, so get the field names to match CLAUDE.md exactly.

Produces
Pydantic models, JSON Schema export, COSE sign/verify utils, config-binding digest, freshness helper
Depends on
Phase 0
Paste into Claude Code
Copy
Context. Read CLAUDE.md and PROGRESS.md first. Implement the information model from architecture §4 as a shared Python package (services/provenance-store/app/schema.py or a shared lib both provenance-store and evidence-fn import — your call, but no duplication).

Do:
1. Pydantic v2 models: OriginClass (enum: human, deterministic-automation, model-assisted, autonomous-model — extensible, so back it with a str-based enum, not a closed literal), EvidenceDescriptor (model_id: str, model_version: str, policy_version: str | None, confidence: float in [0,1], input_ref: str, config_binding: bytes), VerificationClaim (performed: bool, method: str | None, result: Literal["pass","fail","not-run"], verified_at: datetime | None), Freshness (valid_until: datetime, nonce: bytes), and the aggregate ProvenanceStatement (subject_ref: str — e.g. an OAM test id, origin_class, evidence: EvidenceDescriptor, verification: VerificationClaim, freshness: Freshness).
2. config_binding is a digest: sha256(model_id + model_version + policy_version + sorted tool/config manifest) — implement compute_config_binding(...) and store the raw digest bytes.
3. Export the schema as JSON Schema (pydantic's .model_json_schema()) to schema/provenance-statement.schema.json at repo root — this file, not the Python source, is what Phase 7 is allowed to read.
4. COSE signing: use pycose + cbor2. CBOR-encode a ProvenanceStatement, wrap in a COSE_Sign1 message (ES256 over a generated Ed25519 or P-256 test key — pick one, document the choice), expose sign_statement(stmt, key) -> bytes and verify_statement(cose_bytes, pubkey) -> ProvenanceStatement | VerificationError.
5. is_fresh(stmt, now, seen_nonces: set) -> bool: false if now > valid_until, false if nonce already in seen_nonces (replay), true and records the nonce otherwise.
6. Tests: schema validation (rejects confidence=1.5, rejects missing config_binding); CBOR round-trip; sign then verify succeeds; flipping one byte of the signed payload makes verify fail; is_fresh correctly rejects an expired record and a replayed nonce.

Definition of done: `make test` green including the tamper-detection and replay tests; schema/provenance-statement.schema.json committed and matches the Pydantic models field-for-field; update PROGRESS.md; commit: "feat: provenance information model and COSE signing".
Phase 2
Provenance store
~1 session
FastAPI + PostgreSQL + Redis
Done
Architecture §3/§6: the write/read paths that stand in for RESTCONF PUT/GET. Records arrive pre-signed from the Evidence & Verification Function (Phase 3) — this service persists, verifies on the way in, and answers freshness questions fast via Redis so the controller's gate check (Phase 4) is cheap.

Produces
FastAPI app, Alembic migration, POST/GET endpoints, Redis-backed freshness cache
Depends on
Phases 0–1
Paste into Claude Code
Copy
Context. Read CLAUDE.md and PROGRESS.md. Build services/provenance-store as a FastAPI app using the Phase 1 schema and signing utilities.

Do:
1. SQLAlchemy model `provenance_statements`: id (uuid pk), subject_ref (indexed str), payload (JSONB — the decoded ProvenanceStatement), cose_signature (bytea), created_at (timestamptz default now). Alembic migration for it.
2. POST /provenance — body is {statement: ProvenanceStatement, cose_signature: base64 bytes}. Verify the signature server-side against a configured trusted public key (env var / mounted file — don't hardcode); on failure return 422 with a clear reason; on success persist and return the record id.
3. GET /provenance/{id} — returns the stored record.
4. GET /provenance?subject_ref=... — most recent record(s) for a subject, newest first.
5. GET /provenance/{id}/fresh — recomputes is_fresh() from Phase 1; cache the nonce-seen-set in Redis (a set keyed e.g. provenance:nonces) so replay detection survives restarts and works across multiple controller instances; cache the valid-until check with a short TTL to avoid hammering Postgres on repeated gate checks.
6. Structured JSON logging on every write (subject_ref, origin_class, verification.result) — this is what the evaluation harness in Phase 6 will read.
7. Tests (httpx.AsyncClient against a test Postgres — use a docker-compose test profile or testcontainers, your call, but it must be real Postgres, not sqlite, since JSONB semantics matter): valid signed record accepted; tampered signature rejected 422; fresh vs expired vs replayed-nonce all correctly reported by /fresh; querying by subject_ref returns newest first.

Definition of done: `make up && make test` green with a real Postgres+Redis; OpenAPI docs render at /docs; update PROGRESS.md; commit: "feat: provenance store service".
Phase 3
Evidence & verification function
~1–2 sessions
Decision → evidence → (optional) verify → sign → store
Done
The one new role in the architecture (§3, the accent-colored box). Your real ERNET adaptive-OAM agent isn't in this repo, so this phase builds a pluggable interface plus a clearly-labeled mock decision engine — swap the mock for the real agent later without touching anything downstream.

Produces
DecisionEngine protocol, mock implementation, evidence builder, verifier, CLI runner
Depends on
Phases 0–2
Paste into Claude Code
Copy
Context. Read CLAUDE.md and PROGRESS.md. Build services/evidence-fn. This stands in for the ERNET adaptive OAM test-selection agent, which is not in this repo — build to an interface so the mock can be swapped for the real one later.

Do:
1. Protocol DecisionEngine with propose_next_test(context: dict) -> Decision, where Decision has: model_id, model_version, confidence, chosen_test (one of a small fixed set: "loopback", "delay-measurement", "path-trace", "connectivity-check"), input_ref, impact_class ("low" | "high" — "high" for anything that would change live state, "low" for a pure read/diagnostic).
2. MockDecisionEngine: picks a test via a simple weighted-random rule over the four types, generates a plausible confidence, tags impact_class "high" for path-trace/connectivity-check and "low" otherwise. Docstring stating clearly this is a stand-in for the real agent.
3. build_evidence_descriptor(decision) -> EvidenceDescriptor (Phase 1 type), computing config_binding via Phase 1's helper.
4. Verifier interface with a Verifier.check(decision, evidence) -> VerificationClaim. Implement one concrete verifier: DryRunSimulationVerifier — for impact_class=="high", run a stubbed policy/topology dry-run (a small mock topology + a rule like "reject if chosen_test would touch >N devices"; can be entirely synthetic) and set performed=True, method="dry-run-simulation", result accordingly. For impact_class=="low", performed=False, result="not-run" (explicitly: low-impact decisions are not required to be verified — document why in a comment, referencing architecture §5 step 2).
5. Freshness: set valid_until = now + a configurable TTL (default 5 minutes — short, because these are live operational decisions), generate a fresh random nonce per decision.
6. Wire it together: sign via Phase 1, POST to the Phase 2 store via httpx.
7. CLI: `python -m evidence_fn.run --scenario normal|stale|tamper --n 1`. "normal" runs one clean decision through the full pipeline. "stale" signs a record, waits (or fakes clock skew), and re-submits it after a model_version bump in a small in-memory fake registry — used by Phase 5. "tamper" flips a byte in the payload before submission — also used by Phase 5.
8. Tests: MockDecisionEngine always returns a valid Decision; DryRunSimulationVerifier.performed is True only for high-impact; end-to-end test posting one normal-scenario decision to a running store returns 200.

Definition of done: `python -m evidence_fn.run --scenario normal` succeeds against `make up`; unit tests green; update PROGRESS.md; commit: "feat: evidence and verification function with mock decision engine".
Phase 4
Network controller stub
~1 session
Gate logic: signed ∧ verified ∧ fresh
Done
Architecture §5, steps 4–6. This is deliberately dumb: it does not decide policy, it only checks that the required record exists and clears the three-part gate before letting a commit through — the whole point of the design is that this logic doesn't need to know anything about AI.

Produces
FastAPI controller, gate function, in-repo audit log
Depends on
Phases 0–2
Paste into Claude Code
Copy
Context. Read CLAUDE.md and PROGRESS.md. Build services/controller.

Do:
1. POST /actions/{subject_ref}/evaluate — fetches the most recent provenance record for subject_ref from the Phase 2 store, applies check_gate(record) -> GateResult{allow: bool, reason: str}:
   - no record found -> deny, reason "no-provenance-record"
   - signature invalid (store already checks on write, but re-verify here defensively) -> deny, "signature-invalid"
   - impact_class == "high" and verification.performed == False -> deny, "unverified-high-impact-action"
   - impact_class == "high" and verification.result != "pass" -> deny, "verification-failed"
   - not is_fresh(record) -> deny, "stale-or-replayed"
   - else -> allow
2. Persist every evaluation (subject_ref, decision, reason, timestamp) to a small audit table or JSONL log — this feeds Phase 6.
3. GET /audit — lists recent evaluations, newest first.
4. Tests covering every branch of check_gate above with constructed fixture records (valid, missing, tampered, unverified-high-impact, expired, replayed) — one test per branch, named for the reason string it expects.

Definition of done: every check_gate branch has a passing test with an explicit fixture; `make test` green; update PROGRESS.md; commit: "feat: network controller gate logic".
Phase 5
End-to-end demo & adversarial scenarios
~1 session
Wire it together, script the three scenarios
Done
This is the moment the prototype actually demonstrates the gap from the brief: a plain COSE signature can't catch a stale or forged decision, and this system can. The three scenarios map directly to Fig. 1/Fig. 2 in the architecture note and to the "why AI is necessary" argument in the draft.

Produces
Full docker-compose wiring, demo/run_scenarios.py, a readable console/markdown report
Depends on
Phases 0–4
Paste into Claude Code
Copy
Context. Read CLAUDE.md and PROGRESS.md. All four services exist; wire them into one docker-compose stack and script the demo.

Do:
1. Extend docker-compose.yml with provenance-store, controller, and evidence-fn (as a one-shot runner, not a long-lived service) alongside db/redis. `make demo-up` should bring up store+controller and leave evidence-fn runnable on demand.
2. demo/run_scenarios.py, three scenarios, each producing a clear PASS/FAIL against an expected outcome:
   - "happy path": evidence-fn --scenario normal -> controller /evaluate -> expect allow.
   - "stale replay": evidence-fn --scenario stale (signs against an old model_version, replays after a version bump in the fake registry) -> controller /evaluate -> expect deny, reason stale-or-replayed (or a config-binding mismatch if you've wired that check in — either is correct, pick one and document it).
   - "tampered": evidence-fn --scenario tamper -> controller /evaluate -> expect deny, reason signature-invalid.
3. Console output: a small table, one row per scenario, columns scenario / expected / actual / pass-fail. Also write demo/RESULTS.md with the same table in markdown — this is what gets pasted into the draft's examples section.
4. README.md at repo root: what this is (one paragraph, link back to the architecture note's role names), `make up && make demo-up && python demo/run_scenarios.py` as the quickstart, and a short "what to read if you're reviewing this for the I-D" pointer to schema/provenance-statement.schema.json and demo/RESULTS.md.

Definition of done: `python demo/run_scenarios.py` runs all three scenarios against a fresh `make demo-up` and all three PASS against their expected outcome; demo/RESULTS.md committed; update PROGRESS.md; commit: "feat: end-to-end demo with adversarial scenarios".
Phase 6
Evaluation harness
~1 session
The numbers the draft can cite
Done
Three numbers, not a research paper: how often the gate catches a bad record, what it costs an operator who used to trust any signature, and how much latency the check adds. Keep the methodology simple and reproducible — a reviewer should be able to rerun it and get the same numbers.

Produces
Synthetic-load generator, metrics script, CSV + one chart, a results markdown table
Depends on
Phases 0–5
Paste into Claude Code
Copy
Context. Read CLAUDE.md and PROGRESS.md. Build eval/.

Do:
1. eval/generate_load.py — generates N synthetic decisions (default N=200, seeded for reproducibility) with a configurable mix: p_normal, p_stale, p_tampered (defaults 0.85 / 0.10 / 0.05). Runs each through evidence-fn -> controller /evaluate, records the outcome and wall-clock time for the evidence+verify+sign+gate path.
2. eval/metrics.py computing, from the recorded run: detection_rate = correctly-denied stale+tampered / all stale+tampered; false_reject_rate = normal records incorrectly denied / all normal; latency p50/p95/p99 in ms for the full decision-to-gate-result path.
3. A second computed comparison: "naive baseline" = a policy that allows anything with a merely-valid signature (ignoring verification/freshness) — compute what fraction of the injected stale+tampered records that baseline would have wrongly allowed, versus this system's detection_rate. This is the override/trust-rate delta the draft cites.
4. Output: eval/results.csv (raw per-decision rows), a single matplotlib chart (bar: detection rate, this system vs. naive baseline, for stale and tampered separately) saved to eval/results.png, and eval/RESULTS.md with a markdown table of all the numbers above.
5. Tests: metrics functions return values in [0,1]; a hand-constructed fixture run (a few known outcomes) produces the exact expected detection_rate.

Definition of done: `python eval/generate_load.py && python eval/metrics.py` reproducibly regenerates eval/results.csv, eval/results.png, eval/RESULTS.md against a fresh `make demo-up`; update PROGRESS.md; commit: "feat: evaluation harness and baseline comparison".
Phase 7
Independent second implementation
~1 session
Node/TS verifier, spec-only
Done
RFC 7942 Implementation Status wants two independent implementations, and "independent" is the operative word — if this reads the Python source, it isn't one. Give Claude Code only the JSON Schema and the prose spec below; if it tries to open services/, stop it.

Produces
services/verifier-ts — a standalone CLI, fixtures, tests
Depends on
Phase 1's schema file only (not its code)
Before you paste this one: tell Claude Code explicitly not to open services/provenance-store, services/evidence-fn, or services/controller for this phase. The prompt says so too, but it's worth restating in the chat — this is the one instruction in the whole plan that actually matters more than the code it produces.
Paste into Claude Code
Copy
Context. This is a deliberately independent build. Do NOT read services/provenance-store, services/evidence-fn, or services/controller — not even to "check conventions." Read only: schema/provenance-statement.schema.json, and this spec:

A provenance record is a CBOR-encoded object matching that JSON Schema, wrapped in a COSE_Sign1 structure (see RFC 9052) and signed with ES256 over a P-256 key. A record is ALLOW if: (a) the COSE signature verifies against a provided public key, (b) if the record's evidence implies a high-impact action, verification.performed is true and verification.result is "pass", and (c) freshness.valid_until is in the future AND freshness.nonce has not been seen before in this process's lifetime (an in-memory set is fine for this CLI). Otherwise REJECT, with a specific reason string.

Do:
1. New Node/TypeScript project in services/verifier-ts (npm init, tsconfig, a COSE library such as @auth0/cose or cose-js — pick one that supports COSE_Sign1/ES256 verification, document the choice in a short README in that folder).
2. bin/verify-record.ts — CLI: `verify-record --key public.pem --record record.cbor`, prints ALLOW or REJECT plus the reason, exits 0 on ALLOW / 1 on REJECT.
3. fixtures/ — at least: valid.cbor (should ALLOW), expired.cbor (freshness in the past), tampered.cbor (signature won't verify), unverified-high-impact.cbor (high-impact, verification.performed=false). Generate these fixtures however is convenient for a standalone TS project (a small script using the same COSE library, signing with a locally-generated throwaway key committed alongside its public counterpart for reproducibility) — do not import anything from the Python services to produce them.
4. vitest or jest tests asserting the correct verdict + reason string for every fixture.
5. services/verifier-ts/README.md stating explicitly: "built independently from schema/provenance-statement.schema.json and the architecture note's prose only, without reference to the Python implementation" — this sentence is going in the draft's Implementation Status section verbatim-ish, so make it true.

Definition of done: `npm test` green in services/verifier-ts; verify-record correctly classifies all four fixtures from the CLI; update PROGRESS.md; commit: "feat: independent TypeScript verifier (RFC 7942 second implementation)".
Phase 8
Docs & draft mapping
~0.5 session
Close the loop back to the Internet-Draft
Done
The last phase produces nothing new technically — it produces the artifact you actually hand to your mentor and cite in the draft's Implementation Status section.

Produces
MAPPING.md, polished top-level README, OpenAPI export
Depends on
Phases 0–7
Paste into Claude Code
Copy
Context. Read CLAUDE.md and PROGRESS.md. All eight prior phases are complete. This phase is documentation only — no behavior changes.

Do:
1. MAPPING.md — a table with columns: Draft section (Origin-class registry / Evidence descriptor / Verification claim / Freshness binding / Gate procedure) | Architecture note section (§4.1, §4.1, §4.1, §4.1, §5) | Code location (file:line-ish, or module path) | Test(s) that cover it. This is what turns into your I-D's Implementation Status section.
2. Export each FastAPI service's OpenAPI schema to docs/openapi/*.json (they self-generate at /openapi.json — just fetch and commit them from a running `make up`).
3. Polish the root README: one-paragraph summary, architecture diagram reference (link to the published architecture note if you have the URL, otherwise describe the four roles in one line each), full quickstart (`make up`, `make demo-up`, `python demo/run_scenarios.py`, `python eval/generate_load.py && python eval/metrics.py`), and a "two implementations" callout linking to Phase 7's verifier-ts README.
4. Do not modify any service code in this phase — if a test is failing, stop and flag it rather than fixing it here.

Definition of done: MAPPING.md complete and accurate against the actual code; docs/openapi/ populated; README reads clean top to bottom for someone who has never seen this repo; update PROGRESS.md (all 9 phases checked); commit: "docs: implementation-to-draft mapping and polished README".
§
Where each phase lands in the draft
Phase	Internet-Draft section it feeds
1 — Information model	§ YANG module (augment statements), § IANA Considerations (origin-class registry)
2–4 — Store, evidence-fn, controller	§ Architecture, § Procedure / verification workflow
5 — Demo scenarios	§ Examples (or an appendix) — the three scenarios make good worked examples
6 — Evaluation harness	§ Motivation (cite detection-rate delta vs. naive baseline)
7 — Independent verifier	§ Implementation Status (RFC 7942)
8 — Docs & mapping	Working reference for you and your mentor, not draft text 