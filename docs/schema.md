# AI Tutor --- MVP Database Schema Contract

**Status:** Approved\
**Version:** MVP v1\
**Database:** PostgreSQL\
**Data Access:** SQLAlchemy\
**Migrations:** Alembic\
**Vector Search:** pgvector\
**Operating Context:** Controlled demonstration with synthetic/demo
student data

------------------------------------------------------------------------

## 1. Purpose

This document defines the approved conceptual relational schema for AI
Tutor MVP v1.

It translates the approved product requirements and architecture into
persistent entities, relationships, authority boundaries, history
guarantees, constraints, and access patterns.

This is a schema contract, not a complete migration file. Exact SQL
types, ORM syntax, migration implementation, and provider-specific
vector dimensions may be selected during implementation only where this
contract permits them.

------------------------------------------------------------------------

## 2. Schema Principles

The schema must preserve these invariants:

-   student attempts are historical records and must not be overwritten;
-   mastery evidence is historical evidence and must not be silently
    overwritten;
-   AI-generated mastery evidence is distinct from authoritative mastery
    state;
-   student messages/attempts must be persistable before model or
    retrieval processing succeeds;
-   teacher escalations have an explicit lifecycle;
-   curriculum provenance and version information must be preserved;
-   long-term state belongs in PostgreSQL, not in the LLM context
    window;
-   relationships must enforce ownership and authorization boundaries
    where practical;
-   normalized relational design is preferred until demonstrated access
    patterns justify denormalization;
-   vector search supplements relational data; it does not replace
    relational authority.

------------------------------------------------------------------------

## 3. Identity Model

### users

Represents standalone application identities.

Conceptual fields:

-   `id` --- primary key
-   `role` --- approved application role
-   `display_name`
-   `email` or equivalent login identifier where required by the later
    security contract
-   `is_active`
-   `created_at`
-   `updated_at`

MVP roles must support at least:

-   `STUDENT`
-   `TEACHER`

Administrative roles may be added only if required by an approved
security or operational contract.

Authentication credential storage and exact identity fields belong in
`security.md`.

Client-supplied identity must not override authenticated identity.

------------------------------------------------------------------------

## 4. Student and Teacher Profiles

### student_profiles

Represents student-specific application data.

Conceptual fields:

-   `user_id` --- PK/FK to `users.id`
-   demo/student metadata required by approved features
-   `created_at`
-   `updated_at`

### teacher_profiles

Represents teacher-specific application data.

Conceptual fields:

-   `user_id` --- PK/FK to `users.id`
-   teacher metadata required by approved features
-   `created_at`
-   `updated_at`

The user role and profile relationship must be internally consistent.

MVP uses synthetic/demo identities.

------------------------------------------------------------------------

## 5. Course Structure

### courses

Represents a course.

Conceptual fields:

-   `id` --- primary key
-   `name`
-   `grade_level`
-   `subject`
-   `created_at`
-   `updated_at`

For the initial MVP domain, the relevant course is Grade 7 Mathematics.

### units

Represents a unit within a course.

Conceptual fields:

-   `id` --- primary key
-   `course_id` --- FK to `courses.id`
-   `name`
-   `sequence_order`
-   `created_at`
-   `updated_at`

Constraint:

-   a unit belongs to exactly one course.

MVP initially operates on one approved Grade 7 Mathematics unit.

### lessons

Represents an instructional lesson.

Conceptual fields:

-   `id` --- primary key
-   `unit_id` --- FK to `units.id`
-   `name`
-   `sequence_order`
-   `created_at`
-   `updated_at`

Constraint:

-   a lesson belongs to exactly one unit for MVP v1.

------------------------------------------------------------------------

## 6. Learning Objectives

### learning_objectives

Represents a curriculum learning objective or skill.

Conceptual fields:

-   `id` --- primary key
-   `course_id` --- FK to `courses.id`
-   `code` --- curriculum/objective identifier where available
-   `title`
-   `description`
-   `created_at`
-   `updated_at`

Learning objectives belong to a course and may appear in multiple
lessons or problems.

### lesson_learning_objectives

Junction table between lessons and learning objectives.

Conceptual fields:

-   `lesson_id` --- FK
-   `learning_objective_id` --- FK
-   optional `sequence_order`

Recommended primary key:

-   composite (`lesson_id`, `learning_objective_id`)

This prevents duplicate lesson/objective associations.

------------------------------------------------------------------------

## 7. Learning Objective Prerequisites

### learning_objective_prerequisites

Represents directed prerequisite relationships.

Conceptual fields:

-   `learning_objective_id` --- the objective being learned
-   `prerequisite_learning_objective_id` --- required prior objective
-   optional provenance/relationship metadata
-   `created_at`

Recommended primary key:

-   composite (`learning_objective_id`,
    `prerequisite_learning_objective_id`)

Constraints should prevent:

-   an objective from directly being its own prerequisite;
-   duplicate prerequisite edges.

The intended conceptual structure is a prerequisite graph/DAG.

Cycle detection may require application validation because ordinary
relational constraints alone may not conveniently enforce global
acyclicity.

------------------------------------------------------------------------

