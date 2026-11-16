# AI Tutor discovery audit — 15 November 2026 snapshot

**Audience:** project manager planning a demonstrable MVP.
**Audit type:** read-only. No application code, tests, or migrations were changed.
**Performed:** 16 November 2026, against the commit identified as the 15 November 2026 GitHub snapshot.
**Repository:** `AFranklin30/ai-tutor`.
**Roadmap reconciled:** owner master roadmap dated 9 November 2026 (Stages 1–6), including the 9 November amendment that the next product step after the Stage 1 V1-versus-V3 comparison is the Stage 3 learning demo, then Stage 2 evaluation tooling.

This report uses code, contracts, and commands run in this audit as evidence. A document that describes a behavior is not treated as proof that the behavior runs.

## Naming collision — read this before the stage map

Three different things are called “Stage 3” in this repository. They are not the same work.

| Name in the repo | What it actually is | Roadmap stage |
| --- | --- | --- |
| Slice 2a Stage 3 | The PostgreSQL-backed background worker (`ai_tutor/worker.py`). ADR scope text still calls this “the Stage 3 background worker.” | Ongoing production engineering, inside the async-processing slice. Not roadmap Stage 3. |
| Stage 3 DATA / Migration 0003 / ADR-015 | Organization, tenant, and reusable curriculum **schema**. Commit `288ee59`. | Not the roadmap Stage 3 demo. It is data-foundation work. Learning briefs, student histories, and a presentation UI are not in this migration. |
| Roadmap Stage 3 — Learning Intelligence and Demo | Three synthetic students, about ten problems each, tracked correctness/hints/reasoning/misconceptions, local Qwen learning briefs, a simple presentation, and a 2–3 minute recording. | The roadmap stage. Not started. |

Roadmap Stages 1–6 below use the **roadmap** meanings. Repository slice numbers are called out as slices.

---

## 1. Branch and commit audited

Audited commit:

| Field | Value |
| --- | --- |
| Branch audited | `main` |
| Commit | `288ee59153100a015bb0310ec76e80f6d26a00cf` |
| Short SHA | `288ee59` |
| Subject | `feat: add Stage 3 organization and curriculum schema` |
| Author | AFranklin30 |
| Commit date | 13 November 2026, 14:13:58 −0600 |
| Working tree at audit start | Clean. No stash. No local-only commits. |

`git fetch origin --prune` was run during this audit. After fetch, `origin/main` is still `288ee59`.

### Branches compared with `main`

Counts are `git rev-list --left-right --count origin/main...<branch>` (commits on main only, then commits on the branch only).

| Branch | Tip | Ahead of `main`? |
| --- | --- | --- |
| `main` / `origin/main` | `288ee59` | This is the baseline. |
| `origin/feat/stage3-migration-0003` | `288ee59` (identical SHA) | No. `0 0`. Same commit as `main`. |
| `origin/feat/async-message-processing` | `7fccff8` (`docs: correct stale Slice 2a status and polling route`, 9 October 2026) | No. `4 0`. Fully contained in `main`. Merged by PR #1 (`e22e457`). |
| `origin/feat/supplemental-instructional-eval` | `9930811` (`feat: add offline tutor evaluation suites`, 9 November 2026) | No. `4 0`. Fully contained in `main`. Merged by PR #2 (`20e9cf0`). |

Local branches at audit start: `main` only. No unpushed commits (`git log --branches --not --remotes` was empty). No tags.

History on `main`, newest first:

1. `288ee59` — Stage 3 organization and curriculum schema (Migration 0003).
2. `20e9cf0` — Merge PR #2: offline tutor evaluation suites.
3. `9930811` — Offline tutor evaluation suites.
4. `e22e457` — Merge PR #1: Slice 2a asynchronous message processing.
5. `7fccff8` — Docs correction for Slice 2a polling.
6. `a4738ba` — Slice 2a asynchronous message processing.
7. `b6f7e7d` — Backend foundation and message admission.

The user-supplied 15 November snapshot matches this tree: `main` and `feat/stage3-migration-0003` are the same commit, and the async-processing and supplemental-eval branches are already merged and are not ahead of `main`.

This audit’s report lives on a new branch created after the inspection (`cursor/discovery-audit-2026-11-15-63f1`). That branch did not exist before the audit.

---

## 2. Test run results

### Environment actually used

| Item | This audit | What the README records as previously tested |
| --- | --- | --- |
| Python | 3.12.3 | 3.9.6 |
| PostgreSQL | 16.15 (Ubuntu 16.15, cluster `16/main`, started in this VM) | 14.19 |
| Dependencies | `requirements.lock` installed into a fresh virtual environment | Pinned lockfile |
| Database | Disposable database `ai_tutor_audit`, role `tutor_audit`, created for this audit | Disposable schemas inside the caller’s test database |

The suite passed on this newer pair. That does not re-prove the documented 3.9.6 / 14.19 pair. Nothing in the run failed because of the version difference.

PostgreSQL was not installed when the VM was inspected. It was installed and started for this audit (`postgresql` 16 from Ubuntu packages). Ollama is not installed. No `OPENAI_API_KEY` was present, and no model call was made.

### Commands and outcomes

Full suite, from `/workspace`, against disposable schemas that Alembic upgrades to head `0003`:

```sh
export TEST_DATABASE_URL='postgresql+psycopg://tutor_audit:tutor_audit@127.0.0.1:5432/ai_tutor_audit'
pytest -q --tb=no -p no:cacheprovider
```

