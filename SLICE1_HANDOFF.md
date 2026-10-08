# Slice 1 handoff

TASK: COMPLETE — student-message admission through durable PostgreSQL commit, plus authorized replay. No Slice 2 work.

IMPLEMENTED: FastAPI/Pydantic validation; server-mapped opaque bearer authentication; active-user/student/session/course authorization; explicit assignment eligibility and assignment/problem/course consistency; content-only idempotency; atomic message/key writes; PENDING response after commit; metadata-only logging and trace context.

FILES CHANGED:
- Updated all eight existing `docs/*.md` contracts; approvals are `SLICE1-001`–`SLICE1-003` in `docs/decisions.md`. AGENTS.md and skills unchanged.
- Created `ai_tutor/{__init__,api,auth,config,errors,models,observability,repository,service}.py`.
- Created `migrations/env.py`, `migrations/versions/0001_message_admission.py`, `alembic.ini`.
- Created `tests/conftest.py`, `tests/test_messages.py`, `tests/test_migration.py`.
- Created `pyproject.toml`, `requirements.lock`, `.gitignore`, `README.md`, and this handoff.

CONTRACTS USED: requirements §22.6; API §§2–6 and Slice 1 approval; schema §31.5; security demo authentication and non-disclosure rules; architecture §31.7; evals Slice 1 verification. ai-runtime.md explicitly marks all AI processing as later-slice work.

REQUEST/DATA FLOW:

1. FROM: Client. TO: FastAPI/Pydantic.
   WHAT CROSSES: Session UUID, content JSON, Idempotency-Key, bearer credential, optional W3C trace context.
   WHAT COMES BACK: Validated input or sanitized 422; content is never trimmed.
   CODE THAT REVEALS IT: `ai_tutor/api.py` MessageRequest, create_message, invalid_request.
   WHAT COULD GO WRONG: Missing/malformed/duplicate key, invalid UUID/body, oversized/blank content, identity extras. PostgreSQL text cannot store NUL, so it is rejected at validation. Error output does not echo submitted values.

2. FROM: FastAPI. TO: Authentication and authorization.
   WHAT CROSSES: Credential to the server-owned digest mapping; derived user UUID to service checks.
   WHAT COMES BACK: Authorized student/context, or 401/403/non-disclosing 404.
   CODE THAT REVEALS IT: `auth.py:resolve_principal`; `service.py:admit` and `authorize_context`; repository admission reads.
   WHAT COULD GO WRONG: Unknown/disabled principal, teacher role, another student's session, missing enrollment, unassigned work, inconsistent coursework. Client identity cannot replace the principal. Replay still requires access to the original session/course.

3. FROM: Application service. TO: Repository.
   WHAT CROSSES: Trusted principal, route session, exact content, operation/key, trace ID inside a transaction.
   WHAT COMES BACK: Existing message/current state or inserted message identity; no commit ownership passes to the repository.
   CODE THAT REVEALS IT: `service.py:admit`; `repository.py:existing_message`, `eligible_coursework`, `insert_message`, `associate_key`.
   WHAT COULD GO WRONG: Same-key changed content (409); CLOSED new send (409); absent eligibility (403). Replay resolves before new-send gates. Keys span sessions for the same student/operation; session ID is not part of payload comparison.

4. FROM: Repository. TO: PostgreSQL.
   WHAT CROSSES: Parameterized SQL reads/locks/inserts through SQLAlchemy; no model/tool operations.
   WHAT COMES BACK: Rows and constraint results, or database failure.
   CODE THAT REVEALS IT: `repository.py`; `models.py`; migration `0001_message_admission.py`.
   WHAT COULD GO WRONG: Concurrent duplicates, changed authorization during admission, failed writes. Per-student locking serializes admission, relationship/session locks preserve checks, and UNIQUE(student_id, operation, idempotency_key) independently protects duplicates. Message/key writes roll back together. No cascading history deletes.

