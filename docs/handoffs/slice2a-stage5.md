# Slice 2a Stage 5 handoff — 2026-10-08

- **TASK:** COMPLETE for authenticated GET status polling; continued development only, not deployed. Stop before Stage 6.
- **IMPLEMENTED:** `GET /api/v1/coaching/sessions/{session_id}/messages/{message_id}/status`; UUID validation, trusted bearer identity, current user/session/course read authorization, all five approved state envelopes, persisted tutor response, safe FAILED/CANCELLED errors, no-store, and GET-specific storage-unavailability wording. No request body/idempotency key required.
- **FILES CHANGED:** `ai_tutor/api.py` (response models/GET/cache and error handling), `ai_tutor/service.py` (read authorization/envelope/invariant checks), `ai_tutor/repository.py` (single snapshot SELECT); added `tests/test_polling.py`. Synchronized README and docs/api-contract.md, ai-runtime.md, architecture.md, architecture-decisions.md, decisions.md, evals.md; added this handoff. No dependencies/migrations/worker changes. Prior working-tree changes retained.
- **CONTRACTS USED:** `api-contract.md` Asynchronous response polling — SLICE2A-001; security Slice 2a/read authorization; schema §31.6; architecture §31.8; ai-runtime durable delivery; evals staged verification; original Stage 5 authorization and human “continue” following Stage 4.

## Request/data flow and transactions

GET UUID validation → demo bearer principal → MessageService.read_status → one repository SELECT joining account, owned session with active course enrollment, route-scoped student message, and correlated tutor response → approved safe response envelope → 200/no-store. Missing/disabled account is 401; non-student role is 403; non-discoverable resources, missing enrollment, mismatched IDs and tutor IDs are 404. This is historical read authorization, not ACTIVE-only/new-assignment eligibility validation.

A single PostgreSQL statement supplies one consistent snapshot of authorization, status, and output. The short service-owned read transaction performs no DML or row locking. Worker completion can occur concurrently; polling sees the complete old or new state, never a mixture. GET never schedules, retries, closes/reopens sessions, or changes learning state. Authentication, query, and error paths use existing metadata logging without input/output content. Returned state is a snapshot, not a promise it cannot change after the read.

SQLAlchemy storage failure returns GET-specific 503 wording, never instructions to resend POST. Detected impossible status/reply combinations return a sanitized 500. Response models exclude claim tokens, provider failures, and retryability fields. POST behavior remains unchanged.

## Tests/evals run

```sh
TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q tests/test_polling.py --tb=short
# Initial run: 22 passed, 1 failed (missing-auth test inherited client default credential).
# Corrected the test to remove the inherited header; no endpoint policy change.
TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q
# 198 passed in 15.44s, including all 23 final polling cases.
.venv/bin/ruff check .
# All checks passed!
.venv/bin/ruff format --check .
# 44 files already formatted
 git diff --check
# Passed, no output
```

Tests use real PostgreSQL migration/schema constraints. SQL capture checks no DML and one snapshot SELECT. A failure-injection test commits worker completion after the SELECT executes but before delivery: the first response remains consistently PROCESSING/null, and the next is COMPLETED with persisted content. Full suite retains earlier worker, admission, model-adapter, migration, and privacy coverage. No remaining failures/skips in the reported full run.

No standalone type checker is configured. Frontend polling cadence, live model behavior, load, and deployment were not tested because those integrations are outside this stage; server endpoint tests do not certify them.

## Results / contract check

| Classification | Files/contracts and evidence | Impact/action |
| --- | --- | --- |
| MATCH | api.py response/GET models; API Asynchronous response polling | Exact route and state envelopes, HTTP 200 for FAILED, no-store, safe 401/403/404/422/500/503; tested. |
| MATCH | repository.py polling_snapshot, service.py read_status; security read authorization and architecture §31.8 | Current account/owned-session/active enrollment from one statement; historical reads remain available without enabling new work. |
| MATCH | repository.py joined snapshot; schema §31.6, API consistent snapshot | One SELECT/no DML; completion between read and delivery cannot tear state/output. No job mutations or new schema. |
| MATCH | Existing admission/worker and full suite; SLICE2A-001 | Retry budgets, mastery/model authority, fencing and POST replay remain unchanged; 198 tests passed. |
| DOCUMENTATION_DRIFT | API, README, architecture, ai-runtime and ADR-014 implementation status | Updated pending GET statements. Corrected ai-runtime's stale claim that FAILED-to-GET mapping was unresolved using the already-approved SLICE2A-001 envelope. No policy selected. |

- **DECISIONS MADE:** Implementation-level choice of one joined query for consistency; no new authorization or API semantics.
- **APPROVED CONTRACT CHANGES:** None; recorded continuation and synchronized implementation status against existing approvals.
- **DEVIATIONS:** None identified. No remaining IMPLEMENTATION_BUG or DECISION_REQUIRED within this scope.
- **KNOWN RISKS / TODO:** Production model integration and output safety policy remain deferred. No frontend poll/backoff/visibility behavior or deployment is supplied. The query has not been load-tested. Snapshot authorization cannot prevent a subsequent revocation after the read; subsequent polls reauthorize.
- **NEXT LOGICAL SLICE:** Stage 6 integration/failure-injection coverage audit and remaining gaps, following review. No Stage 6 work or deployment begun.
