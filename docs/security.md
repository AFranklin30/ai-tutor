# Security and authorization rules

Status: Approved Steps 4–10 conceptual security boundaries; deferred details remain UNRESOLVED.
Approval: 2026-10-04 human synchronization request; decisions.md STEP4-003 and STEP4-006, with prior approved requirements/architecture/schema.

## Identity and relationships

MVP uses standalone application identity with student and teacher boundaries and synthetic/demo data. Identity is authenticated server-side; client student/user fields never override it. Slice 1 uses the approved demo opaque-bearer mapping below; production authentication and additional credential/session design remain unresolved. No institutional SSO/SIS integration is required.

Students act only on their authorized records/sessions. Teachers access only students/coursework/evidence within approved teacher-course and student-course relationships. Validate objective/course and assignment/problem/course consistency. Enrollment alone does not establish assignment eligibility: specific coursework must be assigned/released to the student. Slice 1 uses explicit student-assignment eligibility; class/group allocation and remaining relationship-lifecycle permissions are deferred.

Normal student closure of their own ACTIVE session requires no teacher approval. Closure is ACTIVE → CLOSED; see api-contract.md §11 for admitted work and replay. Authentication expiration is separate from coaching-session resumability.

## Protected-resource non-disclosure

Apply the same discoverability rule to session/message sends, reads, replays/retries, teacher details, and mastery resources:

- Caller must not discover existence: return 404 Not Found. Examples include another student's protected session/message or a student outside the teacher's authorized relationship.
- Resource is legitimately discoverable but requested action is forbidden: return 403 Forbidden.
- Authorized action conflicts with business state: use the API's state-conflict behavior, including 409 for a new message in CLOSED.

Never reveal ownership as part of a protected denial. Internal logging may retain the real authorization reason. Replay/retry still requires authorization and cannot bypass these boundaries.

### Asynchronous worker and polling — STEP5-001-A1

Authenticated message-status GET applies the same protected-resource rules to the original message/session/course on every read. Knowledge of a message identifier is not authorization. Authorized CLOSED-session reads do not grant permission for new work or explicit retry. Expose only approved student-safe state/output, not worker internals.

Worker deployment does not grant model or tool authority. Background execution uses trusted backend context and existing service-level authorization/policy boundaries. New-session context selection remains minimal and authorized. Worker credential provisioning is operational configuration, not a new student identity or permission mechanism.

## Model, tool, curriculum, and data authority

LLM proposals are untrusted. The deterministic backend validates output, tool names/arguments, trusted identity/context, permission, and current state before execution. Tools are allow-listed and state-dependent. No direct model database, raw SQL, arbitrary network, filesystem, or official mastery authority exists.

The backend/context builder selects the minimum relevant authorized student context; the model cannot browse unrestricted records. RAG filters authorized approved curriculum before relevance ranking; prerequisite links do not grant access. Retrieved documents are untrusted data and cannot override application or security instructions. Restricted answer material must not be exposed indiscriminately.

MasteryEvidence and estimated progress are not authoritative MasteryRecord state. Authorized teachers/human processes control official mastery, with every change historically attributable. AI evidence and original POC predictions remain preserved; teacher feedback is separate, attributed, and linked to its source prediction. AI teacher-focus suggestions are recommendations, not authoritative diagnoses.

## Public output and truthful actions

Public errors/results must not expose provider errors, raw model output, internal prompts, stack traces, unrelated student data, or unnecessary internal AI metadata. Student APIs do not expose internal escalation identifiers/status by default. Keep precise internal failure categories separate from stable student-safe public errors.

Tutor output must be durably committed before return. It must not claim a failed tool action succeeded. Creating an escalation review item is not evidence that an external notification was delivered. Notification behavior remains deferred.

## Step 5 execution and public-response boundary

ToolExecutor mediates model requests through application services and repositories; it never grants direct model PostgreSQL access. Arguments, authority, authorization, business state, and durable-action idempotency must be enforced. Tool results return to the Orchestrator/model context before further reasoning; a requested action is not proof of success.

Only the currently valid owner may finalize processing. Ownership transfer invalidates the stale former owner's ability to finalize competing results. Physical enforcement is deferred, not the guarantee.

