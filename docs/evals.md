# Testing and evaluation policy

Status: Approved Steps 4–10 verification obligations; exact cases, calibrated thresholds, and execution configuration remain UNRESOLVED.
Approval: 2026-10-04 human synchronization request decision 24; decisions.md STEP4-006. Python/pytest are already approved by architecture.md §§2, 26.

## Deterministic contract tests

Future verification must exercise observable guarantees, not merely implementation structure:

| Contract | Required verification |
| --- | --- |
| Durable input/output | Retrieval/model/tool failure cannot erase committed input; no tutor result is returned before its output and logically coupled state commit. |
| Send idempotency | Same student/operation/key and payload returns HTTP 200 with the original message ID and current PENDING/PROCESSING/COMPLETED/FAILED state without new input, job scheduling, or processing attempts; changed payload conflicts and preserves original. Verify FAILED replay is read-only in both ACTIVE and CLOSED sessions. Genuine backend unavailability remains 503. |
| Explicit retry | Reprocess existing eligible FAILED input without new student message; duplicate send is not retry. |
| Ownership/recovery | Concurrent and recovered runs cannot produce competing tutor responses or duplicate durable actions. |
| Durable action idempotency | Automatic/explicit retry and stale recovery reuse successful logical evidence, POC, attempt, escalation, and other effects. |
| Closure | New send in CLOSED conflicts; no new failed-message retry begins; admitted PENDING/PROCESSING work may finish; authorized historical replay returns state without processing. |
| Start New | Old closure and new ACTIVE creation both succeed or neither does; creation failure leaves old session ACTIVE and history intact. |
| Coursework eligibility | Enrollment alone cannot authorize unassigned/unreleased work; validate specific coursework and relationship consistency. |
| Non-disclosure | Protected existence produces 404; discoverable-but-forbidden action produces 403; neither leaks ownership. |
| Attempts/evidence | Actual attempts link to source messages; evidence is attributable and append-only; retry does not duplicate logical records; contradictions remain. |
| Mastery authority/history | AI cannot write official mastery; authorized teacher/human changes preserve previous/new decisions, actor, time, and provenance. |
| POC history | Original AI prediction survives separate attributed CORRECT/PARTLY_CORRECT/INCORRECT teacher feedback. |
| Tool and context boundaries | Unauthorized tools/actions/data are rejected; curriculum cannot override policy; context is authorized and selected. |
| Truthful outcomes | Controlled failure scenarios never return claims that failed actions succeeded. |
| Output/defaults | Validate correlated student/tutor identifiers, student-safe errors, configured length/step/timeout/retry enforcement. |

Tests may require unit, API/integration, database/repository, authorization, and fault-injection scenarios. Exact commands/fixtures remain to be specified once implementation tooling exists; do not claim these tests have run merely because obligations are documented.

## Step 5 flow verification additions

Approval: decisions.md STEP5-001 through STEP5-003. These are required future scenarios, not executed tests or new numeric acceptance thresholds.

- Crash after input commit but before processing: preserve input and recover from committed state.
- Ownership transfer: allow the currently valid owner to finalize and reject competing finalization by the stale former owner.
- Tool effect commits, then later processing fails: recovery reuses the effect without duplicate evidence/POC/escalation; an unsuccessful/uncommitted effect may be retried under approved policy.
- Final output commits, then HTTP response is lost: same-key replay returns current existing result without duplicate input or completed processing; changed payload conflicts.
- Tool loop: results return to Orchestrator/context before further reasoning; requested actions never count as proof of success; response-critical failure cannot produce a success claim; enforce the existing step limit.
- Final response: output and logically coupled state are durable before visibility; exclude unnecessary internal fields from public output while preserving authorized teacher evidence views.
- Explicit retry never creates another Message or reopens CLOSED. Preserve admitted-work completion and atomic Start New guarantees from Step 4.
- Teacher Yes / Partly / No maps to CORRECT / PARTLY_CORRECT / INCORRECT with the original AI prediction and separate attributed determination preserved.
- ProgressService uses the product rubric and accumulated evidence; model confidence alone does not drive progress or authoritative mastery.

Continue probabilistic evaluation of tool-outcome truthfulness, POC feedback comparisons, and accumulated-progress quality under the existing AI evaluation dimensions. Mechanical flow/authority checks and probabilistic wording/quality measurements remain distinct.

