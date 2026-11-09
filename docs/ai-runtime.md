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
4. Return the POST admission response after input commit. Independently, the PostgreSQL-backed worker establishes valid ownership and performs bounded retrieval/model/tool processing outside the durable-input transaction.
5. Validate output and execute only authorized actions. Reuse already successful logical durable effects on retry/recovery.
6. Commit tutor output, logically coupled state/evidence, and COMPLETED status before returning output. Student input and tutor output are separately correlated messages.
7. On terminal failure, retain input and mark FAILED. A genuine dependency outage preventing fulfillment of the current HTTP request uses a student-safe 503. Successful idempotent POST replay returns 200 even for stored FAILED, without creating input, scheduling work, or starting another attempt (SLICE1-004); internal failure categories remain distinct from public errors.

The numbered flow spans separate admission, background-processing, and GET-delivery operations. Committed output becomes available through authenticated GET; the worker does not send the original POST response. Existing safe failure rules remain in force. SLICE2A-001 defines stored FAILED as HTTP 200 with the safe tutor_processing_failed error in the polling envelope.

Every input is a Message. Only actual coursework problem-solving/reasoning becomes a StudentAttempt, traceable to its source message. Evidence is interaction/message/attempt-attributable and append-only. Contradictions remain preserved. Recovery never duplicates a logical attempt or evidence item. Exact attempt-classification mechanics remain unresolved.

## Processing, replay, and recovery

Student message processing follows PENDING → PROCESSING → COMPLETED or FAILED. Processing metadata may change; historical content must remain preserved. Only one active run may own a message; stale PROCESSING work must be detectable/recoverable without competing outputs or duplicate durable effects. STEP5-001-A1 selects one separately deployed PostgreSQL-backed worker. No dedicated queue service is introduced. SLICE2A-001 now defines physical ownership, lease and recovery for this slice; implementation is staged.

User-operation idempotency scope is authenticated student + operation + key. Same key/same payload returns current PENDING, PROCESSING, COMPLETED result, or FAILED state without processing. Changed payload returns 409 and preserves the original. Explicit retry processes the same FAILED message without creating new input; it may not begin in CLOSED. See api-contract.md §§4–6 for public behavior.

System-action idempotency protects logically identical durable POC/evidence/escalation/other writes across automatic retries, explicit retries, stale recovery, and concurrency. Reuse a successful effect instead of repeating it. Tool results must inform the tutor when they affect truthfulness or its next decision. Never claim a failed action succeeded; a persisted review-queue item alone does not establish delivery of an external notification.

## Sessions and scope

MVP supports assigned/published coursework only. Enrollment is distinct from eligibility for a specific assignment/problem; allocation mechanics remain deferred.

PILOT-EVAL-002 (2026-10-19) explicitly excludes generating new practice problems from the MVP. Redirect requests for new practice to another assigned problem without generating one or inventing coursework availability. First-pilot mathematical scope is requirements.md §2.1. An occasional unnecessary question is a quality weakness, not an automatic pilot blocker; it does not excuse any approved blocker. This records approved behavior without modifying the offline prompts or runtime settings.

A student may close their own ACTIVE session: ACTIVE → CLOSED. CLOSED prevents new work. Work already admitted as PENDING/PROCESSING may finish under NORMAL closure with current authorization; administrative/unknown closure cancels unfinished work under SLICE2A-001; FAILED work cannot begin a new explicit retry. Authorized historical replay remains available without processing. Start New atomically closes the old ACTIVE session and creates a new ACTIVE session; failure leaves the old session ACTIVE. Authentication lifetime does not define coaching-session resumability.

Completed learning sessions stay CLOSED. Further conversation uses a new eligible session with minimum relevant authorized prior context. Do not reopen old sessions, dump unrestricted history into model context, or infer official mastery from message/session completion.