Student-visible responses are delivered only after durable commit through controlled FastAPI/HTTP output. Exclude unnecessary raw model output, confidence, internal POC data, tool calls/results, RAG chunks, provider details, traces/stack traces, internal failures, escalation IDs, and other internal state. Expose only authorized information needed by the client; authorized teacher detail views retain their approved evidence access. HTTP delivery loss does not undo committed state or authorize duplicate processing.

Step 5 source: decisions.md STEP5-001 and STEP5-002. Existing authentication, non-disclosure, closure/replay, and teacher mastery authority rules remain unchanged.

## Steps 6–7 authorization and failure truthfulness

Approval: decisions.md STEP6-001 and STEP7-001. Growth and optimization do not relax authorization/context boundaries: metadata filtering, caching if later justified, model routing, and additional application instances must preserve authorized data access and existing durable ownership rules. No cache, routing, or infrastructure security design is selected.

Required retrieval failure must not be concealed by unsupported output presented as curriculum-grounded. Provider HTTP success does not bypass output/policy/authority validation. Reject invalid/disallowed actions, verify tool outcomes, and withhold final tutor output if its required commit fails. Preserve safe public errors and internal classification without exposing protected records or operational details.

Existing non-disclosure and human mastery authority remain unchanged. Step 7 does not complete Step 8 security design or Step 10 monitoring design; deferred age/privacy/accessibility and authentication decisions remain unresolved.

## Step 8 — Deterministic security guarantees

Approval: 2026-10-06 human Step 8 Security synchronization request; decisions.md STEP8-001 and STEP8-002. Preserve Steps 1–7. Untrusted components may propose actions; trusted backend components determine identity, authorization, authority, valid state, and execution. Controls enforceable deterministically must not depend solely on prompts, frontend controls, or model compliance.

### Authentication and trusted execution identity

Authentication establishes who the caller is; authorization determines permitted access/actions. Resolve authenticated user → backend identity → authorized student/teacher context through the trusted authentication mechanism. Client-supplied `student_id`, `teacher_id`, or similar fields cannot establish or replace actor identity. Where possible, derive security-sensitive identity without requiring the client to supply it. Client resource identifiers still require server-side access checks.

Enforce enrollment, teacher-course assignment, session/resource ownership, and specific assignment eligibility on the backend. The demo mechanism is settled by Slice 1 approval below; production authentication and additional credentials/session strategies remain unresolved.

### Prompt injection and tools

Student/user content, model output, and model-generated tool arguments are untrusted. Their instructions cannot override application policy, trusted identity, authorization, allowed tools, session state, or human mastery authority. Security must hold even if a mistaken or prompt-injected model follows malicious instructions. Prompts may reinforce policy but are not the primary security boundary.

LLM proposal → ToolExecutor → validation / authorization / policy → Service → Repository → Database.

Only explicitly allow-listed, context/state-appropriate actions may execute. Validate tool names, schemas, arguments, state, permission, and authority before execution. Prefer semantic/action-specific arguments from the model and authoritative actor/resource context from the backend. A tool proposal naming STUDENT-999 during STUDENT-123's authenticated tutoring session must not redirect the action to STUDENT-999. Model-generated identifiers cannot replace trusted context.

The model has no unrestricted PostgreSQL, filesystem, network, arbitrary-code, authentication-state, authorization-decision, official-mastery, or internal-application access. AI may create authorized evidence/recommendations but cannot establish, overwrite, or directly modify official mastery, including through manipulated tools.

### Authorized retrieval and minimized context

Authenticated/authorized context → deterministic retrieval restrictions → semantic/vector search within permitted scope → authorized chunks → Context Builder → LLM.

Unauthorized chunks must not enter model context because they are semantically similar. Do not retrieve unrestricted data and ask the model to decide access. Preserve applicable authorized-curriculum, course, grade/subject, unit/lesson, objective, and approved-prerequisite filters; prerequisite relationships confer no extra access.

