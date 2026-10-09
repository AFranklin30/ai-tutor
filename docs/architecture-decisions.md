# Architecture decision records

Snapshot reviewed 2026-10-08 for repository publication. These ADRs explain existing
approved contracts and the actual Slice 1 implementation. They do not independently
approve new behavior. [decisions.md](decisions.md) remains the approval log; the domain
contracts identified by [AGENTS.md](../AGENTS.md) remain authoritative.

Implemented is distinguished from planned below. No comparative technology evaluation
is claimed where the historical contracts do not record one. All source paths are relative
to the repository root.

## ADR-001 — Python and FastAPI backend

- **Status:** Confirmed; implemented.
- **Context/problem:** The project needs a validated HTTP boundary for tutoring operations.
- **Decision:** Use Python, FastAPI, and Pydantic, served by Uvicorn.
- **Rationale:** The approved stack supports explicit request validation and a small backend application.
- **Tradeoffs:** Application security and business rules remain backend responsibilities, not framework guarantees.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/architecture.md §2; ai_tutor/api.py; pyproject.toml.

## ADR-002 — PostgreSQL for structured persistent data

- **Status:** Confirmed; implemented.
- **Context/problem:** Student work and related authorization/idempotency records need relational integrity and durable storage.
- **Decision:** Use PostgreSQL through SQLAlchemy and psycopg, with Alembic migrations.
- **Rationale:** Foreign keys, uniqueness constraints, transactions, and row locks support the approved persistence invariants.
- **Tradeoffs:** Local development/tests need PostgreSQL; migration downgrade destroys its tables. pgvector is planned, not part of this migration.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/schema.md §31.5; migrations/versions/0001_message_admission.py.

## ADR-003 — Separate API, authentication, service, and repository layers

- **Status:** Confirmed; implemented.
- **Context/problem:** HTTP parsing, identity, business decisions, and SQL should have clear responsibilities.
- **Decision:** API validates/maps responses; authentication resolves credentials; service authorizes and owns transactions; repository executes SQL.
- **Rationale:** This follows the approved modular-monolith boundaries and keeps persistence separate from HTTP concerns.
- **Tradeoffs:** More modules than an all-in-one endpoint; these are not microservices.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/architecture.md §§4–7, 15, 31.7; ai_tutor/{api,auth,service,repository}.py.

## ADR-004 — Service-owned database transactions

- **Status:** Confirmed; implemented.
- **Context/problem:** Message and idempotency writes must either both commit or both roll back.
- **Decision:** MessageService.admit owns the SQLAlchemy session transaction. Repositories do not commit.
- **Rationale:** One transaction boundary covers authorization locks, replay/admission checks, and coupled inserts.
- **Tradeoffs:** Locks remain held until commit/rollback; future external model calls must not extend the durable-input transaction.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/api-contract.md §6; ai_tutor/service.py; tests/test_messages.py.

## ADR-005 — Commit before successful admission response

- **Status:** Confirmed; implemented.
- **Context/problem:** A success response must not claim durability before the database commits.
- **Decision:** Return from the service after the transaction context exits successfully; new messages are PENDING.
- **Rationale:** Preserves student input before any future AI processing.
- **Tradeoffs:** Commit failure or uncertain outcome returns safe 503; successful commit followed by lost delivery requires replay. This does not guarantee network delivery.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/decisions.md SLICE1-003; ai_tutor/service.py; ai_tutor/api.py.

## ADR-006 — Scoped idempotency for student submissions

- **Status:** Confirmed; implemented.
- **Context/problem:** Client retries and lost responses must not create duplicate logical messages.
- **Decision:** Persist a message reference with UNIQUE(student_id, operation, idempotency_key). Compare parsed content exactly, not session ID or JSON serialization. Return 201 creation, 200 authorized replay, 409 changed content.
- **Rationale:** Database protection and replay preserve one logical send despite retries/concurrency.
- **Tradeoffs:** Keys span sessions for one student/operation; another authorized session with the same key/content replays the original message. Keys persist for the demo lifetime.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/decisions.md SLICE1-002–003; docs/api-contract.md §5; ai_tutor/models.py; ai_tutor/repository.py.

