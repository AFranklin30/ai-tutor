# Slice 2a Stage 4 handoff — 2026-10-08

- **TASK:** COMPLETE for the model-client abstraction and deterministic fake. Continued development only; not deployed. Stop before Stage 5.
- **IMPLEMENTED:** Async `ModelClient.generate(ProcessingInput)` protocol; `ModelProcessor` adapter making exactly one client invocation; explicit `FakeModelClient(response)` with no input capture, database/network access, or automatic selection. Existing failure categories, cancellation, text-shape rules, and worker retry authority preserved.
- **FILES CHANGED:** Added `ai_tutor/model_client.py` and `tests/test_model_client.py`. Updated `README.md`, `docs/ai-runtime.md`, `docs/architecture.md`, `docs/architecture-decisions.md`, `docs/decisions.md`, `docs/evals.md`, and this handoff. Preserved all earlier working-tree changes. No worker/admission code modifications, dependencies, migrations, or endpoints.
- **CONTRACTS USED:** SLICE2A-001; ai-runtime Step 6 thin abstraction, Step 7 failure behavior, Slice 2a worker contract; architecture §31.8; schema §31.6 text/status/response boundaries; security selected-context and authority rules; API read-only replay; evals staged verification. User's “continue” advances to Stage 4 of the previously authorized sequence.
- **REQUEST/DATA FLOW:** Existing authenticated admission commits input/job/key → worker authorizes and commits claim → adapter passes selected ProcessingInput to client outside DB transactions → deterministic fake returns configured text → adapter rejects invalid shape → worker rechecks authorization/ownership and atomically persists response/completion. Transient errors reach the worker unchanged; it schedules or terminates under the existing shared budget. Cancellation propagates to the client. No raw provider response, tools, DB session, claim token, or credentials are passed through the input boundary.
- **TRANSACTION BOUNDARIES:** Unchanged from Stage 3. Client and adapter have no database transaction. Claims, heartbeats, and fenced response/failure commits remain worker service responsibilities; no client-internal retry or extra timeout layer.

## Tests/evals run

```sh
TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q tests/test_model_client.py
# 11 passed in 0.59s
TEST_DATABASE_URL='postgresql+psycopg:///postgres?host=/tmp/ai-tutor-slice1-pg&port=55439' .venv/bin/pytest -q
# 175 passed in 13.84s
.venv/bin/ruff check .
# All checks passed!
.venv/bin/ruff format --check .
# 42 files already formatted
 git diff --check
# passed, no output
```

Seven adapter/fake cases plus four PostgreSQL integration cases: completion/replay and the three approved transient categories. Existing worker concurrency, fencing, migration, privacy, and admission tests also passed. No standalone type checker is configured. No live-model, semantic quality/safety, deployment, or production provider integration tests were run because those implementations are absent. The fake does not establish tutoring quality.

## Results / contract check

| Classification | Evidence / contract | Impact |
| --- | --- | --- |
| MATCH | `model_client.py` ModelProcessor and `test_model_client.py`; ai-runtime thin abstraction and SLICE2A-001 | One client invocation; no nested retry, SDK, network call, or new provider decision. Cancellation propagates. |
| MATCH | `model_client.py` selected ProcessingInput; security model authority / selected-context rules | No database capability, credentials, tool executor, or unrestricted records supplied. No mastery writes or policy authority added. |
| MATCH | Output shape tests; schema §31.6 and ai-runtime invalid-output rules | Non-string/blank/NUL output rejected without coercion; exact valid text retained. Semantic validation remains explicitly deferred. |
| MATCH | PostgreSQL adapter completion/retry tests; api-contract replay and SLICE2A-001 budget | One persisted response; two transient claims maximum; FAILED POST replay=200 without another client call. |
| DOCUMENTATION_DRIFT | README, ai-runtime implementation notes, architecture §31.8, ADR-014 | Synchronized implementation status to completed Stage 4. No contract-policy changes. |

- **DECISIONS MADE:** Ordinary private implementation choices only: a protocol, an adapter, and explicit constructor injection. No selected provider or invented prompt/safety policy.
- **APPROVED CONTRACT CHANGES:** None; recorded staged continuation and implementation/verification status.
- **DEVIATIONS:** None identified within Stage 4. No remaining IMPLEMENTATION_BUG or DECISION_REQUIRED blocks the deterministic abstraction/fake scope.
- **KNOWN RISKS / TODO:** Production provider and semantic output validation are unresolved; text-shape checking alone cannot establish safety. Fake responses must be synthetic and explicitly configured; no fallback or default provider is installed. Live provider timeout/cancellation/error mapping and telemetry remain unverified. Worker requires nonblocking async clients with no hidden retries. No deployment entrypoint or polling endpoint added.
- **NEXT LOGICAL SLICE:** Stage 5 authenticated GET polling, following review. Production integration remains separate and requires the deferred approved policies/provider decisions. No Stage 5 work begun.
