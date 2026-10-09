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
