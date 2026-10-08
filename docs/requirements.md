# AI Tutor --- MVP Requirements

**Status:** Approved\
**Version:** MVP v1\
**Initial Domain:** Grade 7 Mathematics

------------------------------------------------------------------------

## 1. Purpose

The AI Tutor provides students with immediate, curriculum-grounded
instructional support when they are confused or stuck.

The system should help students reason toward understanding rather than
simply completing academic work for them.

The tutor must use available student context and approved curriculum to:

1.  understand what the student is working on,
2.  identify or clarify the student's point of confusion,
3.  provide appropriate instructional scaffolding,
4.  evaluate student attempts,
5.  adapt support based on evidence,
6.  verify understanding,
7.  escalate to a teacher when appropriate.

The primary product outcome is **demonstrated student understanding**,
not merely production of a correct answer.

------------------------------------------------------------------------

## 2. Initial Domain

MVP v1 will initially target **Grade 7 Mathematics**.

Grade 7 Mathematics is the initial implementation and evaluation domain
for:

-   curriculum grounding,
-   learning objectives,
-   points of confusion,
-   diagnostic questioning,
-   instructional scaffolding,
-   student attempts,
-   transfer questions,
-   mastery evidence,
-   teacher escalation.

The architecture should avoid unnecessary coupling to Grade 7
Mathematics so that additional grade levels and subjects can be
supported later.

However, generalized multi-subject functionality is **not** an MVP
requirement.

Do not introduce abstractions solely for hypothetical future subjects
unless a current requirement justifies them.

------------------------------------------------------------------------

## 3. Primary Users

### Student

The student interacts with the AI Tutor for instructional support.

Students may:

-   ask questions,
-   describe confusion,
-   submit reasoning or attempts,
-   respond to diagnostic questions,
-   explain concepts in their own words.

### Teacher

The teacher remains the human instructional authority.

Teachers may eventually review:

-   student attempts,
-   tutoring sessions,
-   points of confusion,
-   mastery evidence,
-   escalations.

Teacher-facing functionality beyond the minimum escalation/review
workflow is not required for the initial MVP.

------------------------------------------------------------------------

## 4. Core Tutoring Flow

The conceptual tutoring loop is:

``` text
Student request
    ↓
Assess available context
    ↓
Identify or clarify Point of Confusion
    ↓
Choose scaffold
    ↓
Student attempts/reasons
    ↓
Evaluate evidence
    ↓
Adapt support
    ↓
Verify understanding
    ↓
Complete OR continue OR escalate
```

The system must not assume that a student's initial statement accurately
identifies the underlying point of confusion.

------------------------------------------------------------------------

## 5. Point of Confusion

A **Point of Confusion (POC)** represents the concept, prerequisite,
reasoning step, misconception, or knowledge gap preventing the student
from progressing.

The tutor should attempt to identify the POC using evidence from:

-   the student's current message,
-   student attempts,
-   current assignment/problem context,
-   relevant learning objectives,
-   available mastery history,
-   approved curriculum,
-   previous interactions within the active coaching session.

If available evidence is insufficient or ambiguous, the tutor should ask
a targeted diagnostic question rather than confidently inventing a POC.

------------------------------------------------------------------------

## 6. Socratic / Scaffold-First Instruction

The tutor should prefer helping the student reason toward an answer
rather than immediately providing the final answer.

The tutor should:

-   ask targeted questions,
-   activate relevant prior knowledge,
-   break problems into manageable reasoning steps,
-   provide hints when appropriate,
-   ask the student to attempt the next step,
-   adapt scaffolding based on the student's response.

Core principle:

> Do not explain what the student may reasonably be capable of
> discovering through appropriate scaffolding.

This principle is pedagogical guidance, not an absolute prohibition
against direct explanation.

Direct explanation may become appropriate when continued scaffolding is
no longer productive or when explanation is required to correct a
misconception.

------------------------------------------------------------------------

## 7. Answer Leakage

The system should avoid unnecessary **answer leakage**.

Answer leakage occurs when the tutor reveals information the student is
expected to reason through before sufficient instructional scaffolding
has occurred.

A response may be factually correct and curriculum-grounded while still
being pedagogically poor because it gives away too much.

The tutor should distinguish between:

-   useful instructional support,
-   necessary explanation,
-   hints/scaffolding,
-   inappropriate answer disclosure.

------------------------------------------------------------------------

## 8. Verification of Understanding

The system must not treat statements such as:

> "I understand."

as sufficient evidence of understanding.

