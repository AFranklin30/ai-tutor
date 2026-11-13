# Approved decisions

Record important human-approved architectural/product decisions only. A proposal or TODO is not approved. Trivial implementation choices do not belong here.

## WF-001 — Engineering workflow bootstrap

- Date: 2026-10-02 (America/Chicago)
- Status: APPROVED
- Decision: Establish root AGENTS.md, eight source-of-truth docs, and five repository-local skills before application implementation.
- Context/problem: Engineering workflow, decision authority, drift control, and handoffs must precede features.
- Options considered: The human specified this structure; no alternative was selected by Codex.
- Rationale: Contract-first implementation, explicit human decision boundaries, scoped skills, and concise handoffs.
- Consequences/tradeoffs: Workflow scaffolding is available; unresolved product contracts still block dependent implementation. Drift checks are procedural until approved tooling exists.
- Approval evidence: Human task “Bootstrap the Codex Engineering Workflow,” sections 2–15, explicitly instructing creation of this workflow and forbidding application implementation.

## Step 4 approval evidence

Date: 2026-10-04 (America/Chicago). Status: APPROVED for decisions below.

Approval source: the human request “Synchronize the AI Tutor repository documentation to complete the approved Step 4 API contract decisions,” containing 25 numbered approved decisions and explicit documentation-only scope. Prior human messages identify requirements.md, architecture.md, and schema.md as approved MVP v1 contracts. This log records approval; it does not invent prior approval dates or additional product choices.

## BASE-001 — Existing MVP contract baseline

- Date recorded: 2026-10-04; original approval dates are not asserted here.
- Status: APPROVED, from the prior explicit human approvals and reaffirmed synchronization request.
- Decision: Grade 7 Mathematics MVP, modular monolith, Python/FastAPI/Pydantic, PostgreSQL/SQLAlchemy/Alembic/pgvector, pytest, OpenTelemetry, one tutor orchestrator, thin model adapter, standalone identity, curated one-unit corpus, synthetic/demo operation, local development.
- Context: Existing approved contracts must not be treated as unapproved scaffolds.
- Options considered: Human-selected baseline; no new comparison or selection made during synchronization.
- Rationale: Preserve approved scope and simple, contract-governed architecture.
- Consequences: No infrastructure/model/provider expansion is implied; exact curriculum, model, and cloud choices remain deferred.
- Contracts: requirements.md; architecture.md §§1–2; schema.md §§1–2.

## STEP4-001 — Durable messages, replay, and processing ownership

- Date: 2026-10-04.
- Status: APPROVED.
- Context/problem: Failures and retries must not lose input or multiply side effects.
- Options considered: The human supplied the approved behavior in decisions 1–12, 23; alternatives were not selected during synchronization.
- Decision/rationale: Persist input before AI processing and output before return; correlate student/tutor messages; current-state replay with scoped keys and changed-payload 409; explicit retry is separate; single processing ownership and nonduplicated durable effects. Initial successful creation is 201; required dependency terminal failure is student-safe 503. SLICE1-004 subsequently clarifies that successful idempotent replay of stored FAILED is 200; 503 applies when genuine unavailability prevents fulfillment of the current request.
- Consequences/tradeoffs: Preserve immutable content/attempt/evidence history while processing metadata evolves. Physical concurrency and storage mechanisms remain deferred.
- Approval evidence: Step 4 human synchronization request, numbered decisions 1–12, 23.
- Affected contracts: api-contract.md §§1–7; schema.md §§11–12, 14, 20–22; architecture.md §31; ai-runtime.md.

## STEP4-002 — Session lifecycle and atomic replacement

- Date: 2026-10-04.
- Status: APPROVED.
- Context/problem: Closure must preserve history and avoid a failed replacement leaving no active session.
- Options considered: The human supplied the approved behavior in decisions 4–5, 13–14; alternatives were not selected during synchronization.
- Decision/rationale: Student closure is ACTIVE → CLOSED; no new work/retry in CLOSED; admitted PENDING/PROCESSING work may finish and authorized replay remains read-only. Start New atomically closes old ACTIVE and creates new ACTIVE.
- Consequences/tradeoffs: Authentication lifetime is separate; expiration duration and physical transaction design remain deferred.
- Approval evidence: Step 4 human synchronization request, numbered decisions 4–5, 13–14.
- Affected contracts: requirements.md §22.1; api-contract.md §§4–5, 11; schema.md §10; architecture.md §31.1; ai-runtime.md.

## STEP4-003 — Assigned coursework and least disclosure

- Date: 2026-10-04.
- Status: APPROVED.
- Context/problem: Course membership and supplied IDs must not overgrant tutoring/data access.
- Options considered: The human supplied the approved behavior in decisions 15–16; alternatives were not selected during synchronization.
- Decision/rationale: Specific assigned/released coursework eligibility is distinct from enrollment. Protected existence uses 404; discoverable resources with forbidden actions use 403.
- Consequences/tradeoffs: No open-practice mode or speculative class/group allocation design is authorized; auth mechanism remains deferred.
- Approval evidence: Step 4 human synchronization request, numbered decisions 15–16.
- Affected contracts: requirements.md §22.1; api-contract.md §§10–11, 16; schema.md §8; security.md.

## STEP4-004 — Progress, official mastery, and history

- Date: 2026-10-04.
- Status: APPROVED.
- Context/problem: Estimated learning progress and official recognition have different authority.
- Options considered: The human supplied the approved behavior in decisions 17–18; alternatives were not selected during synchronization.
- Decision/rationale: Progress labels BUILDING/DEVELOPING/STRONG reflect accumulated evidence, not model confidence. Authorized human workflows own official mastery; preserve every change and its provenance.
- Consequences/tradeoffs: Rubric calibration, official vocabulary/transitions, and physical history design remain deferred.
- Approval evidence: Step 4 human synchronization request, numbered decisions 17–18.
- Affected contracts: requirements.md §22.1; api-contract.md §§12, 14; schema.md §§14–15, 22; ai-runtime.md; evals.md.

## STEP4-005 — POC review and escalation lifecycle

- Date: 2026-10-04.
- Status: APPROVED.
- Context/problem: Review must preserve evidence of what AI predicted and what the teacher concluded.
- Options considered: The human supplied the approved behavior in decisions 19–20; alternatives were not selected during synchronization.
- Decision/rationale: Preserve original AI POC plus separate attributed teacher determination linked to it; feedback CORRECT/PARTLY_CORRECT/INCORRECT; AI focus is advisory; escalation OPEN → IN_REVIEW → RESOLVED.
- Consequences/tradeoffs: No automatic model retraining, extra transitions, or unapproved review-concurrency rules; physical feedback design remains deferred.
- Approval evidence: Step 4 human synchronization request, numbered decisions 19–20.
- Affected contracts: requirements.md §22.1; api-contract.md §13; schema.md §§13, 16, 22; architecture.md §22; ai-runtime.md.

## STEP4-006 — Runtime authority, verification, and deferrals