## Probabilistic AI evaluations

Evaluate POC identification, retrieval quality, grounding, unsupported claims, scaffolding, answer leakage, adaptation, misconception detection, verification of understanding, transfer, tool selection, escalation quality, mastery-evidence quality, progress calibration, structured-output validity, policy compliance, latency/cost, and regressions.

Distinguish deterministic rejection of malformed/unauthorized outputs from measured model rates of producing those outputs. Distinguish backend truthfulness guarantees in controlled tests from model wording/quality evaluations.

Use approved reference cases where available, important slices, runtime/model/prompt/curriculum versions and relevant settings, baseline comparisons, sample counts, failures, variability, and uncertainty. Report limited coverage and skipped checks. Preserve original AI POC predictions and linked teacher feedback for evaluation without rewriting labels to conceal disagreement.

Progress evaluations assess evidence-based BUILDING / DEVELOPING / STRONG against a product-owned rubric using correctness, independence, explanation, and transfer. Confidence alone cannot be the label. Teacher authoritative mastery may differ from AI-estimated progress; that difference alone is not an evaluation failure or permission to rewrite evidence.

## Steps 6–7 verification obligations

Approval: decisions.md STEP6-001 and STEP7-001. These document behavioral obligations, not executed tests, selected datasets, or new release thresholds. Detailed coverage belongs primarily to Step 9; monitoring implementation belongs primarily to Step 10.

- Meaningful model-routing, context-reduction, retrieval, and inference optimizations must be compared against relevant approved behavioral quality metrics as well as latency/cost. Cheaper/faster is insufficient if tutoring quality is sacrificed. Exact routing policy, baselines, and acceptance thresholds remain deferred.
- Required retrieval failure must not produce unsupported output presented as curriculum-grounded. Verify operation-specific grounding requirements without imposing retrieval on every application operation; any degraded response requires an approved policy.
- Inject database failure before input commit and before final-result commit: reject false durability claims, roll back logically coupled writes, and never expose uncommitted final output. A failed status write is not proof that FAILED became durable. Verify recovery from actual committed state.
- Successful provider transport with invalid structure, policy/authority, action, or business/state output must fail tutoring validation without executing disallowed actions. Preserve distinct internal categories and safe public errors.
- Preserve bounded eligible retries, committed input, response-critical tool truthfulness, and all Step 5 crash/ownership/replay/closure/durable-effect scenarios. No new infrastructure or broader retry eligibility is implied.

Deterministic fault-injection/validation checks and probabilistic grounding, truthfulness, and tutoring-quality evaluations remain distinct. No runtime reliability or scaling performance has been established by this documentation change.

## Step 8 security verification obligations

Approval: decisions.md STEP8-001 and STEP8-002. These are future checks of approved guarantees, not runtime security evidence or new numeric acceptance criteria. Detailed coverage remains Step 9.

- Exercise forged client student/teacher identity, direct requests bypassing frontend controls, and model tool arguments naming another student. Trusted backend identity and relationships must control access; unauthorized actions have no requested durable effects.
- Simulate a model following malicious user instructions. Verify deterministic rejection of unauthorized tools/arguments, invalid state, unrestricted capabilities, and official-mastery changes regardless of prompt compliance.
- Exercise protected-resource non-disclosure (404 versus legitimate-visible forbidden 403), cross-user same-key replay, retries/recovery authorization, and stale-owner finalization rejection without weakening existing flow guarantees.
- Supply semantically relevant unauthorized curriculum and unrelated student/teacher records. Verify unauthorized chunks never enter model context and selected context contains only information reasonably needed by the operation.
- Inspect controlled public output, model inputs, and logging for prohibited secret disclosure and unnecessary student/teacher/context/tool/provider information. Internal denial diagnosis must preserve privacy boundaries; rejected actions cannot appear successful.

Deterministic enforcement tests are distinct from probabilistic prompt-injection/response-quality evaluations. Neither documentation review nor future passing tests establish legal compliance. Authentication, secret-management, and deployment-specific compliance choices remain deferred to their dependent design/implementation decisions.

## Step 9 — Evaluation design and decision process

Approval: decisions.md STEP9-001 and STEP9-002. Use this reasoning order:

Behavior → Failure → Cost → Dataset → Metric → Threshold → Scorer → Baseline → Experiment → Slices → Decision → Regression.

