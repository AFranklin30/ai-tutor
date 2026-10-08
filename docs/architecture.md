# AI Tutor --- MVP Architecture

**Status:** Approved\
**Version:** MVP v1\
**Initial Domain:** Grade 7 Mathematics --- one initial unit\
**Operating Context:** Controlled demonstration using synthetic/demo
student data

------------------------------------------------------------------------

## 1. Architecture Goals

The MVP architecture must support the approved tutoring requirements
while remaining simple enough to understand, test, evaluate, and change.

The architecture must support:

-   curriculum-grounded tutoring,
-   relevant student/session state,
-   point-of-confusion identification,
-   scaffold-first tutoring,
-   student attempts,
-   structured AI decisions,
-   application-side validation and authorization,
-   mastery evidence,
-   teacher escalation,
-   rigorous AI evaluation,
-   observability of AI and application behavior.

The MVP should be designed as a modular monolith rather than a
distributed microservice system.

Complexity must be introduced only when demonstrated requirements
justify it.

------------------------------------------------------------------------

## 2. Approved MVP Architecture Decisions

The following decisions are approved for MVP v1:

-   Backend language: Python.
-   Web/API framework: FastAPI.
-   Validation and structured application/model schemas: Pydantic.
-   Relational persistence: PostgreSQL.
-   Python database access/ORM: SQLAlchemy.
-   Database migrations: Alembic.
-   Vector search: pgvector within PostgreSQL.
-   Testing: pytest.
-   Observability standard: OpenTelemetry.
-   Initial operating context: controlled demonstration.
-   Initial student data: synthetic/demo data.
-   Identity model: standalone application identity; no institutional
    SSO/SIS integration.
-   Initial curriculum scope: one curated Grade 7 Mathematics unit.
-   Curriculum is loaded and managed by the application rather than
    synchronized from an external curriculum provider in MVP v1.
-   Teacher escalation is persisted in an application-managed review
    queue.
-   AI may create mastery evidence but may not establish or overwrite
    official mastery.
-   Development begins locally and remains cloud-deployable.
-   Exact cloud provider and deployment platform remain unresolved.
-   MVP uses one tutor orchestrator/agentic loop, not a multi-agent
    architecture.
-   The application uses a thin model abstraction rather than
    introducing LangChain or LangGraph initially.
-   No custom model training or PyTorch requirement exists for MVP v1.

------------------------------------------------------------------------

## 3. High-Level Architecture

``` text
Student / Teacher
        ↓
Frontend / Client
        ↓
FastAPI Application
        ↓
Authentication + Authorization
        ↓
Application Services
        ↓
Tutor Orchestrator
   ├── Student/Session State
   ├── Curriculum Retrieval
   ├── Model Abstraction
   ├── Approved Tools
   ├── Output Validation
   └── Escalation Logic
        ↓
Data / Infrastructure
   ├── PostgreSQL
   ├── pgvector
   └── Observability
```

The MVP is a modular monolith: these responsibilities may be separated
into modules/layers inside one deployable backend application.

They are not separate microservices.

------------------------------------------------------------------------

## 4. Request Boundary

FastAPI is the primary backend request boundary.

Its responsibilities include:

-   receiving API requests,
-   parsing and validating request structures,
-   invoking authentication and authorization,
-   routing requests to application services,
-   returning structured responses,
-   mapping known application failures to appropriate API errors.

FastAPI route handlers should remain thin.

Business logic, tutoring decisions, retrieval logic, and persistence
logic should not be embedded directly in route handlers.

------------------------------------------------------------------------

## 5. Validation Boundary

Pydantic is used for typed validation at application boundaries.

Potential uses include:

-   API request models,
-   API response models,
-   structured model outputs,
-   tool arguments,
-   configuration,
-   internal command/result objects where useful.

Validation does not replace authorization.

A structurally valid action may still be forbidden.

The control boundary remains:

``` text
Input / Model proposal
        ↓
Schema validation
        ↓
Authorization / policy
        ↓
Business logic
        ↓
Persistence constraints
        ↓
Execute or reject
```

------------------------------------------------------------------------

## 6. Application Service Layer

Application services coordinate deterministic business operations
outside the AI model.

Examples include:

