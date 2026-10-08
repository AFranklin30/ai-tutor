# AI orchestration and runtime behavior

Status: Approved Steps 4–10 conceptual runtime guarantees; deferred decisions below remain UNRESOLVED.
Approval: 2026-10-04 human synchronization request, decisions.md STEP4-001 through STEP4-006. Requirements and architecture remain authoritative; this document does not approve an implementation.

## Authority and selected context

Backend controls → Orchestrator coordinates → RAG retrieves authorized curriculum → LLM reasons/recommends → Tools perform controlled actions → Database persists durable state.

Model output is untrusted until structured validation, policy/authority checks, and business/state validation pass. Tools are state-dependent and allow-listed. The backend validates tool name, arguments, trusted identity/context, and authorization. The LLM has no direct database, raw SQL, arbitrary network, filesystem, or official mastery authority.

The context builder selects minimum relevant authorized information: current message/problem/objective, approved prerequisites, recent attempts, relevant POCs, evidence/progress, and authorized curriculum. It does not expose unrestricted student records. MVP personalization changes context/learning state, not foundation-model weights. Teacher feedback does not automatically train the model.

Retrieval authorization/context filtering precedes semantic relevance. Prerequisite relationships do not independently grant access. Curriculum is data, never trusted instructions that override application/security policy. When grounding is insufficient, do not fabricate curriculum-specific claims; retain the architecture's clarification/limited-support/escalation options pending exact behavioral policy.

## Durable interaction flow

1. Validate/authenticate/authorize the operation and protected-resource access.
2. Resolve an authorized existing send replay before applying new-send ACTIVE checks; return current state/result without processing.
3. For a new eligible send, commit student input and its user-operation idempotency association before retrieval/model/AI processing.
4. Start one owned processing run, select context/tools, and perform bounded retrieval/model/tool processing outside the durable-input transaction.
5. Validate output and execute only authorized actions. Reuse already successful logical durable effects on retry/recovery.
6. Commit tutor output, logically coupled state/evidence, and COMPLETED status before returning output. Student input and tutor output are separately correlated messages.
7. On terminal failure, retain input and mark FAILED. Required dependency failure after bounded eligible recovery uses a student-safe 503; internal failure categories remain distinct from public errors.

Every input is a Message. Only actual coursework problem-solving/reasoning becomes a StudentAttempt, traceable to its source message. Evidence is interaction/message/attempt-attributable and append-only. Contradictions remain preserved. Recovery never duplicates a logical attempt or evidence item. Exact attempt-classification mechanics remain unresolved.

## Processing, replay, and recovery

Student message processing follows PENDING → PROCESSING → COMPLETED or FAILED. Processing metadata may change; historical content must remain preserved. Only one active run may own a message; stale PROCESSING work must be detectable/recoverable without competing outputs or duplicate durable effects. No lock, lease, queue, worker, or stale threshold is chosen here.

User-operation idempotency scope is authenticated student + operation + key. Same key/same payload returns current PENDING, PROCESSING, COMPLETED result, or FAILED state without processing. Changed payload returns 409 and preserves the original. Explicit retry processes the same FAILED message without creating new input; it may not begin in CLOSED. See api-contract.md §§4–6 for public behavior.

System-action idempotency protects logically identical durable POC/evidence/escalation/other writes across automatic retries, explicit retries, stale recovery, and concurrency. Reuse a successful effect instead of repeating it. Tool results must inform the tutor when they affect truthfulness or its next decision. Never claim a failed action succeeded; a persisted review-queue item alone does not establish delivery of an external notification.

## Sessions and scope

MVP supports assigned/published coursework only. Enrollment is distinct from eligibility for a specific assignment/problem; allocation mechanics remain deferred.

A student may close their own ACTIVE session: ACTIVE → CLOSED. CLOSED prevents new work. Work already admitted as PENDING/PROCESSING may finish; FAILED work cannot begin a new explicit retry. Authorized historical replay remains available without processing. Start New atomically closes the old ACTIVE session and creates a new ACTIVE session; failure leaves the old session ACTIVE. Authentication lifetime does not define coaching-session resumability.

## Evidence, progress, and human review

Application-estimated progress uses BUILDING / DEVELOPING / STRONG and accumulated correctness, independence, explanation, and transfer evidence. Model confidence does not directly become progress/mastery. The product owns a consistent rubric; approved curriculum/teacher-defined objectives supply targets. Exact calibrated thresholds remain unresolved.