## 8. Course Enrollment and Teacher Assignment

### enrollments

Connects students to courses.

Conceptual fields:

-   `id` --- primary key
-   `student_user_id` --- FK to student identity
-   `course_id` --- FK
-   `status`
-   `created_at`
-   `updated_at`

Constraint:

-   unique active student/course enrollment where appropriate.

### teacher_course_assignments

Connects teachers to courses they are authorized to teach/review.

Conceptual fields:

-   `teacher_user_id` --- FK
-   `course_id` --- FK
-   `created_at`

Recommended primary key:

-   composite (`teacher_user_id`, `course_id`)

For MVP v1, teacher access to student tutoring records/review items must
be constrained through approved course relationships and later security
policy.

Exact permission rules belong in `security.md`.

------------------------------------------------------------------------

### Coursework eligibility relationship

Enrollment is not assignment eligibility. The backend must determine that the specific assignment/problem has been assigned/released to this student. Preserve a conceptual relationship between student eligibility and coursework, separate from course membership. Slice 1 resolves individual eligibility through explicit student-assignment records (§31.5); class/group allocation remains deferred. API-created MVP sessions require eligible assignment/problem context; optional conceptual fields do not permit open-topic tutoring.

## 9. Assignments and Problems

### assignments

Represents assigned work.

Conceptual fields:

-   `id` --- primary key
-   `course_id` --- FK
-   optional `unit_id` --- FK where applicable
-   optional `lesson_id` --- FK where applicable
-   `title`
-   `description`
-   `created_at`
-   `updated_at`

### problems

Represents an individual problem/question.

Conceptual fields:

-   `id` --- primary key
-   `course_id` --- FK
-   optional `lesson_id` --- FK
-   `prompt`
-   optional approved solution/reference metadata
-   `created_at`
-   `updated_at`

The exact representation of solutions, rubrics, or answer keys belongs
in later curriculum/runtime contracts and must not expose restricted
answer material indiscriminately to students.

### assignment_problems

Junction between assignments and problems.

Conceptual fields:

-   `assignment_id` --- FK
-   `problem_id` --- FK
-   `sequence_order`

Recommended primary key:

-   composite (`assignment_id`, `problem_id`)

### problem_learning_objectives

Junction between problems and learning objectives.

Conceptual fields:

-   `problem_id` --- FK
-   `learning_objective_id` --- FK

Recommended primary key:

-   composite (`problem_id`, `learning_objective_id`)

------------------------------------------------------------------------

## 10. Coaching Sessions

### coaching_sessions

Represents a tutoring interaction/session.

Conceptual fields:

-   `id` --- primary key
-   `student_user_id` --- FK
-   `course_id` --- FK
-   optional `assignment_id` --- FK
-   optional `problem_id` --- FK
-   optional `primary_learning_objective_id` --- FK
-   `status`
-   `started_at`
-   optional `ended_at`
-   `created_at`
-   `updated_at`

Approved ordinary student closure is ACTIVE → CLOSED. Closure prevents new work; previously admitted PENDING/PROCESSING work may finish under NORMAL closure with current authorization; SLICE2A-001 requires cancellation for administrative/unknown closure. A FAILED message in CLOSED cannot begin explicit retry, while authorized historical replay remains available without processing. No additional session states/transitions or expiration duration are selected. Start New atomically closes the old ACTIVE session and creates a new ACTIVE session; either both succeed or neither does.

A coaching session belongs to one student.

The student must be authorized for the relevant course/context.

------------------------------------------------------------------------

## 11. Messages

### messages

Represents persisted conversational messages.

Conceptual fields:

-   `id` --- primary key
-   `session_id` --- FK to `coaching_sessions.id`
-   `author_type` --- student, tutor/system-visible assistant, or other
    approved type
-   `content`
-   `created_at`
-   optional metadata needed for tracing/versioning

Messages are historical records.

Student messages must be persisted before downstream model/retrieval
processing when the request flow requires AI processing.

This guarantees that a model timeout or retrieval failure does not erase
the student's submitted interaction.

Messages should not be edited in place to rewrite interaction history.
If correction/redaction behavior is later required, it must preserve an
auditable history appropriate to the approved privacy policy.

Recommended access index:

-   (`session_id`, `created_at`)

------------------------------------------------------------------------

### Message processing and correlation

Student input and tutor response are separate persisted messages. The tutor response is traceable to its source student message; public identifiers are `student_message_id` and `tutor_message_id`. Student processing metadata uses PENDING → PROCESSING → COMPLETED or FAILED, with CANCELLED added by SLICE2A-001; metadata may change without rewriting historical content.

Only one active run owns a message. Stale processing must be detectable/recoverable; competing runs cannot create competing responses or duplicate effects. Conceptual processing state, recovery metadata, and response correlation are required. STEP5-001-A1 selects a separate PostgreSQL-backed worker; committed student messages and processing state remain the durable work source. That deployment decision alone selected no physical schema; SLICE2A-001 and §31.6 now approve the job table, constraints, indexes, and migration. GET polling reads durable state/results without creating work. New-session context may reference authorized prior records without moving or rewriting their original session/message provenance. Session states remain ACTIVE/CLOSED; SLICE2A-001 extends message states to PENDING/PROCESSING/COMPLETED/FAILED/CANCELLED.