-   creating coaching sessions,
-   recording messages,
-   recording student attempts,
-   loading relevant student state,
-   creating mastery evidence,
-   creating teacher escalations,
-   reading teacher review queues.

Application services should depend on clear repository and model
interfaces rather than provider-specific implementations where
practical.

------------------------------------------------------------------------

## 7. Tutor Orchestrator

The Tutor Orchestrator controls the tutoring workflow.

It is responsible for coordinating the approved agentic loop:

``` text
Goal
 ↓
Observe current state
 ↓
Retrieve relevant context
 ↓
Choose next permitted reasoning/action step
 ↓
Invoke model and/or approved tool
 ↓
Validate result
 ↓
Update state
 ↓
Continue, complete, or escalate
```

The orchestrator---not the LLM---owns control of the loop.

The orchestrator must enforce configured stop conditions and may not
permit indefinite autonomous execution.

The orchestrator may coordinate deterministic code, retrieval, model
calls, tools, validation, persistence, and escalation.

------------------------------------------------------------------------

## 8. Single-Agent MVP

MVP v1 uses one tutor orchestrator rather than multiple autonomous
agents.

Capabilities such as diagnosis, tutoring, evaluation, retrieval, and
escalation may exist as separate functions, services, prompts, tools, or
model calls without becoming separate agents.

A future agent boundary requires a demonstrated reason that a function,
tool, deterministic service, or model call is insufficient.

Multi-agent architecture is not an MVP requirement.

------------------------------------------------------------------------

## 9. Model Abstraction

Application code should access language models through a thin internal
model abstraction.

Conceptually:

``` text
Tutor Orchestrator
       ↓
Model Interface
       ↓
Provider Adapter
       ↓
External Model API
```

The abstraction should isolate provider-specific request/response
details from tutoring business logic.

It should make future provider/model changes possible without requiring
the tutoring workflow to be rewritten.

The abstraction must not become a speculative general-purpose AI
framework.

Exact model provider and model selection remain unresolved human
decisions.

------------------------------------------------------------------------

## 10. Model Routing

The architecture may support model routing, but MVP implementation
should begin with the minimum routing behavior required by approved use
cases.

Conceptually:

``` text
Task / context
      ↓
Routing policy
      ↓
Selected model
```

Future routing may consider:

-   task complexity,
-   confidence,
-   latency,
-   cost,
-   fallback conditions.

Exact routing rules and thresholds remain unresolved.

The architecture should permit a progression such as:

``` text
Deterministic logic
      ↓
Primary model
      ↓
Optional stronger/fallback model
      ↓
Human escalation
```

without requiring those stages to be fully implemented initially.

------------------------------------------------------------------------

## 11. Structured Model Output

Model output that influences application behavior must use structured,
validated data.

The model may propose fields such as:

-   student-facing response,
-   suspected point of confusion,
-   confidence,
-   demonstrated-understanding evidence,
-   proposed next action,
-   mastery evidence,
-   escalation recommendation.

Exact schemas belong in `ai-runtime.md` and related API/application
contracts.

Raw model output must not directly authorize sensitive actions.

------------------------------------------------------------------------

## 12. Tools

The tutor may interact with application capabilities through an approved
tool boundary.

Potential tools include:

-   get student mastery/evidence,
-   get current assignment/problem,
-   search curriculum,
-   save student attempt,
-   create mastery evidence,
-   create teacher escalation.

The model may propose a tool call.

The backend must validate and authorize the proposed tool and arguments
before execution.

``` text
LLM proposes tool call
        ↓
Validate tool + arguments
        ↓
Authorize action
        ↓
Execute deterministic backend code
        ↓
Return controlled result
```

The model must not receive arbitrary database, filesystem, network, or
code-execution access.

------------------------------------------------------------------------

## 13. Student and Session State

Short-term tutoring state is managed by the application and persisted as
necessary.

It may include:

-   current coaching session,
-   current problem,
-   current learning objective,
-   suspected/confirmed POC,
-   previous scaffolds,
-   recent attempts,
-   current tutoring goal.

Long-term student evidence and history are stored in PostgreSQL.

The LLM context window is not the authoritative state store.

Only relevant state should be assembled into a model request.

------------------------------------------------------------------------

## 14. Relational Data Layer

PostgreSQL is the primary persistent datastore.