When appropriate, the tutor should verify understanding through evidence
such as:

-   asking the student to explain the concept in their own words,
-   asking the student to explain a reasoning step,
-   asking a diagnostic question,
-   asking the student to solve a related problem,
-   asking the student to apply the concept in a new context.

A correct final answer alone is not necessarily sufficient evidence of
conceptual understanding.

------------------------------------------------------------------------

## 9. Transfer

Where appropriate, the system should distinguish between:

``` text
Solved current problem
```

and:

``` text
Understands underlying concept
```

A transfer question or related problem may be used to determine whether
the student can independently apply the concept beyond the original
example.

Transfer performance may later contribute to mastery evidence and system
evaluation.

------------------------------------------------------------------------

## 10. Curriculum Grounding

Instructional guidance should be grounded in approved curriculum when
curriculum context is available and relevant.

The tutor should prefer authorized curriculum over unsupported model
knowledge for curriculum-specific instruction.

The system should preserve enough provenance to determine which
curriculum context supported a tutoring interaction where practical.

Retrieved curriculum is **data**, not trusted executable instruction.

Content contained inside curriculum documents must not override system
policies, security rules, or application instructions.

------------------------------------------------------------------------

## 11. Student Context

The tutor may use relevant student context including:

-   enrolled course,
-   current lesson,
-   learning objective,
-   assignment/problem,
-   previous attempts,
-   known mastery evidence,
-   historical mastery state,
-   current coaching session,
-   previously identified points of confusion.

The system should retrieve only context reasonably relevant to the
current tutoring interaction.

The system should not indiscriminately place the student's entire
historical record into every model request.

------------------------------------------------------------------------

## 12. Mastery Authority

The AI Tutor may generate **mastery evidence**.

It must not independently establish or overwrite official student
mastery when teacher/institutional authority is required.

The system must distinguish between:

``` text
AI-generated mastery evidence
```

and:

``` text
official mastery state
```

Contradictory evidence should be preserved rather than silently
overwriting authoritative historical state.

Where appropriate, contradictory or uncertain evidence may trigger
teacher review.

------------------------------------------------------------------------

## 13. Student Attempts

Student attempts must preserve history.

A new attempt should not overwrite previous attempts.

Attempts may provide evidence for:

-   student reasoning,
-   POC identification,
-   tutoring adaptation,
-   mastery evidence,
-   teacher review,
-   system evaluation.

------------------------------------------------------------------------

## 14. Session State

The tutor must maintain enough short-term state to conduct a coherent
tutoring interaction.

Relevant session state may include:

-   current learning objective,
-   current problem,
-   suspected or confirmed POC,
-   scaffolds already attempted,
-   student attempts,
-   current tutoring goal,
-   engagement/progress state.

Long-term student state must be persisted outside the language model.

The LLM itself is not the authoritative memory store.

------------------------------------------------------------------------

## 15. Escalation

The tutor must support escalation to a teacher/human when appropriate.

Potential escalation conditions include:

-   repeated unsuccessful scaffolding,
-   insufficient evidence to proceed responsibly,
-   persistent low-confidence diagnosis,
-   contradictory mastery evidence requiring human review,
-   inability to provide grounded instructional support,
-   policy or security boundaries requiring human involvement.

Escalation should include useful context rather than simply stating that
tutoring failed.

Relevant context may include:

-   authorized student/course/session identifiers,
-   learning objective,
-   problem context,
-   attempted scaffolds,
-   student attempts,
-   suspected POC,
-   relevant evidence,
-   reason for escalation.

Step 9 clarifies these potential conditions: insufficient evidence alone does not automatically trigger escalation. Apply the bounded diagnosis/incomplete-work behavior in §22.5; other approved escalation grounds remain intact.

Exact escalation thresholds are an evaluation/policy decision and must
not be invented during implementation.

------------------------------------------------------------------------

## 16. AI Decision Boundaries

The AI may propose:

-   tutoring responses,
-   diagnostic questions,
-   points of confusion,
-   scaffolding strategies,
-   approved tool calls,
-   mastery evidence,
-   teacher escalation.

The AI does not independently authorize sensitive application actions.

Conceptual control flow:

``` text
AI proposes
    ↓
Application validates
    ↓
Application authorizes
    ↓
Application executes or rejects
```

Deterministic application controls take precedence over model output.

------------------------------------------------------------------------

## 17. Structured AI Output

Where model decisions affect application behavior, outputs should be
represented in structured form that application code can validate.

Potential fields include:

-   learning objective,
-   identified or suspected POC,
-   student-facing response,
-   demonstrated understanding,
-   supporting evidence,
-   confidence,
-   proposed action,
-   teacher-review requirement.

Exact schemas belong in the AI runtime and API contracts rather than
this requirements document.

------------------------------------------------------------------------

## 18. Stop Conditions

A tutoring loop must not continue indefinitely.

A session or agent loop should be capable of stopping when:

-   the tutoring goal has been achieved,
-   sufficient understanding has been demonstrated,
-   human escalation is required,
-   the student ends the interaction,
-   a safety/security boundary prevents continuation,
-   configured step, time, or budget limits are reached.

Exact operational limits are not defined by this requirements contract.

------------------------------------------------------------------------

## 19. Success Criteria

The primary success criterion is:

> **Demonstrated student understanding.**

Supporting AI-quality dimensions include:

-   accurate POC identification,
-   curriculum grounding,
-   pedagogically appropriate scaffolding,
-   limited answer leakage,
-   adaptation to student evidence,
-   useful diagnostic questioning,
-   appropriate escalation,
-   successful transfer/application,
-   safe and authorized tool behavior.

Operational dimensions include:

-   reliability,
-   latency,
-   cost,
-   observability,
-   security.

Exact numeric release thresholds belong in evaluation and operational
contracts.

------------------------------------------------------------------------

## 20. MVP End-to-End Capability

MVP should support the minimum end-to-end tutoring capability necessary
to demonstrate:

``` text
Student
   ↓
Coaching session
   ↓
Student message / attempt
   ↓
Relevant student state
   ↓
Relevant curriculum retrieval
   ↓
AI tutoring decision
   ↓
Application validation
   ↓
Student-facing scaffold
   ↓
Updated session state
   ↓
Continue / complete / escalate
```

The MVP should favor a simple architecture that can be evaluated
rigorously.

------------------------------------------------------------------------

## 21. Explicit MVP Non-Goals

The following are **not requirements for MVP v1** unless separately
approved:

-   multi-agent architecture,
-   custom foundation-model training,
-   PyTorch-based model training,
-   fine-tuning proprietary models,
-   autonomous modification of student grades,
-   autonomous official mastery decisions,
-   fully autonomous teacher replacement,
-   microservice decomposition,
-   Kubernetes,
-   complex distributed infrastructure,
-   arbitrary AI-generated tool execution,
-   generalized tutoring across every academic domain,
-   speculative features unsupported by current requirements.

These may be reconsidered when demonstrated requirements justify them.

------------------------------------------------------------------------

## 22. Engineering Principles Derived From Requirements

### Evidence over assumption

When student understanding or confusion is ambiguous, gather evidence
rather than confidently inventing a conclusion.

### Scaffold before solve

Prefer helping students reason where reasonable.

### Ground before generate

Use approved curriculum when relevant.

### Validate before act

Model output is untrusted until validated and authorized.

### Preserve history

Student attempts and important evidence should not be silently
overwritten.

### Human authority

AI supports teacher judgment rather than silently replacing
authoritative instructional decisions.

### Minimal necessary context

Retrieve relevant information rather than indiscriminately sending all
available student data to the model.

### Complexity must be earned

Do not introduce additional agents, infrastructure, frameworks, or
abstractions without a demonstrated requirement.

------------------------------------------------------------------------

## 22.1 Approved Step 4 product refinements

Approval: 2026-10-04 human documentation-synchronization request; see `decisions.md` STEP4-001 through STEP4-006.