Student data is private by default. Access requires an approved relationship and legitimate product need. Students cannot access other students' records; teacher access stays within approved relationships. Context Builder selects only reasonably necessary current problem/objective, relevant prerequisites, recent attempts, POC/evidence, approved retrieved curriculum, and current message, alongside approved runtime instructions/tools. Do not automatically send full histories, unrelated records, other students' data, private teacher information, or unnecessary sensitive data to providers.

Public APIs must not unnecessarily expose internal student information, model reasoning, private teacher information, raw retrieved content, tool data, provider details, or unrelated records. Preserve approved authorized teacher evidence views and existing student-safe output boundaries.

### Security during failure, replay, and recovery

Unauthorized operations must not produce the requested durable side effects; rejected tools must never be presented as successful. Preserve protected-resource 404 versus discoverable-but-forbidden 403. Retain sufficient internal denial information for security/audit diagnosis without disclosing it to unauthorized callers or unnecessarily logging sensitive data.

Retries and recovery cannot bypass authorization. Idempotency remains scoped to authenticated student + operation + key and must not permit cross-user replay. Stale ownership cannot authorize finalization; only the currently valid owner may finalize under the approved authority/state rules. Preserve Step 5–7 transaction, durability, retry, closure, and failure-truthfulness guarantees.

## Step 8 — Secrets, logging, and deployment decisions

Approval: decisions.md STEP8-002. Do not unnecessarily log sensitive student information, secrets, authentication credentials/tokens, or model/context contents. Detailed observability design remains Step 10; privacy/security boundaries apply now.

Application/provider/database secrets stay server-side. Do not put secrets in model prompts or public responses. Any narrowly defined trusted integration requiring secret access must be explicitly approved; no exception or new model/client capability is approved here. Exact secret-management infrastructure remains deferred until dependent implementation/deployment requires it.

This conceptual security contract is not a claim of legal or regulatory compliance. TODO / UNRESOLVED: deployment-specific age requirements, parental consent, retention/deletion, educational-record handling, school deployment, provider data handling, and applicability/requirements of FERPA, COPPA, or other privacy/legal obligations. Resolve these before dependent real-world deployment involving affected users/data. Existing synthetic/demo scope and accessibility deferrals remain unchanged.

Authentication mechanism and required credential/session design must be resolved before dependent implementation; secret handling infrastructure must be resolved when implementation/deployment needs it. Compliance policies require deployment context and human approval. These deferrals do not block completion of conceptual Step 8 or authorize invented defaults.

## Steps 9–10 evaluation-data and logging privacy

Approval: decisions.md STEP9-002 and STEP10-001. Human-reviewed synthetic cases and human-written edges can seed evals. Reviewed/anonymized real interactions and production failures are future dataset sources only when authorized and appropriate under resolved privacy/consent/deployment policies. Step 9 does not approve real-student operation or treat model-generated labels as ground truth.

### Step 10 logging and telemetry privacy

Production logs default to operational metadata: message/session/trace or correlation identifiers, content length, state/status transition, model/provider identifier where appropriate, latency, error category, and retry/recovery information. Identifiers and metadata remain subject to authorized access and privacy rules; metadata-first is not public-by-default.

Do not log raw student messages, raw model responses, complete prompts/context, retrieved chunk contents, secrets/tokens, or unnecessary PII by default. Existing prohibitions on secret disclosure remain in force. Protected application data may retain content under its approved data model/policies; logs should locate interactions without unnecessarily duplicating sensitive content. Apply the same privacy boundary to traces and other telemetry; model/provider identifiers in internal diagnostics do not make them public API fields.

Operational observability and behavioral evals may be correlated without widening access, overriding retention/consent, or exporting unrestricted records to models/judges. Exact telemetry access, sampling, retention, redaction mechanisms, and export destinations remain unresolved before dependent implementation/deployment. No logging exception, production compliance approval, or new secret-management infrastructure is selected.

## Slice 1 approved demo authentication

Approval: decisions.md SLICE1-001 (2026-10-06). For synthetic/local MVP only, opaque bearer credentials map server-side to existing users. Credentials are provisioned outside the student-message endpoint; no login, registration, password management, OAuth, or token issuance is included. Client identity fields are never authoritative. Production authentication remains deferred. This resolves the earlier mechanism deferral only for this controlled-demo slice.