- Date: 2026-10-04.
- Status: APPROVED.
- Context/problem: Bound model behavior and verify contract guarantees without inventing release policy.
- Options considered: The human supplied the approved behavior in decisions 21–25; alternatives were not selected during synchronization.
- Decision/rationale: Backend-owned authority, selected authorized context, approved RAG/tools, defaults of 4,000 characters/five steps/30 seconds/one eligible retry; separate deterministic tests and probabilistic evals.
- Consequences/tradeoffs: Embedding/dimensions, expiration, mastery vocabulary, numeric thresholds, age/privacy/accessibility/training policy, and physical designs remain unresolved.
- Approval evidence: Step 4 human synchronization request, numbered decisions 21–25.
- Affected contracts: ai-runtime.md; security.md; evals.md; api-contract.md §§2, 7–9, 15, 18; architecture.md §31.1.

## STEP5-001 — Explicit application and tutoring flow responsibilities

- Date: 2026-10-05 (America/Chicago).
- Status: APPROVED.
- Context/problem: Conceptual session, model/tool, public-output, and review flows need explicit responsibility boundaries.
- Options considered: Human-specified flows; no new implementation alternative selected.
- Decision/rationale: Preserve Step 1–4 session/replay semantics; validate coursework eligibility; Orchestrator coordinates RAG → Context Builder → model; ToolExecutor mediates actions through services/repositories; tool results feed subsequent reasoning; commit final output before controlled public delivery. Keep the modular monolith/local-first shape.
- Consequences/tradeoffs: The original Step 5 decision introduced no separate deployment requirement. Approved amendment STEP5-001-A1 now permits one separately deployed PostgreSQL-backed worker without a dedicated queue service. Model and internal tool data do not become public output. The abbreviated Step 5 state-check sequence retains Step 4's historical replay exception.
- Approval evidence: Human “We have completed Step 5 — Flow” request, flows 1–4, 10–11 and Important boundaries; explicit instruction to preserve Step 1–4.
- Contracts: architecture.md §31.2; api-contract.md §§2, 11, 13; ai-runtime.md “Approved Step 5 flow detail”; security.md “Step 5 execution and public-response boundary”; evals.md “Step 5 flow verification additions”.

## STEP5-001-A1 — Asynchronous worker, client polling, and session continuity

- Date: 2026-10-08 (America/Chicago).
- Status: APPROVED.
- Context/problem: Slice 1 durably admits student messages as PENDING. Slice 2 needs to process that work independently of the admitting HTTP request. The original STEP5-001 and architecture §31.2 did not authorize a separate worker deployment.
- Decision/rationale:
  - Permit one separately deployed PostgreSQL-backed background worker for asynchronous tutor response generation. FastAPI and the worker share the modular-monolith application boundaries and PostgreSQL database; this is not decomposition into domain microservices.
  - PostgreSQL remains the durable source of admitted work, processing state, and committed results. Work must survive API/worker process loss without depending on an in-memory task or external notification.
  - Separately exclude a dedicated queue service or message broker. Do not introduce Redis, Celery, RabbitMQ, or Kafka. A logical backlog in PostgreSQL is not a dedicated queue service.
  - POST commits input and its idempotency record before returning the admission response. Background processing starts only after that commit.
  - Clients initially poll authenticated GET /api/v1/coaching/sessions/{session_id}/messages/{message_id}/status for current status and committed student-safe output; message_id identifies the student message. POST replay remains available for uncertain send outcomes, not normal polling.
  - Completed learning sessions remain CLOSED to new messages. Students continue through new eligible sessions with minimum relevant authorized prior context. Message COMPLETED does not itself close a session or establish official mastery.
  - Separate admission from slower processing while retaining durable input and the existing database. This addresses the asynchronous workflow, not a measured capacity bottleneck.
- Alternatives considered:
  - Process inside POST: simpler deployment, but couples processing and response delivery to request lifetime.
  - API-process background task: fewer deployment roles, but execution remains coupled to API lifecycle and still needs durable recovery from PostgreSQL.
  - Dedicated broker/task platform: additional operational and consistency responsibilities without a demonstrated MVP need.
  - Repeated POST replay or push delivery for status: retain POST replay for uncertain submission; initially prefer read-only GET polling.
- Consequences/tradeoffs: Operate and supervise an additional deployment role; coordinate API/worker version compatibility, database access and connection capacity, restart/shutdown behavior, health, backlog, and processing-failure visibility. Polling adds HTTP/database reads and detection latency. PostgreSQL availability and capacity affect admission and processing. No broker infrastructure is added.
- Preserved guarantees: Input/output commit boundaries, valid-owner finalization, stale-owner rejection, idempotency, existing bounded retry policy, append-only history, authorization, assigned-coursework scope, selected context, and human mastery authority.
- Open questions: GET wire/error details and polling cadence; physical work discovery/ownership/recovery; deployment supervision and shutdown; any new session-completion trigger or cross-session context policy. Resolve before dependent implementation. No lease, retry, migration, or worker implementation design is approved by this amendment.
- Approval evidence: Human “approve” response to the reviewable STEP5-001 amendment and ten-document synchronization proposal. This approves documentation synchronization, not runtime implementation.
- Contracts: requirements.md; architecture.md §§3, 25.1, 28, 31; api-contract.md; schema.md; ai-runtime.md; security.md; evals.md. README.md and architecture-decisions.md summarize this decision.

## STEP5-002 — Crash recovery and valid-owner finalization

- Date: 2026-10-05 (America/Chicago).
- Status: APPROVED.
- Context/problem: A failed turn or lost response may follow successful durable writes; stale processors may continue after ownership transfer.
- Options considered: Human specified behavioral guarantees; leases/timestamps/tokens/locks or alternatives remain deferred.
- Decision/rationale: Only the currently valid processing owner may finalize. Recover from the last durable commit; uncommitted model output is non-authoritative. Reuse committed logical effects and permit unsuccessful/uncommitted effects to be attempted under approved rules. Same-key replay retrieves current state/result after HTTP loss. Explicit retry neither duplicates input nor reopens CLOSED.
- Consequences/tradeoffs: Requires eventual verification of stale-owner rejection and crash boundaries, without choosing physical infrastructure. Existing bounded retry policy and closure permission for admitted work remain intact.
- Approval evidence: Step 5 human request, flows 5–10.
- Contracts: requirements.md §22.2; schema.md §31.1; architecture.md §31.2; api-contract.md §§2, 4–5; ai-runtime.md; security.md; evals.md.

## STEP5-003 — Teacher feedback and accumulated progress interpretation

- Date: 2026-10-05 (America/Chicago).
- Status: APPROVED.
- Context/problem: Distinguish model observations, application-estimated progress, and authoritative human decisions in concrete flows.
- Options considered: Human-provided feedback mapping and ProgressService responsibility; no additional rubric or state transition selected.
- Decision/rationale: Yes / Partly / No maps to CORRECT / PARTLY_CORRECT / INCORRECT; retain original AI prediction plus separate attributed teacher determination. ProgressService applies the product rubric to validated accumulated evidence; substantial progress changes should have multiple evidence points. Official mastery remains human-controlled.
- Consequences/tradeoffs: BUILDING / DEVELOPING / STRONG remain existing vocabulary, not an additional irreversible transition policy. Calibration, physical persistence, and official mastery transitions stay deferred. Suggested focus remains advisory; no automatic retraining.
- Approval evidence: Step 5 human request, flows 11–12, preserving Step 1–4.
- Contracts: requirements.md §22.2; schema.md §31.1; api-contract.md §§12–14; architecture.md §31.2; ai-runtime.md; evals.md.

