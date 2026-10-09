> **Stage 6 review boundary:** the asynchronous lifecycle is verified end to end with
> real PostgreSQL and deterministic model fakes: 217 tests passed. Production model
> integration and deployment remain pending. Stop for review; not deployed.

# AI Tutor

A K–12 tutoring project designed to help students learn through guided instruction,
with an initial focus on **Grade 7 mathematics**. The goal is demonstrated understanding:
identify confusion, offer appropriate scaffolding, and verify learning rather than simply
supply answers. Students are the primary learners; teachers retain instructional judgment
and authority over official mastery.

**Current status: Slice 2a asynchronous message processing is implemented for review.**
The repository contains the backend foundation, the PostgreSQL-backed worker, the
deterministic model-client boundary, authenticated status polling, and the approved
system-design contracts. It does not yet call a production model provider or provide a
frontend. Development currently uses synthetic student data in a controlled local demo;
production use with children's records is not approved.

## Problem and goals

Students need timely help when they get stuck, while teachers need useful evidence about
where support is needed. The planned Tutor will use approved curriculum and selected learning
evidence to ask diagnostic questions, scaffold reasoning, and verify understanding. It must
preserve student work, protect access to educational records, and keep official mastery under
human authority. These tutoring capabilities are design goals, not claims about Slice 1.

## Architecture

Implemented request path:

```text
Client → FastAPI/Pydantic → Authentication → Service Layer → Repository → PostgreSQL
                                               │                            │
                                               └── response after COMMIT ←──┘
```

This is a modular monolith. The service owns authorization, replay/admission decisions,
and transactions; repositories execute database operations. New messages remain `PENDING`.

Planned asynchronous AI processing will consume durably admitted work, establish processing
ownership, and eventually coordinate authorized retrieval, selected context, model calls,
validated tools, and durable tutor output. Approved amendment STEP5-001-A1 selects one
separately deployed PostgreSQL-backed worker and authenticated GET status polling, without
a dedicated queue service. SLICE2A-001 now approves scheduling, ownership/recovery, and
polling contracts. Stages 1–4 implement database persistence, compatible admission, the worker runtime,
and a deterministic model-client integration boundary.
Production model processing remains **not implemented**; Stage 5 supplies authenticated GET polling. Worker tests verify
single-owner finalization, stale-owner rejection, idempotency, and commit boundaries.

## Current implementation — Slice 1

- One message-admission endpoint with Pydantic validation and safe errors.
- Server-provisioned opaque bearer credentials mapped to existing users; no login/token issuer.
- Backend authorization, active course enrollment, explicit assignment eligibility, and
  assignment/problem/course consistency checks.
- SQLAlchemy service-owned transactions atomically allocate a per-session sequence and persist
  the PostgreSQL student message, unclaimed processing job, and idempotency record.
- Exact-content replay, database unique constraints, and student-level locking for concurrency.
- `201` creation and `200` replay; new messages are durably `PENDING` before success is returned.
- OpenTelemetry request/transaction spans and trace-context propagation, plus structured,
  metadata-first operational logs. No exporter, dashboard, or monitoring platform is configured.

AI-generated responses, RAG, Context Builder, model integration, orchestration, tool execution,
and explicit failed-message processing are not implemented.

## Technology stack

| Area | Used now |
| --- | --- |
| Backend/API | Python, FastAPI, Pydantic, Uvicorn |
| Persistence | PostgreSQL, SQLAlchemy Core/session transactions, psycopg |
| Migrations | Alembic |
| Testing | pytest, HTTPX/FastAPI TestClient, real PostgreSQL |
| Quality checks | Ruff lint/format; Python compilation |
| Instrumentation | OpenTelemetry API/SDK; Python logging with JSON metadata |

pgvector is approved for future retrieval but is not used or installed by the Slice 1 migration.
No model provider, worker framework, or deployment platform is implemented here.

## Documentation and workflow

- [Engineering instructions](AGENTS.md) define contract authority and scope discipline.
- [Requirements](docs/requirements.md), [architecture](docs/architecture.md),
  [schema](docs/schema.md), and [API](docs/api-contract.md) define the approved system.
- [Security](docs/security.md), [AI runtime](docs/ai-runtime.md), and
  [tests/evals](docs/evals.md) cover their respective boundaries.
- [Approved decisions](docs/decisions.md) remains the approval log.
- [Architecture decision records](docs/architecture-decisions.md) explain the implemented
  choices and distinguish them from proposed future mechanisms.
- [Slice 1 handoff](SLICE1_HANDOFF.md) records the code boundaries and original verification.

`main` is the stable Slice 1 baseline. Subsequent Slice 2 work belongs on
`feat/async-message-processing`; creating that branch does not implement or select its runtime design.
The GitHub repository is private initially.

## Roadmap