Metrics and thresholds follow product behavior and failure risk, not popularity. Deterministic API, authentication/authorization, idempotency, transactions, state transitions, tool permissions, retry/recovery, and durable-commit behavior belong primarily in tests. Probabilistic AI behavior belongs primarily in evals. Existing deterministic guarantees remain mandatory regardless of aggregate AI quality.

### Initial MVP eval families

| Family | Behavior to assess |
| --- | --- |
| POC diagnosis (first/core intelligence family) | Evidence-selected diagnosis, valid no-POC/insufficient outcomes, supported multiple POCs, and justified foundational target selection. |
| Scaffolding | Useful diagnostic/scaffolding questions; support for the blocking POC; avoid premature answers; adapt to student response and increase support appropriately when stuck. |
| Understanding verification | Do not treat “I understand” alone as strong mastery evidence; assess explanation, independent attempts and/or transfer; distinguish guided from independent success. |
| RAG / grounding | Retrieve relevant authorized curriculum for objectives/prerequisites; use it correctly; never claim grounding after required retrieval failure. |
| Tool / agent behavior | Correct selection/arguments, valid state and context-dependent allow-list compliance, no unauthorized execution, bounded steps, and no duplicate durable effects. Test deterministic enforcement separately. |
| Mastery / evidence | Evidence reflects demonstrated behavior; guided success is weaker than independent success; preserve contradictions; weak/single evidence does not automatically become mastery; AI never directly changes official mastery. |
| Safety / authority | Prompt-injection resistance; no cross-student disclosure or unauthorized actions; model cannot override trusted identity/state/authority or grant itself mastery authority. |
| AI/system reliability | Assess probabilistic failure/reliability behavior, distinct from deterministic recovery and transaction tests and from operational health monitoring. |

### POC outcomes, evidence, and foundational blockers

Use the approved behavior in requirements.md §22.5 and ai-runtime.md “Step 9 diagnosis behavior”. SPECIFIC_POC, NO_POC, and INSUFFICIENT_EVIDENCE are valid diagnosis outcomes. Correct abstention with insufficient evidence is success, not a requirement to invent a diagnosis. Evaluate selected relevant evidence rather than latest-message-only or full-history context. More context is not automatically better.

Assess diagnostic questioning, useful variation, bounded stopping, insufficient/unknown recording, and incomplete-work visibility without automatic escalation solely for insufficient evidence. Repeated patterns may later be surfaced as observations, never unsupported judgments of laziness/disengagement. Preserve multiple supported POCs; target a foundational blocker only when evidence plus explicit curriculum prerequisites justify it. Otherwise gather evidence. Do not equate diagnosis outcomes with persisted POC/session lifecycle states or processing failure.

### Taxonomy, datasets, and ground truth

Define a POC taxonomy and labeling rubric that account for related/overlapping diagnoses and prerequisite relationships; naive string equality alone is insufficient. Human-review ground-truth cases. Synthetic generation may accelerate dataset creation, but model-generated labels are not automatically ground truth.

Preferred sources over time: synthetic plus human-reviewed cases; human-written edge cases; reviewed/anonymized real interactions when authorized and appropriate; known production failures. This does not approve real-student use or waive privacy/consent rules.

Assess reviewer agreement before relying on the benchmark. Low agreement requires investigation of ambiguous taxonomy, overlapping definitions, insufficient evidence, unclear rubrics, and genuinely non-identifiable cases. Do not claim precise POC accuracy against unstable ground truth.

### Metrics and thresholds

Candidate POC metrics: detection recall and precision; specific-POC classification accuracy; foundational/blocking-POC accuracy; insufficient-evidence detection accuracy; false confident diagnosis rate; calibration/high-confidence accuracy. Select metrics appropriate to the behavior and failure cost; this list does not mandate every metric for every experiment.

Numeric acceptance thresholds remain UNRESOLVED until supported by failure cost, product requirements, baseline performance, domain expertise, and empirical results. Distinguish release thresholds (acceptable deployment behavior) from runtime decision thresholds (sufficient evidence to act in an interaction). The framework's threshold stage identifies the decision criterion; it does not authorize invented numeric values before baseline/experimental evidence. Human approval governs acceptance criteria.

### Scorers

