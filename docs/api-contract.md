# AI Tutor API Contract

**Status:** Approved conceptual MVP v1 API contract; Step 4 decisions synchronized 2026-10-04.
**Scope:** Assigned coursework, coaching sessions/messages/retry, student progress, teacher escalation/POC feedback, and authoritative mastery.
**Version:** 0.1 (approved Step 4 synchronization)
**Approval:** Human synchronization request, recorded in `decisions.md` STEP4-001 through STEP4-006.

## 1. Contract Principles

This API contract defines the externally observable behavior of the MVP surfaces listed in §17. Physical implementation and explicitly deferred policy remain outside this approval.

The implementation must preserve these invariants:

1.  Student identity comes from authenticated server-side identity, not

    a client-supplied `student_id`.

2.  A student may act only on coaching sessions and messages they are

    authorized to access.

3.  Student input is durably persisted before retrieval or model

    processing begins.

4.  Duplicate send operations must not create duplicate student

    messages.

5.  External model/retrieval failures must not erase a committed student

    message.

6.  Model output is untrusted until it passes structural validation and

    application policy/authority checks.

7.  The model may propose approved tool actions; the backend decides

    whether they may execute.

8.  AI-generated mastery evidence is separate from authoritative mastery

    state.

9.  A tutor response must be durably persisted before it is returned to

    the student.

10. Public responses must not expose internal model/provider details,

    stack traces, another student's information, internal escalation

    identifiers, or other unnecessary implementation details.

------------------------------------------------------------------------

# 2. Create and Process Student Message

## Endpoint

`POST /api/v1/coaching/sessions/{session_id}/messages`

Creates and durably admits a student message in an existing session. After input/idempotency commit, return 201 with student_message_id and initial PENDING status. Tutor processing occurs asynchronously through the PostgreSQL-backed worker selected by STEP5-001-A1.

## Authentication

Required.

The authenticated user supplies student identity.

The request body must not accept `student_id`.

## Request Headers

### `Idempotency-Key`

Required for message creation.

The key identifies one logical send operation. Repeating the request

with the same valid key must not create a second student message.

Idempotency lookup/storage and student-message creation must be

transactionally consistent.

## Path Parameters

### `session_id`

Identifier of the coaching session receiving the message.

## Request Body

``` json
{
  "content": "I don't understand how to get x by itself."
}
```

### `content`

-   required;

-   string;

-   must not be empty after applicable normalization;

-   maximum length: **4,000 characters** by default;

-   limit is configurable.

## Request Processing Order

The application must perform the logical workflow below.

``` text
Receive request
    ↓
Validate request
    ↓
Authenticate user
    ↓
Load session
    ↓
Authorize user for session
    ↓
Resolve authorized idempotency replay (return existing current state without processing)
    ↓
For a new send, validate ACTIVE session and eligible coursework
    ↓
BEGIN TRANSACTION
    ↓
Allocate session sequence / advance counter under the session lock
    +
Persist student message as PENDING
    +
Persist unclaimed processing job
    +
Persist/associate idempotency record
    ↓
COMMIT
════════════════════════════════
Durable student-input boundary
    ↓
Return POST admission response

Separate worker path, after durable input commit:
Establish valid processing ownership and mark/start processing
    ↓
Constrained curriculum retrieval
    ↓
Build targeted tutoring context
    ↓
Select currently permitted tools
    ↓
Bounded tutor agent loop
    ↓
Validate model output
    ↓
Apply policy/authority/business checks
    ↓
Execute permitted tools when needed
    ↓
Produce final tutor response
    ↓
BEGIN TRANSACTION
    ↓
Persist tutor response
    +
Persist required resulting state/evidence
    ↓
Mark student message COMPLETED
    ↓
COMMIT
════════════════════════════════
Durable tutor-output boundary
    ↓
Expose committed state/output through authenticated GET polling
```

Stage 2 implementation keeps authorization locks, replay resolution, and all admission writes within the existing service-owned transaction. The diagram identifies the logically coupled write unit; sequence/job creation happens only for a new send. Replay makes no message/job/key/counter writes. Commit failure rolls the entire unit back.

## Student input, attempt, evidence, and response correlation

Every student input is a Message; only actual coursework problem-solving/reasoning is a StudentAttempt. “I do not understand the question” is not necessarily an attempt; “x = 4 because I subtracted 5” is an attempt. Each attempt is traceable to its source student message. Evidence remains attributable to its source interaction/message/attempt, append-only, and nonduplicated on retry/recovery. Contradictory evidence is preserved.

Student and tutor messages are separate persisted records. Use `student_message_id` and `tutor_message_id` for completed results; the tutor response is traceable to its input. Failed/incomplete operation responses identify `student_message_id` without inventing a tutor message.

Initial successful creation uses **201 Created**. An idempotent replay returns current operation state/existing result and must not claim another resource was created. Slice 1 approval below specifies 200 OK replay and the student_message_id/current-status response.

## Processing ownership and durable effects

Only one active processing run may own a student message. Concurrent attempts, automatic/explicit retries, and stale recovery must not produce competing tutor responses or duplicate durable actions, evidence, POCs, attempts, or escalations. If the same logical action already succeeded for the interaction, reuse/return the existing effect. This system-action idempotency is separate from user-operation idempotency. The separate PostgreSQL-backed worker is selected by STEP5-001-A1. SLICE2A-001 and schema.md §31.6 define ownership/recovery storage for this slice; no dedicated queue service is introduced.

## Step 5 recovery and lost-response guarantees

Only the currently valid processing owner may finalize this student message. After ownership transfer, the stale former owner must not finalize competing results. PROCESSING does not establish perpetual liveness. Recovery resumes/restarts from the last durable commit; uncommitted in-memory model output need not be reconstructed.

A failed turn may already have committed tool effects. Reuse those logical effects during retry/recovery; unsuccessful/uncommitted effects may be attempted again under approved rules. The worker deployment is selected; SLICE2A-001 defines lease, lock, token, work-discovery, and recovery mechanisms, with implementation staged.