It stores structured application data such as:

-   students/demo identities,
-   courses,
-   lessons,
-   learning objectives,
-   assignments/problems,
-   coaching sessions,
-   messages,
-   student attempts,
-   points of confusion,
-   mastery evidence/state where applicable,
-   teacher escalations,
-   curriculum metadata.

Exact tables, keys, constraints, relationships, indexes, and
authoritative-state rules belong in `schema.md`.

------------------------------------------------------------------------

## 15. SQLAlchemy and Repository Boundary

SQLAlchemy is the approved Python database access layer.

Application/business logic should not be tightly coupled to raw database
queries spread throughout the codebase.

Repositories or equivalent focused data-access modules should
encapsulate persistence operations where useful.

Conceptually:

``` text
Application Service / Orchestrator
             ↓
Repository / Data Access
             ↓
SQLAlchemy
             ↓
PostgreSQL
```

This boundary exists for clarity and testability, not to require
unnecessary abstraction.

------------------------------------------------------------------------

## 16. Database Migrations

Alembic manages relational schema migrations.

Schema changes must follow the approved schema-change workflow.

Application startup must not silently mutate production schemas.

Schema design remains governed by `schema.md`.

------------------------------------------------------------------------

## 17. Curriculum Architecture

MVP v1 uses a curated, approved Grade 7 Mathematics curriculum corpus.

The initial implementation targets one Grade 7 Mathematics unit.

Curriculum content should have enough metadata to associate material
with relevant concepts such as:

-   course,
-   unit,
-   lesson,
-   learning objective,
-   source/provenance.

Exact curriculum source and first unit content remain separate human
decisions unless explicitly approved elsewhere.

The architecture does not require synchronization with an external
curriculum provider for MVP v1.

------------------------------------------------------------------------

## 18. Retrieval-Augmented Generation

Curriculum grounding uses retrieval-augmented generation (RAG).

Conceptually:

``` text
Approved curriculum
      ↓
Chunk / prepare content
      ↓
Create embeddings
      ↓
Store vectors + metadata
      ↓
pgvector
```

Runtime:

``` text
Student question / tutoring state
      ↓
Construct retrieval query
      ↓
Filter authorized/relevant curriculum
      ↓
Vector retrieval
      ↓
Top relevant curriculum context
      ↓
Tutor Orchestrator / Model
```

Retrieval should support filtering by relevant metadata such as course,
unit, lesson, or learning objective where appropriate.

Exact chunking, embedding model, retrieval K, similarity thresholds, and
reranking strategy remain evaluation-driven decisions.

------------------------------------------------------------------------

## 19. pgvector

pgvector is used for MVP vector similarity search inside PostgreSQL.

This keeps structured data and curriculum vector infrastructure
operationally simple for the initial system.

A dedicated vector database should not be introduced unless scale,
retrieval quality, or operational evidence demonstrates a need.

------------------------------------------------------------------------

## 20. Behavior When Grounding Is Insufficient

The tutor must not fabricate curriculum-specific guidance when
appropriate approved grounding cannot be obtained.

Depending on context, the system may:

-   ask a diagnostic or clarifying question,
-   provide only support that is allowed without curriculum-specific
    claims,
-   report that sufficient approved context is unavailable,
-   escalate for teacher review.

Exact behavioral policy belongs in `ai-runtime.md`.

------------------------------------------------------------------------

## 21. Mastery Evidence Boundary

The AI may produce evidence relevant to student understanding.

That evidence may be persisted.

The AI may not independently convert its evidence into authoritative
official mastery.

Conceptually:

``` text
Student interaction
      ↓
AI evaluation
      ↓
Validated mastery evidence
      ↓
Persist evidence
      ↓
Teacher / authoritative process
```

Official mastery authority remains outside autonomous AI control.

MVP v1 does not require integration with an external official mastery
system.

------------------------------------------------------------------------

## 22. Teacher Escalation

Escalations are persisted in PostgreSQL and exposed through a minimal
application-managed review workflow.

An escalation should preserve enough context for useful human review
without requiring the teacher to reconstruct the entire session
manually.

The minimum architecture supports:

``` text
Tutor determines escalation is needed
        ↓
Backend validates escalation
        ↓
Persist escalation + relevant context
        ↓
Teacher review queue
        ↓
Authorized teacher can inspect review item
```