PILOT-EVAL-003 clarifies inclusion of written `x/d = b` forms with positive whole-number divisor and right-hand side while explicit fractional-coefficient forms remain deferred (requirements.md §2.1). Its isolated seven-case v1-prompt diagnostic design preserves existing local settings and exact response validation; it does not change application orchestration, prompts, human mastery authority or pilot acceptance.

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

A valid final response with no further required tool actions passes through services/repository to PostgreSQL. Commit output and logically coupled evidence/state/completion atomically as appropriate before subsequent delivery through authenticated FastAPI GET and Frontend. The background runtime does not complete the original POST response; all existing validation, tool, authorization, and atomic-finalization requirements remain intact. If visible to the student, the response already has a durable record.

### Failure, ownership transfer, and replay

Use the approved bounded automatic retry policy for eligible transient failures; do not broaden eligibility. Terminal processing failure transitions PROCESSING → FAILED while preserving committed input and internal failure classification; public errors stay safe. Explicit retry validates the existing FAILED message and transitions it to PROCESSING under valid ownership. It creates no duplicate Message and cannot silently reopen CLOSED.

At most one currently valid owner may finalize a student message. Detect stale/dead ownership; another processor may reclaim it, but the stale former owner must not finalize competing results after transfer. A PROCESSING status alone cannot be trusted forever. See the approved Slice 2a section for physical ownership/lease/token/lock and work-discovery choices; STEP5-001-A1 excludes a dedicated queue service.

After a crash, resume/restart from the last durable committed state. Uncommitted model output is not authoritative and need not be reconstructed. Prior committed side effects may survive a later turn failure: recognize/reuse them, while unsuccessful/uncommitted effects may be attempted again under approved rules. User-operation replay and durable-action idempotency protect different boundaries.

If commit succeeds but HTTP delivery is lost, same-key/same-payload replay returns current state/result without new input or repeated completed work. Changed payload conflicts. CLOSED blocks new work/retry; work already admitted as PENDING/PROCESSING may finish under Step 4. No reopening or new expiration policy is implied.

### Teacher review and progress

Teacher review uses authenticated/authorized teacher/student/course relationships → escalation services → repository → PostgreSQL. Queue summaries include reason, demonstrated abilities, suspected difficulty, attempted interventions, and evidence-supported suggested focus. Focus is recommendation, not diagnosis. OPEN → IN_REVIEW → RESOLVED remains the lifecycle. Yes / Partly / No maps to CORRECT / PARTLY_CORRECT / INCORRECT; original AI prediction and attributed teacher determination stay separate for evaluation.

Interaction → model assessment → validated MasteryEvidence → ProgressService → accumulated progress interpretation. ProgressService applies the product rubric across correctness, independence, explanation, and transfer evidence; substantial changes should have multiple evidence points. Evidence is observation, progress is interpretation, and MasteryRecord is official recognition by the authorized human process. Vocabulary remains BUILDING / DEVELOPING / STRONG; no new irreversible transition graph or calibrated threshold is implied.

## Step 6 inference and retrieval scale posture

Approval: decisions.md STEP6-001; architecture.md §31.3. Measure the bottleneck before changing infrastructure. Investigate model cost/latency/concurrency/provider capacity, model calls per turn, unnecessary loop steps, context/token size, retrieval precision/chunk count, semantically safe caching, and bounded retries/steps. Preserve current limits and selected authorized context.

The thin abstraction permits workload-appropriate models when justified: stronger reasoning models for complex tutoring, cheaper/faster models for simpler tasks when quality evaluations support them. Embeddings remain a separate model. STEP5-001-A1 selects the separate-worker topology and PostgreSQL durable work source. No provider, routing rule, cache, or dedicated queue service is selected; other scaling choices remain deferred. Evaluate meaningful model-routing, context-reduction, retrieval, and inference changes against relevant behavioral quality metrics; do not trade tutoring quality solely for cost.

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

## Slice 2a — Approved worker contract (implementation staged)