Use deterministic scoring for structured output, exact/structured labels where appropriate, tool behavior, and authorization. LLM-as-judge may score fuzzy scaffolding quality, answer leakage, pedagogical appropriateness, and some grounding behavior. Judges are not automatically ground truth: validate reliability against representative human expert review before relying heavily on judge metrics. Experts remain important for ambiguity, taxonomy refinement, subtle teaching quality, judge calibration, and newly discovered failures.

### Baselines, experiments, slices, and release decisions

Establish a baseline before claiming improvement. Meaningful prompt, model, RAG, Context Builder, tool, orchestration, and tutoring-policy changes require relevant baseline/eval comparison. Investigate regressions and tradeoffs rather than deciding from one improved metric.

Relevant slices include POC type, math topic, difficulty, evidence quality, clear versus ambiguous evidence, no-POC, insufficient evidence, multiple POCs, “idk”/minimal responses, and retrieval conditions. Overall averages must not hide weak slices.

Release gates follow failure risk and safe containment. Unauthorized actions, high-confidence incorrect POCs, and unacceptable answer leakage are strong gate candidates; exact criteria remain unresolved. A weak but safely handled slice may be monitored/improved without necessarily blocking a controlled MVP. Correct INSUFFICIENT_EVIDENCE on “idk” is safer than fabricated confident diagnosis. This distinction does not relax deterministic security, authority, or durability contracts.

### Regression

After discovering and fixing a failure, add a suitable regression case when practical. Production/teacher-reviewed failures and meaningful edge cases should strengthen the suite under approved data policies. Before production model/prompt/retrieval/orchestration changes, run relevant regression evals and compare quality, safety, important slices, cost, latency, and reliability. A newer/general-purpose stronger model is not automatically better for this Tutor.

## Step 10 — Evaluation and telemetry boundary

Evals answer “Is the Tutor behaving well?” Observability answers “Is the Tutor/system operating healthily?” Correlation is useful, but these signals are not interchangeable. Preserve relevant model, prompt, retrieval, and eval dataset versions on important AI records/traces/eval runs where practical. Use architecture.md §25.1 for operational metrics/spans/alerts and security.md for metadata-first logging. Do not duplicate sensitive application content in telemetry merely for evaluation convenience.

## Slice 1 deterministic verification

Verify real PostgreSQL migration/admission/rollback and duplicate concurrency behavior, not SQLite substitutes: PENDING commit, exact content, authenticated identity, protected lookup, enrollment/assignment eligibility and consistency, CLOSED new-send rejection versus replay, key validation, current-state replay, changed-content conflict, and no client identity override. Test transaction failure both between coupled writes and at commit; inspect database state through a separate connection. Verify metadata-only logging and safe validation errors. No AI eval is applicable to this slice.

## STEP5-001-A1 verification obligations

- Verify admission commits input/idempotency before background work and returns without waiting for tutor completion.
- Verify admitted work survives API/worker lifecycle interruption through PostgreSQL durability; preserve valid-owner and stale-owner guarantees.
- Verify GET authentication, resource authorization, non-disclosure, current durable state, committed-output-only delivery, and no processing or learning-state side effects.
- Preserve POST replay and explicit-retry distinctions, including CLOSED.
- Verify CLOSED sessions reject new messages; admitted work may finish and authorized reads remain available. Message COMPLETED alone must not close a session or update authoritative mastery.
- Verify new-session context retains original provenance and authorized scope without an unrestricted history dump.
- Verify metadata-first correlation across admission, worker, and GET.

These obligations span multiple slices. SLICE2A-001 resolved GET failure mapping; Stages 3–6 verify the implemented worker/admission/polling boundaries. New-session context and other unimplemented product flows remain future obligations, not tested capabilities.

## Deferred evaluation and tooling decisions

TODO / UNRESOLVED: numeric release thresholds; exact calibrated progress/transfer/confidence/escalation rubrics; exact POC taxonomy/labeling rubric and reviewer-agreement criteria; concrete datasets/reference cases and slice coverage using the approved Step 9 dimensions; sample/repeat policy; judge-reliability acceptance criteria; baseline approval; exact formatting/lint/type-check tools and commands; evaluation runner/configuration; performance budgets beyond approved runtime defaults. Do not change criteria merely to make failures pass. Evaluation acceptance decisions require human approval.

## Reporting