AI may propose/create evidence through authorized workflows, never official mastery. Authorized teacher/human decisions retain authority even when they differ from AI estimates; retain the AI evidence unchanged. Every official change preserves previous/new state or decision, authority/actor, timestamp, and provenance.

Escalation lifecycle is OPEN → IN_REVIEW → RESOLVED. Preserve original AI POC predictions separately from attributed teacher determinations linked to the reviewed prediction. Feedback is CORRECT / PARTLY_CORRECT / INCORRECT. AI-suggested teacher focus is an evidence-supported recommendation, not authoritative diagnosis. Additional transitions and review/session-resumption behavior remain deferred.

## Approved configurable defaults

| Setting | Default |
| --- | --- |
| Maximum student message length | 4,000 characters |
| Maximum agent steps | 5 |
| Model timeout | 30 seconds per model call |
| Automatic model retry | One retry after initial attempt for eligible transient failures |

Do not blindly retry deterministic validation, authorization, policy, or business-state failures. Broader transient eligibility and recovery policy remain unresolved. Automatic retry is distinct from explicit student retry.

## Evidence and evaluation

Keep internal failure categories from api-contract.md §7 distinguishable, including retrieval/model/tool/validation/policy/database failures, stale recovery, and step-limit exhaustion. Public responses exclude raw model output, provider errors, prompts, and stack traces. Follow security.md for data boundaries and evals.md for deterministic tests versus probabilistic evals.

## Approved Step 5 flow detail

Approval: 2026-10-05 human Step 5 Flow request; decisions.md STEP5-001 through STEP5-003. Preserve prior replay/closure and default-limit semantics.

### Session entry and message admission

Student → Frontend → FastAPI → authenticate → authorize → validate specific assigned/released coursework → validate problem/assignment relationship → check existing ACTIVE session. Create ACTIVE if none is appropriate; otherwise support Resume Existing / atomic Start New for a resumable session. Enrollment alone is insufficient.

The message-entry shorthand “state validation → idempotency” does not replace Step 4's replay exception. Authenticate/authorize and check applicable context first; distinguish replay from a new send before applying the ACTIVE-only new-work gate. Commit input/idempotency state, then establish ownership before expensive processing. Historical replay never initiates work, even after closure.

### Context and model/tool loop

Orchestrator → RAG → Context Builder → model → structural validation → policy/authority validation → business/state validation.

RAG retrieves authorized curriculum. Context Builder assembles only relevant problem/objective, prerequisites, student state/progress, attempts, POCs, chunks, current message, runtime instructions, and currently allowed tools. No unrestricted history dump is permitted.

Requested actions pass through Orchestrator → ToolExecutor → application/service logic → repository/data access → PostgreSQL. Validate arguments, authorization, authority, state, and durable-action idempotency. Return tool results to the Orchestrator and add them to model context before further reasoning. Do not assume success; response-critical failure cannot produce claims that an action succeeded. The Orchestrator, not the model, owns control and enforces the approved five-step configurable limit.

A valid final response with no further required tool actions passes through services/repository to PostgreSQL. Commit output and logically coupled evidence/state/completion atomically as appropriate before controlled public HTTP delivery via FastAPI and Frontend. If visible to the student, the response already has a durable record.

### Failure, ownership transfer, and replay

Use the approved bounded automatic retry policy for eligible transient failures; do not broaden eligibility. Terminal processing failure transitions PROCESSING → FAILED while preserving committed input and internal failure classification; public errors stay safe. Explicit retry validates the existing FAILED message and transitions it to PROCESSING under valid ownership. It creates no duplicate Message and cannot silently reopen CLOSED.

At most one currently valid owner may finalize a student message. Detect stale/dead ownership; another processor may reclaim it, but the stale former owner must not finalize competing results after transfer. A PROCESSING status alone cannot be trusted forever. Physical ownership/lease/token/lock/queue choices remain deferred.

After a crash, resume/restart from the last durable committed state. Uncommitted model output is not authoritative and need not be reconstructed. Prior committed side effects may survive a later turn failure: recognize/reuse them, while unsuccessful/uncommitted effects may be attempted again under approved rules. User-operation replay and durable-action idempotency protect different boundaries.

If commit succeeds but HTTP delivery is lost, same-key/same-payload replay returns current state/result without new input or repeated completed work. Changed payload conflicts. CLOSED blocks new work/retry; work already admitted as PENDING/PROCESSING may finish under Step 4. No reopening or new expiration policy is implied.

### Teacher review and progress