A sophisticated teacher dashboard is not required for MVP v1.

Approved escalation lifecycle: OPEN → IN_REVIEW → RESOLVED. Preserve original AI POC predictions and separate attributed teacher feedback (CORRECT / PARTLY_CORRECT / INCORRECT). Teacher focus is advisory. Additional transitions, notification behavior, and remaining teacher actions/thresholds stay deferred.

------------------------------------------------------------------------

## 23. Authentication and Authorization

MVP v1 uses standalone application identity rather than institutional
SSO/SIS integration.

Authentication establishes identity.

Authorization determines permitted actions and data access.

Roles are expected to include at least student and teacher boundaries,
with administrative capability added only where required.

Exact auth mechanism, token/session strategy, role definitions, and
permissions belong in `security.md`.

Client-supplied identity fields must not override authenticated
identity.

------------------------------------------------------------------------

## 24. Privacy and Demo Data

MVP v1 operates with synthetic/demo student data.

This decision allows architecture and AI behavior to be developed
without implying that the current system is approved for production
handling of real minors' educational records.

Production privacy, retention, deletion, consent, institutional, and
provider-sharing policies remain unresolved and must be approved before
a real-student pilot.

The architecture should avoid choices that unnecessarily prevent later
implementation of those policies.

------------------------------------------------------------------------

## 25. Observability

The application should use OpenTelemetry-compatible instrumentation.

Observability should cover both ordinary application behavior and
AI-specific execution.

Relevant trace stages may include:

``` text
Request
 ↓
Authentication / authorization
 ↓
Load state
 ↓
Curriculum retrieval
 ↓
Build model context
 ↓
Model selection/call
 ↓
Tool call
 ↓
Output validation
 ↓
Persistence
 ↓
Response
```

Potential metrics include:

-   request latency,
-   error rate,
-   model latency,
-   model/token usage,
-   model cost where available,
-   retrieval behavior,
-   fallback behavior,
-   validation failures,
-   escalation rate.

Exact SLOs, alert thresholds, retention, and remaining production telemetry
mechanisms/policies remain unresolved; §25.1 establishes the approved Step 10 scope.

Synthetic/demo operation does not authorize careless logging practices.

------------------------------------------------------------------------

## 25.1 Step 10 — Operations and observability contract

Approval: decisions.md STEP10-001. Retain OpenTelemetry-compatible instrumentation. Support trace/correlation IDs across request → backend → database → retrieval → Context Builder → orchestrator → model → tools when applicable → validation → durable database commit → response. These are correlation boundaries, not a replacement execution order: preserve §31 and existing transaction/model/tool flows.

Trace important spans for authorization, database operations, retrieval, context construction, model calls, tool execution, validation, and the final durable transaction so latency/failures can be attributed to components. Preserve API §7 internal failure distinctions and safe public errors.

Production logs default to operational metadata: message_id, session_id, trace_id/correlation_id, content length, status/state transition, model/provider identifier where appropriate, latency, error category, and retry/recovery information. Follow security.md “Step 10 logging and telemetry privacy”; protected application records may retain authorized content under existing policies without duplicating it in logs.

Initial metrics should include where practical: request volume; success/failure rate; end-to-end, model, retrieval, and database latency; token/model cost usage; tool/retrieval/structured-output-validation failure rates; retry/recovery rate. These complement existing metrics without selecting a backend, dashboard, or numeric target.

Important AI-system records, traces, and eval runs should retain relevant model, prompt, retrieval, and eval dataset version identifiers where practical to correlate behavior with system changes. No physical field layout or versioning implementation is selected.

Prefer actionable alerts. Candidates include Tutor failure-rate spikes, model/provider failures, database unavailability, retrieval failure spikes, unauthorized-action attempts, unexpected cost increases, and latency beyond defined operational targets. Exact operational thresholds remain deferred until baseline data exists; do not alert on every fluctuation.

Evals measure behavioral quality; observability measures operational health. They may be correlated but are not substitutes. Collector/exporter/storage, sampling, telemetry access/retention, alert delivery, and deployment mechanisms remain unresolved where not already approved; no infrastructure is introduced by this contract.

