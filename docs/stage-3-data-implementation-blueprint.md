# AI Tutor Stage 3 DATA — Implementation Blueprint

**Status:** Approved architecture synchronized; Migration 0003 implementation authored. PostgreSQL integration verification is pending because no disposable database is available. The migration has not been applied to a database, and runtime authorization/tenant routing remain unimplemented.

**Implementation evidence:** SQLAlchemy Core models, Alembic revision `0003`, and PostgreSQL integration tests are present. Ruff, syntax parsing, Alembic offline DDL compilation, metadata table ordering, and test collection passed. No database-backed test or migration application has run.

## 1. Purpose and boundaries

Stage 3 adds organization and tenant boundaries, reusable curriculum ownership, and later student learning evidence, interpretations, learning-state history, and learning briefs. It extends the existing FastAPI / SQLAlchemy Core / PostgreSQL / Alembic application. Existing admission, idempotency, session sequencing, asynchronous processing, and worker recovery remain intact.

Learning evidence is an observation; interpretation is a separately attributed conclusion; human review/correction is separately recorded; and learning state is an authorized, traceable, append-only instructional record. AI evidence or interpretation alone never becomes authoritative learning state. Learning state and briefs are not official mastery. Historical messages are not automatically converted to learning evidence.

This blueprint reconciles the current project-owner instruction identifying Decisions 80–86 and DATA-10/DATA-11 as approved. The checked-out `docs/decisions.md` does not contain those numbered entries or their full text. This document records only the approved outcomes explicitly restated by the project owner here; it does not reconstruct missing options, role names, or transition semantics.

## 2. Approved architecture invariants

- Organizations own reusable curriculum. Tenants are separate workspaces/security boundaries; one organization may own multiple tenants. A tenant belongs to exactly one organization. No implicit parent/child or cross-tenant access is granted.
- Users remain global identities and may have memberships in multiple tenants and organizations. Membership roles are scoped to their respective organization or tenant. Organization curriculum permissions are distinct from tenant access and tenant administration.
- Curriculum libraries may be system, personal, or organization owned. Personal libraries belong to a global user; organization libraries belong to an organization. Tenant offerings are operational records and are not curriculum templates.
- Shared curriculum is adopted by reference at a specific immutable source record/version. An intentional customization creates an immutable organization-owned derivative with provenance to the exact source. Adoption does not silently copy, mutate, or subscribe to future source changes.
- Organization-owned curriculum may be reused across that organization's tenants. Reusable organization-owned course templates and tenant-specific course offerings are separate records.
- Cross-organization evidence contribution is explicit and scoped. Contribution does not transfer evidence ownership or grant general access to the student's tenant records. Source organizations do not gain student access merely by owning curriculum used by a tenant.
- Evidence and interpretation are distinct. Interpretations retain original creator attribution. A correction is a new linked record; it never overwrites the original interpretation.
- Learning state retains immutable history, exact objective version, and authorized source provenance. AI-generated evidence/interpretation alone cannot change authoritative learning state.
- Database constraints enforce relational integrity. Application authorization checks authenticated identity, active membership, role/capability, selected tenant, and resource access. UUID knowledge is not authorization.
- Historical learning and provenance records are preserved; membership revocation does not erase attribution.

## 3. Ownership and authorization model

### 3.1 Organizations and tenants

`organizations` own organization curriculum and organization-scoped memberships/permissions. `tenants` represent workspace/security boundaries and reference one organization. Tenant selection in a request is a selector only. The authenticated global user must have an active membership in the selected tenant, and each resource/action is authorized within that tenant. Organization membership or curriculum permission does not grant tenant student-data access. Tenant membership, including an administrator role, does not grant organization curriculum editing unless an explicit organization permission also grants it.

Parents, tutoring centers, private schools, and other organizations are represented as separate organizations and/or tenants according to which party owns curriculum and which workspace contains student records. The approved no-inheritance rule applies: an organizational relationship alone does not expose another tenant's records. A person can have separate memberships in multiple organizations/tenants.

### 3.2 Membership and permission records