| Result | Count |
| --- | --- |
| Passed | **334** |
| Failed | **0** |
| Skipped | **0** |
| Errors | **0** |
| Collected | 334 |
| Duration | 50.84 seconds |
| Exit code | 0 |

`pytest --collect-only -q` also reported `334 tests collected`. Alembic head is revision `0003`.

Passed counts by module (collection counts; the single full run had zero failures, so these are the pass counts):

| Module | Passed | What it exercises |
| --- | --- | --- |
| `tests/test_messages.py` | 51 | Admission, auth, idempotency, authorization, concurrency, rollback |
| `tests/test_processing_schema.py` | 57 | Migration 0002 constraints, triggers, backfill, history |
| `tests/test_worker.py` | 55 | Claim, lease, fencing, reauthorization, shutdown, failure |
| `tests/test_local_tutor_eval.py` | 44 | Offline Ollama adapter with mocks. No live model. |
| `tests/test_offline_tutor_eval.py` | 32 | Offline runner, fake client, paid-transport mocks |
| `tests/test_polling.py` | 23 | Authenticated GET status reads |
| `tests/test_async_lifecycle.py` | 19 | FastAPI POST/GET + real PostgreSQL + worker + fake model |
| `tests/test_tutor_repeatability.py` | 11 | V1/V2 schedule mechanics with a fake transport |
| `tests/test_model_client.py` | 11 | `FakeModelClient` and worker adapter |
| `tests/test_tutor_prompt_versions.py` | 9 | Prompt v2 is the approved one-line addition |
| `tests/test_pilot_diagnostic.py` | 8 | Seven-case diagnostic plan; fake transport |
| `tests/test_tutor_prompt_v3.py` | 6 | Prompt v3 is v1 plus the approved example |
| `tests/test_curriculum_foundation.py` | 4 | Orgs, tenants, libraries, adoption, derivatives |
| `tests/test_migration.py` | 4 | 0001–0003 parity, legacy-row preservation, downgrade guard |
| **Total** | **334** | |

Lint and compile, same environment:

```sh
ruff check ai_tutor migrations tests
ruff format --check ai_tutor migrations tests
python -m compileall -q ai_tutor migrations tests experiments
```

Ruff check: all checks passed. Ruff format: 33 files already formatted. `compileall`: succeeded (exit 0).

### What this green suite does not prove

- No live Ollama / Qwen generation. `ollama` is not installed. Local-adapter tests mock HTTP.
- No paid provider call. The offline runner’s paid mode was not executed. Its default is a fake client.
- No persistent application database was migrated. Tests create a random schema, upgrade, and drop that schema. Migration 0003 has still not been applied to a non-disposable database (`docs/schema.md` §34, ADR-015).
- No browser or running Uvicorn process was exercised. End-to-end plumbing is covered by `tests/test_async_lifecycle.py` through FastAPI’s test client, a real PostgreSQL schema, the worker, and `FakeModelClient`.
- No curriculum content, lesson selection, assessment scoring, or learning-outcome write was exercised, because those application paths do not exist.
- Historical human-review artifacts cited under `artifacts/` are not in the clone. See section 7.

---

## 3. Component classification

Status vocabulary is exactly one of: **Implemented and verified**, **Implemented but unverified**, **Partially implemented**, **Planned**, **Not started**, **Blocked**.

“Verified” means this audit ran the relevant tests or instantiated the relevant code. “Implemented but unverified” means the repository claims a result that this checkout cannot re-check.