Approval: SLICE2A-001. Stage 1 implements schema/constraints/backfill; Stage 2 atomically creates unclaimed jobs during new-message admission. Stage 3 implements the worker runner/service/repository and test-only deterministic processors. Stage 4 adds the thin model-client adapter and explicitly injected deterministic fake. Stage 5 implements authenticated read-only GET polling. No live provider exists yet. This section supersedes the corresponding ownership/retry deferrals above.

- claim_next(worker_instance_id) → optional Claim: lock user/session/authorization/head/message/job in approved order; reselect the oldest unresolved head; due PENDING only. Expired PROCESSING is fenced and becomes PENDING with two-second recovery backoff if budget remains, else FAILED. Never skip an unresolved head.
- renew_lease(claim) → renewed/lost/cancelled: match token + retry_generation + PROCESSING + unexpired lease/deadline and current authorization. Use PostgreSQL clock_timestamp(); extend to min(now+45 seconds, attempt_deadline_at), never revive expired ownership.
- complete(claim, validated_response) → committed/already-completed/lost/cancelled: reauthorize and fence after locks, then atomically insert the one tutor response and set COMPLETED/terminal job shape. Retain winning token for lost-acknowledgement reconciliation. The locked ownership check is the finalization serialization point, not a wall-clock promise at the instant of COMMIT.
- record_failure(claim, category) → requeued/failed/lost/cancelled: same fencing; only known transient MODEL_TIMEOUT/MODEL_UNAVAILABLE/MODEL_RATE_LIMITED may automatically requeue within the shared budget. Deterministic invalid output, configuration/policy failures, and unknown processing errors do not automatically retry. Database unavailability cannot truthfully record FAILED until a write commits.
- cancel(message_id, cause, trusted_authority) → cancelled/already-terminal: authoritative account/enrollment/coursework/closure policy, not client identity or model arguments. Cancel affected unfinished scope without freeing later unauthorized work. Completed output remains history.
- process_next(processor, stop) claims and commits, invokes at most one initial-generation model call per claim outside transactions, heartbeats independently, then completes or records failure. run(processor, stop) repeats with one active claim per process initially.

Defaults: model timeout 30s; lease 45s; heartbeat every 10s; per-claim deadline 90s; max_attempts=2 per retry generation; retry/recovery backoff 2s. Each claim gets a fresh UUID token and increments lifetime/cycle counts. Require at least 35s lease/deadline remaining before a call. Disable hidden SDK retries. Crash recovery consumes the same budget, even if the crash preceded the call; no nested model/worker retry multiplication. Future multi-step orchestration needs compatible accounting and does not silently change the existing five-step bound.

After heartbeat failure/lost ownership, stop initiating external work, cancel the local request where possible, and reject eventual stale output. A provider may continue after cancellation: exactly-once external execution is not guaranteed. After uncertain final commit, read PostgreSQL before considering further action; never invoke the model just because delivery was lost.

Shutdown: stop claiming; heartbeat during a 35s grace window; then cancel local work and leave lease-expiration recovery. Deployment shutdown does not mark input CANCELLED. Empty poll interval 1s. Database outage backoff 1/2/4/8/15s capped, ±20% jitter. Monitor queue wait/head age, claims/renewals/lease loss, failures/recovery/cancellation, latency, and observed model usage. Log metadata, never raw content, credentials, or claim tokens.

Future explicit retry: only known transient model-provider or infrastructure failures, subject to current authorization, ACTIVE session, retry budgets and rate limits. Invalid output, authorization failures, policy violations, invalid requests and unknown failures are not explicitly retryable. Preserve retry_generation and lifetime count; reset cycle count only in the future authorized workflow. No student-facing retry endpoint is implemented in Slice 2a. Same-key POST replay remains read-only HTTP 200, including FAILED.

## Deferred decisions