## 26. Testing Architecture

pytest is the primary Python test framework.

The system should support:

-   unit tests,
-   API/integration tests,
-   database/repository tests,
-   authorization tests,
-   structured-output validation tests,
-   AI evaluation/regression tests.

AI evaluation design belongs primarily in `evals.md`.

Implementation should keep deterministic system tests distinct from
probabilistic AI quality evaluations.

------------------------------------------------------------------------

## 27. Failure Boundaries

External dependencies such as model APIs and future hosted
infrastructure must be treated as fallible.

The architecture should permit:

-   timeouts,
-   bounded retries where safe,
-   exponential backoff/jitter where appropriate,
-   provider/model fallback when approved,
-   idempotency for duplicate-prone operations,
-   transactional persistence,
-   graceful degradation,
-   useful error reporting.

Exact retry, timeout, fallback, and idempotency policies belong in
implementation/runtime/API contracts as appropriate.

------------------------------------------------------------------------

## 28. Deployment Architecture

Development begins locally.

The application should remain deployable to a cloud environment without
requiring an architectural rewrite.

MVP does not yet select:

-   AWS,
-   Azure,
-   Google Cloud,
-   a specific PaaS,
-   container orchestration platform.

The application should avoid unnecessary provider-specific coupling
until a deployment decision is approved.

Kubernetes is not an MVP requirement.

------------------------------------------------------------------------

## 29. Deliberate MVP Exclusions

The architecture does not initially require:

-   microservices,
-   Kubernetes,
-   multi-agent orchestration,
-   LangChain,
-   LangGraph,
-   PyTorch,
-   custom model training,
-   model fine-tuning,
-   dedicated vector database,
-   institutional SIS integration,
-   institutional SSO,
-   real-student production data,
-   autonomous official mastery decisions,
-   arbitrary model-controlled tool execution.

These are not permanently prohibited.

They require demonstrated need and human approval.

------------------------------------------------------------------------

## 30. Dependency Direction

The preferred dependency direction is:

``` text
API
 ↓
Application Services
 ↓
Tutor Orchestrator / Domain Logic
 ↓
Interfaces
 ├── Repositories
 ├── Model Interface
 ├── Retrieval Interface
 └── Approved Tool Interfaces
 ↓
Infrastructure Implementations
 ├── SQLAlchemy/PostgreSQL
 ├── pgvector
 ├── Model Provider Adapter
 └── OpenTelemetry
```

Business/tutoring logic should not depend directly on provider-specific
infrastructure details where a small interface provides meaningful
isolation.

Avoid abstraction that exists only for hypothetical future requirements.

------------------------------------------------------------------------

## 31. Conceptual End-to-End Runtime

``` text
Student sends message
        ↓
FastAPI receives request
        ↓
Validate request
        ↓
Authenticate + authorize
        ↓
Load coaching session/student state
        ↓
Resolve authorized idempotent replay (return current state; no processing)
        ↓
For a new send, validate ACTIVE session and eligible assigned coursework/problem/objective
        ↓
Commit student input + associated idempotency record
        ↓
Acquire single processing ownership
        ↓
Retrieve approved curriculum context
        ↓
Context Builder assembles bounded authorized model context
        ↓
Model abstraction invokes selected model
        ↓
Receive structured model proposal
        ↓
Pydantic/schema validation
        ↓
Application policy + authorization validation
        ↓
ToolExecutor → services → repository → PostgreSQL when an approved action is needed
        ↓
Tool result → Orchestrator/model context before further reasoning; repeat within step limit
        ↓
Commit tutor output + logically coupled state/evidence + COMPLETED status
        ↓
Return student-facing response
        ↓
Continue / complete / escalate
```

No model response bypasses application validation to directly perform
sensitive application actions.

------------------------------------------------------------------------

## 31.1 Approved Step 4 execution guarantees

See `api-contract.md` §§2–6 and `ai-runtime.md` for the approved flow. Student input and tutor output are separate correlated messages. Processing metadata follows PENDING → PROCESSING → COMPLETED or FAILED without rewriting content history. External calls do not run inside the durable-input transaction.