## 12. Student Attempts

### student_attempts

Represents a student's attempt at a problem or reasoning step.

Conceptual fields:

-   `id` --- primary key
-   `student_user_id` --- FK
-   `session_id` --- FK
-   `problem_id` --- FK where applicable
-   optional `learning_objective_id` --- FK
-   `attempt_content`
-   optional structured answer/reasoning metadata
-   `created_at`
-   optional idempotency/reference metadata

Student attempts are **append-only learning history**.

A new attempt must create a new record rather than overwrite an earlier
attempt.

Corrections or later attempts must not destroy the previous evidence.

Recommended indexes include:

-   (`student_user_id`, `problem_id`, `created_at` DESC)
-   (`session_id`, `created_at`)

------------------------------------------------------------------------

### Attempt source and deduplication

Every input is a Message; not every input is a StudentAttempt. Create an attempt only for actual coursework problem-solving/reasoning. Each attempt must be traceable to its source student message. Retry/recovery reuses an existing logical attempt rather than inserting a duplicate. Exact classification mechanics remain for the runtime contract; the source message is committed before AI processing regardless of later classification.

## 13. Points of Confusion

### points_of_confusion

Represents a suspected or identified POC associated with a tutoring
session.

Conceptual fields:

-   `id` --- primary key
-   `session_id` --- FK
-   optional `learning_objective_id` --- FK
-   optional `prerequisite_learning_objective_id` --- FK
-   `description`
-   `status` --- suspected/confirmed/resolved concepts as later approved
-   optional `confidence`
-   `identified_by` --- AI, teacher, or other approved source
-   `created_at`
-   optional `resolved_at`

POCs should preserve diagnostic history where useful.

If a diagnosis changes, implementation should avoid silently rewriting
historical evidence in a way that makes previous tutoring decisions
impossible to reconstruct.

Exact confidence semantics and status transitions belong in
`ai-runtime.md`.

------------------------------------------------------------------------

### Original prediction and teacher determination

Never overwrite the original AI POC prediction. Preserve separately attributed teacher feedback/determination and its relationship to the prediction reviewed. Categories are CORRECT / PARTLY_CORRECT / INCORRECT. Suggested teacher focus is a supported recommendation, not authoritative diagnosis. Physical feedback/history representation is not selected. Feedback does not automatically train the model.

## 14. Mastery Evidence

### mastery_evidence

Represents evidence relevant to a student's understanding of a learning
objective.

Conceptual fields:

-   `id` --- primary key
-   `student_user_id` --- FK
-   `learning_objective_id` --- FK
-   optional `session_id` --- FK
-   optional `attempt_id` --- FK
-   `source_type` --- AI, teacher, transfer task, assessment, or other
    approved source
-   `evidence_type`
-   `evidence_payload` or structured evidence representation
-   optional `confidence`
-   `created_at`
-   optional model/runtime provenance when AI-generated

Mastery evidence is **append-only evidence history**.

Contradictory evidence must be preserved.

An AI-generated evidence record must not itself update authoritative
mastery state.

Recommended index:

-   (`student_user_id`, `learning_objective_id`, `created_at` DESC)

------------------------------------------------------------------------

### Evidence correlation and estimated progress

Learning/mastery evidence remains attributable to the interaction/message/attempt that produced it. It is append-only; contradictory evidence is preserved. Retry/recovery must not duplicate the same logical evidence.

Application-estimated progress is BUILDING / DEVELOPING / STRONG, based on accumulated correctness, independence, explanation, and transfer evidence. These are not `mastery_records.status` values. Model confidence is not progress/mastery. Approved curriculum/teacher-defined objectives supply learning targets; the product owns the consistent rubric. Calibrated thresholds and physical progress representation remain deferred.

## 15. Authoritative Mastery Record

### mastery_records

Represents the separately maintained authoritative/current mastery state
for a student and learning objective.

Conceptual fields:

-   `id` --- primary key
-   `student_user_id` --- FK
-   `learning_objective_id` --- FK
-   `status`
-   optional `determined_by_user_id` --- FK to authorized human identity
-   optional `basis_summary`
-   `created_at`
-   `updated_at`

Constraint:

-   unique (`student_user_id`, `learning_objective_id`)

Authority rule:

**The AI may create `mastery_evidence`; it may not directly create or
modify authoritative mastery state unless a future explicitly approved
policy changes this boundary.**

For MVP v1, changes to authoritative mastery must occur through an
approved human/authoritative application workflow.

The exact mastery statuses and criteria remain unresolved.

------------------------------------------------------------------------

### Mandatory authoritative history

Every authoritative mastery change must preserve previous decision/state, new decision/state, actor/authority, timestamp, and relevant provenance. Efficient current-state reads must coexist with historically traceable changes. Optional `determined_by_user_id` does not waive authority attribution: the approved human/authoritative process must be identifiable. Current-state `updated_at` alone is insufficient. The exact physical history-table/versioning design and official status vocabulary/transition graph remain deferred.