Teacher review uses authenticated/authorized teacher/student/course relationships → escalation services → repository → PostgreSQL. Queue summaries include reason, demonstrated abilities, suspected difficulty, attempted interventions, and evidence-supported suggested focus. Focus is recommendation, not diagnosis. OPEN → IN_REVIEW → RESOLVED remains the lifecycle. Yes / Partly / No maps to CORRECT / PARTLY_CORRECT / INCORRECT; original AI prediction and attributed teacher determination stay separate for evaluation.

Interaction → model assessment → validated MasteryEvidence → ProgressService → accumulated progress interpretation. ProgressService applies the product rubric across correctness, independence, explanation, and transfer evidence; substantial changes should have multiple evidence points. Evidence is observation, progress is interpretation, and MasteryRecord is official recognition by the authorized human process. Vocabulary remains BUILDING / DEVELOPING / STRONG; no new irreversible transition graph or calibrated threshold is implied.

## Step 6 inference and retrieval scale posture

Approval: decisions.md STEP6-001; architecture.md §31.3. Measure the bottleneck before changing infrastructure. Investigate model cost/latency/concurrency/provider capacity, model calls per turn, unnecessary loop steps, context/token size, retrieval precision/chunk count, semantically safe caching, and bounded retries/steps. Preserve current limits and selected authorized context.

The thin abstraction permits workload-appropriate models when justified: stronger reasoning models for complex tutoring, cheaper/faster models for simpler tasks when quality evaluations support them. Embeddings remain a separate model. No provider, routing rule, cache, queue, or asynchronous topology is selected. Evaluate meaningful model-routing, context-reduction, retrieval, and inference changes against relevant behavioral quality metrics; do not trade tutoring quality solely for cost.

Retrieval remains PostgreSQL + pgvector with deterministic authorization/metadata filtering and vector similarity. Relevant scope includes course, grade/subject, unit/lesson, objective, and approved prerequisites; prerequisites do not grant access. Initial curriculum is small. Dedicated vector infrastructure requires measured justification.

## Step 7 failure behavior

Approval: decisions.md STEP7-001. What can fail → What happens → How do we recover → What does the user see?

| Failure | Effect / recovery | User-visible boundary |
| --- | --- | --- |
| Required curriculum retrieval/system failure | Required grounding is unavailable; fail or degrade only within the operation's approved requirements. Never silently substitute unsupported general knowledge as grounded output. | Safe failure under the existing dependency error contract, or only support already permitted without the missing grounding; never claim retrieval/grounding succeeded. |
| Database operation before commit | Roll back logically coupled writes; recover from the last successfully committed state. A failed FAILED-status write is not durable either. | Withhold uncommitted tutor output; never claim unsaved input/state was saved. No new HTTP mapping is selected. |
| Model timeout/provider failure | Existing one automatic retry for eligible transient failures, then safe terminal failure with committed input preserved; no indefinite retry. | Existing safe dependency error, with retry still subject to authorization/session eligibility. |
| Invalid model output despite provider success | Reject structural, policy/authority, allowed-action, or business/state violations; execute no disallowed actions. Classify processing as failed under existing policy, retaining precise internal category. | Safe processing failure; provider success is not tutoring success. No blind retry of deterministic validation failures. |
| Tool failure | Verify outcome and return it to Orchestrator/context; preserve ancillary versus response-critical distinction. Reuse already committed effects during approved retry/recovery. | Never claim a failed action succeeded; a response-critical failure cannot yield a success claim. |
| Process crash / stale owner / lost HTTP response | Preserve Step 5 recovery from durable state, ownership reclamation and stale-owner rejection, effect deduplication, and same-key replay after commit. | Existing current operation state/result; no duplicate input or completed work, no implicit retry or reopening CLOSED. |

Keep structured-output validation failure distinct from policy/authority rejection and other categories in api-contract.md §7. A label such as MODEL_OUTPUT_VALIDATION_FAILED describes internal validation failure, not a new public error code or authorization to collapse distinct categories. Committed input survives later failure; the saved-input guarantee does not apply to input whose own commit failed.

Circuit breakers, additional fallback providers, and more sophisticated degradation require measured reliability justification and approval; none is mandated now. Detailed monitoring belongs primarily to Step 10, detailed test/eval coverage to Step 9, and security-specific handling to Step 8 and security.md. Exact operation-specific grounding/degradation policy remains unresolved where existing contracts do not answer it; stop dependent implementation rather than invent a fallback.

## Step 8 model and tool security