## STEP6-001 — Measurement-driven scale posture

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Growth may constrain inference, application capacity, database access, or retrieval; speculative distribution would add unnecessary MVP complexity.
- Options considered: Human-provided evolutionary options: application instances/load balancing, query/index/pagination improvements, safe caching, read replicas/partitioning, extreme-scale sharding, improved vector search, model routing, and later asynchronous processing. None was selected for immediate deployment by the original Step 6 decision; STEP5-001-A1 subsequently selects the limited worker topology.
- Decision/rationale: Use Growth → Bottleneck → Solution → Tradeoff. Retain FastAPI modular monolith, PostgreSQL + pgvector, external models, thin model abstraction, small curriculum, and local-first/cloud-deployable posture. Avoid unnecessary permanent-single-instance assumptions. Investigate inference constraints directly; gate meaningful optimizations on behavioral quality evaluation.
- Consequences/tradeoffs: Infrastructure complexity requires measured justification and approval. No Kubernetes, microservices, dedicated queue services/brokers, replicas, partitioning, sharding, dedicated vector service, routing policy, or cache implementation is approved now. STEP5-001-A1 selects one separate worker for asynchronous workflow requirements, not speculative scaling; a logical PostgreSQL backlog is not a dedicated queue service. Other scaling options remain measurement-driven. Embeddings remain separate; model/configuration choices stay deferred.
- Approval evidence: Human “We have completed Step 6 — Scale and Step 7 — Failure” synchronization request, Step 6 and Important preservation/validation instructions.
- Contracts: requirements.md §22.3; architecture.md §31.3; schema.md §31.2; ai-runtime.md “Step 6 inference and retrieval scale posture”; security.md and evals.md Steps 6–7 sections.

## STEP7-001 — Dependency failure truthfulness and durability

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Retrieval/database/tool failure or invalid model output can occur even when another dependency reports success; users must not receive false success or durability claims.
- Options considered: Human-approved safe failure or contract-permitted degradation; exact degradation policy remains deferred. Circuit breakers, additional fallback providers, and sophisticated recovery infrastructure are future options, not selected mechanisms.
- Decision/rationale: Use What can fail → What happens → How do we recover → What does the user see? Enforce required curriculum grounding; reject invalid model output and disallowed actions; roll back logically coupled pre-commit writes; withhold uncommitted final responses; verify tool results. Preserve all Step 5 bounded retry, input durability, ownership, crash recovery, action idempotency, replay, closure, and stale-owner guarantees.
- Consequences/tradeoffs: Provider success alone is not successful tutoring. Failure-state writes are durable only after commit; recovery uses actual committed state. Keep internal classifications and safe public errors without selecting remaining wire mappings. Detailed security, tests/evals, and ops/observability remain primarily Steps 8, 9, and 10 respectively.
- Approval evidence: Same human synchronization request, Step 7 and Validation; no independently selected product policy.
- Contracts: requirements.md §22.3; architecture.md §31.4; schema.md §31.2; api-contract.md §6 “Step 7 dependency failure behavior”; ai-runtime.md “Step 7 failure behavior”; security.md and evals.md Steps 6–7 sections.

## STEP8-001 — Backend security authority and untrusted model boundaries

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Client identity claims, model mistakes, prompt injection, and forged tool arguments must not bypass application authority or disclose protected data.
- Options considered: Human-specified deterministic backend enforcement; prompts/frontend controls may reinforce but cannot replace it. No authentication provider or physical enforcement mechanism selected.
- Decision/rationale: Backend resolves trusted identity and enforces relationships, authorization, authority, valid state, and allow-listed tools. Derive authoritative actor/resource context server-side. Scope retrieval before model context and minimize provider disclosure. Preserve human mastery authority, 404/403 non-disclosure, authorized replay/recovery, and valid-owner finalization.
- Consequences/tradeoffs: Security must hold even if the model follows malicious instructions. Model/client identity cannot redirect actions to other students; unauthorized operations cannot create requested durable effects or false success claims. Steps 1–7 contracts remain in force.
- Approval evidence: Human “We have completed Step 8 — Security” synchronization request, core security principle through student-data privacy and preservation of failure guarantees.
- Contracts: security.md “Step 8 — Deterministic security guarantees”; requirements.md §22.4; architecture.md §31.5; schema.md §31.3; api-contract.md §16 Step 8 subsection; ai-runtime.md and evals.md Step 8 sections.

## STEP8-002 — Privacy, secrets, and compliance decision boundary

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Provider context, public responses, and logs can expose private data or secrets; conceptual security must not be mistaken for compliance approval.
- Options considered: Human-approved privacy/minimization guarantees with authentication and secret-management mechanisms deferred; no legal applicability determination or compliance implementation selected.
- Decision/rationale: Student data is private by default; minimize context/output/log disclosure. Keep secrets server-side and out of model prompts/public responses. Any narrowly defined trusted integration exception requires explicit approval; none is selected. Preserve synthetic/demo scope and defer deployment-specific age, consent, retention/deletion, educational-record, school, provider-handling, FERPA/COPPA/other applicable policy questions until human resolution before affected real-world use.
- Consequences/tradeoffs: Mechanisms must be resolved before dependent implementation/deployment, but their intentional deferral does not block conceptual Step 8. Detailed monitoring remains Step 10. This contract is not evidence of runtime security or legal compliance.
- Approval evidence: Same Step 8 human request, data minimization, student-data privacy, logging/observability privacy, secrets, compliance/child-specific policy, and validation instructions.
- Contracts: security.md “Step 8 — Secrets, logging, and deployment decisions”; requirements.md §22.4; architecture.md §31.5; schema.md §31.3; api-contract.md, ai-runtime.md, and evals.md Step 8 sections.

## STEP9-001 — Evidence-based POC outcomes and bounded diagnosis

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Forced diagnosis, irrelevant context, or unsupported blocker selection can produce confident but unjustified tutoring decisions.
- Options considered: Human-specified SPECIFIC_POC / NO_POC / INSUFFICIENT_EVIDENCE outcomes, selected evidence, multiple supported POCs, and encoded prerequisites; no physical representation or numeric diagnostic bound selected.
- Decision/rationale: Treat insufficient evidence as a valid successful diagnosis outcome. Gather/vary diagnostic evidence within bounds, then record insufficient/unknown and leave work incomplete without automatic escalation solely for insufficiency. Teachers see incompleteness through normal status. Preserve multiple supported POCs and choose a foundational blocker only when supported by evidence and explicit curriculum prerequisites.
- Consequences/tradeoffs: Clarifies requirements.md §15's potential escalation conditions without removing other escalation grounds. Does not add lifecycle states or map incomplete learning to runtime FAILED. Repeated patterns may later be surfaced without unsupported judgments. Exact bound/accounting and persistence/wire visibility remain unresolved before dependent implementation.
- Approval evidence: Human “We have now completed and approved Step 9 — Tests/Evals and Step 10 — Operations/Observability” request, POC diagnosis, valid outcomes, and foundational-blocker sections.
- Contracts: requirements.md §§15, 22.5; architecture.md §31.6; schema.md §31.4; api-contract.md §9 Step 9 alignment; ai-runtime.md “Step 9 diagnosis behavior”; evals.md Step 9.