## 16. Teacher Escalations

### escalations

Represents a tutoring case requiring human review.

Conceptual fields:

-   `id` --- primary key
-   `session_id` --- FK
-   `student_user_id` --- FK
-   `course_id` --- FK
-   optional `learning_objective_id` --- FK
-   optional `point_of_confusion_id` --- FK
-   `reason`
-   `context_summary`
-   `status`
-   optional `assigned_teacher_user_id` --- FK
-   `created_at`
-   optional `review_started_at`
-   optional `resolved_at`
-   optional `resolution_summary`

Approved MVP lifecycle:

``` text
OPEN
  ↓
IN_REVIEW
  ↓
RESOLVED
```

The schema may preserve timestamps and reviewer identity for lifecycle
transitions.

Approved teacher feedback separately preserves the original AI prediction and teacher determination as described in §13. Remaining actions after review, additional transitions, and session resumption after escalation remain deferred; the ordinary closure rules in §10 are settled.

Recommended indexes:

-   (`status`, `created_at`)
-   (`assigned_teacher_user_id`, `status`, `created_at`) where
    assignment is used
-   (`student_user_id`, `created_at`)

------------------------------------------------------------------------

## 17. Curriculum Documents

### curriculum_documents

Represents an approved curriculum source/document.

Conceptual fields:

-   `id` --- primary key
-   `course_id` --- FK
-   optional `unit_id` --- FK
-   optional `lesson_id` --- FK
-   `title`
-   `source_name`
-   `source_reference` or equivalent provenance identifier
-   `version`
-   optional `license_or_permission_metadata`
-   `content_hash` where useful
-   `is_active`
-   `created_at`
-   `updated_at`

Curriculum provenance/versioning must be preserved so the system can
identify what approved material supported tutoring behavior.

The exact Grade 7 Mathematics curriculum source remains unresolved.

------------------------------------------------------------------------

## 18. Curriculum Chunks

### curriculum_chunks

Represents retrieval units derived from approved curriculum documents.

Conceptual fields:

-   `id` --- primary key
-   `document_id` --- FK to `curriculum_documents.id`
-   optional `lesson_id` --- FK
-   optional `learning_objective_id` --- FK
-   `chunk_index`
-   `content`
-   `embedding`
-   `embedding_model`
-   optional `embedding_version`
-   `created_at`

Constraint:

-   unique (`document_id`, `chunk_index`) where chunking version
    semantics permit.

The embedding column uses pgvector.

**The vector dimension must not be hardcoded in this contract before the
embedding model is approved.**

Implementation must resolve the embedding model and compatible vector
dimension before creating the concrete vector column/migration.

If re-embedding strategies require multiple active embedding
representations, that requires an explicit schema/architecture decision
rather than silent mutation.

------------------------------------------------------------------------

## 19. Curriculum/Objectives Association

Where a curriculum chunk supports multiple learning objectives,
implementation may require an explicit junction such as:

### curriculum_chunk_learning_objectives

-   `chunk_id` --- FK
-   `learning_objective_id` --- FK

Recommended primary key:

-   composite (`chunk_id`, `learning_objective_id`)

Whether this junction is required depends on the approved
ingestion/retrieval design.

Do not duplicate objective metadata into chunks solely for convenience
without evaluating access patterns and consistency.

------------------------------------------------------------------------

## 20. Idempotency

Duplicate-prone write endpoints should support idempotent behavior where
the API contract requires it.

The database may include an idempotency record or scoped unique
idempotency keys.

Conceptually:

### idempotency_records

Potential fields:

-   `id`
-   authenticated actor/scope
-   `idempotency_key`
-   operation/endpoint scope
-   request fingerprint where appropriate
-   result/reference metadata
-   `created_at`
-   optional expiration metadata

Exact idempotency storage should be finalized with `api-contract.md`.

The schema must not invent endpoint-specific semantics before that
contract exists.

------------------------------------------------------------------------

### Approved operation and action semantics

User-operation key scope is authenticated student + operation + idempotency key. A new logical send gets a new key; a replay of the same send reuses it. Same key/same payload identifies one student message and returns its current PENDING, PROCESSING, COMPLETED result, or FAILED state without initiating processing. Same key/different payload returns 409 and preserves the original. Valid authorized replay remains possible after session closure. Explicit retry processes the same FAILED message only while the session permits new work.

System durable-action idempotency is distinct: automatic/explicit retries, recovery, and concurrency reuse a successful logically identical effect instead of duplicating escalation, evidence, POC, attempt, or other durable writes. Exact physical storage and retention/expiration remain unresolved.

## 21. Write Guarantees and Transaction Boundaries

Student-submitted history should survive downstream AI failures.

Conceptual request ordering:

``` text
Receive student input
      ↓
Validate/authenticate/authorize
      ↓
Persist student message/attempt
      ↓
Commit durable student history
      ↓
Perform retrieval/model processing
      ↓
Validate AI result
      ↓
Persist resulting tutor message/state/evidence/escalation
```

This means the student's submission is not required to roll back merely
because an external model or retrieval operation fails afterward.

