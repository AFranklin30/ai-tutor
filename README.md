# AI Tutor

A K–12 tutoring project designed to help students learn through guided instruction,
with an initial focus on **Grade 7 mathematics**. The goal is demonstrated understanding:
identify confusion, offer appropriate scaffolding, and verify learning rather than simply
supply answers. Students are the primary learners; teachers retain instructional judgment
and authority over official mastery.

**Current status: Slice 1 — Student Message Admission is implemented.** The repository
contains the backend foundation and approved system-design contracts. It does not yet
generate tutoring responses or provide a frontend. Development currently uses synthetic
student data in a controlled local demo; production use with children's records is not approved.

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
validated tools, and durable tutor output. Worker/queue technology, scheduling, and physical
ownership/recovery mechanisms are **not implemented or selected by this roadmap**. Existing
contracts govern single-owner finalization, stale-owner rejection, idempotency, and commit
boundaries when those features are implemented.

## Current implementation — Slice 1

- One message-admission endpoint with Pydantic validation and safe errors.
- Server-provisioned opaque bearer credentials mapped to existing users; no login/token issuer.
- Backend authorization, active course enrollment, explicit assignment eligibility, and
  assignment/problem/course consistency checks.
- SQLAlchemy service-owned transactions and PostgreSQL UUID/message/idempotency persistence.
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
| 2 | Asynchronous AI Processing | Planned; separate development branch |
| 3 | Agent Orchestration and Retrieval | Planned |
| 4 | Verification and Evaluation | Planned expansion of existing tests and eval contracts |

## Message admission contract

Implemented: `POST /api/v1/coaching/sessions/{session_id}/messages` through PostgreSQL commit.
New input is `PENDING`; no AI processing exists. This is a synthetic/local demo.

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