## STEP9-002 — Risk-driven evaluation and regression policy

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Aggregate metrics, unstable labels, uncalibrated judges, and single-metric experiments cannot reliably establish Tutor quality.
- Options considered: Human-approved deterministic tests, probabilistic eval families, deterministic scorers, calibrated LLM judges, and human expert review; no tool/vendor, dataset, numeric threshold, or baseline result selected.
- Decision/rationale: Apply Behavior → Failure → Cost → Dataset → Metric → Threshold → Scorer → Baseline → Experiment → Slices → Decision → Regression. POC diagnosis is the first/core family. Use taxonomy/rubric-aware human-reviewed ground truth, reviewer agreement, appropriate scorers, risk-derived empirical thresholds, baseline experiments, slice analysis, and regressions across the eight initial families in evals.md.
- Consequences/tradeoffs: Release thresholds differ from runtime evidence thresholds. Safe abstention may allow a weak slice to be monitored without waiving deterministic guarantees. Validate judges with representative experts; production changes compare quality, safety, slices, cost, latency, and reliability. Future real-data use still requires privacy approval. Numeric criteria remain unresolved, not invented.
- Approval evidence: Same human request, Step 9 framework, tests vs evals, taxonomy/datasets/metrics/scoring, experiments/slices/release/regression, and remaining eval families.
- Contracts: evals.md Step 9; requirements.md §22.5; architecture.md §§26, 31.6; ai-runtime.md Step 9; api-contract.md §9; security.md Steps 9–10.

## STEP10-001 — Correlated, privacy-preserving operational observability

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Operations need attributable latency/failure/cost signals without unnecessarily duplicating sensitive tutoring content or confusing health with behavioral quality.
- Options considered: Human-approved OpenTelemetry-compatible correlation, metadata logs, metrics, spans, version identifiers, and actionable-alert candidates; no exporter/backend/dashboard or numeric target selected.
- Decision/rationale: Trace interactions across relevant application/AI/persistence boundaries. Default production logs to operational metadata and exclude raw student/model/prompt/context/chunk content, secrets/tokens, and unnecessary PII. Collect practical volume, success/failure, latency, usage/cost, tool/retrieval/validation failure, and retry/recovery metrics. Retain relevant model/prompt/retrieval/eval dataset versions where practical. Prefer actionable alerts based on measured operational targets.
- Consequences/tradeoffs: Protected application records retain authorized content independently of logs. Correlation does not replace authorization/idempotency or change transaction ordering. Evals assess quality; observability assesses health. Exact thresholds await baseline data; telemetry storage/access/retention/export and implementation choices remain unresolved as applicable.
- Approval evidence: Same human request, Step 10 logs, metrics, traces, versioning, alerts, and evals vs observability.
- Contracts: architecture.md §25.1; security.md Steps 9–10; evals.md Step 10; schema.md §31.4; api-contract.md §7; ai-runtime.md Step 10; requirements.md §22.5.

## SLICE1-001 — Demo authentication

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Previously deferred choices block Slice 1 implementation.
- Options considered: Four recommendations from the prior Slice 1 review, with human clarification of content-only replay comparison.
- Decision/rationale: Opaque bearer credentials map server-side to existing users; provision outside the endpoint. No client identity override, login, registration, passwords, OAuth, or token issuance.
- Consequences/tradeoffs: Demo-only; production authentication remains deferred.
- Approval evidence: Human “Approve the four recommended Slice 1 decisions” message and implementation authorization.
- Contracts: security.md Slice 1; architecture.md §31.7.

## SLICE1-002 — Eligibility and durable admission schema

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Previously deferred choices block Slice 1 implementation.
- Options considered: Four recommendations from the prior Slice 1 review, with human clarification of content-only replay comparison.
- Decision/rationale: UUID identifiers, persisted processing status, explicit student-assignment eligibility distinct from enrollment, and persisted idempotency message references unique by student/operation/key. Commit message plus record atomically; PostgreSQL constraints protect concurrency.
- Consequences/tradeoffs: Class/group allocation and future AI persistence remain deferred. Preserve content exactly; compare content only, superseding the prior proposed session-plus-content comparison.
- Approval evidence: Human “Approve the four recommended Slice 1 decisions” message and implementation authorization.
- Contracts: schema.md §31.5; requirements.md §22.6.

## SLICE1-003 — Admission response and key semantics

- Date: 2026-10-06 (America/Chicago).
- Status: APPROVED.
- Context/problem: Previously deferred choices block Slice 1 implementation.
- Options considered: Four recommendations from the prior Slice 1 review, with human clarification of content-only replay comparison.
- Decision/rationale: 201 creation, 200 authorized replay; student_message_id and current status (new input PENDING). Reject whitespace-only content and identity extras; keys require 1–255 printable non-whitespace ASCII characters or 422. Compare parsed content exactly; changed content conflicts with 409. Retain keys for demo lifetime; replay precedes new-send ACTIVE gate.
- Consequences/tradeoffs: No AI work or explicit failed-message retry is included. Existing security, transaction, lifecycle, and non-disclosure guarantees remain.
- Approval evidence: Human “Approve the four recommended Slice 1 decisions” message and implementation authorization.
- Contracts: api-contract.md Slice 1; evals.md Slice 1.

## REPO-001 — Private repository and stable baseline workflow

- Date: 2026-10-08 (America/Chicago).
- Status: APPROVED.
- Context/problem: Completed Slice 1 needs a versioned remote baseline before further development.
- Options considered: The human explicitly selected a private repository and a separate feature branch; no hosting or public-release alternative was selected.
- Decision/rationale: Initialize/publish private GitHub repository ai-tutor; keep main as the stable Slice 1 baseline; create feat/async-message-processing from that baseline for planned Slice 2 work. Maintain README and an explanatory architecture-decisions.md ADR index, with this file remaining the approval log.
- Consequences/tradeoffs: Public presentation is deferred. Branch separation does not enforce branch protection or select a worker/queue/model architecture. No Slice 2 code is authorized by this repository-setup task.
- Approval evidence: Human repository initialization/publishing request and explicit private/main/feature-branch preference.
- Contracts: Existing domain contracts remain unchanged; README.md and architecture-decisions.md describe implementation versus planned work.

## Deferred decisions — not approved

TODO / UNRESOLVED: exact model/provider and embedding model/dimension; curriculum source/unit/objectives and chunking/versioning; session resumability/expiration duration; official mastery vocabulary/transition graph; calibrated progress rubric and numeric release thresholds; remaining production authentication/relationship policy beyond Slice 1; age/privacy/consent/training/accessibility details; future open-practice mode; class/group allocation beyond Slice 1; physical ownership/recovery/action-idempotency design; physical mastery-history/POC-feedback representation; additional review transitions/concurrency rules; remaining wire-level response mappings and production idempotency expiration beyond Slice 1 demo-lifetime retention. See domain documents for scoped details. Deferral is not permission to invent defaults.

Future approved decisions should retain date, context, options, rationale, consequences, approval evidence, and affected contract references. Do not log trivial coding choices as architectural decisions.

## SLICE1-004 — Successful FAILED-message replay remains HTTP 200

