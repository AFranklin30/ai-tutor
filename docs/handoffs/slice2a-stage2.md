# Slice 2a Stage 2 handoff — 2026-10-08

TASK: COMPLETE for review — integrate admission and fixtures with revision 0002. Continued development only, not deployment. Stop before Stage 3.

IMPLEMENTED: Allocate session_sequence under the already-held session lock, advance its counter, insert PENDING student message, insert an unclaimed processing job, and associate the key in one transaction. Return 201 only after commit. Authorized replay returns 200/current status without changing job, message, key, or counter, including FAILED and CLOSED-session replay.

FILES CHANGED IN THIS STAGE:
- ai_tutor/repository.py: sequence allocation, sequence-bearing message insert, and processing-job insertion; no repository commits.
- ai_tutor/service.py: invoke those writes only in the validated new-send branch.
- tests/conftest.py: valid FAILED-state test setup through allowed transitions and coupled terminal job metadata.
- tests/test_messages.py: preserve original assertions; correct CLOSED/FAILED fixtures; assert job cardinality and no replay writes; add per-write rollback and concurrent-sequence coverage.
- tests/test_processing_schema.py: retain obsolete-writer rejection using fault injection; add HTTP replay and fresh admission after actual legacy-data upgrade.
- README.md; docs/schema.md; docs/architecture.md; docs/architecture-decisions.md; docs/api-contract.md; docs/ai-runtime.md; docs/evals.md: synchronize implementation status and verification.
- docs/handoffs/slice2a-stage2.md: this report.

CONTRACTS USED: SLICE1-004 (FAILED replay=200), SLICE2A-001, schema.md §31.6, architecture.md §31.8, API authorization/replay/admission contracts. Human explicitly accepted Stage 1 for continued development and authorized Stage 2 only. No new design decision or schema change.

REQUEST/DATA FLOW: Existing request validation → opaque-bearer identity → user/session locks and authorization → replay lookup. Replay returns existing state. New send checks ACTIVE/coursework → sequence/counter → student message → job → key → COMMIT → 201. Any write/commit failure rolls back all coupled writes; existing safe 503 behavior remains. No processing attempt starts.

## Classification of all 18 Stage 1 failures

All were IMPLEMENTATION_BUG findings attributable to approved schema integration (including incompatible test setup). No unrelated failures were found. Each named case now passes.

| Prior failing test in tests/test_messages.py | Cause / correction |
| --- | --- |
| test_created_pending_visible_after_commit | Missing sequence/job in admission; integrate coupled writes. |
| test_closed_new_send_but_replay_allowed | Admission dependency plus CLOSED fixture missing closure_reason; use NORMAL. |
| test_key_boundaries[!] | Valid admission rejected by new schema; integrate coupled writes. |
| test_key_boundaries[255 tildes] | Same schema-admission dependency; boundary assertion unchanged. |
| test_replay_canonical_json_and_exact_content_conflict | Initial admission never committed; preserve exact-content comparison. |
| test_key_scope_is_student_and_operation_not_session | Initial admission failed; preserve student/operation key scope and original-session authorization. |
| test_replay_still_checks_authorization | Setup admission failed; keep revoked-enrollment 404 assertion. |
| test_replay_reads_current_processing_state_without_processing | Admission dependency plus direct PENDING→FAILED fixture incompatible with transition/job guards; supply valid FAILED setup. |
| test_failed_replay_returns_200_without_processing_writes[ACTIVE] | Same FAILED setup dependency; retain 200/same-ID/read-only assertions and snapshot jobs/counters. |
| test_failed_replay_returns_200_without_processing_writes[CLOSED] | Same dependency plus NORMAL closure reason; preserve read-only CLOSED replay. |
| test_concurrent_duplicate_requests | Each new-send attempt violated schema; preserve exactly one 201 and five 200 assertions. |
| test_database_unique_constraint_protects_without_service_lock | Initial setup and manual duplicate write lacked sequence/job; fix setup and require the actual uq_idempotency_scope failure. |
| test_rollback_between_message_and_idempotency_insert | New schema prevented normal recovery admission; retain rollback and subsequent 201 assertions. |
| test_commit_failure_never_returns_success | Subsequent recovery send could not satisfy schema; retain 503/empty-state/201 assertions. |
| test_lost_response_replay_and_metadata_logs | Initial admission failed so no accepted result existed; preserve metadata/privacy assertions. |
| test_configurable_length_and_maximum | Valid maximum-length send failed persistence; keep 201/422 assertions. |
| test_distinct_keys_allow_distinct_messages | Both valid admissions failed persistence; retain separate-message assertions. |
| test_concurrent_same_key_different_payload | Neither candidate could commit; retain exactly 201/409 assertion. |

The Stage 1 negative test is retained as test_legacy_admission_write_remains_rejected: inject the obsolete message writer and still require 503 plus empty input/key/job tables. The production path is now compatible; this test does not demand that it remain broken.

TESTS/EVALS RUN:
- TEST_DATABASE_URL pointing to the disposable local PostgreSQL 14.19 server, .venv/bin/pytest -q --tb=short: 109 passed in 8.26s. This includes all migration/schema tests, the 18 previously failing cases, and six new cases (four rollback boundaries, concurrent distinct sequences, and upgraded-data admission).
- .venv/bin/ruff check ai_tutor migrations tests: passed.
- .venv/bin/ruff format --check ai_tutor migrations tests: passed.
- git diff --check: passed.
- No AI evaluations: no model behavior is implemented. No separate static type checker is configured. Real database tests provide migration/application integration evidence, not future worker or production deployment evidence.

RESULTS: MATCH for approved admission, authorization, idempotency, read-only FAILED replay, and atomic persistence. All 18 integration bugs resolved; zero remaining test failures. No schema weakening, skipped tests, or altered public assertions.

DECISIONS MADE / APPROVED CONTRACT CHANGES: No new product/schema/API decision. Applied the previously approved contract under explicit Stage 2 authorization. Only implementation-status documentation changed.

DEVIATIONS: None. Existing uncommitted Stage 1 and earlier documentation/test work was preserved. Migration 0002 and database constraints were not changed in Stage 2.

KNOWN RISKS / TODO: Work remains PENDING; no worker, model client, GET polling, or student-facing explicit retry exists. Old application versions still cannot write revision 0002. Not deployed; test migrations ran only in disposable isolated schemas.

NEXT LOGICAL SLICE: Stage 3 claiming/order/leases/fencing/retry/recovery after this review. Do not start it automatically.