Use distinct, auditable records for `tenant_memberships`, `tenant_membership_roles`, `organization_memberships`, `organization_membership_roles`, and `organization_curriculum_permissions`. Membership and role grants have stable IDs, grantor/creator attribution, creation/effective timestamps, and revocation/deactivation timestamps; do not delete prior grant history. Role/capability values must come from the approved Decisions 80–86 vocabulary. The current checkout does not contain the vocabulary, so the migration stores opaque non-empty role/capability codes and seeds none. It does not enforce the approved vocabulary or implement authorization; those code-level checks must use the recovered approved values before grants are used.

Organization membership is not itself curriculum permission. The organization permission relation identifies the organization, member, capability, grantor, and effective/revoked interval. Tenant roles and organization roles are separate namespaces. Application authorization checks that grants are active; FKs establish identity and scope, not current authorization.

### 3.3 Composite ownership rules

Use unique composite parent keys where a child must prove common scope, for example `(tenant_id, organization_id)` on tenants and `(organization_id, library_id)` on organization libraries. Membership-dependent records include tenant/organization and user keys where practical. A normal FK cannot prove a membership is active; active status and role/capability remain authorization checks. FKs to users, organizations, tenants, and provenance records use `RESTRICT`, not cascading deletion.

## 4. Curriculum ownership, adoption, and offerings

### 4.1 Libraries

A curriculum library has an owner kind `SYSTEM`, `PERSONAL`, or `ORGANIZATION`, with exactly one compatible owner: no owner FK for system scope, `owner_user_id` for personal scope, or `owner_organization_id` for organization scope. A check constraint prevents mixed/missing owners. Personal-library access is limited to its owner and explicitly authorized application operations. Organization-library access is controlled by organization curriculum permissions. Tenant membership does not grant library edit permission.

### 4.2 Curriculum records and hierarchy

`curriculum_courses` are reusable templates owned through a curriculum library. `curriculum_units` belong to a template course; `curriculum_lessons` belong to a unit. Their stable UUIDs, content, ownership, and creation provenance are immutable after publication. A content change creates a new immutable record/version and preserves links to the preceding/source version where applicable. Objectives remain reusable logical instructional targets; course associations are optional many-to-many relationships, not objective ownership.

Existing physical `courses` are operational course offerings, not reusable curriculum templates. Preserve that table and its existing IDs/FKs. Add an optional reference from an offering to a reusable `curriculum_courses` record. Assignments, problems, enrollments, eligibility, sessions, messages, idempotency, and processing jobs continue to use the existing offering/course path until tenant-aware application code is implemented.

### 4.3 Shared adoption and derivatives

A tenant adopts shared curriculum by reference to an exact immutable source record/version. The adoption record preserves source owner, source record/version, adopting tenant, actor, and time. Adoption neither changes source ownership nor grants student-record visibility to the source owner. New source versions do not silently change an existing tenant's selected version.

An intentional organization customization creates a new immutable record/version in an organization-owned library and a typed derivation/provenance link to the exact source owner, record/version, actor, and time. Do not edit the shared source or represent provenance as an unvalidated `(table_name, UUID)` pair. Source snapshots/versions and derivative records remain available for audit even if an adoption is retired.

Tenant-specific offerings reference the selected organization template/version but retain tenant-specific delivery identity and lifecycle. Enrollment and coursework remain attached to the offering. Template reuse does not merge tenants or student data.

### 4.4 Provenance supporting relations

Use typed FK relations for adoption/derivation of curriculum record types rather than polymorphic IDs. Add exact source identity and exact version/snapshot identifiers, `adopting_tenant_id` where the consumer is a tenant, actor, timestamp, and status/retirement data only where required by the approved contract. Prevent duplicate active adoption of the same exact source within the same tenant with a partial unique index. A derivative relation points from the new immutable organization-owned record to its exact source. Adoption by reference and derivation are different relations.

## 5. Learning objectives and curriculum mappings

Objectives have stable logical identities and immutable versions. An objective can exist independently of a course and be reused by many courses. Optional `course_learning_objectives` is a many-to-many mapping. `problem_learning_objectives` binds a problem and objective/version only when their course/tenant context is compatible; composite FKs should prove that relation rather than requiring a course owner on the objective.

Concepts, objectives, and standards are separate reusable entities with stable identities and immutable versions. System-owned records have no organization owner; organization-owned records have one. Version rows inherit owner scope from the identity. Version-specific objective/concept mappings support `PRIMARY`, `SUPPORTING`, and `RELATED`; objective/standard mappings and prerequisites reference exact versions. A stable logical objective identity groups its versions. Current-version pointers must reference a version belonging to that same identity. Do not add a business rule limiting primary mapping cardinality unless present in the approved source contract.