- Date: 2026-10-08 (America/Chicago).
- Status: APPROVED.
- Context/problem: Broad terminal-processing-failure 503 wording could be mistaken for the HTTP status of a later successful idempotent POST replay, contradicting the approved Slice 1 behavior and existing regression test.
- Options considered: Return the original processing failure's HTTP status, or distinguish successful replay retrieval from current service unavailability.
- Decision/rationale: An authorized identical idempotent POST replay returns 200 with the previously accepted message ID and current state, including FAILED. It creates no message, schedules no job, and starts no processing attempt. Reserve 503 for genuine unavailability preventing fulfillment of the current request. New intentional input uses a new key; worker retries do not require a new client key.
- Consequences/tradeoffs: Clarifies earlier Step 4/7 failure wording without changing authentication, authorization, explicit-retry eligibility, or Slice 1 runtime behavior. It does not approve the remaining Slice 2a schema, worker, or GET response design.
- Approval evidence: Human request “Choose 200 OK — update the API contract” and explicit request for a FAILED-replay regression test.
- Contracts: api-contract.md §§3, 5–6; ai-runtime.md durable interaction flow; evals.md deterministic contract tests.

## SLICE2A-001 — Processing persistence, ordered workers, and polling

- Date: 2026-10-08 (America/Chicago).
- Status: APPROVED.
- Context/problem: Durable admission needs operational job metadata, strict session ordering, fenced processing, and read-only status delivery without conflicting status authorities.
- Options considered: Extend messages with all worker fields versus one dedicated job per input; duplicate statuses versus messages as sole authority; skip FAILED versus preserve ordering; external brokers versus existing PostgreSQL; flat versus session-nested polling route.
- Decision/rationale: Dedicated message_processing_jobs without a status column; messages.processing_status remains authoritative. Approve the Slice 2a design and final three-area clarification: sequence-based session heads, FAILED barriers, one PROCESSING message per session, token/lease fencing, coupled finalization and unique tutor response, closure reasons and CANCELLED, and authenticated nested GET polling. See schema.md §31.6, architecture.md §31.8, api-contract.md polling, and ai-runtime.md Slice 2a for exact contracts.
- Defaults: Model timeout 30 seconds, lease 45 seconds, heartbeat 10 seconds, claim deadline 90 seconds, maximum two claims per retry generation, two-second retry/recovery backoff, 35-second shutdown grace. No hidden SDK retries; one initial-generation model invocation per claim.
- Explicit retry clarification: Only known transient model-provider or infrastructure failures may become eligible for future student retry, subject to current authorization, ACTIVE session, retry budgets, and rate limits. Invalid model output, authorization failures, policy violations, invalid requests, and unknown failures are not explicitly retryable. Preserve retry_generation; do not implement a student-facing retry endpoint in Slice 2a.
- Consequences/tradeoffs: FAILED blocks later messages; permanently nonretryable work requires continuation through a new eligible session. Database triggers enforce committed state shape, not runtime authorization or lease fencing. Exactly-once external model execution is not guaranteed. New schema requires compatible admission before deployment. Legacy acceptance order is deterministic (created_at, id), not reconstructed historical commit order; CLOSED legacy sessions become UNKNOWN and unfinished work is cancelled. Unexpected legacy processing/response history aborts migration for review.
- Approval evidence: Human “I approve the Slice 2a schema and worker contract” with final explicit-retry policy and six implementation stages. Stage 1 is authorized now; stop for review before Stage 2. Earlier STEP5-001-A1 and SLICE1-004 remain in force.
- Scope: No broker, RAG, tutor summaries, cross-session memory, or multi-agent orchestration. Stage 1 covers models/migration/constraints/triggers/backfill and PostgreSQL tests only.

- Staged implementation authorization update (2026-10-08): The human accepted Stage 2 for continued development, not deployment, and authorized Stage 3 claiming, leases/heartbeat/deadlines, fencing, retries/recovery/shutdown, authorization checks, and PostgreSQL tests with a deterministic fake. Stop after Stage 3 for review. No production model client, GET endpoint, RAG, dashboard, or explicit student retry endpoint is authorized in this stage. This extends the original staged authorization; it does not change SLICE2A-001 policy.

- Staged implementation continuation (2026-10-08): Human “continue” after the Stage 3 completion report advances the previously authorized sequence to Stage 4 (model-client abstraction and deterministic fake). No provider selection, production model integration, GET endpoint, or deployment is included. This records execution scope, not a new product or architecture decision.

- Staged implementation continuation (2026-10-08): Human “continue” after the Stage 4 report advances the previously authorized sequence to Stage 5, the authenticated read-only status GET. Existing SLICE2A-001 wire, authorization, and consistency contracts apply unchanged. No deployment, production model integration, or explicit retry endpoint is included.

- Stage 6 authorization: Human explicitly requested “Slice 2a — Stage 6: End-to-End Integration and Failure Validation,” real PostgreSQL/deterministic-model testing, and minimal changes for validation or confirmed defects. Stop after Stage 6 for review; no production provider, deployment, new slice, or unapproved endpoint. This records execution scope, not a new design decision.

## OFFLINE-EVAL-001 — Tutor prompt v1 synthetic offline experiment

- Date: 2026-10-13 (America/Chicago).
- Status: APPROVED for isolated experiment implementation and deterministic verification only.
- Context: Evaluate the supplied tutor prompt without integrating experimental replies into student processing.
- Options: Existing worker/provider integration versus separate offline runner; automatic instructional judging versus human review. Human selected isolation and human review.
- Decision: OpenAI Responses API, `gpt-5.4-mini`, explicitly `reasoning.effort=none`, input ceiling 8,000 tokens including instructions/context, output allowance 1,000 tokens, 30-second timeout, `store=false`, no SDK/internal/automatic retries, one request/sample per case. At most ten earlier completed whole student/tutor exchanges; remove oldest whole exchanges to fit and exclude later messages. Required-content overflow fails locally without truncation/provider contact. Exactly one nonblank, NUL-free `reply` string; malformed/incomplete outputs fail.
- Data/policy: Human-reviewed synthetic Grade 7 Mathematics fixtures only, `3x = 36` where applicable. Preserve missing/ambiguous-context conditions. Prompt v1 and twelve expectations supplied by human. No real data, tools, actions, persistence to student records, or public API changes.
- Evaluation: Human review of six dimensions, PASS/FAIL/NOT_APPLICABLE with context-grounded reasons. No automatic instructional judge, weights, aggregate score, release threshold, or quality claim from JSON validation. See evals.md offline subsection.
- Consequences: Fake execution proves mechanics only. Explicit paid command is separate; paid execution remains unrun until human explicitly requests it. No production provider/runtime approval is implied. Single samples cannot establish robustness or improvement.
- Approval evidence: Human message beginning “The following configuration was approved in my planning chat,” its explicit initial experiment approvals, implementation/synchronization request, and subsequent six-dimension clarification in this session. This entry records those messages, not independent approval of earlier unseen planning content.
- Contracts: requirements.md, architecture.md, ai-runtime.md, security.md and evals.md “Offline tutor evaluation v1” sections. API/schema unchanged because the experiment has no endpoints/database.

## OFFLINE-EVAL-002 — First paid run and Luna switch