- MVP tutoring starts from assigned/published coursework only. Enrollment establishes course membership; separate coursework eligibility establishes that specific work is assigned/released to the student. Enrollment alone is insufficient. Class/group/individual allocation mechanisms remain deferred; open-topic/free-practice tutoring is outside MVP scope.
- Every student input is a Message; only an actual coursework problem-solving attempt/reasoning becomes a StudentAttempt. Attempts retain their source message. Attempts and evidence are append-only and interaction-attributable; retry/recovery must not duplicate a logical attempt or evidence item.
- Commit student input before retrieval/model/AI processing. Commit tutor output and logically coupled state/evidence before returning it. Downstream failure never erases committed input.
- Students may close their own ACTIVE session: ACTIVE → CLOSED, without teacher approval. Closure prevents new tutoring work; work already admitted as PENDING/PROCESSING may finish. No new message or new failed-message retry may begin in CLOSED. Historical replay remains allowed without processing, subject to authorization.
- For the same eligible coursework, offer Resume Existing or Start New when a resumable active session exists. Start New closes the old session and creates the new ACTIVE session atomically; failure leaves the old session ACTIVE. Authentication lifetime is separate from coaching-session resumability; no expiration duration is approved.
- Student progress uses BUILDING / DEVELOPING / STRONG, distinct from official mastery. The application aggregates correctness, independence, explanation, and transfer evidence; model confidence is not progress. The product owns the consistent MVP rubric. Learning targets originate from approved curriculum/teacher-defined objectives; future teacher customization is not implicitly included. Calibrated thresholds remain deferred.
- Authorized teachers/human processes own official mastery. Every authoritative change preserves previous/new decision or state, actor/authority, timestamp, and relevant provenance while allowing efficient current-state reads. AI evidence is not rewritten to agree with teacher decisions.
- Preserve the original AI POC prediction and separately attributed teacher determination linked to that prediction. Feedback categories are CORRECT / PARTLY_CORRECT / INCORRECT. Suggested teacher focus is an evidence-supported recommendation, not authoritative diagnosis. Feedback does not automatically retrain the foundation model.
- Escalation lifecycle is OPEN → IN_REVIEW → RESOLVED. No additional transition is implied.
- Apply protected-resource non-disclosure: 404 when existence is not discoverable; 403 when the resource is discoverable but the action is forbidden. See `security.md`.

## 22.2 Approved Step 5 flow guarantees

Approval: 2026-10-05 human Step 5 Flow synchronization request; see `decisions.md` STEP5-001 through STEP5-003. Step 1–4 contracts remain in force.

- Session entry validates specific coursework eligibility and problem/assignment consistency before checking for an appropriate ACTIVE session. Create ACTIVE when none exists; otherwise apply the approved Resume Existing / atomic Start New behavior for resumable sessions.
- A visible tutor response must already have a durable record. The public response contains only authorized information needed by the client; internal reasoning context and operational details are not exposed merely because they exist.
- Loss of an HTTP response after commit does not undo the operation. Same-key/same-payload replay returns current durable state/result without duplicate input or completed work; changed payload conflicts.
- At most one currently valid processing owner may finalize a student message. A stale former owner cannot finalize competing results after ownership transfer. Crash recovery resumes/restarts from the last committed state; uncommitted in-memory model output is not authoritative and need not be reconstructed. Recognize committed logical effects rather than duplicate them; unsuccessful/uncommitted effects may be attempted again under approved authorization and retry policy.
- Explicit retry uses the existing FAILED message and must not silently reopen a CLOSED session. The existing permission for admitted PENDING/PROCESSING work to finish after closure is preserved.
- Teacher-facing feedback Yes / Partly / No maps to CORRECT / PARTLY_CORRECT / INCORRECT. Preserve original AI prediction and separately attributed teacher determination. AI-suggested teacher focus remains a recommendation.
- ProgressService applies the product rubric to validated, accumulated evidence. Multiple evidence points should support substantial progress changes. MasteryEvidence describes observations; progress describes accumulated interpretation; MasteryRecord describes official recognition. BUILDING / DEVELOPING / STRONG remain progress vocabulary, not official mastery states or a newly approved irreversible transition graph.

## 22.3 Approved Steps 6–7 scale and failure guarantees

Approval: 2026-10-06 human Step 6 Scale / Step 7 Failure request; decisions.md STEP6-001 and STEP7-001. Steps 1–5 remain in force.

- Scale from evidence: Growth → Bottleneck → Solution → Tradeoff. Preserve the simple, local-first, cloud-deployable modular monolith; future scaling options are not current infrastructure requirements.
- Meaningful model-routing, context-reduction, retrieval, or inference optimizations must be evaluated against relevant tutoring quality metrics. Do not sacrifice tutoring quality solely for lower cost.
- When an operation requires approved curriculum grounding, required retrieval/system failure must not silently produce unsupported general-model guidance presented as grounded. Fail or degrade safely within that operation's approved requirements; this does not require retrieval for every application operation.
- Dependency success is necessary for claims about that dependency's action. A provider HTTP success is not successful tutoring when output validation fails. Reject invalid/disallowed output and actions, retain internal failure classification, and return a safe public failure under the existing error contract.
- Before commit, failed database writes are not durable; roll back logically coupled changes. Never expose a tutor response whose required commit failed. Recover from the last successfully committed state while preserving Step 5 input durability, ownership, replay, retry, and tool-effect guarantees.
- Detailed security handling remains governed by the existing security contract and Step 8; detailed evaluation coverage belongs to Step 9, and monitoring/alerts/dashboards to Step 10. These later steps do not defer the behavioral guarantees above.