TODO / UNRESOLVED: model/provider; embedding model/dimension; retrieval/chunking/reranking parameters; exact runtime output schemas; detailed grounding/refusal/escalation policy; confidence/transfer/progress thresholds; session resumability duration; additional session/POC states; official mastery vocabulary/transition graph; additional escalation transitions/concurrency rules; durable tool-action idempotency mechanisms beyond Slice 2a; future explicit-retry budgets/rate limits; exact non-dependency terminal failure mappings; age policy; privacy/consent/training rules; accessibility; runtime budgets beyond approved defaults. Deferral never authorizes invented defaults.


### Stage 3 implementation notes

`processing_service.py` owns claim, renewal, completion, failure, and policy cancellation
transactions. `worker.py` runs one injected async processor outside those transactions and
maintains an independent heartbeat task. `cancel(claim)` rechecks persisted policy and live
ownership; discovery also cancels denied sessions under the user/session locks. No arbitrary
caller-supplied cancellation cause or administrative API is exposed.

Processor implementations must cooperate with the event loop and validate student-safe
output before returning text. Current deterministic fakes verify mechanics only; they do not
establish tutoring quality or production model safety. Production adapter, output policy,
deployment signal wiring, and telemetry export remain later work. Cancellation can stop
local consumption but cannot guarantee that a remote provider stops billing/execution.

Discovery reads all unresolved session heads in this controlled MVP to avoid starvation
behind a fixed prefix of FAILED heads. Candidate reads end before per-session claim
transactions. Each transaction applies a one-second lock timeout and five-second statement
timeout; model calls never hold its locks. Larger backlogs may require measured query and
batching work, without changing session ordering or ownership contracts.


### Stage 4 implementation notes

`model_client.py` defines an async `ModelClient.generate(ProcessingInput)` boundary and
`ModelProcessor` adapter. A call receives only the worker-selected input, never a database
session, claim token, credentials, tools, or unrestricted student records. The adapter
invokes the client once, propagates cancellation/failure, and rejects non-string, blank,
or NUL-containing output as MODEL_INVALID_OUTPUT without modifying valid text.
This is the existing persistence shape check, not a new semantic validation policy.

`FakeModelClient` requires explicitly supplied synthetic text, returns it deterministically,
and stores only that configured response and a call counter. It performs no network/database
access and captures no student input. It is opt-in dependency injection, never a production
fallback. No automatic model routing or client-internal retries are introduced. Stage 3's
worker remains the timeout/retry/lease authority. Approved production output policy and a
provider adapter are still prerequisites for live model integration.

## Offline tutor evaluation v1 — OFFLINE-EVAL-001

Approval: decisions.md OFFLINE-EVAL-001, human configuration/implementation message and supplied tutor prompt in this session. This is an isolated experiment, not the worker model implementation or production tutoring policy.

`experiments/tutor_v1/prompt.txt` preserves the supplied prompt as v1. `cases.py` supplies Grade 7 Mathematics, current message, authorized problem (or deliberately missing problem), and explicitly selected earlier completed exchanges. History may be incomplete; no later messages or excluded explanations may be reconstructed. At most ten exchanges are sent, oldest whole exchanges removed to fit. Instructions/current message/problem are never truncated. Required-content overflow records REQUIRED_CONTENT_OVERFLOW without a provider request.

Approval update: decisions.md OFFLINE-EVAL-002 authorizes the Luna switch and one paid run. OpenAI Responses API uses `gpt-6-luna`, explicit reasoning effort `none`, input ceiling 8,000 tokens, output allowance 1,000 tokens, 30-second local deadline, no retries and `store=false`. No tools, previous-response chaining, server conversation, RAG, worker retry policy, or automatic fallback. The runner uses direct standard-library HTTP rather than an SDK. It rejects incomplete provider output, refusals/tool output, malformed JSON, extra/duplicate fields, nonstring/blank/NUL replies. Structural validation is not mathematical, instructional, or semantic policy validation.

