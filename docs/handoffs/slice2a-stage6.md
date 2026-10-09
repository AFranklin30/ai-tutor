# Slice 2a Stage 6 — End-to-end integration and failure validation

**TASK: COMPLETE for development review. Not deployed. Stop after Stage 6.**

## Inspection and approved acceptance criteria

Read AGENTS.md, requirements, applicable API/architecture/schema/runtime/security/eval contracts, and the Stage 2–5 handoffs. No standalone Stage 1 handoff exists in the repository; `SLICE1_HANDOFF.md` is for Slice 1, not Slice 2a Stage 1. Stage 1 was inspected through migration 0002, schema §31.6, its existing tests, and the Stage 2 handoff's compatibility report. This is a missing historical artifact, not evidence that Stage 1 failed or permission to fabricate its historical results.

The repository contains migration 0002 and its triggers/backfill, atomic message/sequence/job/key admission, ordered fenced worker with leases/recovery, deterministic model adapter/fake, and authenticated polling. Existing Stage 1–5 work is uncommitted and was preserved.

Previously approved Stage 6 is PostgreSQL integration and failure-injection validation in the six-stage implementation authorization. Concrete invariants are SLICE2A-001; requirements §§22.1–22.4 and Slice 2a refinements; architecture §31.8; schema §31.6; ai-runtime approved worker contract; security execution/read authorization; API asynchronous polling and idempotent admission; evals deterministic/flow/staged verification. The current human request explicitly enumerates Stage 6 scenarios. No undefined behavior blocks this synthetic lifecycle scope. Deferred product/model policies are not invented or certified here.

## Implemented / changed files

- Added `tests/test_async_lifecycle.py`: 19 parametrized cases joining actual API routes to the existing worker/model adapter/fake and real PostgreSQL, including actual worker-process termination.
- Updated `README.md`: current Stage 6 status and verification limits.
- Updated `docs/evals.md`: Stage 6 acceptance evidence and corrected stale text that GET failure mapping was still undecided.
- Updated `docs/architecture.md` §31.8: connected lifecycle verification status.
- Updated `docs/decisions.md`: recorded explicit Stage 6 authorization; no new design decision.
- Added `docs/handoffs/slice2a-stage6.md`: this report and coverage map.

No application code, migration, dependency, endpoint, or runtime contract changes. No confirmed runtime defects found; no assertions weakened.

## Request/data flow and transaction evidence

Authorized POST → service locks/validates identity, enrollment and coursework → message + session sequence/counter + job + idempotency record commit → 201/PENDING. A separate database connection and GET observe the committed input/job.

Worker discovery → ordered claim/authorization transaction → commit token/PROCESSING → ModelProcessor/configured FakeModelClient outside database locks → current authorization and ownership checks → atomic tutor insertion + COMPLETED/job terminal metadata → GET reads one authorized consistent snapshot. Heartbeats use independent short transactions. Replays and repeated polling do not mutate jobs, counters, inputs, responses, or keys.

A commit-hook test polls through a separate HTTP/DB connection while the completion transaction contains the uncommitted response: GET still returns PROCESSING/null. After commit it returns COMPLETED/persisted output. A rollback-injection test fails after response insertion: GET exposes no output, input/key/job survive, and the claim remains recoverable.

## End-to-end and failure coverage — all passed in the full run

Paths below are relative to `tests/`. The named Stage 6 tests are in `test_async_lifecycle.py`; other evidence is retained existing coverage, not newly implemented behavior.

| Requested scenario | Executed evidence |
| --- | --- |
| Authorized send → durable PENDING input/job → initial poll | `test_connected_lifecycle_competing_workers_replay_and_immutable_polling`; checks separate-connection committed rows and linked IDs. |
| Worker/fake → atomic completion → persisted-response GET | Same connected test through `ModelProcessor(FakeModelClient)`; one input and one tutor response. |
| Repeated polling is read-only | Same test snapshots messages/jobs/keys/session counters before and after repeated GET; `test_polling.py::test_all_states_are_read_only_safe_and_uncached` also traps DML. |
| Identical POST replay / different-payload conflict | Connected test during processing requires 200/same ID and 409 respectively with unchanged snapshot; `test_messages.py` also covers concurrent identical/conflicting admissions. |
| Competing workers | Connected test's second worker cannot claim the busy head; `test_worker.py::test_independent_worker_processes_claim_only_one_session_head` races three independent processes. |
| Crash and expired-claim recovery | `test_actual_worker_process_crash_recovery_and_stale_completion` terminates a spawned worker after claim commit/model entry, shifts persisted timestamps to expiry, recovers within the same budget, and completes through a replacement worker/fake. |
| Heartbeat, deadlines, no external-work locks | `test_worker.py::test_runner_external_work_has_no_database_locks_and_heartbeats`, `test_renewal_cannot_extend_fixed_deadline`, `test_expired_claim_cannot_finalize_before_recovery`, timeout and heartbeat-outage tests. |
| Stale completion/failure/renewal/cancellation | Stage 6 crash test rejects stale completion/failure without writes; existing `test_crash_recovery_new_token_and_all_stale_callbacks_fenced` and generation-mismatch test cover all callbacks. |
| Transient recovery / permanent, unknown, invalid-output failures | `test_processor_failures_fifo_barriers_and_safe_polling` (five cases) exercises faults through model adapter and public polling. |
| Retry exhaustion | Same test requires terminal FAILED after two transient claims; existing model-client cases exercise all three transient categories. |
| FIFO and failed/backoff barriers | Same test admits two inputs, prevents overtaking during backoff/FAILED, and permits the next message only after successful completion; existing locked-head tests retain each lock-boundary check. |
| Closure before claim or during processing | `test_policy_changes_across_connected_lifecycle`: NORMAL completes admitted work; ADMINISTRATIVE/UNKNOWN cancel it; all CLOSED cases reject new sends. |
| Authorization changes before claim/finalization | Same test covers account disable/enrollment revocation; original worker tests also cover eligibility/assignment consistency and heartbeat revocation. |
| Polling across completion commit | `test_polling_cannot_see_uncommitted_tutor_response`; existing polling test also completes between snapshot acquisition and HTTP delivery without tearing the payload. |
| Failed finalization preserves durable input | `test_failed_finalization_preserves_input_and_withholds_output`; existing admission/schema tests cover all coupled admission rollback boundaries and deferred response/state integrity. |
| Unauthorized messages/responses | Connected completed-result test denies other student/teacher; polling suite covers missing/invalid credentials, tutor IDs, mismatched/nonexistent resources and revoked reads. |
| Safe public errors/privacy | Failure cases require generic public errors; existing polling SQL failure and worker logging tests exclude provider/SQL/content/credential/token details. |
| Graceful shutdown / database outage | Existing worker shutdown, in-flight completion, heartbeat database-failure and interruptible-backoff tests remain passing. |