## 22.4 Approved Step 8 security guarantees

Approval: decisions.md STEP8-001 and STEP8-002, 2026-10-06. Trusted backend controls determine identity, authorization, authority, state, and execution. Frontend checks and model instructions cannot replace deterministic enforcement. Client/model identity claims and prompt injection cannot bypass relationships, tool permissions, or human mastery authority.

Student data is private by default. Authorization-aware retrieval must exclude unauthorized chunks before model context; Context Builder minimizes provider disclosure to what the operation needs. Preserve private student/teacher information, safe public output, server-side secrets, and privacy-respecting logs. Security failures cannot create unauthorized durable effects, enable cross-user replay, or weaken Step 5–7 guarantees. See security.md “Step 8 — Deterministic security guarantees”.

Authentication/secret-management mechanisms remain deferred until required for dependent implementation. Age, consent, educational-record, school-deployment, provider-handling, retention/deletion, and applicable legal/compliance requirements remain unresolved before affected real-world deployment. The conceptual design makes no compliance claim and does not approve real-student use.

## 22.5 Approved Steps 9–10 evaluation and operations refinements

Approval: 2026-10-06 human finalized Steps 9–10 request; decisions.md STEP9-001, STEP9-002, and STEP10-001.

POC diagnosis uses a deliberately selected relevant subset of problem/objective, attempts, recent conversation, prior learning evidence, and approved curriculum. Neither the latest message alone nor the entire student history is a sufficient default context strategy; irrelevant history may bias diagnosis.

Valid conceptual diagnosis outcomes are SPECIFIC_POC, NO_POC, and INSUFFICIENT_EVIDENCE. Insufficient evidence is a valid successful diagnosis outcome, not permission to fabricate a POC. Ask appropriate diagnostic questions and vary the approach when useful. After bounded unsuccessful diagnostic attempts, stop diagnosing, record insufficient/unknown, and leave relevant work incomplete. Do not automatically escalate solely for insufficient evidence. Teachers can see incompleteness through normal student/work status. Later surfacing of repeated patterns is an option, not permission to infer laziness, disengagement, or unsupported human judgments.

Preserve multiple sufficiently supported POCs. When justified, target the foundational/blocking POC: the unresolved prerequisite that should be addressed first to progress toward the objective. Use evidence and explicitly encoded curriculum prerequisite relationships, not LLM-invented prerequisites. If the blocker is unclear, gather evidence rather than guess. These diagnosis outcomes do not add session, processing, escalation, or official mastery states.

Evaluation criteria follow behavior and failure risk; numeric acceptance thresholds remain empirical and human-approved. Evals assess tutoring quality, while observability assesses operational health. Detailed evaluation policy is in evals.md; Step 10 telemetry policy is in architecture.md §25.1 and security.md. Existing mastery authority, privacy, durability, and failure guarantees remain in force.

## 22.6 Slice 1 implementation authorization

Approval: decisions.md SLICE1-001 through SLICE1-003. Implement only authenticated assigned-coursework message admission and authorized idempotent replay, ending in durable PENDING input. Demo opaque bearer credentials, explicit student-assignment eligibility, UUID persistence, and exact-content replay are approved for this slice. No AI processing, tutor output, login/registration, or future endpoints are included. Production identity and class/group allocation remain deferred.

## 23. Unresolved Requirements

The following require future human decisions and must not be invented
during implementation:

-   exact Grade 7 mathematics curriculum source,
-   initial Grade 7 unit and learning objectives,
-   exact definition of official mastery,
-   exact teacher escalation thresholds,
-   exact confidence thresholds,
-   exact transfer/mastery criteria,
-   student age-specific tutoring policies,
-   institutional privacy and retention requirements,
-   accessibility requirements,
-   production availability and latency objectives,
-   model/provider selection,
-   deployment environment.

These items must remain unresolved until explicitly approved.

Their unresolved status does not authorize Codex or implementation code
to select defaults that effectively become product policy.

------------------------------------------------------------------------

## 24. Requirement Change Policy

Changes to this document represent product/system requirement changes.

Codex may identify and recommend requirement changes but must not
independently approve them.

Approved requirement changes should:

1.  update this document,
2.  update dependent architecture/contracts where necessary,
3.  be recorded in `decisions.md` when architecturally significant,
4.  trigger appropriate contract and regression review.