## ADR-007 — Student-level row locking

- **Status:** Confirmed implementation choice under approved concurrency guarantees.
- **Context/problem:** Same-student requests can race across sessions while sharing an idempotency-key scope.
- **Decision:** Lock the user row for admission; lock session and relevant authorization rows through commit. Retain the independent unique constraint.
- **Rationale:** A small, understandable concurrency strategy supports correctness in the controlled demo.
- **Tradeoffs:** Same-student sends serialize, limiting that student’s throughput. No distributed worker ownership/lease design is implied.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/schema.md §31.5; ai_tutor/repository.py; tests/test_messages.py concurrency cases.

## ADR-008 — Backend-authoritative authorization

- **Status:** Confirmed; implemented for Slice 1.
- **Context/problem:** Client fields, frontend controls, and future model output cannot establish permission.
- **Decision:** Derive principal from the server credential map; verify active user/student role, session ownership, enrollment, assignment eligibility, and coursework consistency.
- **Rationale:** Protects records and keeps enrollment distinct from assignment release. Replay still requires access and can resolve before the ACTIVE-only new-send gate.
- **Tradeoffs:** Requires pre-provisioned users/coursework/session relationships. Protected lookups return 404; visible forbidden actions return 403.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/security.md; docs/decisions.md SLICE1-001–002; ai_tutor/auth.py; ai_tutor/service.py.

## ADR-009 — Preserve message history

- **Status:** Confirmed; application-level append-only content.
- **Context/problem:** Later processing failures or corrections must not erase original student submissions.
- **Decision:** The implemented repository only inserts message content; there is no message edit/delete API. Processing metadata is separate from content.
- **Rationale:** Preserves the original evidence of what the student submitted and its traceability.
- **Tradeoffs:** Slice 1 originally relied on application history preservation. SLICE2A-001 Stage 1 now rejects ordinary message history UPDATE/DELETE through database triggers; database administrators can still bypass controls. Production redaction/retention remain unresolved; revision 0002 rejects populated downgrade.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/schema.md §§11, 22–23; ai_tutor/repository.py; ai_tutor/models.py.

## ADR-010 — Privacy-aware operational logging

- **Status:** Confirmed; implemented for request completion.
- **Context/problem:** Diagnostics should not duplicate sensitive student/model content or expose credentials.
- **Decision:** Emit allow-listed JSON metadata: trace/message/session identifiers, content length, status, latency, and error category. Sanitize public errors.
- **Rationale:** Operational metadata can identify an interaction without logging its content.
- **Tradeoffs:** Metadata still requires authorized handling. This slice does not implement telemetry access/retention/export policy or claim regulatory compliance.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/security.md Steps 9–10; ai_tutor/observability.py; ai_tutor/api.py; tests/test_messages.py.

## ADR-011 — OpenTelemetry-compatible instrumentation

- **Status:** Confirmed; limited implementation.
- **Context/problem:** Latency/failure attribution requires interaction correlation across boundaries.
- **Decision:** Create request and transaction spans, propagate valid W3C trace context, and persist a trace ID on admitted messages. Disable automatic exception-content capture on those spans.
- **Rationale:** Implements the approved instrumentation standard while protecting sensitive exception/SQL data.
- **Tradeoffs:** No exporter, collector, dashboard, or alert system is configured. Correlation IDs are not identity or idempotency authority.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/architecture.md §25.1; ai_tutor/api.py; ai_tutor/service.py.

## ADR-012 — PostgreSQL-backed asynchronous processing