## 6. Evidence, source snapshots, and cross-organization contribution

`learning_evidence` is an append-only observation with tenant, student, observation/recording times, source/observer attribution, evidence type, assistance context, and producer provenance where applicable. Evidence is not a conclusion. `evidence_source_registry` identifies the stable source record; `evidence_source_versions` stores immutable content snapshots/hashes and capture provenance; `evidence_sources` links evidence to both the registry identity and exact snapshot. Source identity and snapshot/version are separate concepts.

Typed source FKs and composite constraints/validation bind the evidence, source, snapshot, tenant, student, and appropriate session/problem context. A source version must belong to the selected source registry entry. Do not use a polymorphic source table/ID. Keep source snapshots minimal under the existing privacy contract. Existing messages remain eligible source records; no historical message-to-evidence backfill is authorized by this schema plan.

Cross-organization evidence contribution is recorded as an explicit, scoped contribution/reference with originating tenant/student ownership and source provenance. It does not copy ownership, confer general organization or student access, or bypass tenant authorization. The requesting/receiving context must be authorized by the approved contribution relation; access to the underlying evidence remains subject to explicit scope checks. This capability is not part of Migration 0003; its supporting evidence relations belong to the later evidence migration.

## 7. Interpretations and corrections

`learning_interpretations` is separate from evidence and learning state. It retains the original creator identity, responsible organization, timestamp, content, evidence links, evidence type, and model/runtime provenance where applicable. Creator attribution is immutable. Do not conflate model authorship, human review, and state authorization.

A correction creates a new interpretation/correction record linked to the original via a typed `interpretation_corrections` relation, with correcting record, corrected record, actor, time, and correction provenance. Both interpretation records remain immutable; the correction relation does not overwrite content or reassign original authorship. This relation records correction provenance only and does not create review statuses, approvals, interpretation versioning, or automatic learning-state transitions.

Human review actions, including any authorization to change state, are separately attributed and auditable. Exact review-transition rules and learning-state semantics remain governed by their approved product contract; this blueprint does not invent transition names or infer that every correction changes state.

## 8. Learning-state history and briefs

A current instructional state is unique per `(tenant_id, student_user_id, logical_objective_id)` and points to an exact objective version. Each change appends an immutable history row with revision, state snapshot, exact objective version, timestamp, and authorized source references. A current-row update and history insert occur in one transaction under a row lock and expected-revision check; a unique constraint handles first creation races, and stale writes fail instead of silently overwriting.

History references evidence, interpretations, and the separately recorded human review/authorization or authorized import that caused the state update. `AUTHORIZED_IMPORT` records include importing actor, authorization/source reference, import event identifier, timestamp, and source snapshot/provenance. A database constraint/trigger prevents update/delete of historical state and verifies source identity/scope. Composite FKs bind history and source to the same tenant, student, logical objective, and exact objective version where applicable. Prior current/history versions are retained. AI evidence or interpretation without the separately authorized operation cannot update state.

Learning briefs are immutable, versioned instructional snapshots per tenant/student/logical objective. Each records exact objective version, generation provenance, and evidence/interpretation references. Read visibility is enforced by application authorization using the student's tenant and approved student/teacher relationships; possession of a brief ID is not authorization. A brief is not official mastery. Expiration, retention, and any additional reader group are not expanded beyond the approved privacy/product contracts.

Objective-standard and prerequisite relationships are version-specific. Preserve their history through immutable objective versions or append-only mapping records with exact provenance; do not mutate historical curriculum relationships in place.

## 9. Relational inventory and integrity

### Core Stage 3 learning records (later migrations, not Migration 0003)

1. `learning_concepts` and `learning_concept_versions`.
2. `learning_objectives` and `learning_objective_versions`.
3. `learning_standards` and `learning_standard_versions`.
4. Versioned objective/concept, objective/standard, course/objective, problem/objective, and prerequisite relations.
5. `learning_evidence`, objective links, source registry, source snapshots, evidence/source links, and explicit cross-organization contribution relations.
6. `learning_interpretations`, interpretation/evidence links, and linked interpretation corrections.
7. `student_learning_states`, immutable state history, evidence/interpretation/review/import provenance links.
8. `learning_briefs` and immutable evidence/interpretation source links.