| Component | Status | Evidence |
| --- | --- | --- |
| Requirements and MVP scope | Implemented and verified | `docs/requirements.md` is the approved MVP v1 contract (Grade 7 mathematics, synthetic/demo). §23 still lists unresolved product decisions (curriculum source, mastery definition, model/provider, deployment, privacy). Reading the file confirms the contract; it does not mean the product meets §20. |
| Architecture documents and ADRs | Implemented and verified | `docs/architecture.md`, `docs/architecture-decisions.md` (ADR-001 through ADR-015), `docs/decisions.md`. These describe the target system as well as what is built. ADR-015 records Migration 0003 as schema-only. |
| Message and job schema (Alembic 0001, 0002) | Implemented and verified | `migrations/versions/0001_message_admission.py`, `migrations/versions/0002_async_message_processing.py`, tables in `ai_tutor/models.py`. 51 + 57 + worker/lifecycle tests passed on PostgreSQL 16. |
| Organization and curriculum schema (Alembic 0003) | Implemented and verified | `migrations/versions/0003_organization_curriculum.py`. Metadata has 26 tables; Alembic head is `0003`. `tests/test_curriculum_foundation.py` (4) and `tests/test_migration.py` (4) passed. Schema foundation only: no API writes these tables. Not applied outside disposable test schemas. |
| Learning-record schema (objectives, attempts, POC, mastery, escalations, evidence, interpretations, briefs, curriculum chunks) | Planned | Specified in `docs/schema.md` §§6–19 and blueprint §§5–8. None of those tables are among the 26 SQLAlchemy tables. Blueprint §9 says they are later migrations, not 0003. |
| Message admission service | Implemented and verified | `ai_tutor/service.py` `MessageService.admit`, `ai_tutor/repository.py`. Commits message + job + idempotency key before returning. `tests/test_messages.py` passed. |
| Implemented HTTP API | Implemented and verified | Two product routes in `ai_tutor/api.py`. See section 4. Lifecycle tests drive them. |
| Remaining contracted HTTP API | Not started | Routes listed in `docs/api-contract.md` and absent from `create_app()` are inventoried in section 4. |
| Authentication | Partially implemented | `ai_tutor/auth.py` maps a server-provisioned opaque bearer token (SHA-256) to a user UUID via `DEMO_CREDENTIALS_JSON`. Tests cover that mechanism. No login, registration, password, OAuth, or token issuer (`decisions.md` SLICE1-001). Production identity is an unresolved decision (`docs/requirements.md` §22.4, §23). |
| Student authorization and worker reauthorization | Implemented and verified | Admission checks active student, owned session, active enrollment, and assignment eligibility (`ai_tutor/service.py`, `ai_tutor/repository.py`). Worker re-checks account, enrollment, coursework, and closure on claim/renew/complete (`ProcessingRepository.lock_context`). Revocation cancels unfinished work. Covered by message, worker, and lifecycle tests. |
| Tenant and organization isolation at runtime | Not started | Tables and foreign keys exist. `docs/security.md` “Stage 3 curriculum ownership…” states application authentication, tenant resolution, and authorization enforcement remain unimplemented. No request code reads `tenants` or memberships. `users.role` is still only `STUDENT` or `TEACHER`. |
| Background worker lifecycle | Implemented and verified | Flow in §3.1. `ai_tutor/worker.py`, `ai_tutor/processing_service.py`, `ai_tutor/processing_repository.py`. 55 worker tests and 19 lifecycle tests passed. The processor is injected. The API process does not start a worker. |
| Worker process entrypoint / deployment supervisor | Not started | `Worker` is constructed only from tests. No `__main__` under `ai_tutor/`. No Dockerfile, process manager, or health check. |
| In-application model integration | Partially implemented | `ai_tutor/model_client.py` defines a `ModelClient` protocol, `ModelProcessor` (one call; rejects blank or NUL text), and `FakeModelClient` (returns caller-supplied text). 11 model-client tests passed. The file’s own docstring says there is no provider, SDK, prompt, or tool use. A nonempty string is accepted as a tutor reply. |
| Offline model adapters | Partially implemented | `experiments/tutor_v1/runner.py` can call OpenAI Responses for model id `gpt-6-luna` when `--mode paid` is selected. `experiments/tutor_v1/local.py` can call a locally owned Ollama server for `qwen3.5:4b-q4_K_M`. Fake/mocked tests passed (32 + 44). This audit did not run either live adapter. They are not imported by `ai_tutor`. |
| AI tutoring runtime (State → Retrieval → Context → Reasoning → Action → Validation) | Not started | No orchestrator, context builder, retrieval, tool executor, or tutoring policy module under `ai_tutor/`. Contract: `docs/ai-runtime.md`, `docs/architecture.md` §§7–12 and §31. The offline runner is a single prompt plus a fixed fixture, then a `{reply: string}` check. It is not this loop. Detail in §3.2. |
| Retrieval, embeddings, pgvector | Not started | Approved in `docs/architecture.md` §§17–19. No `pgvector` extension, embedding column, chunk table, or retrieval query in migrations or `ai_tutor/`. `README.md` says pgvector is not installed by the Slice 1 migration; 0002 and 0003 do not add it either. |
| Offline evaluation harness and frozen datasets | Partially implemented | Twelve cases in `experiments/tutor_v1/cases.py`. Seven pilot cases in `experiments/datasets/pilot-one-step-v1.json` and `pilot-one-step-v2.json`. Six supplemental scenarios in `experiments/datasets/instructional-scenarios-v1.json`. Prompts v1, v2, and v3 on disk. Deterministic harness tests passed. The supplemental JSON is not imported by any Python module, so nothing fails if it drifts. No automated instructional judge. |
| V1 versus V3 comparison | Planned | Roadmap Stage 1 exit condition. Prompts exist. Supplemental dataset sets `execution_authorized` to false and leaves repetitions and acceptance procedure null. `docs/decisions.md` SUPP-EVAL-001 and OFFLINE-EVAL-006 forbid treating dataset approval as a generation run. No comparison artifact is in git. |
| V1 versus V2 repeatability results | Implemented but unverified | `docs/evals.md` and `docs/experiments/tutor-repeatability.md` say a later local run produced 30 observations and 180 human judgments, with a mixed, slice-dependent comparison and no overall winner. `docs/research/tutor-v1-v2-repeatability.json` records that narrative and hashes of `artifacts/` files. `artifacts/` is gitignored (`.gitignore`) and is absent from this clone (`git ls-files artifacts` is empty). This audit did not re-run the model, so those judgments are not verified here. Protocol mechanics with a fake transport are verified (11 tests). |
| Evaluation platform (behavior receipts, promptfoo, DeepEval, Langfuse, Ragas, continuous regression store) | Not started | Backlog in the 9 November roadmap Stage 2. `docs/evals.md` “Deferred evaluation and tooling decisions” leaves the runner/tooling choices unresolved beyond the isolated offline experiment. No Promptfoo, DeepEval, Langfuse, or Ragas dependency in `requirements.lock`. |
| Curriculum ownership, adoption, and org derivatives (database) | Implemented and verified | Tables `organizations`, `tenants`, memberships, `curriculum_libraries` (`SYSTEM` / `PERSONAL` / `ORGANIZATION`), `curriculum_courses`, `curriculum_units`, `curriculum_lessons`, `tenant_curriculum_course_adoptions`, and course/unit/lesson derivation tables. Four foundation tests passed, including shared adoption, immutable derivative provenance, and offering-versus-template separation. |
| Curriculum application (browse, adopt, assign, serve a lesson) | Not started | No route, service, or worker read of those tables. `ProcessingInput` carries message id, session id, content, and trace id only (`ai_tutor/processing_service.py`). |
| Assessments and recorded activity outcomes | Not started | No assessment, score, or attempt table. `problems.prompt` is text on an operational problem. Student work is stored as `messages` only. No progress or mastery write path. |
| AI curriculum drafts with human approval | Not started | Curriculum rows have no draft, review, or approval status. Migration 0003 installs immutability triggers; it does not install a draft-then-approve workflow. Blueprint §7 says interpretation corrections do not create review statuses. |
| Creator attribution | Partially implemented | Schema columns exist and tests can write them: `created_by_user_id` on curriculum courses, units, and lessons; grantor columns on memberships and permissions; `adopted_by_user_id`; `derived_by_user_id`. That is row provenance, not a product workflow. Interpretation-creator and human-review tables from blueprint §§6–7 are not migrated. Role and capability codes are opaque non-empty strings; the approved vocabulary (Decisions 80–86) is not in `docs/decisions.md`. |
| Frontend | Not started | No HTML, JavaScript, TypeScript, `package.json`, or client directory. `README.md` states there is no frontend. FastAPI’s generated `/docs` page is framework boilerplate, not a student UI. |
| Deployment, CI, and secret management | Not started | No Dockerfile, Compose file, `.github` workflows, or secret-manager integration. `Settings.from_environment` reads `DATABASE_URL`, `DEMO_CREDENTIALS_JSON`, and optional `MAX_MESSAGE_CHARACTERS` (`ai_tutor/config.py`). No `.env.example`. Cloud provider is an explicit unresolved decision (`docs/architecture.md` §32). |
| Observability | Partially implemented | OpenTelemetry spans without an exporter (`ai_tutor/api.py` comment and `TracerProvider()`). Metadata-only logs in `ai_tutor/observability.py` and `ai_tutor/worker_observability.py`. Tests cover log privacy. No dashboard, alert sink, or trace backend (`docs/architecture.md` §25.1). |
| Documentation set | Partially implemented | Contracts under `docs/` are extensive and are the authority for implementation. Several status pages contradict the tree at `288ee59`. See section 7. |