A database commit can succeed while its HTTP response is lost. Same-key/same-payload replay returns current existing operation state/result, not an automatic duplicate-key error or another execution of completed work. Changed payload returns 409. Preserve §5's replay-before-new-send-state-check distinction, including CLOSED-session replay.

## Message Processing Lifecycle

A student message has the following processing states (SLICE2A-001 also adds CANCELLED):

``` text
PENDING
   ↓
PROCESSING
   ├──→ COMPLETED
   └──→ FAILED
```

### `PENDING`

The student message is durably stored but tutor processing has not

successfully begun/completed.

### `PROCESSING`

Tutor processing is in progress.

A `PROCESSING` record must not be assumed to represent a live worker

indefinitely. Implementations must support detection/recovery of stale

processing using time-based metadata such as `processing_started_at` and

a configurable stale threshold.

### `COMPLETED`

Tutor processing completed successfully and the tutor-visible

response/state required for the turn has been durably committed.

### `CANCELLED`

Trusted authorization or administrative/unknown-closure policy has stopped unfinished processing. Terminal, no response, no restart through replay. Input history remains durable.

### `FAILED`

Tutor processing did not complete successfully after applicable bounded

automatic recovery/retry behavior.

The original student message remains durable and may be eligible for

explicit retry.

## Retrieval Rules

Retrieval must be constrained by deterministic application context

before semantic relevance is considered.

The runtime should search:

1.  the current authorized curriculum context; and

2.  approved prerequisite learning objectives when relevant.

The model must not independently decide whether unrelated or

unauthorized curriculum is permitted.

Retrieval parameters such as `top_k`, similarity thresholds, chunking

strategy, embedding model, and reranking remain evaluation-driven

configuration unless separately approved.

## Context Construction

The model should receive a deliberately selected context, not an

unrestricted dump of student history.

Relevant context may include:

-   current student message;

-   current problem;

-   current learning objective;

-   approved prerequisites;

-   relevant recent attempts;

-   relevant mastery evidence / estimated progress;

-   relevant points of confusion;

-   retrieved approved curriculum chunks;

-   tutor instructions;

-   currently permitted tool definitions.

## Model Output Trust Boundary

Model output is untrusted.

Before application actions or student-visible output, the backend must

apply:

1.  structured/schema validation;

2.  policy and authority checks;

3.  business/state validation;

4.  execution of only approved actions.

A structurally valid model response is not automatically an authorized

action.

## Tool Authority

The model may request only tools exposed by the orchestrator for the

current state.

The model does not directly execute database writes, raw SQL, filesystem

operations, arbitrary network operations, or unrestricted application

code.

The backend validates tool name, arguments, trusted identity/context,

authority, and current state before execution.

Tool results must be returned to the tutor runtime when the result

affects the truthfulness or next decision of the tutor.

The tutor must not claim that an externally observable action succeeded

unless the application has evidence that it succeeded.

Example: if teacher escalation creation fails, the tutor must not tell

the student that the teacher was notified.

## Step 5 model/tool and final-response flow

Orchestrator → authorized RAG → Context Builder → model → structural validation → policy/authority validation → business/state validation.

For a validated requested tool: Orchestrator → ToolExecutor → application/service logic → repository/data access → PostgreSQL. ToolExecutor enforces argument, authority, authorization, state, and durable-action idempotency rules. Tool results return to the Orchestrator and model context before additional reasoning; the model must not assume success. Response-critical tool failure cannot yield a claim of success.

When a valid final response has no further required tool actions: services → repository → PostgreSQL, commit the tutor response and logically coupled evidence/state/completion atomically as appropriate, then FastAPI → controlled public HTTP response → Frontend → Student. If the student sees the response, its durable record already exists. The Orchestrator owns the loop and its approved maximum step limit.

Expose only authorized information the client needs. Do not expose unnecessary raw model output, confidence, internal POC data, tool calls/results, RAG chunks, provider details, traces, stack traces, internal errors, escalation IDs, or other internal state. This preserves authorized teacher evidence/detail views rather than making internal data public by default.

## Agent Loop Limits

Default configurable MVP limits:

-   maximum message length: **4,000 characters**;

-   maximum agent steps: **5**;

-   model timeout: **30 seconds per model call**;

-   automatic model retry: **1 retry after the initial attempt** for

    eligible transient failures.

Retries must be bounded.

Transient failures may be retried.

Deterministic failures such as request validation, authorization denial,

policy rejection, or invalid business state must not be blindly retried.

## Mastery and Progress Behavior

The tutor may create append-only `MasteryEvidence`.

Evidence may capture dimensions such as:

-   correctness;

-   independence;

-   explanation;

-   transfer.

A correct answer produced with substantial tutoring assistance is weak

evidence of independent understanding rather than strong mastery

evidence.

Estimated student progress must be based on multiple pieces of evidence

rather than directly assigning the model's confidence score as

mastery/progress.

The application-owned progress calculation may aggregate multiple

evidence records into an AI-estimated learning/progress state.

The AI must not directly create or modify authoritative `MasteryRecord`

state.

Official mastery remains controlled by an approved teacher/authorized

workflow.

## Successful Response

A completed student-facing result exposes only information required by the client. The example below describes committed completed output, not the initial POST admission response. The approved Slice 2a polling subsection defines the GET envelope; Stage 5 implements this read-only endpoint.

Example:

``` json
{
  "student_message_id": "MSG-100",
  "tutor_message_id": "MSG-101",
  "content": "What operation would undo adding 5?",
  "status": "COMPLETED"
}
```

The student API does not expose by default:

-   raw model output;

-   model/provider identifiers;

-   internal confidence values;

-   internal point-of-confusion representation;

-   internal tool calls;

-   internal mastery-evidence details;

-   escalation identifiers/status;

-   another student's information;

-   stack traces or infrastructure errors.

If a future student UI requires additional state, it must be added

deliberately as a student-safe public representation.

------------------------------------------------------------------------

## Slice 1 approved admission and replay details

Approval: decisions.md SLICE1-003. Slice 1 stops after committing student input as PENDING; it performs no AI work. New creation returns 201 Created; authorized replay returns 200 OK with student_message_id and current status. Initial response example:

```json
{"student_message_id": "00000000-0000-4000-8000-000000000001", "status": "PENDING"}
```