### Organization and curriculum foundation — Migration 0003 plan

Migration 0003 introduces organizations, tenants, tenant memberships/roles, organization memberships/roles, organization curriculum permissions, curriculum libraries, reusable curriculum courses, units, and lessons. It also introduces typed curriculum adoption/derivation support needed for approved ownership/provenance. Existing `courses` remains the operational tenant offering table and gains only compatibility-safe optional references/scope needed to link new offerings; no existing application write path is enabled or changed by the migration alone.

### Keys, checks, and indexes

- UUID primary keys; `TIMESTAMPTZ` for effective, audit, and provenance times; explicit created/updated fields only where mutability is approved.
- Unique composite parent keys for all composite FKs, including tenant/organization, tenant/user membership, library owner/scope, curriculum parent/child, stable identity/version, state/source scope, and source identity/snapshot.
- Check constraints enforce owner-kind/owner-FK consistency, valid temporal ordering, positive sequence/version numbers, permitted evidence/assistance fields, and same-row shape rules.
- Partial unique indexes enforce one active membership for a given tenant/user and one active grant/adoption for its scoped principal/resource. Historical revoked/deactivated rows remain.
- Lookup indexes begin with tenant/scope and then common parent or time keys: memberships by `(tenant_id,user_id)`, org roles by `(organization_id,user_id)`, library/course hierarchy by owner/library/parent, adoption by tenant/source, and later evidence/state/brief queries by `(tenant_id,student_user_id,objective_id,observed_at)`.
- `RESTRICT` is the default for ownership, membership, curriculum, provenance, evidence, interpretation, and learning-history FKs. Do not cascade-delete historical records.
- FKs and checks enforce structural sameness; application checks enforce active memberships and permission policy. Use narrowly scoped PostgreSQL triggers only for cross-row or immutable-history invariants a declarative constraint cannot express.

## 10. Tenant consistency and authorization matrix

| Data | Owner/scope | Required integrity and access rule |
|---|---|---|
| Organization curriculum | System, personal user, or organization library | Owner-kind check and owner FK; organization capability for organization writes; personal owner for private library; tenant membership alone gives no edit right. |
| Shared curriculum adoption | Adopting tenant references exact source version | Typed source FK, tenant FK, actor/time; exact source retained; no inherited student access. |
| Course offering and coursework | Tenant-specific offering; assignments/problems follow offering | Preserve current FK path; later composite tenant/course FKs and tenant-scoped authorization; no template/offering conflation. |
| Evidence and source snapshots | Originating tenant/student | Composite tenant/student/source/version FKs; contribution relation grants only approved scoped access. |
| Interpretation/correction | Tenant/student plus responsible organization | Immutable creator attribution; linked correction retains both records; tenant authorization remains independent of source curriculum owner. |
| Learning state/history | Tenant/student/logical objective | One current state; append-only history; same-scope evidence/interpretation and human authorization/import provenance. |
| Learning brief | Tenant/student/logical objective | Exact objective/source versions; authorized student/teacher view only; ID is not access. |

## 11. Existing implementation and compatibility findings

- `ai_tutor/models.py` is SQLAlchemy Core `MetaData`; current `users.role` is constrained to `STUDENT`/`TEACHER`. Existing `courses` is the course used by enrollment, assignments, problems, and sessions.
- `ai_tutor/repository.py` authorizes a student-owned session, active enrollment, and assignment/problem/course consistency. `ai_tutor/service.py` owns the transaction and atomically persists message, processing job, and idempotency record. Preserve this flow.
- `migrations/env.py` uses `models.metadata` as Alembic `target_metadata`. The source-controlled chain is `0001_message_admission` → `0002_async_message_processing`; deployed database revision is not verified.
- `0002` has message/job integrity checks, immutable message-history protections, deferred consistency triggers, indexes for due/expiring work, and a populated-history downgrade refusal. It performs locks and validates legacy message rows.
- Existing tests use isolated PostgreSQL schemas, Alembic upgrades, metadata parity, admission/idempotency, message/job deferred invariants, worker claim/recovery/fencing, concurrency, and rollback behavior. Preserve them as regression evidence; do not use `metadata.create_all()` to stand in for Alembic.

No production connection or live database inspection is part of this plan. Existing rows have no tenant/org scope. Do not assume their owner mapping.