Nothing in the current tree is **Blocked** in the sense that a missing dependency stops the code that already exists. Several **next** product slices are gated by unresolved human decisions and should be treated as blocked until those decisions are made:

| Next slice that is gated | Missing decision | Where it is recorded |
| --- | --- | --- |
| Production tutor model inside the worker | Model/provider selection | `docs/requirements.md` §23, `docs/architecture.md` §32, `docs/ai-runtime.md` deferred list |
| Curriculum-grounded tutoring and a real Grade 7 lesson | Exact curriculum source, first unit, and objectives | `docs/requirements.md` §23 and §2.1 |
| Operational use of org/tenant role grants | Approved role and capability vocabulary (Decisions 80–86 are not in the checkout) | `docs/stage-3-data-implementation-blueprint.md` §§3.2 and 12.1, ADR-015 |
| Any demo with real children | Age, consent, retention, educational-record, and school-deployment rules | `docs/security.md` Step 8, `docs/requirements.md` §22.4 |
| V1 versus V3 model execution | Separate human authorization to run models; repetitions and acceptance procedure are unset | `docs/decisions.md` SUPP-EVAL-001, OFFLINE-EVAL-006 |

### 3.1 Worker flow — verified in code and tests

The expected pipeline is Student Message → Authentication → Idempotency → Job Creation → Worker Claim → Processing → Reauthorization → Completion.

| Step | What the code does | Verified? |
| --- | --- | --- |
| Student message | `POST /api/v1/coaching/sessions/{session_id}/messages` in `ai_tutor/api.py`. Body is `{"content": ...}` plus an `Idempotency-Key` header. | Yes. Message tests and lifecycle tests. |
| Authentication | `resolve_principal` hashes the bearer token and looks up a pre-provisioned user id. Missing, malformed, or unknown tokens return 401. The client cannot choose the user id. | Yes. `tests/test_messages.py` authentication cases. |
| Idempotency | Same student + same key + same content returns the existing message and does not create a job or start work (`MessageService.admit`). Different content on the same key returns 409. Replay of a `FAILED` message returns 200 and does not reschedule. | Yes. Message tests, including concurrent duplicates. |
| Job creation | For a new send, one transaction locks the user, checks an `ACTIVE` session and coursework eligibility, allocates `session_sequence`, inserts the student message as `PENDING`, inserts one `message_processing_jobs` row, and stores the idempotency record. The HTTP response is built only after commit. | Yes. Service code and processing-schema tests. |
| Worker claim | A separate `Worker.process_next` calls `ProcessingService.claim_next`. It takes the oldest unresolved head of a session, uses `SKIP LOCKED`, and commits a `PROCESSING` claim with a fresh token, lease, and deadline before calling the processor. The API server never calls this. | Yes. Worker tests. There is no production process that runs it. |
| Processing | The injected async processor runs **outside** the database transaction. In the app, the only client is `FakeModelClient`, which ignores the student text and returns its configured string. `ModelProcessor` checks that the string is nonempty and has no NUL. No curriculum, history, lesson, or tool call is loaded. | Yes, as a deterministic stub. Not as tutoring. Lifecycle tests use the fake. |
| Reauthorization | Before renew and before complete, `lock_context` re-reads the user, session, enrollment, coursework eligibility, and closure. Disabled account, revoked enrollment, ineligible coursework, or administrative/unknown closure cancels unfinished messages in that session. A stale claim token cannot finalize. Normal closure still allows already-admitted work. | Yes. `test_current_authorization_and_closure_cancel_unfinished_scope` and `test_runner_discards_result_after_heartbeat_authorization_loss` passed with the rest of the suite. |
| Completion | `complete` inserts a tutor `messages` row (`author_type="tutor"`, `in_reply_to_message_id` set) and sets the student message to `COMPLETED` in the same transaction. `GET .../status` reads that snapshot. `FAILED` and `CANCELLED` return safe public errors and no model text. | Yes. Polling and lifecycle tests. |