Operations that represent one logical state transition should be atomic
where partial persistence would create invalid state.

Examples may include:

-   creating an escalation together with required lifecycle/context
    references;
-   creating a mastery record update together with required
    human-authority metadata;
-   creating related records that must exist together to satisfy
    constraints.

Exact endpoint transaction boundaries must be synchronized with
`api-contract.md`.

Do not hold long-running database transactions open across external
LLM/network calls unless an explicitly approved design requires it.

------------------------------------------------------------------------

## 22. History Preservation

The following data is historical and must not be silently overwritten:

-   student attempts;
-   mastery evidence;
-   conversational messages;
-   significant POC diagnostic history where required to reconstruct
    tutoring behavior;
-   escalation lifecycle/review history to the extent required by the
    approved workflow.

Mutable "current state" records such as a session status or
authoritative mastery record may be updated only according to approved
authority and lifecycle rules.

Authoritative mastery history and original AI POC plus separate teacher determination are mandatory under §§13–15. Other audit requirements remain deferred. No physical event/history-table design is approved merely by requiring historical traceability.

------------------------------------------------------------------------

## 23. Deletion and Retention

MVP v1 uses synthetic/demo data.

Approved demo behavior:

-   demo records remain until intentionally reset or deleted through an
    approved administrative/development process;
-   no automatic production-style retention schedule is assumed;
-   a future deliberate demo-reset capability may clear/reseed demo
    data.

Production retention, deletion, consent, and real-student privacy
requirements remain unresolved.

The absence of a production retention policy must not be interpreted as
approval for indefinite retention of real student data.

------------------------------------------------------------------------

## 24. Accessibility and Age Policy

Accessibility requirements remain unresolved for both demonstration and
production contexts.

Student age-specific tutoring policy also remains unresolved.

The schema must not encode assumptions that make those future policies
unnecessarily difficult to implement.

Synthetic/demo student records do not resolve age-related product
policy.

------------------------------------------------------------------------

## 25. Normalization

MVP schema should begin normalized.

Use relational entities and junction tables to represent true
relationships rather than embedding duplicated copies of authoritative
data across tables.

Denormalization should require:

1.  a demonstrated access/performance need,
2.  an explicit source of truth,
3.  a synchronization strategy,
4.  human approval when it changes the schema contract materially.

------------------------------------------------------------------------

## 26. Indexing Strategy

Indexes should be driven by known access patterns.

Initial likely access patterns include:

-   messages for a session ordered by time;
-   attempts for a student/problem ordered newest-first;
-   evidence for a student/objective ordered newest-first;
-   open/in-review escalations for a teacher/course;
-   curriculum chunks filtered by course/unit/lesson/objective and
    searched by vector similarity;
-   current mastery record for a student/objective;
-   prerequisite lookup for an objective.

Primary keys and foreign keys should be indexed according to PostgreSQL
behavior and query requirements.

Do not create speculative indexes without an expected access pattern.

Indexes improve reads but add storage and write cost.

------------------------------------------------------------------------

## 27. Foreign Key and Integrity Policy

Foreign keys should enforce valid relational references for core domain
records.

Use appropriate:

-   `NOT NULL`,
-   `UNIQUE`,
-   `CHECK`,
-   foreign-key constraints,
-   composite uniqueness,
-   transactional invariants.

Deletion behavior (`RESTRICT`, `CASCADE`, soft-delete, etc.) must be
selected deliberately per relationship and synchronized with
retention/privacy requirements.

Because production deletion policy is unresolved, implementation must
not casually adopt broad cascading deletion of learning history.

------------------------------------------------------------------------

## 28. Time and Ordering

Persistent event/history records should include reliable creation
timestamps.

Application logic should not assume timestamp uniqueness.

Where strict ordering is required, stable identifiers or explicit
sequence/order fields should be used in addition to timestamps.

All persisted timestamps should use a consistent timezone-aware
representation.

------------------------------------------------------------------------

## 29. Provenance

AI and curriculum-derived records should preserve enough provenance to
support evaluation and debugging.

Potential provenance may include:

-   curriculum document/version;
-   chunk identifiers;
-   model identifier;
-   model/runtime version;
-   prompt/runtime configuration version;
-   source type;
-   trace identifier.

Exact provenance fields belong partly in `ai-runtime.md` and `evals.md`.

Do not persist unnecessary sensitive/raw data merely for observability.

------------------------------------------------------------------------

## 30. Schema Authority Boundaries

### AI may propose or create through authorized backend workflows:

-   student-facing tutor responses;
-   suspected POCs;
-   mastery evidence;
-   escalation recommendations;
-   approved tool actions.

### AI may not directly:

-   modify arbitrary database records;
-   change official mastery;
-   change grades;
-   bypass teacher/course ownership;
-   delete learning history;
-   alter curriculum authority/provenance;
-   execute raw SQL.

All AI-originated persistence must pass deterministic application
validation and authorization.

------------------------------------------------------------------------

## 31. Conceptual Relationship Map