| Slice | Scope | Status |
| --- | --- | --- |
| 1 | Message Admission | Implemented |
| 2 | Asynchronous AI Processing | Stages 1–6 implemented/validated for review; production model provider pending |
| 3 | Agent Orchestration and Retrieval | Planned |
| 4 | Verification and Evaluation | Planned expansion of existing tests and eval contracts |

## Message admission contract

Implemented: `POST /api/v1/coaching/sessions/{session_id}/messages` through PostgreSQL commit.
New input starts `PENDING`; the Slice 2a worker then processes it with a deterministic model
fake. Production model integration is not implemented. This is a synthetic/local demo.

## Local setup

Tested with Python 3.9.6 and PostgreSQL 14.19. Dependencies are pinned in
`requirements.lock`; `pyproject.toml` records supported ranges. Use a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost/ai_tutor'
.venv/bin/alembic upgrade head
```

Provision existing users, course enrollment, assignments/problems, assignment/problem
membership, explicit student-assignment eligibility, and ACTIVE coaching sessions outside
this endpoint. `tests/conftest.py` demonstrates complete synthetic provisioning through the
SQLAlchemy tables; it is not a production provisioning service. No login or session-creation
endpoint is included. `ACTIVE` enrollment plus eligibility are required for new sends.

Supply `DEMO_CREDENTIALS_JSON` in server-side configuration as a JSON object mapping
SHA-256 hex digests of operator-provisioned opaque bearer credentials to existing user UUIDs.
Do not put the raw credentials in that mapping, source control, logs, or request bodies.
The application authenticates the credential and checks that its mapped user exists/is active.
Production credential lifecycle and authentication are deferred. Configuration is read from
process environment variables; the application does not automatically load a `.env` file.
For a startup-only check without provisioned credentials, `export DEMO_CREDENTIALS_JSON='{}'`
is valid and denies all message authentication until a real demo mapping is supplied.

```sh
.venv/bin/uvicorn ai_tutor.api:create_app --factory --host 127.0.0.1
```

Request: `Authorization: Bearer <opaque credential>`, `Idempotency-Key: <logical-send-key>`,
JSON `{"content":"I need a hint."}`. New creation returns 201 with
`{"student_message_id":"<UUID>","status":"PENDING"}`; same-key/content replay returns 200
and the current state. Reuse the original key if response delivery is uncertain. A new key
represents a new send. Content is preserved, not trimmed. Empty/whitespace-only content,
unknown body fields, oversized content, and invalid keys are rejected with safe 422 errors.
PostgreSQL text cannot store NUL; the request validator rejects that unrepresentable value.
The default content limit is 4,000 characters (`MAX_MESSAGE_CHARACTERS` is configurable).

Keys are scoped to student + operation, **not session**. Reusing a key with identical content
on another authorized session returns the original message; it does not create a message in
the new session. Access to the original session/course is checked as well. Replays can resolve
after closure but never initiate processing. A database error returns safe 503 without claiming
the input was saved; same-key replay can determine the result of an uncertain commit.

## Testing and verification

Stage 2 verification on **2026-10-08**: the complete real-PostgreSQL suite passed
**109 tests**, including migration round-trip/backfill and atomic admission tests.
All 18 Stage 1 integration failures are resolved without weakening their public assertions.
See [Stage 2 handoff](docs/handoffs/slice2a-stage2.md) for their classification and exact commands.
Worker, model, polling, and explicit-retry behavior remains unimplemented.

Use a disposable PostgreSQL database whose user can create schemas:

```sh
export TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost/ai_tutor_test'
.venv/bin/pytest -q
.venv/bin/ruff check ai_tutor migrations tests
.venv/bin/ruff format --check ai_tutor migrations tests
```

Publication verification on **2026-10-08**: **45 tests passed in 2.91 seconds** against
PostgreSQL 14.19 with Python 3.9.6. Ruff lint/format and dependency checks passed.
Uvicorn factory startup was smoke-tested on localhost: OpenAPI returned 200 and an
unauthenticated valid message request returned 401. No application data was written by that check.

Coverage includes admission/PENDING durability, exact content and canonical JSON replay,
authentication/authorization/non-disclosure, assignment eligibility, CLOSED-session replay,
cross-student/session key scope, duplicate/conflicting concurrent requests, database uniqueness,
write/commit rollback, migration round-trips, and log/trace privacy. AI evals do not apply yet;
a static type checker is not configured. Fault injection is not a production outage/load test.

Each test creates a randomly named schema, runs Alembic, provisions synthetic records,
and drops only that schema afterward. Tests fail rather than silently skip if the test URL
is missing. Real PostgreSQL is necessary for constraint, transaction, locking, and concurrency
checks. The initial migration has no backfill. Its downgrade destroys its tables and is for
disposable development databases only. No migration has been applied to an application database.

## Boundaries and limitations

`api.py` validates requests and maps safe responses; `auth.py` resolves credentials;
`service.py` authorizes and owns the transaction; `repository.py` performs SQL operations;
`models.py` describes the tables. Return from the service occurs only after commit.
A student-row lock serializes that student's concurrent sends; a database unique constraint
independently protects idempotency. This simple design favors correctness over per-student
write throughput. Other students can proceed concurrently. Admission locks session and
existing enrollment/eligibility rows through commit, so concurrent changes cannot invalidate
checks between admission and commit.

Message history has no update/delete application path. Processing metadata may change only
in later approved slices. The initial schema uses a partial unique index for ACTIVE enrollment,
without forbidding inactive enrollment history. There are no cascading deletes of learning history.

Request/transaction spans use OpenTelemetry, propagate valid W3C trace context, and write the
trace ID on new messages. Logs emit allow-listed JSON metadata. Automatic exception-content
capture is disabled on spans to avoid leaking SQL/student data. There is no exporter or
monitoring platform. Trace IDs are correlation only, never identity or idempotency authority.
No type checker is configured yet; Ruff, compilation, and PostgreSQL tests are the current checks.

RAG, Context Builder, models, orchestration, tools, tutor output, explicit retry processing,
production auth, group allocation, and the wider observability platform remain out of scope.


## Slice 2a Stage 3 — Worker review boundary

`ai_tutor.worker.Worker(service, processor).run(stop)` runs one active claim per worker
instance. Construct `ProcessingService` with a SQLAlchemy sessionmaker bound to the same
PostgreSQL database as admission. The injected processor is an async, nonblocking callable
that accepts `ProcessingInput` and returns validated student-safe text; deterministic test
fakes are in `tests/test_worker.py`. No production processor or deployment entrypoint is supplied.
A future deployment entrypoint must connect its termination signal to the asyncio stop event.

The worker commits a claim before calling the processor, renews leases independently, and
fences response/failure writes in separate short transactions. Failed or backoff-delayed
session heads block later messages. PostgreSQL recovers expired claims within the same
persisted budget. Logs exclude input/output and claim tokens; metrics have no exporter.

Stage 3 verification on **2026-10-08**: **164 real-PostgreSQL tests passed**, including
55 worker tests and all 109 existing tests. Ruff lint and formatting passed.
See [Stage 3 handoff](docs/handoffs/slice2a-stage3.md) for transaction boundaries,
contract review, exact commands, and remaining integration responsibilities.


## Slice 2a Stage 4 — Deterministic model-client boundary

`ai_tutor.model_client` provides `ModelClient.generate(ProcessingInput)`, `ModelProcessor`
(the adapter to the existing worker callable), and `FakeModelClient(response)`.
The fake requires explicit synthetic text and is never selected automatically or used as
fallback after provider failure. For a controlled test, inject
`Worker(service, ModelProcessor(FakeModelClient("Synthetic test response")))`.

The adapter makes one call and checks the existing persisted-text shape. The worker still
owns timeout, heartbeat, fencing, and retry budgets. Semantic tutoring/output policy and
production provider selection remain unresolved; a nonempty string is not evidence of safety.
There are no prompts, SDKs, network calls, tools, or new endpoint/migration in this stage.
See [Stage 4 handoff](docs/handoffs/slice2a-stage4.md) for verification and the contract review.


## Slice 2a Stage 5 — Authenticated status polling

`GET /api/v1/coaching/sessions/{session_id}/messages/{message_id}/status` reads one
consistent PostgreSQL snapshot of current account, session/course visibility, message state,
and persisted tutor response. No body or Idempotency-Key is required. All authorized states
return 200 with `Cache-Control: no-store`; FAILED/CANCELLED expose only approved safe errors.
CLOSED sessions remain readable with current authorization. Reads do not create jobs or retries.

No frontend polling loop or production model integration is supplied. See
[Stage 5 handoff](docs/handoffs/slice2a-stage5.md) for exact verification and contract findings.


## Slice 2a Stage 6 — End-to-end and failure validation

The full suite passes **217 tests**, including 19 connected lifecycle cases added in
`tests/test_async_lifecycle.py`. Verification connects actual FastAPI POST/GET routes,
services/repositories, migrated PostgreSQL, the worker, and the configured deterministic
model fake. It includes process termination/recovery, competing workers, FIFO and failure
barriers, policy changes, read-only replay/polling, and atomic output visibility.

No runtime defect was found in Stage 6, and no application code, migration, endpoint, or
contract policy changed. The tests use synthetic content; they do not certify production
model safety, deployment supervision, load capacity, or real-student readiness.
See [Stage 6 acceptance map and handoff](docs/handoffs/slice2a-stage6.md).