- Date: 2026-10-18 (America/Chicago).
- Status: APPROVED by the human request “Prepare and run our first paid offline AI Tutor evaluation.”
- Context/options: Retain the earlier mini model or switch the isolated experiment to the explicitly selected `gpt-6-luna`; human selected Luna.
- Decision/rationale: Use `gpt-6-luna`, reasoning `none`; authorize exactly one paid run of the existing twelve synthetic cases, one response per case and no automatic retries. Preserve prompt v1, fixtures, context selection, six pending human review dimensions, 8,000 input ceiling, 1,000 output allowance, 30-second timeout and store=false.
- Consequences: New evidence file only; no reruns of failures; stop on unavailable credentials/billing without repeated attempts. Secure environment credential use only. Backend, worker, public API and student records remain isolated. No instructional acceptance decision is authorized.
- Approval evidence: Current human execution request and its explicit limits. This supersedes OFFLINE-EVAL-001’s model and implementation-only execution restriction; all other boundaries remain.

## OFFLINE-EVAL-003 — Local Ollama Qwen3.5 4B synthetic baseline

- Date: 2026-10-18 (America/Chicago).
- Status: APPROVED by the current human request “Add a local-model option to our isolated offline AI Tutor evaluation experiment.”
- Context: Available hardware is a MacBook Air M1 with 16 GB unified memory; RTX 3080 PC unavailable. Compare synthetic local responses without paid/hosted inference, preserving the existing experiment.
- Options: Continue hosted Luna, add the requested local Qwen3.5 4B via Ollama, or substitute another model/runtime. Human explicitly selected Ollama and compressed 4-bit Qwen3.5 4B and forbade silent substitution; preserve Luna and fake mode.
- Decision/rationale: Official verified tag qwen3.5:4b-q4_K_M (Q4_K_M mixed precision, not every tensor four bits). Separate local adapter/command with loopback-only owned server and cloud disabled, no new application dependency or integration. Standard-library HTTP, no credentials. Local num_ctx=12288 accommodates unchanged 8000 input ceiling and 1000 generation allowance plus headroom within the advertised 262144 model context; disable thinking with verified native runtime controls. Keep 30-second deadline and no automatic retries; no budget/timeout reduction or prompt tuning without further human approval. Preserve prompt/cases/context-selection rules and all six pending dimensions. Qwen-specific conservative estimation assumptions and observed counters must be disclosed.
- Verification/authorization: Mocked local transport tests first. One local twelve-case experiment may run after setup succeeds. Download/install requires internet; verify disconnected generation afterward, or provide exact manual steps and explicitly report it unverified. Interactive installation/unavailable permissions may be left to the human after independent work is complete. New evidence paths only; no automatic reruns of failures.
- Consequences: Installation/model load/context caches consume disk and unified memory. A model's advertised context does not establish M1 speed or memory fit; measure and report honestly. Setup failure is not a completed baseline. JSON validity is mechanics only, not tutoring safety or acceptance. Backend, worker, API and student records remain untouched.
- Approval evidence: Current human request explicitly authorizes the model/runtime, local-only boundaries, preserved settings/review policy, authoritative document updates, mocked tests, one conditional run, and manual setup/disconnection fallback. 12288 is the implementation context allocation behind the approved requirement to accommodate input/output/framing, not an increased input or output budget.
- Contracts synchronized: requirements, architecture, ai-runtime, security and evals local offline subsections. API/schema not applicable: no endpoint, database access or schema change.

## OFFLINE-EVAL-004 — Scoped evidence-attribution prompt v2 preparation

- Date: 2026-10-19 (America/Chicago).
- Status: APPROVED for preparation and deterministic checks only; real-model generation and paid API calls explicitly prohibited in this task.
- Context: The supplied baseline review records unsupported student-method attribution in cases 3 and 8. Whether a small prompt clarification changes that behavior is unknown.
- Options: Keep v1 as the sole prompt, broadly tune tutoring instructions, or add the exact requested evidence-attribution clarification as a separately selected v2. Human selected the narrow third option and preservation of all baseline artifacts.
- Decision/rationale: Add the human's exact paragraph after existing rule 3, with no other prompt changes. Preserve original v1, fixtures, rubric, baseline generation evidence and human review. Allow explicit v2 selection in isolated CLIs and record selected version/hash; keep v1/fake defaults and Luna support. Local v2 must match the recorded v1 Qwen model digest and unchanged generation/admission/schema/timeout/one-sample settings; new evidence paths exclusively created. Expectations and judgments remain outside model input.
- Hypothesis: May reduce unsupported attribution in cases 3/8 while preserving supplied-method recognition in cases 4/10; not an established cause or proven fix. All twelve cases require existing six-dimension regression review. One sample/case is exploratory, without causal/statistical improvement or acceptance claims.
- Consequences: Added prompt length affects the unchanged conservative admission bound, but deterministic checks confirm the twelve fixed cases keep identical selected context. A future mismatched model digest fails before generation. No prompt/model tuning, retries, new dataset, rubric, threshold or runtime integration is authorized.
- Approval evidence: Current human message beginning “Prepare a scoped prompt-v2 experiment for the offline AI Tutor evaluation,” exact quoted addition, explicit hypothesis/comparison plan, preservation requirements and prohibition on real generation. No additional approvals or reviewer agreement are inferred.
- Contracts synchronized: ai-runtime and evals prompt-v2 subsections; existing requirements/architecture/security isolation remains unchanged. API/schema N/A because no endpoint or data-model change.

## OFFLINE-EVAL-005 — Focused v1/v2 repeatability preparation

- Date: 2026-10-19 (America/Chicago, current session date).
- Status: APPROVED for research preservation, preparation and deterministic verification only. Local generation and paid calls explicitly prohibited during this task.
- Context: Source-linked baseline reviews show a mixed picture: changed case 3 attribution, persistent case 8 problems and a v2 case 5 mathematical regression. One observation each cannot establish a reliable prompt effect or a cause.
- Options: Stop with single-response observations, prepare a focused repeated comparison, or expand to a full/held-out regression study. Human selected a focused repeatability comparison on five known cases and explicitly limited its conclusions.
- Decision: Preserve a research record, exact prompt addition/hashes, dataset/model/settings, slices and provenance. Prepare cases 3/4/5/8/10 × v1/v2 × three fresh samples = exactly thirty scheduled slots, at most thirty attempts, not retries/replacements. Preserve existing prompts/fixtures/rubric/model digest/generation/context/timeout controls and timeout stopping. Use reproducible randomized ordering; keep its seed separate from model seeding. No conversation carries between samples. New exclusive artifacts preserve successes/failures/unexecuted slots; raw evidence, label-masked view and version mapping remain separate. Fake remains default; no paid mode or application integration.
- Rationale/consequences: Sampling may expose variation in a small known-case set but cannot prove causal improvement, statistical significance or generalization. Prior baseline exposure means label-masked, not fully blinded independent review. Pending human judgments, no automated judge, aggregate score, threshold or new precision/recall metric. Broader regression coverage must be revisited before any later promotion. Real execution awaits a later instruction; no execution approval date is invented.
- Approval evidence: Current human message beginning “Prepare the next offline AI Tutor experiment: a scoped v1/v2 repeatability comparison,” including its exact design, preservation constraints, masking requirements and no-generation instruction. Earlier planning-chat approval dates are not supplied and remain unknown; review provenance is copied from approved review artifacts.
- Ordinary implementation choices: schedule seed 20261019, deterministic SHA-256 sort with recorded algorithm, fresh bundle names and opaque review IDs. This seed does not change model-generation settings and is not represented as a separate human approval.
- Contracts synchronized: requirements, architecture, ai-runtime and evals focused-repeatability subsections. Existing security boundaries apply without change. API/schema N/A: no endpoint, database/model-schema or application boundary changes.