## 12. Migration 0003 plan — organization and curriculum foundation

### 12.1 SQLAlchemy Core metadata models — IMPLEMENTED, database-unverified

Core `Table` definitions are implemented in `ai_tutor/models.py`, preserving the current metadata naming conventions:

1. `organizations`: UUID PK, non-empty name, active flag, and creation time.
2. `tenants`: UUID PK, organization FK `RESTRICT`, non-empty name, active flag, creation time; unique `(organization_id,id)` for composite scope FKs.
3. `tenant_memberships`: UUID PK, tenant/user FKs `RESTRICT`, created/activated/deactivated/grantor fields; unique scope key `(tenant_id,id,user_id)` and partial unique active `(tenant_id,user_id)`.
4. `tenant_membership_roles`: UUID PK, membership FK, approved `role_code`, grant/revoke times and grantor; partial unique active `(membership_id,role_code)`; role-code catalog/value is taken from the approved source, not invented here.
5. `organization_memberships`: UUID PK, organization/user FKs `RESTRICT`, lifecycle and creator fields; partial unique active `(organization_id,user_id)`.
6. `organization_membership_roles`: UUID PK, organization-membership FK, approved organization `role_code`, grant/revoke times and grantor; scoped active unique index.
7. `organization_curriculum_permissions`: UUID PK, composite organization/organization-membership FK, opaque capability code, grant/revoke times and grantor; scoped active unique index. This does not grant tenant student access.
8. `curriculum_libraries`: UUID PK, owner kind, nullable owner user/org FK, display metadata and time; check enforces exactly the appropriate owner. System library has neither owner FK.
9. `curriculum_courses`: UUID PK, library FK, immutable template fields/provenance and time; unique `(library_id,id)` for children and adoption references.
10. `curriculum_units`: UUID PK, course FK, immutable unit content/order/provenance; unique `(course_id,id)`; indexes by course and sequence/order.
11. `curriculum_lessons`: UUID PK, unit FK, immutable lesson content/order/provenance; unique `(unit_id,id)`; indexes by unit and sequence/order.
12. Typed supporting relations: `tenant_curriculum_course_adoptions` references a tenant and the exact immutable course/library row, with adopting user/time and retirement history; `curriculum_course_derivations`, `curriculum_unit_derivations`, and `curriculum_lesson_derivations` reference exact typed source and target rows, with actor/time. No polymorphic source ID. Adoption is a reference; derivation is a separately owned immutable record. The immutable source row ID identifies the selected content version in this foundation.

Role and capability columns are opaque non-empty strings because their approved vocabulary was not recoverable during preflight. No values are seeded, and no authorization path may treat arbitrary stored codes as approved. The vocabulary must be recovered before role grants become operational; this is a documentation traceability gap, not a request to reconsider the approved architecture.

### 12.2 Compatibility bridge to current coursework — IMPLEMENTED, database-unverified

Keep physical `courses` as the operational offering table. Add nullable `tenant_id → tenants.id` and nullable `curriculum_course_adoption_id`. Add `tenant_curriculum_course_adoptions` with unique `(tenant_id,id)` and use a composite FK from `(courses.tenant_id,courses.curriculum_course_adoption_id)` to that adoption key. Each adoption points to the exact `curriculum_course_id` and source library; an active partial unique index prevents duplicate active adoption while retaining retired adoption rows. Both columns may remain NULL together for legacy rows; a row check requires either both NULL or both populated. Preserve existing course UUIDs and child FKs. Do not rename or repurpose `courses`.

Add these columns without defaults, initially nullable, and install FKs as `NOT VALID` before a separate validation step; this avoids treating old NULL rows as tenant-owned and allows a controlled lock/validation window. Do not backfill them without the reviewed mapping. Do not add `NOT NULL` or tenant composite FKs to assignments, problems, enrollments, eligibility, sessions, messages, or idempotency in 0003. Those require a later tenant-aware app/data migration. Old runtime writes continue to create legacy-compatible offerings and preserve current behavior until that application slice is deployed.

### 12.3 Migration operation order