The implementation stores only credential digests in server-side configuration and looks up the mapped existing active user. Enrollment and explicit student-to-assignment eligibility are separate checks; class/group allocation remains deferred. Existing 404/403, replay authorization, and privacy rules remain in force.

## Demo data, logging, and deferred policy

MVP uses synthetic/demo student data, not approved real-minor production records. Demo data remains until an approved intentional reset/deletion process; no production retention schedule is implied. Synthetic operation is not permission for careless logging or unrestricted data sharing. Do not persist unnecessary sensitive/raw data for observability.

TODO / UNRESOLVED: production authentication/credential/session mechanism beyond Slice 1 demo mapping; additional role/relationship lifecycle permissions; production privacy, consent, retention, deletion, provider-sharing, audit, secrets/key-management policies; age-specific behavior; accessibility in demo and production; future training/fine-tuning use. Teacher feedback does not automatically retrain models. These must be approved before dependent implementation/use; no defaults are implied.

## Slice 2a execution authorization — SLICE2A-001

Recheck enabled account, active enrollment, eligible/consistent coursework, and closure at claim, renewal, and completion. NORMAL CLOSED permits previously admitted work; ADMINISTRATIVE/UNKNOWN CLOSED, disabled accounts, or revoked enrollment prevent further processing/completion and cancel unfinished work through trusted services. Unknown reasons fail closed. Revocation/closure writers coordinate user → session → authorization rows → message → job locks; output committed before revocation remains history. No model or client can supply cancellation authority.

No new student-facing explicit retry endpoint in Slice 2a. Future eligibility is restricted to known transient provider/infrastructure failures under current authorization, ACTIVE session, retry budgets and rate limits; invalid output, authorization, policy, invalid-request and unknown failures are excluded. Read-only POST replay stays 200 for FAILED. GET status authorizes each read and never exposes claims, internal failures, or unauthorized cancellation state.

## Offline tutor evaluation v1 — OFFLINE-EVAL-001

Approval: decisions.md OFFLINE-EVAL-001. Only the fixed human-reviewed synthetic fixtures may be sent; no real student inputs/database extraction path. Provider storage is explicitly disabled (`store=false`); this is not a claim about all provider retention. Credentials stay in environment/transport headers, outside prompts/artifacts. A fixed HTTPS OpenAI endpoint rejects redirects. No tools or external-action authority exists. Output is untrusted: shape checks do not establish semantic safety and replies never enter student records or delivery.

Local ignored `artifacts/` may hold synthetic supplied context, replies, expectations, metadata and human review. This is a narrowly scoped offline evidence artifact, not a production raw-content logging exception. Provider error payloads/headers and secrets are not persisted or printed. Paid execution is a separate explicit command and must remain unrun until requested. Local timeouts do not guarantee cancellation at the provider.

### Local offline evaluation option — OFFLINE-EVAL-003

The local CLI sends only the fixed synthetic fixtures, never requests API keys, and has no paid/hosted inference path. It owns an Ollama server with `OLLAMA_NO_CLOUD=1`, `OLLAMA_HOST=127.0.0.1:11435`, one parallel request and one loaded model. It refuses an occupied port and requires startup-log confirmation of cloud disabling and loopback binding before contacting the server. Transport fixes the loopback destination, disables environment HTTP proxies and rejects redirects; no tools or endpoint override exists. Preflight rejects model/quantization/tokenizer mismatch, remote model metadata, extra model system text or stored messages, and absent support for disabling thinking. Model download is a separate, explicitly internet-dependent setup step, never triggered by inference.

Temporary server logs are used internally to verify controls, never copied to evidence, and closed on exit; model error bodies and thinking traces are not printed or persisted in evidence. Synthetic final replies, metadata and pending reviews remain in new ignored artifacts only. Native Ollama chat has no OpenAI `store` parameter; each request supplies its complete context without server conversation identifiers or application persistence. Local runtime caches/normal installation files are not a claim of zero disk writes. A disconnected-internet test remains required evidence: a CLI flag records operator attestation only, never automatic verification. Local-only configuration is not itself proof of network disconnection.