## PILOT-EVAL-001 — Three qualitative student-facing pilot blockers

- Date: 2026-10-19 (America/Chicago).
- Status: APPROVED for the three evaluation criteria and their pilot-blocking consequence. No student-facing pilot, generated-practice scope change or model execution is approved by this record.
- Context: Existing evaluation policy defines mathematical correctness, evidence discipline and context use, but leaves exact release gates deferred. The human now explicitly approves three concrete qualitative blockers for a student-facing pilot.
- Options: Leave all exact pilot criteria deferred, or record the three specified qualitative gates while retaining other unresolved evaluation and deployment decisions. The current human instruction selects the specified gates.
- Decision: (1) The tutor must distinguish answer correctness from explanation correctness. (2) The tutor must not invent student reasoning or claim understanding without evidence. (3) The tutor must not judge an answer without sufficient, unambiguous problem context. A confirmed violation in the required evaluation suite blocks a student-facing pilot until addressed. Passing the suite does not establish zero real-world risk.
- Rationale: Answer validity, claims about student reasoning/understanding and judgments under ambiguous context require separate, evidence-grounded evaluation. These approved criteria give those failures an explicit pilot consequence without combining dimensions into an overall score or inventing calibrated numeric thresholds.
- Consequences: evals.md now records the three gates and qualifies its previous general deferral only for those gates. Existing six-dimension criteria and historical judgments are preserved; no past run is re-adjudicated or cleared for pilot use here. Required pilot-suite membership/coverage and other numeric or release decisions remain unresolved; the exploratory twelve-case baseline and focused five-case comparison are not designated sufficient. Existing synthetic/demo, security, privacy, authorization, deployment and human-mastery boundaries remain applicable.
- Scope explicitly not approved: Generated practice remains an unresolved proposed scope change. Current coursework restrictions remain in force. Requirements.md §8 related-problem/new-context examples are not explicit generated-practice approval; their relationship to any proposed expansion requires a human scope decision, not silent policy reconciliation.
- Approval evidence: Current user message beginning “Record our three approved pilot-blocking criteria in `docs/evals.md` and record their approval in `docs/decisions.md`,” followed by the exact three criteria, confirmed-violation blocking rule, real-world-risk limitation and explicit instruction to leave generated practice unresolved. No additional approval or historical approval date is inferred.
- Contracts: evals.md “Approved student-facing pilot-blocking criteria — PILOT-EVAL-001” and its qualified release-gate paragraph. Consistency checked against the existing offline Mathematical correctness/Evidence discipline/Context use/Coursework scope rubric; requirements.md §§8, 22.1, 22.5; ai-runtime.md authority/evidence and offline boundaries; security.md authorization/data/deployment rules; architecture.md §31.6. These are evaluation gates over existing behavioral obligations, not a new runtime implementation, API, schema or authorization change.

## PILOT-EVAL-002 — First-pilot scope, practice exclusion and seven-case membership

- Date: 2026-10-19 (America/Chicago); recording date for the current approval, not an invented historical planning timestamp.
- Status: APPROVED documentation and dataset preparation only; no inference or student-facing deployment authorized.
- Context/options: Previously, generated practice and required-suite membership were unresolved. The human selected a restricted first pilot and seven concrete cases, rather than expanding to generated practice or treating exploratory baselines as an acceptance suite.
- Decision: First pilot uses one-step equations with positive whole-number constants, coefficients and solutions; negatives, fractional coefficients and decimals are deferred. Generating new practice problems is outside the MVP; a confirmed required-suite violation blocks the pilot until addressed. An occasional unnecessary question is a quality weakness, not an automatic blocker. Preserve all three PILOT-EVAL-001 criteria and their blocking consequence. Passing the suite does not establish zero real-world risk.
- Dataset: Approve the seven supplied table cases as separately versioned `experiments/datasets/pilot-one-step-v1.json`, preserving problems, context, student messages and expectations. Mappings apply the existing six-dimension rubric and approved blockers, without automated judgments or new thresholds. Original twelve fixtures, prompts, settings and evidence remain unchanged.
- Rationale/consequences: Bound pilot content and separate safety-critical failures from pedagogical weaknesses. Section 8 verification examples stay inside assigned/published coursework and do not authorize generation. This narrowly supersedes PILOT-EVAL-001's historical unresolved generated-practice status and approves seven suite members; that prior approval record remains intact. No broader release acceptance or historical re-adjudication follows.
- Unresolved/DECISION_REQUIRED: The supplied `x/4 = 6` uses an integer divisor but normalized fractional coefficient; `x - 5 = 9` uses a positive literal but normalized negative constant. Clarify whether the approved scope refers to surface literals/divisors (recommended interpretation for human consideration) rather than silently interpreting it. Preserve both cases exactly meanwhile. Summarized prior tutor/completed-assignment context needs faithful execution rendering; no exact prior utterance or next assignment is invented. Repetitions, final acceptance procedure, further coverage and execution authorization remain unresolved. Dependent execution waits for required decisions.
- Approval evidence: Current human message containing the seven-row table, followed by “Synchronize these approved decisions,” the four explicit bullets, preservation instructions and prohibition on inference. No additional approvals or historical dates are inferred.
- Contracts: requirements.md §2.1 and §8/§22.1; ai-runtime.md “Sessions and scope”; evals.md “First-pilot dataset and additional gate — PILOT-EVAL-002.” Existing architecture, authorization, API, database and mastery boundaries are unchanged.

## PILOT-EVAL-003 — Division notation, exact guidance history and diagnostic sampling

- Date: 2026-10-19 (America/Chicago), current recording/approval date; unknown historical planning timestamps are not inferred.
- Status: APPROVED clarifications and preparation only. Current task explicitly prohibits inference and paid calls; no pilot/deployment approval.
- Context/options: PILOT-EVAL-002 left division terminology, exact guidance context and diagnostic sampling unresolved. The human chose to include integer-divisor notation while deferring explicit fractional-coefficient forms, supplied exact synthetic history, and selected a bounded v1 diagnostic instead of final acceptance.
- Decision: Include written `x/d = b` with positive whole-number divisor and right-hand side. Explicit fractional-coefficient forms remain deferred; do not exclude the approved division/subtraction examples through algebraic normalization. Preserve other mathematical scope limits, all three original blockers, generated-practice exclusion/blocker and the occasional-unnecessary-question quality distinction.
- Exact history: Student “How do I solve x + 6 = 14?”; Tutor “Try subtracting 6 from both sides.”; current Student “8.” Preserve source dataset v1; create clarified dataset v2 with stable case IDs and unchanged review expectations/mappings.
- Diagnostic design: Prompt v1; seven cases; three fresh attempts each, 21 scheduled slots maximum. Each slot is a separate observation, not a retry/replacement. Keep model/digest, settings, context/overflow rules, output schema, timeout and stop behavior. No prior sample conversation carries forward. Expectations/scoring stay outside model input, judgments pending. Diagnostic evidence is not final pilot acceptance; final acceptance procedure and further coverage remain unresolved.
- Rationale/consequences: The clarified notation and exact synthetic exchange permit faithful diagnostic preparation without fabricating student actions. A distinct local-only command and exclusive plan/evidence paths preserve existing experiments; fake remains default. Schedule ordering/seed is separate from unchanged model-generation defaults. Reuse original token-estimation assumptions and actual usage reporting. Early stop preserves unexecuted slots and may prevent all 21 requests.
- Approval evidence: Current human message beginning “Record and prepare these approved clarifications,” with division form, exact history, prompt v1/three fresh attempts, preservation rules, pending diagnostic judgments and explicit “Do not run inference or paid calls.” No final acceptance or actual execution approval is inferred.
- Contracts: requirements.md §2.1; ai-runtime.md Sessions and scope / PILOT-EVAL-003 clarification; evals.md Seven-case v1 diagnostic design. This entry narrowly resolves the corresponding historical PILOT-EVAL-002 questions without altering that record. Architecture, security, API, schema, backend, worker and student records are unchanged.