1. Confirm actual Alembic head and backup/restore plan in the target non-production environment; do not assume source files equal deployed state.
2. Create `organizations`, then `tenants` with organization FK and composite unique key.
3. Create tenant memberships and tenant role grants; create organization memberships and organization role grants; create separate organization curriculum permission records.
4. Create curriculum libraries with owner-kind checks; create template courses, then units, then lessons.
5. Create typed adoption/derivation support after its source parent tables exist; include exact source identity/version and actor/time provenance.
6. Add nullable `courses.tenant_id` and `courses.curriculum_course_adoption_id` compatibility fields and indexes/FKs without rewriting old rows. If a lock review shows these column operations exceed the safe migration window, split the compatibility bridge into a subsequent migration while retaining 0003's new tables.
7. Install only integrity triggers required for immutable curriculum/adoption history; no application authorization is implied by trigger presence.
8. Downgrade may remove the new foundation only when it is empty. If populated, fail closed and require a separately reviewed export/restore procedure; never cascade-delete curriculum provenance or memberships.

### 12.4 Constraint inventory

- PK for each entity; `RESTRICT` FKs to global users, organizations, tenants, libraries, and curriculum parents.
- Unique `(organization_id,id)` on tenants; membership scope keys; `(library_id,id)` on curriculum courses; `(course_id,id)` on units; `(unit_id,id)` on lessons.
- Owner-kind check for system/personal/organization libraries; status and temporal ordering checks; role/capability code columns reject empty strings; approved-vocabulary enforcement remains pending source recovery; no duplicate active scoped membership, role, permission, or adoption.
- Derivation/adoption FKs preserve exact typed source and target. Composite ownership keys prevent mismatched organization/library/tenant references.
- Index tenant memberships by tenant/user and user/tenant; organization membership and permissions by organization/user; tenants by organization; curriculum hierarchy by parent/order; adoptions by tenant/source; existing `courses` compatibility FKs by tenant/template.

## 13. Later migration ordering and integrity scope

After 0003 and after tenant-aware application authorization is implemented, subsequent migrations can add/reconcile tenant scope on assignments, problems, enrollments, eligibility, assignment/problem links, sessions, messages, and idempotency references. Use a reviewed row-level ownership manifest; add composite parent unique keys and `NOT VALID`/validated FKs where suitable; validate before tightening nullability. Preserve user-scoped idempotency `(student_id,operation,key)`, message sequences, reply-session FK, message/job deferred triggers, and all worker recovery indexes/constraints. Do not change the job-to-message one-to-one relationship or worker lock order.

Then add stable curriculum identities/versions and mapping/adoption provenance; source registry and immutable snapshots; evidence/contribution links; attributed interpretations/corrections; learning state/history and source authorization; and briefs. Keep objective and standard mappings version-specific and historical. Do not backfill evidence from messages. Do not activate tenant-scoped writes until authorization and constraints are deployed together.

## 14. Testing and rollout strategy

Migration 0003 was verified against a private, disposable PostgreSQL 14.19 cluster on the development host. Docker was installed but its daemon socket was inaccessible; the local cluster was therefore initialized under `/tmp/ai-tutor-0003-pg`, configured to reject TCP connections, and exposed only through `/tmp/ai-tutor-0003-socket`. It used no production URL or credentials and was removed after verification. The test fixture continued to create and drop its own randomly named schemas inside the dedicated `ai_tutor_migration_0003_test` database.

From an empty schema, migrations 0001, 0002, and 0003 applied successfully; the recorded revision was `0003`. The resulting schema contained 26 application tables, matching all 26 SQLAlchemy metadata tables, with no extra or missing tables and zero Alembic metadata differences. PostgreSQL reported 144 constraints and 22 non-internal triggers. The empty-schema downgrade to base and re-upgrade roundtrip passed. A populated-0002 upgrade preserved a legacy operational course plus a pending message, its sequence, processing job, and idempotency record. The downgrade guard rejected removal when Stage 3 data existed and retained the records and revision.

The requested PostgreSQL integration and regression selection passed: 213 tests covering curriculum foundation, migration parity/roundtrip and preservation, message admission, idempotency, session sequencing, polling, asynchronous processing, and worker recovery. These tests also exercised tenant/organization ownership, memberships and opaque role grants, library ownership, curriculum hierarchy, shared adoption, derivation provenance, immutable course/unit/lesson and adoption records, tenant offering integrity, and concurrent adoption retirement versus offering creation. The adoption validation locks the selected source row while checking its active status, so concurrent retirement and creation serialize instead of allowing an offering to slip through after retirement. Runtime authorization remains deferred and was not tested or implemented.