Implementation detail: input admission uses a conservative upper bound (UTF-8 bytes of the whole serialized text-only request plus 1,024 framing tokens), not an exact provider token count. This intentionally overcounts, may drop history or fail before an exact count would, and makes no token-utilization claim. The fixed single-user-message/no-tools format is required for this bound; format/model changes require revisiting it. Provider truncation is disabled. Local timeout cannot guarantee remote cancellation or prevent billing; no timeout triggers an automatic retry.

### Local Ollama baseline — OFFLINE-EVAL-003

Approval: current human request, recorded in decisions.md OFFLINE-EVAL-003. Explicit command: `python -m experiments.tutor_v1.local --output NEW_PATH.jsonl`. Fake remains the existing runner's default; Luna is unchanged. Pin the requested tag `qwen3.5:4b-q4_K_M`; require installed Q4_K_M, qwen35 architecture, 4.xB parameter size, local model digest and runtime version. Record model parameters, renderer/parser, template hash and tokenizer metadata. Require `/api/show` thinking values to include boolean false, and send top-level `think=false` to `/api/chat`; absent support fails setup rather than substituting behavior or models. Preserve prompt v1 as the system message and the identical serialized synthetic context as one user message. No additional model system prompt or stored messages may enter it.

Send the exact existing reply schema as `format`, `stream=false`, `num_predict=1000`, `num_ctx=12288`, `keep_alive=5m`. Model library metadata advertises 262144 context tokens; preflight requires model capacity at least 12288 and `/api/ps` verifies that the loaded context is exactly 12288 after a valid reply. This provides 8000 admitted input tokens + 1000 generated tokens + 3288 context headroom; the input bound already includes an assumed 1024 framing reserve. No silent reduction of context/budget or timeout. Keep 30-second total generation deadline including cold load, plus socket timeout; metadata calls also have a 30-second deadline and server startup has a separate 30-second limit. No generation retry or warmup generation occurs. Stop the remaining run on timeout, transport failure, model/context/control mismatch or evidence that input/output limits or thinking controls failed; record remaining cases NOT_EXECUTED. Other invalid/incomplete outputs fail their case without rerunning it.

**Qwen-specific input admission:** Do not invoke the OpenAI estimator. Inspect Qwen's own registry GGUF metadata: tokenizer.ggml.model=gpt2 and tokenizer.ggml.pre=qwen35, with byte-level BPE vocabulary/merges. Independently use serialized local request UTF-8 bytes + 1024 assumed renderer/framing tokens as a deliberately conservative text-only input bound. Counting JSON keys/schema bytes overcounts; the fixed two-message, no-tools/no-images format and absence of extra model system/history are required assumptions. The reserve is not a measured exact tokenizer bound or universal proof. As before, select at most ten earlier completed whole exchanges, remove oldest whole exchanges until the bound is <=8000; never truncate instructions/current message/problem; required overflow fails without generation. Available actual prompt_eval_count is checked after generation against both 8000 and the estimated bound; an exceedance fails and stops further generation. Exact equality with Luna's selected history is not promised when conservative transport-specific overhead differs. No tokenizer dependency is added.

**Output accounting:** Ollama documents num_predict as the maximum generated tokens and eval_count as generated-token usage, not just the visible reply string; JSON formatting tokens consume the allowance too. Prompt counts and nanosecond load/prompt/generation/total durations are captured separately, including usage available on invalid/incomplete replies. With thinking enabled, reasoning can consume generated-token budget; this baseline requests disabled thinking and rejects observed thinking fields, never strips them to pass validation. Ollama's counters are runtime-specific, not OpenAI billing counts or a separately verified reasoning-token breakdown. Require done=true, done_reason=stop, exact returned model, no thinking/tool/image output, and then validate the complete content with the existing exact reply schema (including duplicate/extra key rejection). Length-limited JSON fails even if parseable. Available eval_count >1000 fails. JSON validity does not establish mathematical correctness, instructional safety, mastery or acceptance. All six human judgments remain pending.