``` text
User
 ├── StudentProfile
 └── TeacherProfile

Student ──< Enrollment >── Course ──< TeacherCourseAssignment >── Teacher

Course
 └── Unit
      └── Lesson
           └──< LessonLearningObjective >── LearningObjective
                                             │
                                             └──< ObjectivePrerequisite >── LearningObjective

Course
 └── Assignment
      └──< AssignmentProblem >── Problem
                                  └──< ProblemLearningObjective >── LearningObjective

Student
 └── CoachingSession
      ├── Message
      ├── StudentAttempt ──> Problem
      ├── PointOfConfusion ──> LearningObjective
      ├── MasteryEvidence ──> LearningObjective
      └── Escalation

Student ──< MasteryRecord >── LearningObjective

Course / Unit / Lesson
 └── CurriculumDocument
      └── CurriculumChunk
           └── pgvector embedding
```

------------------------------------------------------------------------

## 31.1 Step 5 durable-flow invariants

Approval: `decisions.md` STEP5-002 and STEP5-003. This section adds conceptual guarantees, not physical tables/columns or locking designs.

Only the currently valid processing owner may finalize a student message. Once ownership transfers, stale former owners cannot commit competing final results. Stale/dead ownership must be detectable and recoverable; a PROCESSING label alone does not prove liveness. SLICE2A-001 now specifies leases/timestamps/tokens/locks for this slice; see §31.6 and ai-runtime.md.

Recovery resumes/restarts from the last durable committed state. Uncommitted model output is non-authoritative and need not be reconstructed. Preserve correlation to committed message/attempt/evidence/tool effects; reuse a successful logical side effect on retry/recovery and permit retry of an unsuccessful/uncommitted effect only under approved rules. Do not interpret an overall failed turn as proof that every tool write failed.

Student-visible tutor output must already exist durably with logically coupled state/evidence committed as appropriate. A lost HTTP response does not erase committed output or justify another logical send. User-operation replay and system-action deduplication remain distinct (§20).

Teacher UI Yes / Partly / No maps to CORRECT / PARTLY_CORRECT / INCORRECT and preserves separate attributed determination linked to the original AI prediction (§13). ProgressService consumes accumulated validated evidence; it does not replace the authoritative human mastery workflow. No physical history/feedback/progress design is selected.

## 31.2 Steps 6–7 persistence implications

Approval: decisions.md STEP6-001 and STEP7-001. PostgreSQL + pgvector remains the MVP store. Prefer measured query/index/access-pattern improvements before replica, partitioning, or sharding designs; none of those future mechanisms is selected here. Metadata/authorization filtering continues to constrain vector retrieval. Embedding model/dimension and exact vector-index configuration remain deferred.

A required database operation that fails before commit has no durable result. Roll back logically coupled writes; withhold final tutor output if its required commit fails. Recover from the last successful commit using §31.1 ownership and durable-effect rules. A failed write of FAILED metadata cannot itself be claimed durable; recovery must use the actual committed state. This applies existing commit semantics and does not add a processing state or select a recovery mechanism.

Steps 6–7 add no entity, field, relationship, migration, retention change, or physical scaling topology. Append-only attempts/evidence, human mastery authority/history, and original AI prediction/teacher-feedback separation remain unchanged.

## 31.3 Step 8 security implications

Approval: decisions.md STEP8-001 and STEP8-002; enforcement rules are in security.md. Existing identity/profile, enrollment, teacher-course, session/resource, and assignment-eligibility relationships remain the authorization basis. Client/model identity values cannot redefine the authenticated actor or authorize access to a different student. Idempotency cannot enable cross-user replay; recovery cannot bypass authorization or valid-owner finalization.

Step 8 selects no new fields, tables, credential storage, row-security mechanism, secret store, retention schedule, or migration. Student data remains private by default, with minimized model/public/log disclosure. Human mastery history and append-only AI evidence retain their existing authority boundaries. Deployment-specific age/consent/educational-record/provider-handling/compliance decisions remain unresolved before dependent real-world use; demo retention behavior is unchanged.

## 31.4 Steps 9–10 diagnosis and provenance implications

Approval: decisions.md STEP9-001 and STEP10-001. Existing curriculum prerequisite relationships (§7) provide explicit edges for foundational-blocker selection; the model must not invent them. Preserve multiple supported POCs and original AI predictions/evidence rather than forcing exactly one or overwriting history.

SPECIFIC_POC, NO_POC, and INSUFFICIENT_EVIDENCE are diagnosis outcomes, not newly approved values of points_of_confusion.status, coaching_sessions.status, Message processing state, or official mastery. Bounded insufficient diagnosis must be recorded as insufficient/unknown with relevant work incomplete and visible through normal student/work status. TODO / UNRESOLVED: exact persistence and read representation for diagnosis outcomes, current intervention target, and incomplete-work visibility before dependent implementation. No new table/column/state or migration is selected here.

Extend §29's conceptual provenance to relevant model, prompt, retrieval, and eval dataset versions on important AI-system records/traces/eval runs where practical. Support interaction trace/correlation IDs without treating them as identity, authorization, or replacements for idempotency keys. Exact storage/version representation remains deferred. Protected application content follows existing data policies; metadata-first logging does not delete or rewrite student attempts, evidence, POCs, or mastery history.