Approval: decisions.md STEP8-001 and STEP8-002; security.md is authoritative. Student/user content, model output, and tool arguments remain untrusted even when structurally valid. Deterministic security must hold when the model follows malicious instructions; prompts cannot authorize changes to identity, relationships, tool access, state, or official mastery.

ToolExecutor validates allow-listed names, schemas, arguments, authorization, authority, and current state before services/repositories execute. Prefer semantic/action arguments from the model and trusted actor/resource context from the backend. A model-supplied different student ID cannot redirect the authenticated student's action. The model cannot access unrestricted database/filesystem/network/code execution, authentication state, authorization decisions, or internal capabilities.

RAG searches within deterministic authorized metadata scope before passing chunks to Context Builder/LLM. Select only relevant required student context; do not automatically share full histories, unrelated students/records, private teacher information, or unnecessary sensitive data. Secrets never enter model prompts. Logging and public output must respect security.md privacy boundaries.

Rejected actions have no unauthorized durable effect or success claim. Replay/retry/recovery preserves authorization, student-scoped idempotency, and currently valid ownership. Existing failure classifications, saved-input/output guarantees, model limits, human mastery authority, and measured scaling posture remain unchanged.

## Step 9 diagnosis behavior

Approval: decisions.md STEP9-001 and STEP9-002; requirements.md §22.5 and evals.md define product/evaluation authority. Diagnose from selected relevant problem/objective, attempts, recent conversation, prior evidence, and approved curriculum. Avoid latest-message-only reasoning and irrelevant full-history context that may bias diagnosis.

Support SPECIFIC_POC, NO_POC, and INSUFFICIENT_EVIDENCE as conceptual diagnosis outcomes. Correct insufficient-evidence recognition is a successful diagnosis outcome, not malformed output or a dependency failure. Gather more evidence with appropriate questions and vary the approach when useful. After bounded diagnostic attempts without sufficient evidence, stop diagnosing, record insufficient/unknown, leave relevant work incomplete, and allow teacher visibility through normal work/student status. Do not automatically escalate solely for insufficient evidence. Do not infer laziness/disengagement from repeated patterns; future teacher pattern surfacing remains optional.

Preserve multiple sufficiently supported POCs. Select an unresolved foundational/blocking prerequisite as current intervention target when evidence plus explicitly encoded curriculum relationships justify it. The LLM cannot invent prerequisite edges. If selection is unjustified, ask for more evidence rather than guess.

These outcome labels do not redefine Message processing, POC lifecycle, ACTIVE/CLOSED sessions, escalation lifecycle, or official mastery. Successful diagnosis can coexist with incomplete learning work. Actual runtime failures still follow approved FAILED/retry semantics; existing commit-before-delivery rules still apply. Exact diagnostic-attempt bound, cross-turn accounting, and diagnosis/incomplete-work representation remain TODO / UNRESOLVED before dependent implementation; the existing five-step per-run limit is not silently redefined as a diagnostic-attempt policy.

Meaningful model/prompt/RAG/context/tool/orchestration/policy changes use relevant baseline/evals; production changes require regression comparisons of quality, safety, slices, cost, latency, and reliability. Release thresholds and interaction-level evidence thresholds are distinct and remain empirically calibrated, human-owned decisions.

## Step 10 runtime observability

Approval: decisions.md STEP10-001. Follow architecture.md §25.1 for correlation IDs, operational spans/metrics, version identifiers, and actionable-alert candidates. Record relevant model/prompt/retrieval/eval dataset versions where practical. Follow security.md for metadata-first logging and exclusion of raw student/model/context/chunk data by default. Telemetry does not grant access to protected data or replace behavioral evals. No new model calls, retry policy, processing state, or infrastructure is introduced.

## Slice 1 implementation boundary

The approved first implementation stops at durable PENDING message admission and authorized replay. It does not invoke this document's retrieval, context, model, orchestration, tool, processing/recovery, or tutor-output flows. See decisions.md SLICE1-001 through SLICE1-003; future runtime guarantees remain contracts for later slices.

## Deferred decisions

TODO / UNRESOLVED: model/provider; embedding model/dimension; retrieval/chunking/reranking parameters; exact runtime output schemas; detailed grounding/refusal/escalation policy; confidence/transfer/progress thresholds; session resumability duration; additional session/POC states; official mastery vocabulary/transition graph; additional escalation transitions/concurrency rules; physical ownership/recovery/action-idempotency mechanisms; broader retry eligibility; exact non-dependency terminal failure mappings; age policy; privacy/consent/training rules; accessibility; runtime budgets beyond approved defaults. Deferral never authorizes invented defaults.