Only one active processing run owns a student message. Stale work must be detectable/recoverable. Retries/recovery/concurrency cannot create competing tutor responses or duplicate durable effects: reuse a previously successful logical action. User-operation idempotency and system-action idempotency are distinct. Locks, leases, queues, workers, and their physical design remain unresolved.

Session closure is ACTIVE → CLOSED. New work cannot begin after closure; previously admitted PENDING/PROCESSING work may finish. FAILED work in CLOSED cannot begin explicit retry. Authorized replay may retrieve historical state/results without processing. Start New atomically closes the old ACTIVE session and creates the replacement; failure leaves the old session ACTIVE. Resumability duration remains unresolved.

MVP coursework eligibility is distinct from enrollment. Application services validate specific assignment/release eligibility before new tutoring. No class/group/individual allocation infrastructure is selected here.

Progress is application-estimated BUILDING / DEVELOPING / STRONG, separate from official mastery. Every official mastery change must remain historically attributable while supporting current reads; no physical history design is selected. Original AI POC and teacher feedback remain separately traceable.

Backend controls → Orchestrator coordinates → RAG retrieves authorized curriculum → LLM reasons/recommends → Tools perform controlled actions → Database persists durable state. Minimum relevant authorized student context is selected by the backend; personalization does not change foundation-model weights.

Approved configurable runtime defaults are 4,000 message characters, five agent steps, 30 seconds per model call, and one automatic retry for eligible transient failures. Broader eligibility remains unresolved. Authorization/non-disclosure rules are defined in `security.md`; deterministic verification and AI eval obligations in `evals.md`.

## 31.2 Approved Step 5 component flows

These are responsibilities inside the existing local-first modular monolith, not new deployments, queues, workers, or microservices. Approval: `decisions.md` STEP5-001 through STEP5-003.

| Component | Responsibility |
| --- | --- |
| FastAPI/backend | Authentication/authorization entry and controlled public HTTP responses |
| Application services | Eligibility, business rules, permitted transitions, and coordinated writes |
| Repositories/data access | Read/write PostgreSQL through approved persistence boundaries |
| Tutor Orchestrator | Own bounded reasoning loop, processing coordination, and finalization |
| RAG | Retrieve relevant authorized curriculum |
| Context Builder | Assemble minimum relevant authorized context, runtime instructions, and allowed tools |
| Model | Produce untrusted reasoning/recommendations; no application authority |
| ToolExecutor | Mediate validated model-requested actions through application services |
| ProgressService | Apply product-owned rubric to accumulated validated evidence |
| PostgreSQL | Authoritative durable application state |

Session entry: Student → Frontend → FastAPI → authenticate → authorize → validate coursework eligibility → validate problem/assignment relationship → check existing ACTIVE session. Create ACTIVE if none is appropriate; otherwise offer approved Resume Existing / atomic Start New for a resumable session. Failed replacement leaves the old session ACTIVE.

Message entry preserves §31 replay handling: authenticate/authorize and validate applicable business context, distinguish historical replay from new work, then validate ACTIVE eligibility for a new send. Commit input/idempotency state before processing ownership and expensive AI work. A closed-session replay is not rejected as a new send.

Runtime: Orchestrator → RAG → Context Builder → model → structural validation → policy/authority validation → business/state validation. Context includes relevant problem/objective, approved prerequisites, student evidence/progress, recent attempts, POCs, retrieved chunks, current message, instructions, and allowed tools.

Tool branch: Orchestrator → ToolExecutor → application/service logic → repository → PostgreSQL. Enforce arguments, authorization, authority, state, and durable-action idempotency. Results return to the Orchestrator and enter model context before further reasoning. The model must not presume success. The Orchestrator enforces the existing five-step configurable limit.

Final branch (no further required tool actions): validated final response → services → repository → PostgreSQL; atomically persist logically coupled output/evidence/state and completion as appropriate, then COMMIT → FastAPI controlled HTTP response → Frontend → Student.

Recovery starts from the last durable commit, not lost model output. Only the currently valid owner may finalize; a stale former owner cannot finalize after transfer. Reuse previously committed logical effects; failed/uncommitted effects may be attempted again under approved rules. Exact ownership/reclamation mechanism remains deferred.