- **Status:** Approved roadmap, STEP5-001-A1 and SLICE2A-001; Stages 1–2 persistence and compatible admission implemented; worker processing remains unimplemented.
- **Superseded or resolved by:** ADR-014 and decisions.md SLICE2A-001. The Slice 2 worker and lease mechanisms described as unimplemented above are built: ordered claims, lease/heartbeat renewal, fixed deadlines, recovery, and stale-owner fencing. Production model provider and deployment platform remain unresolved.
- **Context/problem:** Admission must become durable before expensive tutoring work, and the stable baseline must remain usable while future processing is explored.
- **Decision:** Slice 1 stops at PENDING. Plan Slice 2 asynchronous processing on feat/async-message-processing; later work must honor approved ownership, retry, recovery, and commit guarantees.
- **Rationale:** Separates current proven admission from future AI behavior and preserves a reviewable main baseline.
- **Amendment:** STEP5-001-A1 selects one separately deployed worker using PostgreSQL as the durable work source. Clients initially use authenticated GET polling. Dedicated queue services, Redis, Celery, RabbitMQ, and Kafka are excluded. Worker deployment and queue-service selection are distinct decisions.
- **Tradeoffs:** Additional deployment supervision and database load; SLICE2A-001 now specifies discovery/ownership/recovery and polling wire details. Provider and deployment platform remain unresolved. A feature branch alone grants no design approval.
- **Alternatives considered:** Synchronous POST processing, API-process background tasks, dedicated broker/task platform, repeated POST polling, and push delivery; see STEP5-001-A1 for tradeoffs.
- **Evidence:** docs/architecture.md §§31.2–31.4; docs/ai-runtime.md; docs/decisions.md STEP5-001-A1, STEP5-002, STEP6-001, REPO-001. decisions.md remains the approval authority.

## ADR-013 — Demo opaque bearer credentials; production identity deferred

- **Status:** Confirmed; demo implemented, production mechanism unresolved.
- **Context/problem:** Slice 1 needs trusted identity without building a full account-management system.
- **Decision:** Map SHA-256 digests of operator-provisioned opaque bearer credentials to existing user UUIDs in server-side configuration; verify the mapped user in PostgreSQL.
- **Rationale:** Implements the approved synthetic/local authentication mechanism without accepting client student IDs.
- **Tradeoffs:** No login, registration, password management, OAuth, issuance endpoint, or production identity-provider integration. Configuration/provisioning is external to this endpoint.
- **Alternatives considered:** No comparative evaluation recorded in the cited sources.
- **Evidence:** docs/decisions.md SLICE1-001; docs/security.md Slice 1; ai_tutor/auth.py; ai_tutor/config.py.

## Scope and verification

Application endpoints admit student messages and read their authorized status/results. The initial Alembic migration
creates ten supporting tables; tests exercise the real PostgreSQL boundaries. AI response
generation, RAG, and agent tools remain planned; the Stage 3 background worker is tested with deterministic processors. See [README.md](../README.md)
for current verification results and [SLICE1_HANDOFF.md](../SLICE1_HANDOFF.md) for the implemented
boundary walkthrough. Future ADR updates must trace back to actual human approvals or clearly
identify proposals; they must not silently redefine a contract.

## ADR-014 — Slice 2a processing persistence and staged deployment

- **Status:** Approved design; Stages 1–4 persistence/admission/worker/model-client abstraction and fake implemented for development review; Stage 5 polling also implemented; production provider pending.
- **Decision:** SLICE2A-001 uses a job table without duplicate status, session sequences and FAILED barriers, leased/fenced workers, unique correlated tutor responses, classified closure/cancellation, and nested authenticated status GET. Future explicit retries permit only known transient failures under authorization, ACTIVE session, budgets and rate limits; no new student retry endpoint in Slice 2a.
- **Tradeoffs:** Deferred integrity triggers require coordinated message/job writes and fixture updates. Revision 0002 must not run with old admission. Legacy order uses deterministic timestamps/UUIDs; unknown closure fails closed. PostgreSQL remains durable authority; no broker or exactly-once external-call claim.
- **Evidence:** decisions.md SLICE2A-001; schema.md §31.6; architecture.md §31.8; ai-runtime.md Slice 2a; api-contract.md polling.