5. FROM: Transaction commit. TO: API response.
   WHAT CROSSES: Only the committed message identifier and current status.
   WHAT COMES BACK: 201 for creation, 200 for replay; newly created messages are PENDING.
   CODE THAT REVEALS IT: `service.py:admit` returns after `sessions.begin()` exits; `api.py:create_message` chooses status afterward.
   WHAT COULD GO WRONG: Commit failure/uncertainty produces safe 503 without claiming input was saved. A lost response after successful commit is resolved by same-key replay. No AI processing begins.

TESTS/EVALS RUN:
- `TEST_DATABASE_URL=<disposable local PostgreSQL URL> .venv/bin/pytest -q`: **45 passed in 2.79s**, PostgreSQL 14.19, Python 3.9.6.
- `.venv/bin/ruff check ai_tutor migrations tests`: passed.
- `.venv/bin/ruff format --check ai_tutor migrations tests`: 14 files formatted.
- `.venv/bin/python -m compileall -q ai_tutor migrations tests`: passed after permitting macOS bytecode-cache access.
- `.venv/bin/python -m pip check`: no broken requirements.
- Real PostgreSQL migration upgrade/downgrade/re-upgrade and metadata comparison; synthetic fixtures in isolated schemas. Each schema is removed after its test. No application database migrated.
- Tests cover auth/identity, business eligibility, non-disclosure, key/content boundaries, canonical JSON equivalence, current-state/closed-session replay, cross-session and cross-student scope, concurrent duplicates/conflicts, independent keys, constraint protection without service locks, injected write/commit failures, discarded-response replay, metadata logs, and trace exception privacy.
- No separate static type checker configured; compilation is not type checking. No AI evals apply. No live HTTP disconnect/database-crash test, production auth test, or throughput benchmark was performed; fault tests inject failures around real PostgreSQL transactions.

RESULTS / CONTRACT CHECK:

| Classification | Evidence | Impact/action |
| --- | --- | --- |
| MATCH | API Slice 1 + `api.py:152`, `auth.py:9`, `service.py:27`; validation/identity tests | Approved identity and 201/200/PENDING behavior implemented. |
| MATCH | Schema §31.5 + `models.py:147`, repository writes and migration; concurrent/rollback tests | Unique key scope and coupled commit enforced by PostgreSQL. |
| MATCH | API §5 + service replay branch; canonical-content, closed-session, and cross-session tests | Exact parsed content only; no implicit processing or new send on replay. |
| MATCH | Security + service/repository authorization; telemetry privacy tests | Session/course access, separate assignment eligibility, minimized output/log/trace data. |
| DOCUMENTATION_DRIFT — resolved | Slice 1 approvals vs earlier deferred auth/allocation/replay paragraphs | Scoped deferrals updated; production/future-slice decisions remain open. |
| IMPLEMENTATION_BUG — none outstanding | Final tested Slice 1 implementation and migration | No unresolved mismatch identified in reviewed scope. This is not a production security certification. |
| DECISION_REQUIRED — none blocking Slice 1 | SLICE1-001–003 settle required choices | Production auth, group allocation, AI/recovery mechanisms remain later-slice decisions. |

DECISIONS MADE: Applied explicit human approvals. Implementation choices: SHA-256 credential digests in server configuration, UUID4, SQLAlchemy Core repositories, row locks plus unique constraint, safe JSON metadata logs, and a partial unique ACTIVE-enrollment index. No AI/schema policy beyond this slice was selected.

APPROVED CONTRACT CHANGES: Demo identity; individual assignment eligibility; UUID/status/idempotency persistence; 201/200 response; exact content comparison, key validation and demo-lifetime retention. Recorded before dependent code.

DEVIATIONS: No scope expansion. The initial migration implements only required fields/relationships; future conceptual entities remain unimplemented. Runtime only creates PENDING; tests may seed FAILED metadata to verify replay never initiates processing.

KNOWN RISKS / TODO: Demo credentials require external provisioning and operator-managed configuration. Users/coursework/sessions must already be provisioned (fixture example in tests). Per-student serialization favors correctness over per-student throughput. No telemetry exporter/platform or production deployment has been configured. Migration downgrade destroys its tables and is only for disposable databases.

NEXT LOGICAL SLICE: Await explicit instruction. RAG, context building, models, orchestration, tools, tutor generation, and explicit retry processing have not begun.