Report actual commands/checks, versions/evidence, observed outcomes, regressions, uncertainty, and what was not run with reasons/risks. Deterministic test results and probabilistic eval results must be clearly distinguished. Run the repository contract-check workflow and provide a concise handoff after implementation. Documentation synchronization is not runtime verification.

## Slice 2a staged verification — SLICE2A-001

Stage 1 must run real PostgreSQL tests for migration/metadata parity, deferred message/job/result shapes, immutable input, unique reply/same-session/student source, unique PROCESSING session under contention, closure reasons, attempt/error checks, backfill preservation and cancellation, ambiguous-history rejection, transactional migration rollback, and guarded downgrade. Explicitly test old admission rejection on 0002; Stage 1 is not deployable with old admission. SQLAlchemy metadata comparison alone does not verify triggers.

Later stages must preserve FAILED replay=200 with no scheduling, add atomic message/job/key/counter admission, session FIFO/backoff/FAILED barriers, ownership/lease/stale completion, crash and shutdown injection, read-only authenticated GET, safe failures, and metadata privacy. Existing fixtures that directly write FAILED/CLOSED must be updated to valid coupled data without weakening public assertions. No live-model eval is applicable to Stage 1.

Stage 2 verification adds rollback injection after sequence allocation, message insertion, job insertion, and key association; concurrent distinct-send sequence allocation; and HTTP replay/new-send against a real 0001→0002 backfill. FAILED replay snapshots jobs and session counters as well as input/key records, while trapping writes. Fixture corrections preserve existing HTTP/privacy/authorization/idempotency assertions; they do not disable constraints or simulate a worker. Exact executed results and the 18-failure classification are in handoffs/slice2a-stage2.md.


Stage 3 verification adds 55 real-PostgreSQL worker cases covering separate-process claims,
locked heads, retry/FAILED barriers, independent heartbeat, expiry and fixed deadlines,
stale tokens/generations, authorization/closure cancellation, single-response completion,
rollback and uncertain acknowledgement, bounded transient retries, sanitized failures,
shutdown and database backoff. The complete suite passed 164 tests. These deterministic
processor tests make no claim about model quality. See handoffs/slice2a-stage3.md.

Stage 4 adds 11 deterministic model-adapter tests: exact synthetic response preservation,
invalid output rejection without coercion/retry, cancellation propagation, PostgreSQL
completion/replay, and each known transient failure exhausting the existing two-claim
budget with FAILED replay remaining read-only. The full suite passed 175 tests. No live
provider or tutoring-quality eval is claimed; see handoffs/slice2a-stage4.md.

Stage 5 adds 23 PostgreSQL polling cases: all five states and exact safe envelopes,
no-store responses, missing/invalid/duplicate credentials, teacher/other-student denial,
non-discoverable and mismatched/tutor resources, malformed UUIDs, disabled/revoked access,
historical reads after closure or loss of new-work eligibility, safe storage/invariant errors,
and worker completion between snapshot acquisition and delivery. SQL capture verifies one
read query and no DML. Full suite: 198 passed; details in handoffs/slice2a-stage5.md.


## Slice 2a Stage 6 — Integration acceptance evidence

Stage 6 implements the previously authorized PostgreSQL integration/failure-injection
validation, with the human's explicit end-to-end scenario list. No new behavior or numeric
acceptance threshold is inferred. The authoritative invariants remain SLICE2A-001,
requirements §§22.1–22.4/Slice 2a, architecture §31.8, schema §31.6, ai-runtime's worker
contract, security's execution/read authorization, and the API polling/replay contract.

`tests/test_async_lifecycle.py` adds 19 cases through actual POST/GET handlers, service and
repository transactions, migrated PostgreSQL, worker, and configured FakeModelClient.
The complete suite passed 217 tests in 18.01s. Existing tests retain admission rollback,
heartbeat/deadline, independent-process claim contention, schema, privacy, and error coverage.
See `handoffs/slice2a-stage6.md` for each requested scenario mapped to test evidence.

An actual spawned worker is terminated after committing a claim and entering its fake model.
Its persisted timestamps are then shifted to exercise expiry without a 45-second test wait.
Existing heartbeat/timeout tests use shortened compatible settings; no claim is made about
production scheduling, real provider cancellation, load, or external model quality. PostgreSQL
constraints remain enabled. No assertions, retry policy, or contract criteria were weakened.