Teacher review: Teacher → Frontend → FastAPI → authenticate → authorize teacher/student/course relationships → escalation service → repository → PostgreSQL. Queue summaries show reason, demonstrated ability, suspected difficulty, previous interventions, and evidence-supported suggested focus. Deeper evidence remains authorization-scoped. Lifecycle and feedback remain those in §22 and api-contract.md §13.

Progress: interaction → model assessment → validated MasteryEvidence → ProgressService → accumulated progress interpretation. Official mastery remains the authorized human workflow, with preserved history. No physical progress storage or new mastery transitions are selected.

## 31.3 Step 6 — Measurement-driven scaling

Approval: decisions.md STEP6-001. Apply Growth → Bottleneck → Solution → Tradeoff. FastAPI, PostgreSQL + pgvector, external model APIs, and the thin model abstraction remain the modular-monolith MVP. FastAPI is not currently expected to be the primary bottleneck; model inference is a significant potential cost, latency, concurrency, and provider-capacity constraint. These are expectations to measure, not benchmark results.

| Growth / measured bottleneck | Conditional solution | Tradeoff / boundary |
| --- | --- | --- |
| Application-server capacity | Clients → load balancing/routing → multiple application instances | Avoid unnecessary dependence on one permanent server instance; retain durable ownership/idempotency guarantees across instances. No load balancer is required now. |
| Database query/read/table growth | Query optimization, appropriate indexes, pagination, safe caching; later read replicas or partitioning if justified; sharding only at extreme scale | Prefer the simplest effective optimization. Added consistency and operational complexity require justification; no replicas, partitioning, or sharding now. |
| Curriculum growth / retrieval latency or quality | Deterministic metadata/authorization filtering plus vector similarity in PostgreSQL + pgvector; improved indexing/search when measured need warrants it | Filter by authorized curriculum and relevant course, grade/subject, unit/lesson, objective, and approved prerequisites. Do not search all curriculum indiscriminately. A dedicated vector system requires measured scale, latency, operational, or retrieval justification. |
| Inference cost / latency / concurrency / provider capacity | Investigate model selection/routing, calls per turn, avoidable loop steps, context/token size, retrieval precision/chunk count, safe caching, provider capacity, bounded steps/retries | Evaluate meaningful changes against tutoring quality; lower cost alone cannot justify quality loss. No routing policy, cache design, or new retry budget is selected. |

The thin model abstraction should permit workload-appropriate models when justified: stronger models for complex tutoring reasoning and cheaper/faster models for simpler classification/transformation only when evaluations support acceptable quality. Embeddings use a separate embedding model; provider/model/dimension remain unresolved.

Initial curriculum remains one small curated unit. Additional application instances, routing/load balancing, caching, database read scaling, improved vector indexing/search, model routing, and asynchronous processing are evolutionary options. Kubernetes, microservices, queues, sharding, and dedicated vector infrastructure are not introduced for hypothetical future scale. Exact deployment and physical scaling mechanisms remain deferred.

## 31.4 Step 7 — Failure boundaries

Approval: decisions.md STEP7-001. Use What can fail → What happens → How do we recover → What does the user see? The operational failure matrix is in ai-runtime.md “Step 7 failure behavior”; API error mappings remain in api-contract.md §§3, 6–7.

Required retrieval failure cannot be disguised as curriculum-grounded tutoring. Provider success still requires structural, policy/authority, action, and business/state validation. Invalid output must be rejected without executing disallowed actions. Required database writes must commit before their results are treated as durable; logically coupled writes roll back together on pre-commit failure, and an uncommitted final tutor response is withheld.

Keep the Step 5 recovery model: bounded eligible retries, durable input, explicit retry of the same FAILED message, one valid finalizing owner, stale-owner rejection, recovery from committed state, durable-action reuse, lost-response replay, and closure restrictions. Process crashes do not imply a requirement to introduce worker infrastructure.

Circuit breakers, extra fallback providers, and sophisticated degradation strategies are future options requiring demonstrated reliability need and approval, not MVP requirements. Detailed failure traces/metrics/alerts/rate monitoring/dashboards belong primarily to Step 10; existing OpenTelemetry and internal classification obligations remain. Detailed tests/evals belong primarily to Step 9; security-specific handling remains governed by security.md and Step 8.

## 31.5 Step 8 — Trusted security boundaries

