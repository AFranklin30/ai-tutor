# Slice 2a Stage 3 handoff — 2026-10-08

- **TASK:** COMPLETE for Stage 3 development review only. Not deployed. Stop before Stage 4.
- **IMPLEMENTED:** Session-ordered PostgreSQL claiming; UUID claim tokens; independent heartbeat; fixed attempt deadlines; fenced completion/failure/cancellation; bounded retry and crash recovery; graceful shutdown; metadata-only events/metrics. Deterministic processor fakes only.
- **FILES CHANGED:** New `ai_tutor/processing_repository.py` (ordered discovery/locks/writes), `ai_tutor/processing_service.py` (transactional ownership and policy), `ai_tutor/worker.py` (async runner), `ai_tutor/worker_observability.py` (safe logs/metrics), `tests/test_worker.py` (55 cases). Updated implementation status in `README.md`, `docs/architecture.md`, `docs/architecture-decisions.md`, `docs/ai-runtime.md`, `docs/evals.md`; recorded staged authorization in `docs/decisions.md`; added this handoff. Earlier Stage 1/2 working-tree changes are preserved. No Stage 3 migrations, dependencies, admission changes, or endpoint additions.
- **CONTRACTS USED:** `decisions.md` SLICE2A-001 and STEP5-001-A1; `schema.md` §31.6; `architecture.md` §31.8; `ai-runtime.md` Slice 2a; `security.md` Slice 2a execution authorization; `api-contract.md` admission/replay; `evals.md` staged verification. User expressly authorized Stage 3 after Stage 2 acceptance.

## Request/data flow and transactions

1. Existing POST admission authenticates and authorizes; commits input/sequence/job/key together. No Stage 3 changes to this boundary. Same-key FAILED replay remains HTTP 200 and read-only.
2. Worker discovery reads oldest unresolved heads and ends its transaction. Each candidate gets a short transaction locking user → session → current authorization rows → exact oldest unresolved message → job. Locked heads never cause later messages in the session to be selected. FAILED and backoff heads block later work.
3. Claim transaction changes authoritative message status and coupled job metadata atomically, increments persisted claim counts, and returns a claim only after commit. Current account/enrollment/coursework and closure checks gate processing. NORMAL closure permits admitted work; revocation or administrative/unknown closure cancels unfinished scope.
4. Processor runs outside database transactions. A separate async heartbeat task uses its own short database transactions. Before dispatch, renewal rechecks ownership/auth and the remaining safe call window. Defaults remain timeout 30s, lease 45s, heartbeat 10s, deadline 90s, two claims/generation, retry delay 2s, shutdown grace 35s.
5. Completion reacquires the same lock order and checks live token/generation/lease/deadline and current authorization. Tutor insertion plus COMPLETED/job finalization commit together. Winning token is retained; repeated completion or uncertain acknowledgement resolves to the single durable response. The database unique constraint remains authoritative.
6. Failure/retry/cancellation use the same fencing. Expired claims are recovered under locks, consume the existing budget, and either requeue after backoff or become FAILED. Worker shutdown stops claiming, maintains heartbeat during grace, then cancels local processing and leaves lease recovery; it does not invent domain cancellation.

All worker transactions have local lock/statement timeouts. No external processor executes under database locks. Revocation/administrative writers must continue to use the documented lock discipline.

## Verification

Executed against local PostgreSQL 14 using isolated per-test schemas and actual Alembic upgrades:

```sh
TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q tests/test_worker.py --tb=short
# 52 passed in 5.66s (initial focused run)

TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q
# 164 passed in 13.43s (109 existing + final 55 worker cases)

.venv/bin/ruff check .
# All checks passed!
.venv/bin/ruff format --check .
# 40 files already formatted (final check)
```

The full suite includes migration/backfill/constraint tests, separate-process claim contention, locked-head behavior, expiry/crash recovery, stale completion/failure/renewal/cancellation, finalization rollback, lost acknowledgement, policy revocation, NORMAL/admin/unknown closure, timeout/heartbeat failure, graceful completion/shutdown, database backoff, and logging privacy. No tests skipped or remaining failures in the reported run.

No standalone type checker is configured. No live-model eval, deployment/supervisor test, external provider cancellation test, or load test was run: those integrations are outside Stage 3 and remain unverified. Deterministic fakes do not establish model quality, safety, or provider latency.

## Contract check / results

| Classification | Files and contract | Evidence and action |
| --- | --- | --- |
| MATCH | `processing_repository.py`, `processing_service.py`; schema §31.6, architecture §31.8 | Exact-head selection, lock order, sole message status, coupled job metadata, unique tutor result; PostgreSQL concurrency/rollback tests pass. |
| MATCH | `worker.py`, `processing_service.py`; ai-runtime Slice 2a, SLICE2A-001 | Fresh tokens, fixed deadline, independent renewal, bounded budget/backoff, recovery, and shutdown tested; no processor under DB locks. |
| MATCH | `processing_repository.py`, `processing_service.py`; security Slice 2a, architecture §31.8 | Authorization and closure checked on claim/renewal/finalization; stale callbacks cannot cancel replacement work. Revocation/closure tests pass. |
| MATCH | Unchanged admission/API; api-contract admission/replay, SLICE1-004 | Full existing suite passes, including FAILED replay without new job/attempt. No GET or retry endpoint added. |
| MATCH | `worker_observability.py`, `tests/test_worker.py`; security logging rules, evals staged verification | Logs exclude content/provider exception bodies/claim tokens; deterministic failure injection and concurrency evidence. Metrics have no high-cardinality ID labels. |
| DOCUMENTATION_DRIFT | README, architecture §31.8, ai-runtime Slice 2a, architecture-decisions ADR-014 | Prior statements that worker implementation was pending were synchronized to this authorized Stage 3 implementation. No contract policy altered. |

No remaining IMPLEMENTATION_BUG or DECISION_REQUIRED identified within Stage 3. Requirements/mastery/AI authority boundaries are preserved: this worker neither writes mastery nor adds curriculum/model/tool authority. Full product and later-slice behavior is not certified by this scoped review.

- **DECISIONS MADE:** Ordinary implementation details only: async injected callable, transaction-local query timeouts, read-only discovery followed by candidate transactions, metadata instrumentation. No new product/design policy.
- **APPROVED CONTRACT CHANGES:** None. Recorded the user's Stage 3 authorization and synchronized implementation/verification status.
- **DEVIATIONS:** None from the Stage 3 contract. Production processor and deployment wiring deliberately remain absent.
- **KNOWN RISKS / TODO:** Exactly-once external execution remains impossible; cancellation-resistant providers may continue remotely. Processor implementations must be nonblocking async and return validated student-safe text. Future deployment must wire termination signals to `Worker.run(stop)` and configure supervision/connections/telemetry export. Discovery currently reads all unresolved session heads (controlled-demo scale); large-backlog performance is unmeasured. No production safety/output policy is inferred from the fake. No GET delivery yet.
- **NEXT LOGICAL SLICE:** Stage 4 model-client abstraction/deterministic fake integration under the approved staged plan, only after human review. No work on that stage has begun.