The pipeline above is real and tested. The “Processing” step does not tutor. It stores whatever nonempty string the injected callable returns.

### 3.2 AI runtime — expected loop versus what exists

The product contract (`docs/ai-runtime.md` “Approved Step 5 flow detail”, `docs/architecture.md` §31) is:

State → Retrieval → Context → Reasoning → Action → Validation, with the application owning the loop and the model remaining untrusted.

| Stage | In the student-facing application | In the offline experiment |
| --- | --- | --- |
| State | Identity, session, enrollment, and eligibility are loaded to admit or cancel work. No point of confusion, attempt history, mastery, or lesson state is assembled. | Each case carries a fixed synthetic problem, a short history list, and one student message (`experiments/tutor_v1/cases.py`). |
| Retrieval | Absent. No query against curriculum or student history. | Absent. Context is the fixture, not a search. |
| Context | Absent. The worker’s `ProcessingInput.content` is the raw student message. | A JSON object with grade 7, subject, problem, selected history, and the current message is placed in one user turn (`runner.py` `case_context`). |
| Reasoning | Absent. No prompt is sent by `ai_tutor`. | One instructions string (`prompt.txt`, `prompt-v2.txt`, or `prompt-v3.txt`) plus that JSON. Default execution is a fake. Paid mode targets `gpt-6-luna`. Local mode targets `qwen3.5:4b-q4_K_M`. |
| Action | Persist the returned string as the tutor message. No tools. | Return one `reply` string. No tools, no database writes (`runner.py` module docstring). |
| Validation | Nonempty string, no NUL character. No mathematical, pedagogical, or policy check. | JSON shape `{reply: string}` and a conservative input-size bound. Human review of the six dimensions is manual and is not executed by pytest. |

Model integration in the product path is a deterministic stub. The offline adapters contain real HTTP clients, and this audit did not execute them. Historical local Qwen runs are described in docs and are not reproducible from this clone (section 7).

---

## 4. API route inventory

Instantiating `create_app()` with a local `DATABASE_URL` and `DEMO_CREDENTIALS_JSON='{}'` registered exactly these routes:

### Product routes (implemented)

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/api/v1/coaching/sessions/{session_id}/messages` | Authenticated admission. `201` and `PENDING` when created. `200` and current status on same-key/same-content replay. Does not run the worker. |
| `GET` | `/api/v1/coaching/sessions/{session_id}/messages/{message_id}/status` | Authenticated read of status and, when `COMPLETED`, the stored tutor text. `Cache-Control: no-store`. No writes. |

### Framework routes (FastAPI defaults, not a product)

| Method | Path |
| --- | --- |
| `GET` | `/openapi.json` |
| `GET` | `/docs` |
| `GET` | `/docs/oauth2-redirect` |
| `GET` | `/redoc` |

There is no health route, login route, or static-file mount.

### Contracted routes with no implementation

From `docs/api-contract.md` (student coursework, sessions, retry, progress, teacher escalation, teacher mastery). None of these functions exist in `ai_tutor/`:

| Method | Path | Contract role |
| --- | --- | --- |
| `GET` | `/api/v1/students/me/courses` | Course list for the student |
| `GET` | `/api/v1/students/me/assignments` | Assignment list |
| `POST` | `/api/v1/coaching/sessions` | Start a coaching session |
| `GET` | `/api/v1/coaching/sessions/{session_id}` | Read a session |
| `PATCH` | `/api/v1/coaching/sessions/{session_id}` | Close a session |
| `POST` | `/api/v1/coaching/messages/{message_id}/retry` | Explicit retry of a failed message. Slice 2a explicitly excludes a student retry endpoint (`docs/api-contract.md`, SLICE2A-001). |
| `GET` | `/api/v1/students/me/progress` | Progress read |
| `GET` | `/api/v1/teacher/escalations` | Teacher queue |
| `GET` | `/api/v1/teacher/escalations/{escalation_id}` | Escalation detail |
| `PATCH` | `/api/v1/teacher/escalations/{escalation_id}` | Resolve escalation |
| `GET` | `/api/v1/teacher/students/{student_id}/mastery` | Official mastery read |
| `PATCH` | `/api/v1/teacher/students/{student_id}/mastery/{objective_id}` | Official mastery update |

No route exists for organizations, tenants, curriculum libraries, units, lessons, assessments, or learning outcomes.

---

## 5. Curriculum versus runtime — dependency finding

**A student learning experience depends on unfinished curriculum infrastructure.** Migration 0003 does not remove that dependency.

What “learning experience” means here is the demo in section 8: a student logs in, picks a lesson, talks with a tutor that is using that lesson, completes an activity or assessment, and the outcome is stored.

Evidence:

- The worker never reads `curriculum_libraries`, `curriculum_courses`, `curriculum_units`, `curriculum_lessons`, adoptions, or derivations. `ProcessingInput` is the student message text plus ids (`ai_tutor/processing_service.py`).
- Message admission authorizes against legacy operational tables (`courses`, `enrollments`, `assignments`, `problems`, `student_assignment_eligibility`, `coaching_sessions`). Those rows are inserted by tests or by an operator. There is no product API that creates them. `courses.tenant_id` and `courses.curriculum_course_adoption_id` stay null together for that legacy path (`ai_tutor/models.py` check `tenant_adoption_pair`).
- There is no lesson entity on the request path, no assessment entity, and no outcome table. `problems` are a title/prompt attached to an operational course, not a scored assessment.
- Retrieval of approved curriculum is specified (`docs/architecture.md` §18, `docs/requirements.md` §10 and §20) and has no implementation. Requirements say that when grounding is required, a retrieval failure must not be presented as grounded tutoring (`docs/requirements.md` §22.3).
- Blueprint §15 states Migration 0003 creates schema foundations only and does not change student-visible functionality.

What can run without the curriculum tables: a pre-seeded student, course, assignment, problem, eligibility row, and `ACTIVE` session; a bearer token; `POST` a message; a separately started worker whose processor is `FakeModelClient`; `GET` the canned reply. `tests/test_async_lifecycle.py` passed that plumbing path. That path does not pick a lesson, does not use curriculum content, and does not record an assessment outcome.

The curriculum schema is a prerequisite for a later tenant-aware product. It is not a substitute for the tutor runtime, and the tutor runtime does not use it yet. Shipping 0003 did not move the student-visible demo forward.

---

## 6. Roadmap Stages 1–6 — completed versus outstanding

Source: owner roadmap of 9 November 2026, with the same-day amendment: finish the Stage 1 V1-versus-V3 comparison, then the Stage 3 learning demo, then Stage 2 tooling. The roadmap’s “current active stage” line still says Stage 1.

### Stage 1 — Establish tutor quality (roadmap: active)

**Exit condition:** a documented, reproducible V1 versus V3 comparison. **That exit condition is not met.**

| Roadmap item | State on `288ee59` |
| --- | --- |
| Inspect and preserve an evaluation runner | Done. `experiments/tutor_v1/runner.py`, `local.py`, `repeatability.py`, `diagnostic.py`. Isolated from `ai_tutor`. |
| Twelve-case evaluation | Preserved in `experiments/tutor_v1/cases.py`. Mechanical tests passed. |
| Seven-case pilot diagnostic | Preserved in `pilot-one-step-v1.json` and `pilot-one-step-v2.json`. In-repo review file `docs/experiments/pilot-one-step-v1-diagnostic-01/review-view.json` is `mode: PREPARED_ONLY` (21 slots, no replies in git). A handoff claims a later scored run whose JSON lives under gitignored `artifacts/`. |
| Supplemental six-scenario dataset (SUPP-EVAL-001, approved 8 November) | Frozen at `experiments/datasets/instructional-scenarios-v1.json`. Specification approved. `execution_authorized: false`. No Python loader. |
| Six human-review dimensions, no aggregate score | Written in `docs/evals.md`. Not computed by code. |
| Pilot blockers (PILOT-EVAL-001) | Recorded: distinguish answer correctness from explanation correctness; do not invent student reasoning; do not judge an answer without sufficient problem context. Final acceptance procedure remains unresolved (PILOT-EVAL-003). |
| Prompt v1, v2, v3 | Files exist. v2 adds an attribution sentence. v3 adds one worked example to v1 and does not include the v2 sentence (`tests/test_tutor_prompt_v3.py` passed). |
| Identical inputs run on V1 and V3 | Not done. Unauthorized. |
| Human review of a V1 versus V3 run | Not done. |
| V1 versus V2 repeatability | Docs say a 30-observation local run and 180 judgments were completed and were mixed, with no winner. Raw artifacts are not in the clone. Treat as reported, not re-verified. This is not the Stage 1 exit comparison. The exit comparison is V1 versus V3. |

### Stage 2 — Evaluation infrastructure (roadmap: after the demo)

**Not started as tooling.** Policy text exists in `docs/evals.md` (deterministic tests versus human review, regression expectations, no invented numeric threshold).

Outstanding, matching the roadmap backlog: behavior receipts, layered verification beyond pytest, continuous evaluation, golden-dataset governance, task-specific suites beyond the frozen JSON files, independent-learning checks, regression history that travels with the repo, Promptfoo, DeepEval / LLM judges, Langfuse, and (when RAG exists) Ragas.

The current pytest suite is a strong deterministic regression net for admission, worker, schema, and eval-harness mechanics. It is not the Stage 2 evaluation platform, and it does not score tutoring quality.

### Stage 3 — Learning intelligence and demo (roadmap: next after V1 versus V3)

**Not started.**

| Roadmap prototype piece | State |
| --- | --- |
| Three synthetic students, about ten problems each | No demo dataset of that shape. Pilot fixtures are seven one-step equations. Offline fixtures are twelve cases plus six supplemental scenarios, used for prompt review, not for a student record. |
| Track correctness, hints, reasoning, misconceptions, subsequent attempts | No attempt, hint, misconception, or outcome tables. |
| Local Qwen 3.5 4B learning briefs | The offline adapter can target `qwen3.5:4b-q4_K_M` for tutor replies. It does not generate learning briefs. `learning_briefs` is listed as a later migration and is not in the database. |
| Validate claims against source records; separate observation from inference | Specified in the Stage 3 DATA blueprint. Tables are not migrated. |
| Simple presentation interface and a 2–3 minute recording | No UI. No recording in the repo. |

The work that landed on 13 November (Migration 0003) is organization and curriculum **storage**. It is useful later. It is not this demo.

### Stage 4 — Retrieval and knowledge systems

**Not started.** pgvector, embeddings, chunking, student-history retrieval, and curriculum RAG are specified and absent from code and dependencies. The roadmap says to introduce them when retrieval requirements are concrete. Those requirements are still unresolved (`docs/architecture.md` §32: embedding model, retrieval parameters).

### Stage 5 — Learning data and model improvement

**Not started.** No consent capture, interaction sampling, training-set curation, or train/eval split pipeline. The roadmap forbids automatic training on raw conversations. Nothing in the repo trains a model.

### Stage 6 — Advanced model adaptation

**Not started**, consistent with the roadmap and with MVP non-goals in `docs/requirements.md` §21 (no custom training, no fine-tuning as an MVP requirement).

### Ongoing — production engineering

| Area | State |
| --- | --- |
| Demo authentication and student message authorization | Partial, and verified for the demo bearer and the message/worker checks. |
| API reliability for admission and polling | Implemented and verified. |
| Worker reliability (leases, fencing, crash recovery, single-owner completion) | Implemented and verified against PostgreSQL with a fake processor. |
| Database architecture | Message/job schema and org/curriculum foundation are migrated in tests. Learning records, vectors, and tenant-scoped coursework are not. |
| Deployment, CI, monitoring, secret management, scalability | Not started. |
| Real-student privacy and safety | Explicitly not approved. |

---

## 7. Tech debt and risks

### Documentation drift

- `README.md` opens with “Slice 2a … 217 tests passed” and later still says “New messages remain PENDING,” “Planned asynchronous AI processing,” and “`main` is the stable Slice 1 baseline” with Slice 2 work belonging on `feat/async-message-processing`. Those sentences are stale at `288ee59`. Later README sections correctly describe the worker, polling, and offline evals. A reader who stops early will plan the wrong slice.
- `docs/architecture-decisions.md` “Scope and verification” says the initial migration creates ten tables and that AI response generation remains planned, while also referring to a Stage 3 worker. Head is revision `0003` with 26 tables, and a worker exists.
- `docs/stage-3-data-implementation-blueprint.md` lines 1–5 say PostgreSQL verification is pending and that no database-backed test has run. Section 14 of the same file says 0003 was verified on PostgreSQL 14.19 and that 213 selected tests passed, and that full collection was 334. This audit’s full run is 334 passed on PostgreSQL 16.15. The header is stale; section 14 matches the suite size. The “not applied to a non-disposable database” statement is still accurate.
- `docs/decisions.md` does not contain Decisions 80–86 or DATA-10/DATA-11. STAGE3-DATA-001 and ADR-015 record only a restatement. Role codes cannot be treated as an approved vocabulary until that source text is recovered.
- Human-review evidence for V1/V2 repeatability and for the pilot diagnostic is cited at `artifacts/...` paths. `.gitignore` ignores `artifacts/`. Those files are not in git history (`git ls-files artifacts` is empty). A fresh clone cannot reproduce the claimed 30-observation comparison or the 126 diagnostic judgments. `docs/research/tutor-v1-v2-repeatability.json` preserves a summary and hashes, which is not the same as the raw replies.

### Product and engineering risks

- **Demo quality is unevaluated against the roadmap exit test.** V3 has not been run against V1. Known V1/V2 notes in the research JSON describe a mixed result, including a reported case where v2 rejected a correct answer. That is a prompt-risk signal, and it is not a substitute for the missing V1-versus-V3 run.
- **Any nonempty string can become the tutor reply** once a worker is pointed at a client (`ModelProcessor` and `ProcessingService.complete`). There is no answer-leakage, mathematical, or curriculum-grounding check on the product path. The three pilot blockers cannot be enforced by the running system.
- **The API and the worker are separate processes, and only the API has a documented start command** (`uvicorn ai_tutor.api:create_app --factory`). A message stays `PENDING` until some other process constructs a `Worker`. No such process is shipped.
- **Users, courses, assignments, problems, eligibility, and sessions must be inserted out of band.** `tests/conftest.py` is the only complete provisioning example. There is no admin API.
- **Tenant columns do not protect existing rows.** Legacy courses are valid with both tenant columns null. Runtime authorization does not know about tenants. Adding organizations in the database does not isolate students.
- **Curriculum rows are immutable immediately**, with creator ids, and there is no draft or approval state. A future “AI draft, human approves” flow needs a new contract and schema. It cannot be layered on 0003 without a design decision.
- **Supplemental dataset can rot.** No test imports `instructional-scenarios-v1.json`.
- **No CI.** The 334-test result exists only where someone starts PostgreSQL and sets `TEST_DATABASE_URL`. A pull request can merge without that run.
- **No type checker** is configured (`README.md`, `pyproject.toml`). Ruff and pytest are the checks.
- **Version skew.** This audit passed on Python 3.12 and PostgreSQL 16. Prior write-ups cite 3.9.6 and 14.19. CI would need a chosen pair.
- **Secrets.** Demo credentials are hashes in an environment variable. There is no rotation story, no `.env.example`, and no production secret store. That matches the approved deferral, and it blocks any shared demo that people can log into without an operator editing the environment.
- **Real students are out of scope.** Security and requirements documents withhold age, consent, retention, and school-deployment approval. A demonstrable MVP for stakeholders has to stay on synthetic data.
- **`gpt-6-luna` paid mode is unproven in this audit.** The model id is hard-coded in `experiments/tutor_v1/runner.py`. This audit did not call the provider and does not claim the id is available or billed as the docs assume.
- **Local Qwen path is unproven in this environment.** Ollama is absent. Prior local-run claims depend on a specific model digest recorded in `docs/ai-runtime.md` and on artifacts that are not in git.

---

## 8. Gaps blocking an end-to-end demo

Target demo: a student logs in, picks a lesson, chats with the tutor, completes an activity or assessment, and the outcome is recorded.

That demo is **not** a small wiring task on top of `main`. The tested system can store a message and, if a separate worker is started with a fake client, store a canned reply. Everything the stakeholder would recognize as a tutoring session is still missing.

| Demo step | What exists | What blocks the step |
| --- | --- | --- |
| Student logs in | Opaque bearer lookup, users pre-inserted, role `STUDENT`/`TEACHER`. | No login or registration endpoint, no session cookie or issued token, no UI, no way for a student to obtain a credential. Production identity is an unresolved decision. |
| Student sees courses and lessons | Operational `courses` can be seeded. Curriculum course/unit/lesson rows can be inserted by SQL. | No list API, no UI, no link from a curriculum lesson to a coaching session. The worker will not read the lesson even if the row exists. |
| Student opens a coaching session on that lesson | `coaching_sessions` table and tests that seed an `ACTIVE` session. | `POST /api/v1/coaching/sessions` is specified and not implemented. Sessions are not tied to a lesson. |
| Student chats with a tutor | `POST` message and `GET` status work. Worker can persist a string. | No process starts the worker. The only in-app model client returns a fixed string and does not see curriculum or history. No State → Retrieval → Context → Reasoning → Action → Validation loop. No prompt on the product path. Live model execution for V1 versus V3 has not been done, so there is no evidenced tutor to put behind the chat. |
| Tutor stays inside the lesson and checks understanding | Requirements §§6–10 and the three pilot blockers. | No retrieval, no lesson context, no pedagogical validator. A nonempty reply is success. |
| Student completes an activity or assessment | `problems.prompt` can hold synthetic problem text if someone inserts the row. | No assessment model, no “submit attempt” API distinct from a free-text message, no scoring, no transfer task. Generating practice problems is outside the approved MVP (`docs/requirements.md` §2.1). |
| Outcome is recorded | Student message text and, after a worker runs, tutor message text, with processing status. | No attempt history, point of confusion, mastery evidence, progress (`BUILDING` / `DEVELOPING` / `STRONG`), learning state, or learning brief. Official mastery is specified as a human decision and has no table or teacher API. Message `COMPLETED` means “a reply row was stored,” not “the student learned.” |

### Smallest honest demonstration available today

A plumbing demonstration, already covered by `tests/test_async_lifecycle.py`, and not re-run here as a long-lived server:

1. Apply migrations to an empty database (head `0003`).
2. Insert a synthetic student, course, assignment, problem, eligibility row, and `ACTIVE` coaching session the way `tests/conftest.py` does.
3. Put that student’s bearer-token hash in `DEMO_CREDENTIALS_JSON`.
4. Start Uvicorn.
5. `POST` a message and receive `201 PENDING`.
6. In another process, run `Worker` with `ModelProcessor(FakeModelClient("<chosen synthetic reply>"))`.
7. `GET` the status and show `COMPLETED` plus that reply.

That demonstration has no login screen, no lesson picker, no model reasoning, no assessment, and no learning outcome. It should not be described as the roadmap Stage 3 demo.

### What has to land before the stakeholder demo is truthful

Ordered by the roadmap amendment (finish Stage 1’s comparison, then the learning demo), and by what the demo definition actually requires:

1. **Authorize and run the V1 versus V3 comparison** on the frozen datasets, with human review on the six dimensions, and keep the raw artifacts in a place a clone can see. The roadmap says the learning demo starts after this. It is not done.
2. **Choose a model for the product worker** (today this is an explicit unresolved decision). Wire one real client behind `ModelClient`, with the application still validating output. A fake string cannot carry a stakeholder demo of tutoring.
3. **Add a runnable worker process** beside the API, even for a single-machine demo.
4. **Approve one Grade 7 unit and lesson** (curriculum source is unresolved) and serve it through a student-visible API. Migration 0003 can store it; nothing reads it.
5. **Let a synthetic student sign in and open a session** on that lesson. Demo credentials can stay synthetic; there still has to be a login or an issued demo credential and a session-create path. Real children remain unapproved.
6. **Record an attempt and an outcome** that a person can distinguish from “message completed”: at least an append-only attempt and a stored result for one activity. Official mastery can stay out of the demo; the roadmap’s own warning is that AI-assisted completion is not proof of learning.
7. **A minimal UI** for login, lesson pick, chat, and the recorded outcome. None exists.
8. **Keep Stage 2 tooling and Stage 4 RAG off the critical path of the first recording** unless the demo script claims curriculum-grounded answers. If the script claims grounding, retrieval is no longer optional, and it is currently unbuilt. The requirements forbid pretending a reply is curriculum-grounded when retrieval did not happen.

Until those gaps close, the repository is a verified message pipeline plus a verified curriculum schema plus an offline prompt laboratory. It is not yet a demonstrable student tutoring session.