## Tests/evals run

Against disposable local PostgreSQL 14, isolated per-test schemas, Alembic upgrades and enabled integrity triggers:

```sh
TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q tests/test_async_lifecycle.py --tb=short
# 17 passed in 2.13s (initial focused run)

TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q
# 217 passed in 18.01s (198 existing + final 19 Stage 6 cases)

.venv/bin/ruff check .
# All checks passed!
.venv/bin/ruff format --check .
# 47 files already formatted (final check)
git diff --check
# Passed, no output
```

No failures or skips in the full run. An unused import in the new test file was caught by lint and removed before execution; no runtime defect was found. No standalone type checker is configured.

## Contract check / results

| Classification | Contract and implementation/test evidence | Conclusion |
| --- | --- | --- |
| MATCH | Requirements durable-input/output guarantees; schema §31.6; service/repository/worker; connected and commit/rollback tests | PostgreSQL remains authority; input survives failure; uncommitted response is not exposed. |
| MATCH | SLICE2A-001 ordering/ownership/budgets; processing_service.py/worker.py; crash, FIFO, heartbeat and stale-owner tests | One valid finalizer, bounded shared budget, no overtaking, no new broker or model authority. |
| MATCH | Security and API polling/replay; api.py/service.py/repository.py; connected policy and read-only tests | Current authorized reads, closure policy, safe envelopes, no mutation from polling/replay. |
| MATCH | AI-runtime client authority; model_client.py and deterministic fault subclasses | No production LLM, unrestricted records, tools, mastery or curriculum changes; fake-only integration evidence. |
| DOCUMENTATION_DRIFT | evals STEP5-001-A1 paragraph still called GET failure mapping undecided | Corrected using approved SLICE2A-001/API mapping; synchronized Stage 6 implementation status. No behavior decision changed. |
| DOCUMENTATION_DRIFT | Missing standalone Stage 1 handoff | Disclosed as a historical documentation gap. Do not reconstruct an unverified historical run; current full suite verifies migration behavior. |

**Verdict: COMPLETE / MATCH for Stage 6 synthetic integration scope.** No remaining confirmed IMPLEMENTATION_BUG or blocking DECISION_REQUIRED found. Missing historical Stage 1 handoff remains disclosed; it does not invalidate current executable migration verification.

## Decisions, deviations, limits and next boundary

- **DECISIONS MADE / APPROVED CONTRACT CHANGES:** No product, schema, security, retry or API policy decisions. Only test coordination/fault injection and status documentation.
- **DEVIATIONS:** None. Existing tests were retained unchanged; no runtime code was modified.
- **KNOWN RISKS / UNTESTED:** FastAPI is exercised through TestClient, not deployed HTTP/TLS. The crash test kills a real worker process but accelerates expiry through persisted timestamp changes; heartbeat tests use shortened compatible settings. No production supervisor, real DB-server restart/network partition, load benchmark, provider timeout/billing/cancellation, browser polling cadence, semantic output safety, or tutoring-quality evaluation was tested. Exactly-once remote execution is not guaranteed. Deployment wiring and provider/safety policies remain deferred. Fake output is explicit synthetic content, not evidence of safe real-student tutoring.
- **UNIMPLEMENTED:** Production provider and semantic validation, RAG/Context Builder, tools/orchestration, frontend polling, dashboards, explicit student retry, cross-session memory, and remaining full-MVP teaching/mastery/escalation workflows. No claim that completing this infrastructure slice completes the product.
- **NEXT LOGICAL SLICE:** Human review and selection of the next authorized scope. No deployment or next-slice implementation is authorized by this handoff.