Approval: decisions.md STEP8-001 and STEP8-002. security.md owns the detailed guarantees. Backend authentication resolves actor context; services enforce relationships, authority, and valid state. Frontend controls and LLM prompts are not substitutes for deterministic enforcement, including when the model follows injected instructions.

Tool execution uses LLM proposal → ToolExecutor → validation/authorization/policy → Service → Repository → Database. Derive authoritative actor/resource context from the backend; model arguments supply semantic/action information and cannot substitute another student's identity. No unrestricted model database, filesystem, network, arbitrary-code, authentication-state, authorization, or official-mastery capability is granted.

RAG restricts authorized metadata scope before supplying chunks to Context Builder/LLM. Context Builder minimizes student/teacher/provider disclosure. Public output, internal denial diagnostics, logging, and server-side secret handling retain privacy boundaries. Replay/recovery preserves authorization and valid-owner finalization.

No authentication provider, secret-management product, new security service, or infrastructure is selected. Deployment-specific compliance remains unresolved before affected real-world use. Step 8 approves architectural guarantees; detailed test coverage remains Step 9 and operational monitoring Step 10.

## 31.6 Steps 9–10 — Evaluation and runtime integration

Approval: decisions.md STEP9-001, STEP9-002, STEP10-001. evals.md owns the behavior-to-regression framework, eight initial AI eval families, human-reviewed ground truth, scorers, baselines, slices, and risk-driven release decisions. Deterministic controls remain software tests; probabilistic behavior remains AI evals. Numeric thresholds stay unresolved.

Context Builder selects relevant evidence for diagnosis; the orchestrator supports SPECIFIC_POC, NO_POC, and INSUFFICIENT_EVIDENCE outcomes, multiple supported POCs, and a justified foundational intervention target using encoded prerequisites. Insufficient evidence alone neither means runtime failure nor automatically creates escalation. Bounded diagnosis can end with recorded unknown/insufficient evidence and incomplete work visible through normal status. Exact persistence/wire representation and diagnostic-attempt bound remain deferred; no new session/processing state is selected.

§25.1 defines operational correlation, metadata-first logs, metrics, spans, versioning, and actionable-alert candidates. Existing modular-monolith scaling posture, privacy/security boundaries, human mastery authority, and Step 5–7 durability/recovery remain unchanged.

## 31.7 Slice 1 implementation boundary

Approval: decisions.md SLICE1-001 through SLICE1-003. Minimal FastAPI request validation → demo opaque-bearer authentication → service authorization/admission/replay → repository → PostgreSQL transaction → commit → 201 creation or 200 replay. Use SQLAlchemy/Alembic/pytest and UUIDs. Record metadata-only request completion and OpenTelemetry-compatible request/transaction spans, without a telemetry platform/exporter. No AI processing starts and all newly admitted messages remain PENDING. Existing users/coursework/sessions are provisioned outside this endpoint.

## 32. Unresolved Architecture Decisions

The following remain unresolved and must not be silently selected during
implementation:

-   exact model provider/model,
-   exact embedding provider/model,
-   exact first Grade 7 Mathematics unit and curriculum source,
-   production authentication beyond the approved Slice 1 demo mechanism,
-   remaining teacher review actions beyond the approved escalation lifecycle/feedback,
-   exact official mastery definition,
-   exact AI confidence/escalation thresholds,
-   exact retrieval parameters,
-   exact model routing/fallback rules,
-   remaining timeout/retry eligibility and recovery policy beyond approved configurable defaults in `ai-runtime.md`,
-   production privacy/retention/deletion requirements,
-   production accessibility requirements,
-   production SLOs,
-   cloud/deployment provider,
-   production secrets/key-management approach.

These unresolved items do not invalidate the approved conceptual
architecture.

They must be resolved before implementation that materially depends on
them.

------------------------------------------------------------------------

## 33. Architecture Change Policy

Changes to major architectural boundaries require human approval.

Codex may identify architectural issues, tradeoffs, or recommendations
but must not independently approve changes to:

-   deployment shape,
-   data authority,
-   agent boundaries,
-   model/tool authority,
-   persistence strategy,
-   security boundaries,
-   curriculum grounding strategy,
-   major frameworks/infrastructure.

Approved architecture changes should update this document and, where
significant, `decisions.md`, followed by contract consistency review.