Sources verified 2026-10-18: [official tag](https://ollama.com/library/qwen3.5:4b-q4_K_M), [GGUF tokenizer/context metadata](https://ollama.com/library/qwen3.5:4b-q4_K_M/blobs/a9d0a3e1d8c9), [chat API](https://docs.ollama.com/api/chat), [thinking controls](https://docs.ollama.com/capabilities/thinking), [runtime parameters](https://docs.ollama.com/modelfile), [model details](https://docs.ollama.com/api-reference/show-model-details), [loaded-model metadata](https://docs.ollama.com/api/ps). Installed runtime support must still pass preflight; fetched documentation is not an executed local test.

### Scoped prompt v2 preparation — OFFLINE-EVAL-004

Approval: human request dated 2026-10-19 and decisions.md OFFLINE-EVAL-004. Preserve `prompt.txt` v1 byte-for-byte. `prompt-v2.txt` is v1 with exactly this additional paragraph immediately after rule 3's evidence-discipline instruction; no other prompt text or numbering changes:

> Distinguish who supplied each step. A valid mathematical method is not evidence that the student used it. A step suggested by the tutor is not evidence that the student independently chose it. If the student’s method is unknown, ask neutrally how they reached their answer.

Both isolated CLIs accept explicit `--prompt-version v2`; omitted selection remains v1, and the runner's default mode remains fake. The selected prompt alone is passed through existing admission/context/output paths. Evidence records its selected version and SHA-256 using the existing convention (UTF-8 prompt text with trailing newlines stripped), while dataset version/hash remain those of the unchanged v1 fixtures. No scoring expectations, review judgments, comparison notes or human-review artifact are sent to the model.

For a local v2 comparison, require the exact v1 model digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` for `qwen3.5:4b-q4_K_M`, as recorded in `artifacts/tutor-v1-local-qwen35-first-disconnected.jsonl`. Record the required digest in the new header and reject a mismatch before any generation. Preserve all existing local generation settings, context-selection/overflow rules, 30-second timeout, exact reply schema, one sample/case, no retries, cloud-disabled loopback lifecycle and exclusive evidence creation. Longer prompt text is counted by the existing local admission policy; the twelve fixed cases still select identical context without removing history. Luna support remains available without changing its transport/settings. This approval covers preparation/deterministic verification only: do not execute real-model v2 generation or paid API calls in this task.

### Focused v1/v2 repeatability protocol — OFFLINE-EVAL-005

Current human authorization covers preparation/deterministic checks only. The separate repeatability CLI has `prepare` and `run` actions; run defaults to fake, and only explicit `--mode local` selects local inference. There is no paid option. The fixed design schedules cases 03/04/05/08/10 × prompts v1/v2 × three samples, for exactly thirty unique slots and at most thirty request reservations. A failed slot is never replaced or retried. Original single-sample runners and baseline artifacts are unchanged; this is a separate focused multi-sample protocol.

Execution order is a reproducible pseudorandom ordering: sort the fixed slot IDs by SHA-256 of `schedule:<integer seed>:<slot ID>`, with slot ID as a tie breaker (`sha256_sort_v1`). Record schedule seed 20261019, complete schedule and schedule hash. This seed is solely for scheduling/masked ID ordering; no model-generation seed is passed or inferred. Model/runtime seed defaults remain unmodified and are recorded as unspecified, not falsely known. Each request is newly constructed by the existing local case path with only the selected prompt and that case's authorized problem/current message/selected earlier exchanges. No previous sample replies, conversation identifiers, scoring expectations, judgments, schedule fields or sample identifiers enter model input. Ordinary prompt-prefix caching is not conversation history; it can affect timings and is recorded where available.

Validate saved schedule/spec/mapping against the fixed design, current prompt hashes, dataset hash and unchanged configuration before opening any local server. Require the baseline model/digest and the baseline sampling parameters (presence_penalty=1.5, temperature=1, top_k=20, top_p=0.95), inspected rather than silently adjusted. Preserve all existing local context bounds/selection, num_ctx=12288, num_predict=1000, think=false, timeout=30 seconds including cold load, output schema, no tools, no retries, loopback/cloud-disabled server and single-request concurrency. Sampling parameters remain model defaults, not new tuning. Runtime version is recorded, not fabricated or silently treated as identical.

Reserve and flush one slot-start event before its single call; budget reservations never exceed thirty. Record case ID, prompt version/hash, sample ID, opaque review ID, execution position, outcome and available native usage/timing. Preserve incomplete/invalid outcomes with their usage; do not manufacture a valid reply. Preserve the existing halt categories: MODEL_TIMEOUT, LOCAL_INPUT_BOUND_EXCEEDED, LOCAL_MODEL_MISMATCH, LOCAL_OUTPUT_ALLOWANCE_EXCEEDED, UNEXPECTED_THINKING_OR_ACTION, LOCAL_RUNTIME_CONTEXT_UNVERIFIED and LOCAL_REQUEST_FAILED. The failed slot remains failed and all remaining slots are written NOT_EXECUTED. Setup failure yields thirty NOT_EXECUTED slots and zero calls. A caught interruption marks the reserved slot as failed with unknown request reach, conservatively consumes its reservation, stops and preserves the remainder. No resume/replacement path exists. An uncatchable termination can leave a flushed slot-start with an unknown outcome and no final review export; the full schedule remains on disk and no automatic replay is authorized.

All files are new and exclusively created in fresh directories. Raw run evidence, label-masked review view and version mapping are separate files; no baseline generation/review file is updated. Review export preserves each available reply verbatim and the required selected context, omitting prompt labels/hashes, execution position, sample IDs, timing metadata and slot IDs from the reviewer view. Review order uses a separate hash domain and opaque IDs; version mapping stays separate. This is label-masked review, not fully blinded independent review: baseline replies were seen and wording can reveal conditions. All six new judgments remain pending, including slots with mechanical failures or no execution. No model/automatic instructional judge or acceptance computation exists.

Historical follow-up: the preceding OFFLINE-EVAL-005 text records the preparation-time authorization and plan. The schedule was later executed and its human review finalized; the separate run evidence and descriptive comparison are recorded in `docs/evals.md` under “Subsequent V1/V2 repeatability execution and review.” The preparation record and its approval scope remain unchanged.

### Isolated example-only prompt v3 preparation — OFFLINE-EVAL-006

Approval: current human example-based experiment preparation request; decisions.md OFFLINE-EVAL-006. Preserve v1 and v2 exactly. New `experiments/tutor_v1/prompt-v3.txt` branches directly from unchanged `prompt.txt` v1, adding only the approved three-line example immediately before the JSON-output instructions:

> Example: For x + 4 = 11, the student says, “7, because I added 4.”
> Appropriate response: “7 is the correct answer. Can you show me where you added 4?”
> Confirm the result without endorsing the conflicting explanation or assuming what the student actually did.

Existing isolated runner/local selectors accept explicit `--prompt-version v3`; omitted version remains v1 and fake remains the main runner default. This selectable variant does not authorize any execution or choose the eventual suite/repetitions. Evidence uses the existing selected-version/effective-prompt SHA-256 convention. Local v3 checks the unchanged baseline model digest before generation, just as v2 does. Preserve all other settings, context/overflow handling, output schema, no retries, timeout and isolation. Fixed diagnostic and repeatability protocols are unchanged; no application/backend/public API or student-facing behavior is implemented.

Research/proposal: `docs/research/tutor-prompt-v3-example.json`. V3 tests whether one concrete example may improve compliance with v1's existing result/explanation and conflict-investigation rules, not a newly established cause or proven fix. Datasets, rubric, existing prompts and historical evidence stay unchanged. Scoring/review/research data stay outside model input; the approved example alone is new input instruction. No model calls in this preparation task.