Preserve valid content exactly; reject whitespace-only content and extra identity fields. Idempotency-Key is required, 1–255 printable ASCII characters, no whitespace; missing/invalid keys return 422. The logical payload is content only, compared as its parsed string without trimming or serialization differences. Scope remains authenticated student + operation + key, not per-session. Same scope/content replays the original authorized message; different content returns 409. Retain keys for the demo lifetime.

Authenticate and authorize session/course access before replay; replay does not bypass access to the original message/session if the route names another session. Resolve authorized replay before new-send ACTIVE and specific assignment-eligibility gates. New sends require enrollment, explicit assignment eligibility, and consistent course/assignment/problem membership. Closed-session replay remains read-only. Existing API error semantics remain; a database dependency failure yields safe 503 without asserting that an unconfirmed write was saved. No new failure-processing or explicit retry endpoint is implemented.

These approvals resolve earlier replay-status, normalization, key validation/retention, and PENDING-response deferrals for this slice only.

## Asynchronous response polling — SLICE2A-001

Approved replacement for the earlier STEP5-001-A1 flat route (no alias):
`GET /api/v1/coaching/sessions/{session_id}/messages/{message_id}/status`.
Both IDs are UUIDs. No request body or Idempotency-Key. Design approved; Stage 5 implemented and verified for continued development, not deployment.

Authenticate and authorize the original student/session/course on every read. Require a student message in the route session. Apply existing non-disclosure, not the ACTIVE-only new-send gate. Read status and response from one consistent database snapshot. GET never admits work, retries, reopens sessions, or mutates learning state.

All successfully read states return HTTP 200 and Cache-Control: no-store. Exact response fields:

```json
{"student_message_id":"<UUID>","status":"PENDING","tutor_response":null,"error":null}
```

PROCESSING uses the same shape with status PROCESSING. COMPLETED sets tutor_response to {"tutor_message_id":"<UUID>","content":"<persisted student-safe response>"} and error=null. FAILED has tutor_response=null and error={"code":"tutor_processing_failed","message":"Your message was saved, but the tutor could not complete a response."}. CANCELLED has tutor_response=null and error={"code":"message_processing_cancelled","message":"Your message was saved, but processing has stopped."}. No retryable field, lease/token, provider internals, or raw failure details. Revoked read authorization yields the protected-resource denial, not a cancellation payload.

Errors use the existing error envelope: 401 authentication_required for invalid/missing credentials or disabled/missing account; 403 forbidden for legitimately discoverable forbidden actions; 404 not_found for missing/non-discoverable resources, mismatched session/message, or tutor-message ID; 422 validation_error for malformed UUIDs; 503 storage_unavailable/service_unavailable when GET cannot be served; 500 internal_error for unexpected invariant failure. GET unavailability text: "Status is temporarily unavailable. Please try again." Never instruct GET callers to resend POST. Stored FAILED is 200, not 503; background failure cannot change the already returned admission response.

Client polls after 2s, then 4s/8s capped with ±20% jitter while PENDING/PROCESSING. Stop on COMPLETED/FAILED/CANCELLED or 401/403/404/422. On network/503 failure use 2/4/8/16/30s capped and respect a longer Retry-After. Pause hidden pages; resume/reload through GET using saved session/message IDs. An unknown message ID after lost POST acknowledgement is recovered with same-key/content replay before GET polling. Never automatically turn FAILED into a new POST or explicit retry.

# 3. Error Contract

Errors should be specific enough to support the legitimate client's user

experience while avoiding disclosure of unauthorized or unnecessary

internal information.

## Request Validation Failure

**HTTP:** `422 Unprocessable Content`

No student message is created.

Example:

``` json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid data.",
    "details": [
      {
        "field": "content",
        "message": "Message cannot be empty."
      }
    ]
  }
}
```

## Authentication Failure

**HTTP:** `401 Unauthorized`

The request lacks valid authentication.

No student message is created.

## Authorization Failure

Apply §16 consistently to session/message creation, replay/retry, teacher details, and mastery access:

- **404 Not Found** if the caller may not discover whether the protected resource exists (including another student's session/message or a student outside the authorized teacher relationship).
- **403 Forbidden** if the resource is legitimately discoverable but the action is forbidden.

No new student message is created by a denied operation. Public errors must not disclose ownership; internal telemetry may retain the real denial reason.

## Session Not Found

**HTTP:** `404 Not Found`

The requested session cannot be resolved under the API's approved lookup

semantics.

## Session State Conflict

**HTTP:** `409 Conflict`

The request is otherwise valid, but the requested action is not

permitted in the session's current state.

Example:

``` json
{
  "error": {
    "code": "session_state_conflict",
    "message": "This coaching session is no longer accepting messages."
  }
}
```

## Tutor Dependency / Model Timeout

Failure examples below assume an authorized retry remains permitted. `retryable: true` must not be interpreted as permission to start retry in CLOSED; apply current authorization/session rules.

When a required service/dependency is unavailable and the backend cannot fulfill the current operation:

**HTTP:** `503 Service Unavailable`

This is not the response to a successfully resolved idempotent POST replay. If the backend can return the accepted message, return 200 with its current state, including FAILED; do not copy the original processing failure's HTTP status. See §5 and decisions.md SLICE1-004.

The student message remains stored and becomes `FAILED` if processing

cannot recover within the bounded retry policy.

Example:

``` json
{
  "student_message_id": "MSG-847",
  "status": "FAILED",
  "retryable": true,
  "error": {
    "code": "tutor_temporarily_unavailable",
    "message": "Your message was saved, but the tutor couldn't respond right now. Please try again."
  }
}
```

Provider/model names and low-level timeout details remain internal.

## Invalid Model Output

Invalid structured model output is an internal model/runtime failure.

The student should not receive implementation language such as "the AI

generated an invalid schema."

If bounded runtime recovery fails, return a student-safe processing

failure while preserving the committed student message.

Example:

``` json
{
  "student_message_id": "MSG-847",
  "status": "FAILED",
  "retryable": true,
  "error": {
    "code": "tutor_processing_failed",
    "message": "Your message was saved, but the tutor couldn't complete a response. Please try again."
  }
}
```

Internally, this failure must remain distinguishable from model timeout,

retrieval failure, tool failure, policy rejection, and other failure

classes for observability and evaluation.

## Tool Failure

Tool failures are classified by their effect on correctness and

truthfulness.

### Recoverable / ancillary failure

If a failed internal operation does not make the tutor's response false

or unsafe, the implementation may complete the student-facing turn while

recording/recovering the internal failure according to approved runtime

behavior.

### Response-critical failure

If the failed tool is required for the tutor response to remain truthful

or consistent, the tutor must not return a response that claims the

action succeeded.

Example: a failed teacher-escalation write means the tutor cannot state

that a teacher was successfully notified.

------------------------------------------------------------------------

# 4. Retry Existing Failed Message

## Endpoint

`POST /api/v1/coaching/messages/{message_id}/retry`

Retries tutor processing for an already-persisted failed student

message.

It does **not** create a new student message.

## Authentication

Required.

## Authorization

The authenticated student must be authorized to act on the referenced

message/session.

Authorization must be based on trusted server-side

ownership/relationship data.

## Eligibility

The referenced message must:

-   exist under approved lookup semantics;

-   represent a student message;

-   be accessible to the authenticated student;

-   be in `FAILED` and eligible for explicit retry under the current session/authorization rules.

Attempting to retry a successfully completed/non-retryable message

returns an appropriate state conflict rather than creating duplicate

processing.

## Retry and closure

SLICE2A-001: future explicit retry is restricted to known transient model-provider or infrastructure failures, subject to current authorization, ACTIVE session, retry budgets, and rate limits. Invalid model output, authorization failures, policy violations, invalid requests, and unknown failures are not explicitly retryable. No student-facing explicit retry endpoint is implemented in Slice 2a; retry_generation is preserved for future work.

Explicit retry validates eligibility on the existing FAILED student message, transitions it to PROCESSING under valid ownership, and never creates a new message or silently reopens a closed session. If its session is CLOSED, no new retry may begin. A same-key send replay returning FAILED is not an explicit retry and never starts processing.

## Processing

``` text
Load existing message
    ↓
Authenticate / authorize
    ↓
Validate retry eligibility
    ↓
PROCESS SAME MESSAGE
    ↓
Retrieval / context / model / tools
    ↓
Persist successful tutor result
    ↓
COMPLETED
```

The retry endpoint must not call the normal "create new student message"

operation.

------------------------------------------------------------------------

# 5. Idempotency Semantics

Scope: **authenticated student + operation + idempotency key**. A new logical message send gets a new key. Retry/replay of the same logical send reuses that key.

| Existing operation, same key and same payload | Replay outcome |
| --- | --- |
| PENDING | 200 OK; return current PENDING state |
| PROCESSING | 200 OK; return current PROCESSING state |
| COMPLETED | 200 OK; return existing completed result |
| FAILED | 200 OK; return current FAILED state and the same student_message_id; do not reprocess |

Same key with a different payload returns **409 Conflict**, preserves the original message unchanged, and creates no second message. For Slice 1, compare the parsed content string exactly, without trimming; session ID and serialization are not part of the logical payload.

Approval: decisions.md SLICE1-004. A successful authorized same-key/same-payload POST replay always returns **200 OK**, including when stored processing status is FAILED. Return the previously accepted message; do not create another message, schedule another job, reset processing status, or start another processing attempt. A new intentional student message uses a new key. Internal worker retries do not use a new client idempotency key. A stored FAILED state does not make a successful replay unavailable. Use **503 Service Unavailable** only when a genuine service/dependency outage prevents the backend from fulfilling the current request.

Replay asks “what happened to my operation?” Explicit retry asks “process my FAILED message again.” These are separate operations. Authentication and protected-resource authorization apply to both.

A legitimately submitted operation may be replayed after ACTIVE → CLOSED to retrieve its current state/result, without starting work. Resolve valid replay before applying the ACTIVE-only rule for new sends. Replay must not report a second creation; initial successful creation alone uses 201 Created. Slice 1 retains keys for the controlled-demo lifetime and returns 200 for replay; unrelated remaining wire details stay deferred.

# 6. Transaction Boundaries

External model/retrieval calls must not be kept inside the database

transaction that establishes durable student input.

Required conceptual sequence:

``` text
TRANSACTION A
Allocate session sequence / advance counter under the session lock
Create student message
Create unclaimed processing job
Create/associate idempotency record
COMMIT
External retrieval/model/tool processing
TRANSACTION B
Persist tutor response
Persist logically coupled resulting state/evidence
Mark processing completed
COMMIT
Return response
```

Operations that must succeed/fail together should be atomic.

Exact transaction composition for evidence, progress updates, escalation

creation, and other tool side effects must preserve the relevant

business invariants and truthfulness guarantees.

------------------------------------------------------------------------

## Terminal failure and action guarantees

After terminal processing failure, preserve the committed student message and mark it FAILED. A genuine dependency outage that prevents fulfillment of the current HTTP request returns student-safe **503 Service Unavailable**. Successfully reading an accepted message for idempotent POST replay returns **200 OK**, even when its stored state is FAILED; the earlier processing failure does not change the replay HTTP status. Keep specific internal failure categories separate from public errors; never expose provider errors, raw model output, internal prompts, or stack traces. Exact mapping for other failure categories remains a downstream contract decision.

The durable student-input transaction and tutor-result transaction are distinct. Logically coupled result/state/evidence and COMPLETED status commit before output is returned. Already successful logical tool effects are reused if later processing/commit fails; retries must not duplicate those effects. SLICE2A-001 selects the physical processing concurrency design; durable tool-action mechanisms remain separate.

## Step 7 dependency failure behavior

Approval: decisions.md STEP7-001. Required curriculum retrieval failure, including inability to obtain authorized curriculum because of system failure, must not be replaced with unsupported general-model output presented as grounded. Fail or degrade only within the operation's approved requirements. This does not require retrieval for unrelated operations. Genuine dependency unavailability preventing fulfillment of the current request retains safe 503 behavior. SLICE1-004 clarifies that successful idempotent POST replay of stored FAILED is 200 and performs no processing; no fallback response is selected.

A successful model/provider HTTP request does not establish successful tutoring. Reject structurally invalid, policy/authority-invalid, disallowed-action, or business/state-invalid output; do not execute disallowed actions. Treat processing as failed under the existing runtime/error policy, retain the corresponding internal category, and expose only safe public failure. Do not broaden automatic retry eligibility for deterministic validation failures.

On database failure before commit, roll back logically coupled writes and do not treat them as durable. In particular, withhold a final response if its required commit fails. Do not claim that input was saved or FAILED metadata persisted unless the relevant commit succeeded. Recovery uses the last durable state, with Step 5 stale-owner rejection and action deduplication intact. Lost HTTP delivery after a successful commit remains replay, not evidence of rollback.

Tool outcomes return to the Orchestrator and must be verified before claims of success. Preserve response-critical versus ancillary failure behavior in §3. Across retrieval, model, database, and tools, do not present required operations as successful unless they actually succeeded. Exact unresolved non-dependency failure mappings remain deferred.

Steps 6–7 add no endpoint, pagination parameters, or response shape. Step 6 scaling options remain conditional architecture choices. Detailed failure monitoring belongs primarily to Step 10, detailed evaluation coverage to Step 9, and security-specific failure handling to security.md / Step 8; §7's existing internal categories remain required.

# 7. Observability Requirements

Internal telemetry should distinguish at least:

-   request validation failure;

-   authentication failure;

-   authorization failure;

-   session-state conflict;

-   retrieval failure;

-   model timeout;

-   model/provider transport failure;

-   model structured-output validation failure;

-   policy/authority rejection;

-   tool validation failure;

-   tool execution failure;

-   database/transaction failure;

-   stale processing recovery;

-   agent step-limit exhaustion;

-   successful completion.

Public errors remain stable and student-safe even when internal failure

classification is more detailed.

------------------------------------------------------------------------

## Step 10 correlation and telemetry boundary

Approval: decisions.md STEP10-001. Support internal interaction trace/correlation across API/backend, database, retrieval, Context Builder, orchestration, model/tools, validation, durable commit, and response. Use architecture.md §25.1 for spans, operational metrics, versioning, and actionable-alert candidates. Production logs default to metadata under security.md; existing precise internal failure categories remain distinct from safe public errors.

No new public trace header, response field, endpoint, authorization capability, or error mapping is approved here. Correlation IDs do not replace authenticated-student-scoped idempotency or valid processing ownership. Exact public correlation representation, if needed, requires a later contract decision.

# 8. Guardrail Boundary

This API contract relies on the approved runtime/security guarantees in
`ai-runtime.md` and `security.md`; explicitly deferred details remain unresolved.

At minimum:

-   retrieved curriculum must be authorized and approved;

-   model output is untrusted;

-   tool access is allow-listed and state-dependent;

-   tool arguments are validated;

-   trusted student/session identity is derived server-side;

-   the model cannot change official mastery;

-   the model cannot bypass authorization;

-   the model cannot execute raw SQL or arbitrary code;

-   student-visible responses must not claim failed actions succeeded;

-   prompt/model behavior must not override deterministic backend

    authority.

------------------------------------------------------------------------

# 9. Evaluation Boundary

The deterministic guarantees and AI behavioral quality of these API surfaces are specified for verification in `evals.md`. Numeric release thresholds remain deferred.

Evaluation should eventually measure, among other things:

-   point-of-confusion identification quality;

-   curriculum grounding/retrieval quality;

-   hallucination/unsupported-answer rate;

-   scaffolding quality;

-   tendency to give answers too early;

-   correct tool selection;

-   correct escalation behavior;

-   mastery-evidence quality;

-   progress-estimation quality/calibration;

-   structured-output validity;

-   policy/authority compliance;

-   retry/failure recovery;

-   latency and cost;

-   regression against previously passing tutoring scenarios.

Exact release thresholds remain evaluation-driven decisions rather than

API semantics.

------------------------------------------------------------------------

## Step 9 diagnosis and evaluation alignment

Approval: decisions.md STEP9-001 and STEP9-002. Follow evals.md for risk-driven tests/evals, baseline/regression comparisons, and unresolved numeric thresholds. SPECIFIC_POC, NO_POC, and INSUFFICIENT_EVIDENCE are valid conceptual diagnosis outcomes; insufficient evidence is not automatically a processing error, failed message, or teacher escalation.

Bounded diagnosis may stop with recorded insufficient/unknown evidence and incomplete work visible to authorized teachers through normal work/student status. Preserve multiple supported POCs and target a justified blocker using encoded prerequisites. Exact outcome/status visibility wire representation remains unresolved before dependent implementation. This approval does not add a public payload, endpoint, session state, mastery state, or automatic session closure; existing API and failure behavior remain intact.

# 10. Assigned Coursework Discovery

The MVP tutoring entry point is **assigned coursework**.

The MVP does not initially expose unrestricted browsing of all Grade 7
objectives as a primary tutoring entry point.

Conceptual supporting endpoints include:

- `GET /api/v1/students/me/courses`
- `GET /api/v1/students/me/assignments`

Additional assignment/problem read shapes may be added as required by the
frontend without changing the approved authority model.

Conceptual student flow:

```text
Student
  ↓
Assigned course
  ↓
Current assignment
  ↓
Problem
  ↓
Get Help
  ↓
Create/resume coaching session
```

The selected course, assignment, problem, and associated learning objectives
provide deterministic application context for tutoring and curriculum
retrieval.

The LLM must not invent the student's assigned coursework.

------------------------------------------------------------------------

# 11. Coaching Sessions

## 11.1 Create Coaching Session

### Endpoint

`POST /api/v1/coaching/sessions`

Creates a tutoring session tied to authorized assigned coursework.

Conceptual request:

```json
{
  "assignment_id": "ASSIGN-42",
  "problem_id": "PROBLEM-7"
}
```

The request must not use a client-supplied `student_id` as authority.
Student identity is derived from authentication.

Before creation, the backend must validate at least:

1. the authenticated student;
2. student enrollment/access to the relevant course;
3. assignment/course consistency;
4. problem/assignment consistency;
5. specific assignment/release eligibility, independently of enrollment;
6. applicable session/business-state rules.

### Create/resume entry flow

Student → Frontend → FastAPI → authenticate → authorize → validate specific assignment eligibility → validate problem/assignment relationship → check for an appropriate existing ACTIVE session. If none exists, create a new ACTIVE session. For a resumable ACTIVE session in the same context, use the choice below; no expiration duration is inferred.

### Existing Resumable Session

If a resumable active coaching session already exists for the same approved
coursework context, the product should offer the student a choice:

- **Resume existing session**
- **Start new session**

If the student chooses **Start new**:

1. atomically close the old ACTIVE session and create a new ACTIVE session;
2. preserve all previous history;
3. if either operation fails, neither takes effect and the old session remains ACTIVE.

The physical transaction implementation is not selected here.

The old session must not be deleted merely because the student starts a new
one.

If an older session is no longer resumable under the approved lifecycle
policy, a new session may be created.

### Session continuity — STEP5-001-A1

Completed learning sessions remain CLOSED to new messages. Continue through a new eligible session, with selected authorized prior context. Message COMPLETED alone does not close a session. Previously admitted PENDING/PROCESSING work may finish after NORMAL closure with current authorization; SLICE2A-001 cancels unfinished work for administrative/unknown closure; authorized historical GET and POST replay remain read-only. No CLOSED-session retry is added.

### Session Lifetime

A tutoring/coaching session is persisted application state. It is not a
continuously running process.

Authentication-token/session expiration and coaching-session
resumability/expiration are separate concerns.

The exact coaching-session resumability/expiration duration remains an
explicit later lifecycle/security decision and must not be silently invented
during implementation.

### Coursework eligibility

Course enrollment alone does not assign every course assignment. The backend must establish specific assigned/released coursework eligibility in addition to enrollment and assignment/problem/course consistency. Slice 1 uses explicit student-assignment eligibility; class/group allocation remains deferred.

## 11.2 Get Coaching Session

### Endpoint

`GET /api/v1/coaching/sessions/{session_id}`

Returns a student-safe representation of a coaching session the authenticated
student is authorized to discover.

For another student's protected session, public behavior must avoid confirming
that the resource exists or revealing ownership.

Where the resource is outside the caller's authorized discoverable scope, use
non-disclosing lookup semantics such as:

`404 Not Found`

Internal telemetry may still classify the event accurately as an authorization
denial.

This does not require every authorization failure in the entire API to become
404; it applies where existence itself is protected information.

## 11.3 End Coaching Session

### Endpoint

`PATCH /api/v1/coaching/sessions/{session_id}`

A student may request to end their own active coaching session.

The client does not receive authority to assign arbitrary session states.

The backend must:

1. authenticate the student;
2. authorize access/ownership;
3. validate the current session state;
4. apply only an approved transition.

Approved MVP student-requested transition:

```text
ACTIVE → CLOSED
```

Normal student-requested closure does not require teacher approval.

Session history remains preserved.

The authority model is:

```text
Student requests
      ↓
Deterministic backend validates/permits
      ↓
State transition occurs
```

Teacher intervention is reserved for workflows where human judgment or
authority adds value rather than ordinary session closure.

------------------------------------------------------------------------

### Closure and existing operations

CLOSED prevents new tutoring work. A new message returns **409 Conflict**; a FAILED message cannot begin a new explicit retry. Under SLICE2A-001, work already admitted as PENDING/PROCESSING may finish only for NORMAL closure with current authorization. ADMINISTRATIVE/UNKNOWN closure cancels unfinished work; absent/unrecognized reasons fail closed. Authorized same-key replay remains permitted but never initiates processing. ACTIVE → CLOSED requires no teacher approval and preserves history. Authentication lifetime is separate from coaching-session resumability; no duration is selected.

# 12. Student Progress

## Endpoint

`GET /api/v1/students/me/progress`

Returns a student-safe representation of AI-estimated learning progress.

Student-facing estimated progress is distinct from authoritative mastery.

## Progress flow

Student interaction → model assessment → validated MasteryEvidence → ProgressService → accumulated progress interpretation. ProgressService applies the consistent product rubric; multiple evidence points should support substantial changes. Confidence alone is not progress. BUILDING / DEVELOPING / STRONG are the existing vocabulary, not approval of a one-way-only transition policy. Official MasteryRecord remains the human-authorized recognition described in §14.

## Internal Evidence Dimensions

Progress calculation may use evidence dimensions including:

- correctness;
- independence;
- explanation;
- transfer.

These dimensions are useful internally for evidence aggregation, tutor
adaptation, teacher views, and evaluation.

The student UI does not need to expose these terms directly.

## Student-Facing Progress States

The MVP uses understandable product-defined states:

- `BUILDING`
- `DEVELOPING`
- `STRONG`

The API should pair the overall state with student-friendly learning targets
derived from approved curriculum/objectives.

Conceptual response:

```json
{
  "learning_objective": "Solve two-step equations",
  "progress": "DEVELOPING",
  "demonstrated": [
    "I can solve a two-step equation with some help.",
    "I can explain why I use opposite operations."
  ],
  "next_targets": [
    "I can solve a two-step equation without hints.",
    "I can use this strategy on a new kind of problem."
  ]
}
```

The MVP should avoid unsupported false precision such as presenting a student
as "73% mastered" when that precision has not been validated.

## Learning-Target Authority

The LLM does not invent official learning targets or mastery criteria.

Targets originate from approved curriculum/teacher-defined objectives under product-owned definitions and later may
be teacher-configurable if that feature is deliberately added.

For the MVP, the product owns a consistent
`BUILDING / DEVELOPING / STRONG` rubric so system behavior can be evaluated
against stable criteria.

The evidence/progress system determines what has been demonstrated. The
student-facing layer translates that evidence into understandable language.

------------------------------------------------------------------------

# 13. Teacher Escalations

## Escalation Lifecycle

Approved MVP lifecycle:

```text
OPEN → IN_REVIEW → RESOLVED
```

## Teacher review flow

Teacher → Frontend → FastAPI → authenticate → authorize teacher/student/course relationships → escalation application/service → repository → PostgreSQL. Queue summaries remain concise and evidence-supported; authorized detail can provide supporting history. Suggested teacher focus remains advisory.

Teacher-facing Yes / Partly / No corresponds respectively to CORRECT / PARTLY_CORRECT / INCORRECT. Preserve the original AI prediction and store the attributed teacher determination separately, linked to the reviewed prediction. This separation supports later POC evaluation.

## 13.1 Teacher Escalation Queue

### Endpoint

`GET /api/v1/teacher/escalations`

Returns escalations only for students/courses the authenticated teacher is
authorized to access.

The queue is a triage surface and should not dump all raw tutoring history.

Useful queue/detail summary information may include:

- why the teacher is seeing the escalation;
- relevant learning objective;
- what the student has demonstrated;
- where the student appears to be stuck;
- relevant interventions already attempted;
- an AI-suggested teacher focus.

## 13.2 Escalation Detail

### Endpoint

`GET /api/v1/teacher/escalations/{escalation_id}`

Returns deeper supporting evidence for an authorized teacher.

The detail view may expose relevant attempts, POC history, tutoring evidence,
and other approved context needed for human judgment without granting
unrestricted access to unrelated student data.

## AI-Suggested Teacher Focus

The LLM may synthesize available evidence into a suggested teacher focus.

Example:

```text
Check whether the student understands division with negative integers.
```

This is an **AI recommendation**, not an authoritative diagnosis.

The recommendation should be accompanied by enough supporting evidence for the
teacher to evaluate it.

The teacher retains human judgment and decision authority.

## 13.3 Update / Resolve Escalation

### Endpoint

`PATCH /api/v1/teacher/escalations/{escalation_id}`

Supports approved lifecycle transitions and low-friction teacher feedback.

When resolving an escalation, the primary feedback question should capture
whether the suggested POC was accurate:

- `CORRECT`
- `PARTLY_CORRECT`
- `INCORRECT`

If `CORRECT`, the teacher should be able to resolve without completing an
unnecessary additional form.

If `PARTLY_CORRECT` or `INCORRECT`, the product may reveal a lightweight
follow-up such as:

- different point of confusion;
- student understood after more practice;
- student needed prerequisite support;
- not enough information;
- other, with optional short text.

The product principle is:

> Ask for the minimum useful feedback first; request more detail only when the
> signal indicates that correction information is valuable.

## POC Historical Integrity

The original AI POC prediction/recommendation must be preserved.

If the teacher disagrees, the teacher's determination is stored separately
rather than rewriting the AI's historical prediction. Preserve attribution and the relationship to the particular prediction reviewed.

Conceptually:

```text
AI predicted POC
      +
Teacher confirmed/corrected POC
      ↓
Preserved evaluation history
```

This history may later support POC evaluation, failure analysis, and
improvement.

Teacher feedback must not automatically trigger foundation-model retraining.

------------------------------------------------------------------------

# 14. Teacher Mastery

## 14.1 Read Student Mastery

### Endpoint

`GET /api/v1/teacher/students/{student_id}/mastery`

Authorized teachers may view relevant mastery information for students within
their approved course/student relationship.

The view may include:

- AI-estimated progress;
- supporting mastery evidence;
- current authoritative mastery status;
- relevant authoritative mastery history.

## 14.2 Update Authoritative Mastery

### Endpoint

`PATCH /api/v1/teacher/students/{student_id}/mastery/{objective_id}`

Before applying a mastery decision, the backend must validate at least:

1. authentication;
2. teacher role/authority;
3. approved teacher-course relationship;
4. student/course relationship;
5. learning-objective/course consistency;
6. permitted authoritative state transition.

## Mastery Authority

`MasteryEvidence` and authoritative mastery are different concepts.

The AI may:

- observe;
- assess;
- create evidence through approved workflows;
- estimate progress;
- recommend.

The AI may not directly establish or overwrite official mastery.

An authorized teacher/workflow owns authoritative mastery decisions.

If AI-estimated progress is `BUILDING`, but an authorized teacher has valid
evidence from outside the AI tutor that the student demonstrated mastery, the
teacher may establish authoritative mastery.

The AI does not veto the authorized human decision.

The underlying AI evidence is not rewritten to agree with the teacher.

This preserves both:

```text
What the AI observed
        and
What the authorized teacher decided
```

## Authoritative Mastery History

Authoritative mastery changes must preserve previous decision/state, new decision/state, actor/authority, timestamp, and relevant provenance. Efficient current-state reads must coexist with every authoritative change remaining historically traceable. No physical history-table/versioning design is selected.

Example:

```text
Oct 4  → MASTERED
Oct 18 → new evidence / misconception discovered
Oct 18 → NEEDS_REVIEW (if this becomes an approved state)
```

The later decision must not erase the earlier decision as though it never
occurred.

The exact authoritative mastery state vocabulary and allowed transition graph
remain subject to final schema/state-machine alignment before affected
implementation.

------------------------------------------------------------------------

# 15. Personalization and Student Learning State

MVP personalization does **not** require continuously retraining the foundation
model on student records.

The student's learning model may evolve as the application accumulates
authorized evidence such as:

- attempts;
- points of confusion;
- mastery evidence;
- teacher POC feedback/corrections;
- authoritative mastery changes;
- relevant interaction history.

The context builder selects the minimum relevant authorized information for
the current tutoring decision.

Conceptually:

```text
Student evidence / learning state
              ↓
Relevant authorized context selected
              ↓
Foundation model
              ↓
Personalized tutoring response
```

The foundation model may remain the same while the student's context changes.

The LLM must not receive unrestricted access to the student's entire record
merely because more history exists.

Future use of aggregated student interaction data for fine-tuning or model
training is a separate product, privacy, consent, governance, and evaluation
decision, especially for minors. It is not part of this MVP API contract.

------------------------------------------------------------------------

# 16. Cross-Endpoint Authorization and Non-Disclosure

Authorization must be based on trusted server-side relationships rather than
client claims.

Relevant relationships include:

- student identity;
- enrollment;
- session ownership/access;
- teacher-course assignment;
- student-course enrollment;
- objective/course membership.

For protected resource lookup, return **404 Not Found** when the caller must not discover existence. Return **403 Forbidden** when the resource is legitimately discoverable but the requested action is forbidden. This applies across protected session/message, teacher, and mastery operations. Authorization is required for replay as well as new actions.

Internal observability may retain a more precise failure reason than the
public response.

This principle should be applied deliberately rather than mechanically: a
legitimate client should still receive useful `403`, `404`, or `409` behavior
where doing so does not create an information-disclosure problem.

------------------------------------------------------------------------

## Step 8 trusted identity and security enforcement

Approval: decisions.md STEP8-001 and STEP8-002; security.md defines the guarantees. Derive authenticated actor identity server-side, preferably without client-supplied security-sensitive identity fields. Client resource IDs are access targets, not proof of caller identity or permission. Enforce approved relationships and assignment eligibility on the backend, regardless of frontend restrictions or model instructions.

Prompt-injected user/model text and forged tool identities cannot authorize actions, change session permissions, or modify official mastery. Unauthorized operations create no requested durable effects; rejected tools cannot yield success claims. Retry/recovery must enforce authorization; student-scoped idempotency must not permit cross-user replay, and stale owners cannot authorize finalization. Preserve §16's 404/403 distinction and all Step 5–7 failure guarantees.

Public output exposes only authorized information needed by the client, without unnecessary internal student/model/teacher/RAG/tool/provider details or unrelated records. Secrets do not belong in public responses or model prompts. Internal security diagnosis remains privacy-scoped. No endpoint, payload shape, authentication provider, new status mapping, or compliance policy is selected by Step 8.

# 17. API Surface Summary

The approved conceptual MVP API surface now includes at least:

## Student / Coursework

- `GET /api/v1/students/me/courses`
- `GET /api/v1/students/me/assignments`
- supporting assignment/problem reads as required by the frontend

## Coaching

- `POST /api/v1/coaching/sessions`
- `GET /api/v1/coaching/sessions/{session_id}`
- `PATCH /api/v1/coaching/sessions/{session_id}`
- `POST /api/v1/coaching/sessions/{session_id}/messages`
- `GET /api/v1/coaching/sessions/{session_id}/messages/{message_id}/status` — status/result polling; approved by SLICE2A-001; implemented in Stage 5
- `POST /api/v1/coaching/messages/{message_id}/retry`

## Student Progress

- `GET /api/v1/students/me/progress`

## Teacher Escalations

- `GET /api/v1/teacher/escalations`
- `GET /api/v1/teacher/escalations/{escalation_id}`
- `PATCH /api/v1/teacher/escalations/{escalation_id}`

## Teacher Mastery

- `GET /api/v1/teacher/students/{student_id}/mastery`
- `PATCH /api/v1/teacher/students/{student_id}/mastery/{objective_id}`

Repeated CRUD/read shapes may reuse the validation, authentication,
authorization, state, error, and transaction patterns already established in
this contract without requiring the same depth of design discussion unless
they introduce a materially new boundary or authority model.

------------------------------------------------------------------------

# 18. Explicitly Deferred / Decision Required

The following must not be silently invented during implementation:

1. exact coaching-session resumability/expiration duration and policy;
2. exact authoritative mastery state vocabulary and transition graph;
3. final pagination/filter/sort parameters for teacher queues and coursework
   lists;
4. final assignment/problem discovery response shapes required by the
   frontend;
5. accessibility-specific API representation requirements;
6. age-specific behavior (including demonstration), broader privacy/consent/training policy, and production requirements for minors;
7. future teacher customization of progress/mastery rubrics;
8. open-topic/practice tutoring outside assigned coursework;
9. any future use of student interaction data for model
   training/fine-tuning;
10. exact retrieval configuration such as embedding model, `top_k`,
    similarity thresholds, reranking, and chunking where not separately
    approved.

These items should be resolved in the appropriate later design step or
classified as `DECISION_REQUIRED` before implementation that depends on them.

------------------------------------------------------------------------

Additional deferred implementation details beyond approved SLICE2A-001: durable tool-action idempotency storage; physical mastery-history/teacher-feedback representation; class/group allocation; production idempotency expiration; remaining endpoint wire mappings beyond approved Slice 2a polling; message-to-attempt classification mechanics; future explicit-retry budgets/rate limits. These do not permit changing approved conceptual outcomes.

# 19. Step 4 API Contract Status

The API design now covers the major MVP surfaces and authority boundaries:

- assigned coursework discovery;
- coaching-session lifecycle;
- core coaching-message processing;
- failed-message retry;
- student progress;
- teacher escalation/review;
- teacher POC feedback;
- authoritative mastery read/update;
- history-preservation requirements;
- cross-endpoint authorization/non-disclosure.

This document remains a conceptual contract until the cross-document contract
review confirms consistency with:

- `requirements.md`;
- `schema.md`;
- `architecture.md`;
- `ai-runtime.md`;
- `security.md`;
- `evals.md`;
- `decisions.md`.

Any conflict found by that review must be classified rather than silently
resolved:

- `MATCH`
- `IMPLEMENTATION_BUG`
- `DOCUMENTATION_DRIFT`
- `DECISION_REQUIRED`

Step 4 should be marked complete after that consistency review identifies no
unresolved blocking contract conflict.


## Step 4 synchronization review — 2026-10-04

- MATCH: Approved decisions 1–25 from the human synchronization request are reflected across requirements, architecture, schema, API, runtime, security, evals, and decisions; AGENTS.md authority and approval boundaries are preserved.
- DECISION_REQUIRED: Explicitly deferred policy, physical design, and remaining wire details in §18 and domain documents remain unresolved. They block dependent implementation, not completion of this conceptual synchronization.
- No remaining DOCUMENTATION_DRIFT or IMPLEMENTATION_BUG finding was identified within this documentation review. Implementation was not exercised.
- Validation: all eight documents reviewed; JSON examples parsed, fences/reference targets checked, endpoint inventory preserved, and AGENTS.md unchanged. No application tests or AI evals ran because this was documentation-only work.

STEP 4 VERDICT: READY