To reproduce the same local-only setup with Homebrew PostgreSQL 14, substitute a unique empty temporary directory and database name if either is already in use. Do not put a production URL in `TEST_DATABASE_URL` or `DATABASE_URL`.

```sh
mkdir -p /tmp/ai-tutor-0003-pg /tmp/ai-tutor-0003-socket
initdb -D /tmp/ai-tutor-0003-pg --auth-local=trust --auth-host=reject
pg_ctl -D /tmp/ai-tutor-0003-pg -l /tmp/ai-tutor-0003-pg/server.log \
  -o "-h '' -k /tmp/ai-tutor-0003-socket" start
createdb -h /tmp/ai-tutor-0003-socket -p 5432 ai_tutor_migration_0003_test
TEST_DATABASE_URL="postgresql+psycopg://$(id -un)@/ai_tutor_migration_0003_test?host=/tmp/ai-tutor-0003-socket" \
  .venv/bin/pytest -q tests/test_curriculum_foundation.py tests/test_migration.py \
  tests/test_messages.py tests/test_processing_schema.py tests/test_polling.py \
  tests/test_async_lifecycle.py tests/test_worker.py
dropdb -h /tmp/ai-tutor-0003-socket -p 5432 ai_tutor_migration_0003_test
pg_ctl -D /tmp/ai-tutor-0003-pg stop -m fast
rm -rf /tmp/ai-tutor-0003-pg /tmp/ai-tutor-0003-socket
```

Repository test discovery collected 334 tests after this milestone's test additions, compared with 327 tests collected from the previous Git baseline. All baseline test modules remain discoverable; the only additional module is `tests/test_curriculum_foundation.py`. There were no collection errors or test-configuration changes. The earlier six-test figure came from targeted collection of only the new foundation and migration tests, not from full repository discovery.

The added tests exercise one organization with multiple tenants, a user in multiple tenants, invalid membership scope, role/permission separation, membership history, personal/org/system library owner shape, shared reference adoption, immutable derivative provenance, and tenant offering/template separation. Authorization decisions remain application responsibilities and are not implemented by these schema tests.

For later migrations add tests for source identity vs snapshot version, same tenant/student/context integrity, cross-organization contribution scope, interpretation creator and linked correction immutability, state provenance/history including authorized import, concurrent state revisions, immutable briefs, source cardinality as specified by the approved contract, and no AI-only authoritative state changes.

No model evaluation or paid model call is required for these relational migration tests.

## 15. Deferred behavior and implementation gates

- Migration 0003 creates schema foundations only. It does not add endpoints, change authentication, tenant routing, app authorization, message admission, worker behavior, or student-visible functionality.
- Tenant-aware authorization and operational row backfill are a later coordinated application/schema slice. Existing rows must not be assigned to invented tenants.
- Cross-organization contribution execution and read paths are later evidence-layer work; Migration 0003 grants no student-data access.
- Official mastery, automatic mastery transitions, automatic interpretation-to-state transitions, real-student import, external curriculum synchronization, and privacy/retention changes remain governed by their existing contracts and are not introduced here.
- Review transition semantics and state vocabulary are not invented by this blueprint. Learning-state writes require the already approved authorization/provenance contract.

## 16. Documentation reconciliation and remaining risks

The prior blueprint incorrectly listed already-approved choices as unresolved: separate organization and tenant scopes/roles; personal curriculum ownership; reference adoption; immutable organization-owned derivatives; organization templates versus tenant offerings; explicit cross-organization evidence contributions; source identity versus source snapshots; interpretation creator attribution/correction links; and authorized learning-state history. Those are now recorded as settled architecture invariants above, not approval questions.

The checked-out approval log lacks the full text of Decisions 80–86 and DATA-10/DATA-11. The current project-owner instruction is the approval evidence used for this synchronization. Preserve that traceability limitation; do not invent individual decision titles, exact role codes, review transitions, or state semantics.

Migration 0003 is authored from the approved architecture. Before applying it, verify the actual database revision, obtain the approved role/capability vocabulary from its authoritative record, review nullable-column lock cost on a populated non-production clone, and produce a deterministic legacy ownership mapping before any backfill or `NOT NULL` enforcement. No production database may be used for this preparation.