## 31.5 Slice 1 approved physical persistence

Approval: decisions.md SLICE1-002. Use UUID identifiers, persisted message processing status, and explicit student-to-assignment eligibility records. The minimal schema supports existing users, courses, enrollments, assignments, problems, assignment/problem membership, eligibility, coaching sessions, messages, and idempotency records. Do not create AI/evidence/mastery tables for this slice.

Student messages preserve content exactly and begin PENDING. Student/tutor authors remain distinct. Idempotency records reference the logical student message and enforce UNIQUE(student_id, operation, idempotency_key). For this endpoint compare content only, not session ID or HTTP/JSON serialization. Retain records for the controlled-demo lifetime. Message plus idempotency association commit atomically, with PostgreSQL as authoritative duplicate protection.

Implementation mapping: student_assignment_eligibility has composite student/assignment PK; messages have processing_status and nullable trace_id; idempotency_records use the approved unique scope and a message FK (content is compared with the referenced message, avoiding duplicated text). Existing required relationships use non-null FKs and no cascading history deletion. UUIDs use application-generated UUID4; timestamps are timezone-aware. Check constraints represent existing roles/session/processing states. A partial unique enrollment index enforces one ACTIVE enrollment per student/course without prohibiting inactive history. No processing ownership, AI tables, curriculum vectors, or production retention design is selected.

A per-student transaction row lock serializes competing sends across sessions; session and authorization relationship locks protect admission until commit. The unique idempotency constraint independently rejects duplicate scopes. This is an implementation of approved atomicity, not an AI ownership/recovery design. New initial migration requires no backfill; downgrade is destructive and only intended for disposable development databases.

Earlier UUID, idempotency storage, and allocation deferrals are resolved for this slice only; future class/group allocation and unrelated physical schema decisions remain deferred.

## 31.6 Slice 2a approved physical processing contract

Approval: decisions.md SLICE2A-001. This supersedes the physical worker deferrals in §11/§31.1 for this slice. messages.processing_status is the only status; jobs have no status column. Message states are PENDING / PROCESSING / COMPLETED / FAILED / CANCELLED. Session states remain ACTIVE / CLOSED.

### Columns and constraints

coaching_sessions adds next_message_sequence BIGINT NOT NULL DEFAULT 1, positive; closure_reason VARCHAR(24) NULL DEFAULT NULL. ACTIVE requires NULL; CLOSED requires NORMAL, ADMINISTRATIVE, or UNKNOWN. Existing CLOSED sessions backfill UNKNOWN without inferring completion from ended_at.

messages adds session_sequence BIGINT NULL DEFAULT NULL and in_reply_to_message_id UUID NULL DEFAULT NULL. Students require positive sequence and no reply target; tutors require no sequence, a student reply target in the same session, and COMPLETED status. UNIQUE(session_id, session_sequence), UNIQUE(id, session_id), UNIQUE(in_reply_to_message_id), and restrictive composite reply FK (in_reply_to_message_id, session_id) → messages(id, session_id). Partial UNIQUE(session_id) for student PROCESSING prevents competing processing rows. Message identity/content/provenance is immutable and messages cannot be deleted through ordinary DML.

message_processing_jobs columns (all timestamps TIMESTAMPTZ):

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| message_id | UUID PK, restrictive FK messages.id | No | none |
| attempt_count | INTEGER | No | 0 |
| cycle_attempt_count | INTEGER | No | 0 |
| max_attempts | INTEGER | No | 2 |
| retry_generation | INTEGER | No | 0 |
| claim_token | UUID | Yes | NULL |
| worker_instance_id | UUID | Yes | NULL |
| claimed_at | TIMESTAMPTZ | Yes | NULL |
| lease_expires_at | TIMESTAMPTZ | Yes | NULL |
| attempt_deadline_at | TIMESTAMPTZ | Yes | NULL |
| next_attempt_at | TIMESTAMPTZ | Yes | clock_timestamp() |
| last_error_code | VARCHAR(64) | Yes | NULL |
| last_error_at | TIMESTAMPTZ | Yes | NULL |
| cancel_reason | VARCHAR(32) | Yes | NULL |
| finished_at | TIMESTAMPTZ | Yes | NULL |
| created_at | TIMESTAMPTZ | No | clock_timestamp() |
| updated_at | TIMESTAMPTZ | No | clock_timestamp(); application updates on mutation |

Checks: attempt_count >= cycle_attempt_count >= 0; max_attempts >= 1; cycle_attempt_count <= max_attempts; retry_generation >= 0. Error code/time are both NULL or both populated. Error vocabulary: MODEL_TIMEOUT, MODEL_UNAVAILABLE, MODEL_RATE_LIMITED, MODEL_INVALID_OUTPUT, MODEL_CONFIGURATION, POLICY_REJECTED, PROCESSING_ERROR, LEASE_EXPIRED, DATABASE_FAILURE. Cancellation vocabulary: ACCOUNT_DISABLED, ENROLLMENT_REVOKED, COURSEWORK_INELIGIBLE, SESSION_ADMIN_CLOSED, SESSION_CLOSURE_UNKNOWN. No raw exception/content storage in jobs.