## OFFLINE-EVAL-006 — Example-only prompt v3 preparation

- Date: 2026-10-19 (America/Chicago, session date); no unknown historical approval dates inferred.
- Status: APPROVED isolated preparation and deterministic checks only; no inference, paid calls or pilot authorization.
- Context: V1 already requires separate result/explanation checking and focused conflict investigation. Recent diagnostic division replies twice endorsed the incorrect explanation, while a third suggested multiplication without clearly investigating the conflict (review IDs 81575998aea53e015af4, 4cf4333be3c81423bac6, 7c5b7fee41bd51abd9e3). These observations motivate a hypothesis, not an established cause.
- Options: Retain v1, combine earlier v2 changes, or isolate a single concrete example on unchanged v1. The human selected the isolated example; v3 is next available after v1/v2 and does not include v2's change.
- Decision: Create prompt-v3.txt exclusively from unchanged prompt.txt with only the exact three-line example quoted in ai-runtime.md OFFLINE-EVAL-006, immediately before JSON-output instructions. Make it explicitly selectable under existing offline version/hash patterns; keep default v1/fake and preserve Luna support, model digest/settings, datasets, rubric, no retries, context/overflow/output/timeout controls and historical evidence. Extend the existing local baseline-digest gate to v3. No new application behavior or dependency.
- Research question: Can a concrete example improve the tutor’s handling of correct answers paired with conflicting explanations? Hypothesis: a concrete example may improve compliance; not an established cause or proven fix. Independent variable: this single example addition. Record source-linked findings separately from the hypothesis in docs/research/tutor-prompt-v3-example.json.
- Consequences/limits: Future evaluation must test transfer beyond the example equation, preservation of correct-method recognition and broader regressions. The prior diagnostic dataset informed the change and is not held out. Concrete evaluation suite/transfer cases, repetitions, execution authorization and final acceptance procedure remain unresolved. No existing run count or protocol is silently adopted, and no quality/acceptance claim follows.
- Approval evidence: Current human message beginning “Prepare an isolated example-based prompt experiment,” exact specified example, research question/observation/hypothesis and explicit no-generation requirements. No additional human approvals or independent reviewer agreement claimed.
- Contracts: ai-runtime.md and evals.md OFFLINE-EVAL-006. Existing requirements/pilot blockers, architecture, security and human authority remain unchanged; API/schema N/A because no interface or database change.

## SUPP-EVAL-001 — Supplemental six-scenario instructional evaluation suite

- Date: 2026-11-08 (America/Chicago; documentation approval record date).
- Status: APPROVED for the supplemental scenario specification and versioned dataset; no model execution or paid calls are authorized by this decision.
- Context: The human-approved six-scenario specification adds instructional regression and transfer cases to the existing evaluation structure while preserving the original twelve-case offline evaluation and seven-case pilot diagnostic.
- Decision: Preserve the six approved scenarios in `experiments/datasets/instructional-scenarios-v1.json` as an independent supplemental dataset. Keep it outside the required pilot gate; it adds evidence but does not change pilot acceptance requirements.
- Scoring constraints: Retain the existing six human-review dimensions and PASS/FAIL/NOT_APPLICABLE judgments with reviewer explanations. Expected behaviors and review criteria remain outside model-facing input. Do not add weights, aggregate scores, a separate score for the Scenario 1/2 pair, an overall winner, new pilot blockers, or a release threshold. Scenarios 1 and 2 are reviewed as a descriptive consistency pair only.
- Preservation: Existing twelve-case and seven-case datasets, prompts, run artifacts, and human reviews retain their identities and are not replaced or rewritten. The separate V1/V2 repeatability outcome is recorded additively in evaluation documentation; its preparation record remains historical.
- Unresolved: Future V1/V3 execution authorization, repetition policy, and final acceptance procedure remain outside this decision.
- Approval evidence: Human message confirming the supplemental specification passed final review, authorizing versioned dataset creation and documentation synchronization, and explicitly requiring the suite remain outside the pilot gate with the existing scoring constraints.
- Contracts: `docs/evals.md` “Supplemental instructional scenarios — SUPP-EVAL-001”; no change to requirements, prompts, API, schema, security, or runtime behavior.

## STAGE3-DATA-001 — Organization, curriculum, and learning-data ownership synchronization

- **Date:** 2026-11-12 (America/Chicago).
- **Status:** APPROVED target architecture, reaffirmed for implementation planning; no migration execution or runtime change authorized by this record.
- **Context:** The project owner confirmed Decisions 80–86 and DATA-10/DATA-11 are authoritative and directed documentation reconciliation before preparing Migration 0003. The checked-out approval log did not contain those numbered records, so this entry records only the outcomes expressly restated in the current instruction.
- **Decision:** Organizations own reusable curriculum; tenants are separate security workspaces, one organization may own multiple tenants, and users may have multiple separately scoped memberships. Organization curriculum permissions are distinct from tenant roles. Curriculum libraries may be system, personal-user, or organization owned. Shared curriculum is adopted by reference to an exact immutable source; intentional customization creates an immutable organization-owned derivative with preserved provenance. Reusable organization-owned course templates remain separate from tenant-specific course offerings. Cross-organization evidence contributions are explicit and scoped, while source tenant/student ownership and access controls remain in force. Evidence source identity and snapshots are distinct. Interpretations preserve creator attribution; corrections link a new record without overwriting the original. Learning-state history preserves authorized provenance and prior versions. AI evidence or interpretation alone does not become authoritative learning state.
- **Scope and consequences:** Preserve message admission, idempotency, asynchronous processing, worker recovery, and existing datasets. Migration 0003 is a schema foundation only; no application behavior or production database change is included. Exact role/capability codes and any transition semantics must be transcribed from their approved source rather than inferred.
- **Approval evidence:** Current project-owner instruction beginning “We are officially beginning the AI Tutor implementation phase,” explicitly stating that the conceptual architecture approval process is complete and Decisions 80–86 plus DATA-10/DATA-11 are authoritative, with the listed reconciliation topics.
- **Contracts:** `docs/schema.md` §34; `docs/security.md` “Stage 3 curriculum ownership and evidence contribution”; `docs/architecture.md` §31.9; `docs/stage-3-data-implementation-blueprint.md`. Historical Slice 2a handoff remains unchanged.