Exactly one job per student message, none per tutor; deferred constraint triggers check final transaction state, including message/job changes and tutor-response relationships:

| Status | Required committed job/result shape |
| --- | --- |
| PENDING | next_attempt_at present; token, worker ID, claim timestamp, lease, deadline, cancellation, finished_at NULL; no response |
| PROCESSING | token, worker ID, claim timestamp, lease and deadline present; claimed_at < lease_expires_at <= attempt_deadline_at; next_attempt_at, cancellation, finished_at NULL; no response |
| COMPLETED | exactly one correlated tutor response; winning token and finished_at present; lease/deadline/scheduling/cancellation NULL |
| FAILED | error code/time and finished_at present; lease/deadline/scheduling/cancellation NULL; no response |
| CANCELLED | cancel_reason and finished_at present; token/lease/deadline/scheduling NULL; no response |

Prior error metadata may survive retries; terminal claim metadata may remain except cancelled tokens. It never defines a second status. Cross-table checks lock the source message to serialize consistency validation. Runtime services must still follow user → session → authorization rows → message → job lock order, reauthorize, and fence claims. Triggers do not implement claims, retries, cancellation services, or new admission automatically.

Allowed student transitions: initial PENDING; PENDING → PROCESSING/CANCELLED; PROCESSING → PENDING/COMPLETED/FAILED/CANCELLED; FAILED → PROCESSING/CANCELLED. COMPLETED/CANCELLED are terminal. Same-state updates preserve permitted metadata; user content/provenance cannot change. Future explicit retry increments retry_generation and resets cycle_attempt_count, not lifetime attempt_count.

Indexes: (session_id, session_sequence) on unresolved student PENDING/PROCESSING/FAILED; unique PROCESSING session; jobs(next_attempt_at, message_id) WHERE next_attempt_at IS NOT NULL; jobs(lease_expires_at, message_id) WHERE lease_expires_at IS NOT NULL. Existing session/created index remains.

### Migration and deployment boundary

Revision 0002 requires a maintenance window: stop admission and workers, back up, then migrate transactionally with source-table locks. Reject existing non-PENDING or tutor messages and inconsistent legacy idempotency relationships; do not fabricate processing history. Backfill per-session student sequence by (created_at, id), set counters to max+1, and create one job per input. Only ACTIVE, enabled STUDENT accounts with active enrollment and consistent eligible coursework stay PENDING. Unknown CLOSED, disabled accounts, revoked enrollment, or ineligible coursework become CANCELLED with controlled reason; preserve content and idempotency.

Validate every backfilled message before committing. Failure rolls back DDL and data together. Downgrade is deliberately restricted to an empty messages table; populated databases require coordinated backup restore or a reviewed forward migration rather than destroying processing/provenance data.

Stage 1 did not update admission. Stage 2 now allocates the session sequence and atomically creates message + job + key + counter update in the existing service-owned transaction; replay performs none of those writes. Old admission remains incompatible with 0002 and must not be mixed with it. Slice 1 FAILED/CLOSED test setup now supplies valid coupled metadata and closure reasons without relaxing production constraints or public assertions. These stages are accepted for continued development only, not deployment.

## 32. Unresolved Schema Decisions

The following remain unresolved and must not be silently invented during
implementation:

-   primary-key representation outside the approved Slice 1 UUID design;
-   production authentication fields beyond Slice 1 server-configured credential mapping;
-   exact initial curriculum source;
-   exact first Grade 7 Mathematics unit;
-   exact objective codes/content;
-   exact embedding model and vector dimension;
-   exact chunking/versioning strategy;
-   exact mastery statuses and official mastery criteria;
-   exact POC status/confidence semantics;
-   additional coaching-session states/transitions beyond approved ACTIVE → CLOSED;
-   exact escalation actions after review and session resume behavior;
-   idempotency details outside Slice 1 storage, content comparison, 200 replay, and demo-lifetime retention;
-   physical durable tool-action mechanisms beyond approved Slice 2a processing ownership/recovery;
-   exact physical mastery-history and teacher-feedback representation;
-   class/group coursework allocation beyond approved Slice 1 explicit individual eligibility;
-   exact production deletion/retention behavior;
-   exact production audit requirements;
-   exact accessibility-related persisted preferences/data;
-   exact age-policy-related persisted fields;
-   enum implementation outside the approved Slice 2a VARCHAR/check constraints;
-   exact cascade/restrict/soft-delete behavior where downstream policy
    is required.

These items may be resolved in later contracts before dependent
migrations are implemented.

------------------------------------------------------------------------

## 33. Schema Change Policy

Schema changes require review against:

-   `requirements.md`,
-   `architecture.md`,
-   `api-contract.md`,
-   `ai-runtime.md`,
-   `security.md`,
-   `evals.md`,
-   applicable approved decisions.

Codex may propose schema changes but must not independently approve
product, authority, privacy, or major data-model decisions.

Schema changes should use Alembic migrations and follow the repository's
`schema-change` skill.

No application code or migration should silently redefine this contract.
