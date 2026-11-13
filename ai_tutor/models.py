"""SQLAlchemy Core metadata; processing services are implemented in later stages."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData(
    naming_convention={
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
    }
)


def identifier(name="id", target=None, primary_key=False, ondelete=None):
    args = [ForeignKey(target, ondelete=ondelete)] if target else []
    return Column(name, UUID(as_uuid=True), *args, primary_key=primary_key, nullable=False)


def created():
    return Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now())


users = Table(
    "users",
    metadata,
    identifier(primary_key=True),
    Column("role", String(16), nullable=False),
    Column("display_name", Text, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    created(),
    CheckConstraint("role IN ('STUDENT', 'TEACHER')", name="role"),
)

organizations = Table(
    "organizations",
    metadata,
    identifier(primary_key=True),
    Column("name", Text, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    created(),
    CheckConstraint("length(name) > 0", name="name_nonempty"),
)
tenants = Table(
    "tenants",
    metadata,
    identifier(primary_key=True),
    identifier("organization_id", "organizations.id", ondelete="RESTRICT"),
    Column("name", Text, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    created(),
    UniqueConstraint("organization_id", "id", name="uq_tenants_organization_id"),
    CheckConstraint("length(name) > 0", name="name_nonempty"),
)
Index("ix_tenants_organization", tenants.c.organization_id)
tenant_memberships = Table(
    "tenant_memberships",
    metadata,
    identifier(primary_key=True),
    identifier("tenant_id", "tenants.id", ondelete="RESTRICT"),
    identifier("user_id", "users.id", ondelete="RESTRICT"),
    identifier("created_by_user_id", "users.id", ondelete="RESTRICT"),
    Column("activated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("deactivated_at", DateTime(timezone=True)),
    created(),
    UniqueConstraint("tenant_id", "id", name="uq_tenant_memberships_tenant_id"),
    UniqueConstraint("tenant_id", "id", "user_id", name="uq_tenant_memberships_tenant_id_user"),
    CheckConstraint(
        "deactivated_at IS NULL OR deactivated_at >= activated_at", name="membership_dates"
    ),
)
Index(
    "uq_tenant_memberships_active",
    tenant_memberships.c.tenant_id,
    tenant_memberships.c.user_id,
    unique=True,
    postgresql_where=tenant_memberships.c.deactivated_at.is_(None),
)
Index("ix_tenant_memberships_user", tenant_memberships.c.user_id, tenant_memberships.c.tenant_id)
tenant_membership_roles = Table(
    "tenant_membership_roles",
    metadata,
    identifier(primary_key=True),
    identifier("tenant_id", "tenants.id", ondelete="RESTRICT"),
    identifier("tenant_membership_id"),
    Column("role_code", Text, nullable=False),
    identifier("granted_by_user_id", "users.id", ondelete="RESTRICT"),
    Column("granted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("revoked_at", DateTime(timezone=True)),
    UniqueConstraint("tenant_id", "id", name="uq_tenant_membership_roles_scope"),
    ForeignKeyConstraint(
        ["tenant_id", "tenant_membership_id"],
        ["tenant_memberships.tenant_id", "tenant_memberships.id"],
        name="fk_tenant_membership_roles_membership_scope",
        ondelete="RESTRICT",
    ),
    CheckConstraint("length(role_code) > 0", name="role_code_nonempty"),
    CheckConstraint("revoked_at IS NULL OR revoked_at >= granted_at", name="role_dates"),
)
Index(
    "uq_tenant_membership_roles_active",
    tenant_membership_roles.c.tenant_membership_id,
    tenant_membership_roles.c.role_code,
    unique=True,
    postgresql_where=tenant_membership_roles.c.revoked_at.is_(None),
)
Index(
    "ix_tenant_membership_roles_scope",
    tenant_membership_roles.c.tenant_id,
    tenant_membership_roles.c.tenant_membership_id,
)
organization_memberships = Table(
    "organization_memberships",
    metadata,
    identifier(primary_key=True),
    identifier("organization_id", "organizations.id", ondelete="RESTRICT"),
    identifier("user_id", "users.id", ondelete="RESTRICT"),
    identifier("created_by_user_id", "users.id", ondelete="RESTRICT"),
    Column("activated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("deactivated_at", DateTime(timezone=True)),
    created(),
    UniqueConstraint("organization_id", "id", name="uq_organization_memberships_scope"),
    CheckConstraint(
        "deactivated_at IS NULL OR deactivated_at >= activated_at", name="membership_dates"
    ),
)
Index(
    "uq_organization_memberships_active",
    organization_memberships.c.organization_id,
    organization_memberships.c.user_id,
    unique=True,
    postgresql_where=organization_memberships.c.deactivated_at.is_(None),
)
Index(
    "ix_organization_memberships_user",
    organization_memberships.c.user_id,
    organization_memberships.c.organization_id,
)
organization_membership_roles = Table(
    "organization_membership_roles",
    metadata,
    identifier(primary_key=True),
    identifier("organization_id", "organizations.id", ondelete="RESTRICT"),
    identifier("organization_membership_id"),
    Column("role_code", Text, nullable=False),
    identifier("granted_by_user_id", "users.id", ondelete="RESTRICT"),
    Column("granted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("revoked_at", DateTime(timezone=True)),
    UniqueConstraint("organization_id", "id", name="uq_organization_membership_roles_scope"),
    ForeignKeyConstraint(
        ["organization_id", "organization_membership_id"],
        ["organization_memberships.organization_id", "organization_memberships.id"],
        name="fk_organization_membership_roles_membership_scope",
        ondelete="RESTRICT",
    ),
    CheckConstraint("length(role_code) > 0", name="role_code_nonempty"),
    CheckConstraint("revoked_at IS NULL OR revoked_at >= granted_at", name="role_dates"),
)
Index(
    "uq_organization_membership_roles_active",
    organization_membership_roles.c.organization_membership_id,
    organization_membership_roles.c.role_code,
    unique=True,
    postgresql_where=organization_membership_roles.c.revoked_at.is_(None),
)
Index(
    "ix_organization_membership_roles_scope",
    organization_membership_roles.c.organization_id,
    organization_membership_roles.c.organization_membership_id,
)
organization_curriculum_permissions = Table(
    "organization_curriculum_permissions",
    metadata,
    identifier(primary_key=True),
    identifier("organization_id", "organizations.id", ondelete="RESTRICT"),
    identifier("organization_membership_id"),
    Column("capability_code", Text, nullable=False),
    identifier("granted_by_user_id", "users.id", ondelete="RESTRICT"),
    Column("granted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("revoked_at", DateTime(timezone=True)),
    ForeignKeyConstraint(
        ["organization_id", "organization_membership_id"],
        ["organization_memberships.organization_id", "organization_memberships.id"],
        name="fk_organization_curriculum_permissions_membership_scope",
        ondelete="RESTRICT",
    ),
    CheckConstraint("length(capability_code) > 0", name="capability_code_nonempty"),
    CheckConstraint("revoked_at IS NULL OR revoked_at >= granted_at", name="permission_dates"),
)
Index(
    "uq_organization_curriculum_permissions_active",
    organization_curriculum_permissions.c.organization_membership_id,
    organization_curriculum_permissions.c.capability_code,
    unique=True,
    postgresql_where=organization_curriculum_permissions.c.revoked_at.is_(None),
)
Index(
    "ix_organization_curriculum_permissions_scope",
    organization_curriculum_permissions.c.organization_id,
    organization_curriculum_permissions.c.organization_membership_id,
)
curriculum_libraries = Table(
    "curriculum_libraries",
    metadata,
    identifier(primary_key=True),
    Column("owner_kind", String(16), nullable=False),
    Column("owner_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")),
    Column(
        "owner_organization_id",
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
    ),
    Column("name", Text, nullable=False),
    created(),
    UniqueConstraint("owner_organization_id", "id", name="uq_curriculum_libraries_org_id"),
    CheckConstraint(
        "(owner_kind = 'SYSTEM' AND owner_user_id IS NULL AND owner_organization_id IS NULL) OR "
        "(owner_kind = 'PERSONAL' AND owner_user_id IS NOT NULL AND "
        "owner_organization_id IS NULL) OR "
        "(owner_kind = 'ORGANIZATION' AND owner_user_id IS NULL AND "
        "owner_organization_id IS NOT NULL)",
        name="owner_shape",
    ),
    CheckConstraint("length(name) > 0", name="name_nonempty"),
)
curriculum_courses = Table(
    "curriculum_courses",
    metadata,
    identifier(primary_key=True),
    identifier("library_id", "curriculum_libraries.id", ondelete="RESTRICT"),
    Column("title", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("grade_level", Integer, nullable=False),
    identifier("created_by_user_id", "users.id", ondelete="RESTRICT"),
    created(),
    UniqueConstraint("library_id", "id", name="uq_curriculum_courses_library_id"),
    CheckConstraint("length(title) > 0", name="title_nonempty"),
    CheckConstraint("length(subject) > 0", name="subject_nonempty"),
)
Index("ix_curriculum_courses_library", curriculum_courses.c.library_id)
curriculum_units = Table(
    "curriculum_units",
    metadata,
    identifier(primary_key=True),
    identifier("curriculum_course_id"),
    Column("title", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("sequence_order", Integer, nullable=False),
    identifier("created_by_user_id", "users.id", ondelete="RESTRICT"),
    created(),
    UniqueConstraint("curriculum_course_id", "id", name="uq_curriculum_units_course_id"),
    UniqueConstraint(
        "curriculum_course_id", "sequence_order", name="uq_curriculum_units_course_order"
    ),
    ForeignKeyConstraint(["curriculum_course_id"], ["curriculum_courses.id"], ondelete="RESTRICT"),
    CheckConstraint("length(title) > 0", name="title_nonempty"),
    CheckConstraint("sequence_order > 0", name="sequence_order_positive"),
)
Index("ix_curriculum_units_course", curriculum_units.c.curriculum_course_id)
curriculum_lessons = Table(
    "curriculum_lessons",
    metadata,
    identifier(primary_key=True),
    identifier("curriculum_unit_id"),
    Column("title", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("sequence_order", Integer, nullable=False),
    identifier("created_by_user_id", "users.id", ondelete="RESTRICT"),
    created(),
    UniqueConstraint("curriculum_unit_id", "id", name="uq_curriculum_lessons_unit_id"),
    UniqueConstraint(
        "curriculum_unit_id", "sequence_order", name="uq_curriculum_lessons_unit_order"
    ),
    ForeignKeyConstraint(["curriculum_unit_id"], ["curriculum_units.id"], ondelete="RESTRICT"),
    CheckConstraint("length(title) > 0", name="title_nonempty"),
    CheckConstraint("sequence_order > 0", name="sequence_order_positive"),
)
Index("ix_curriculum_lessons_unit", curriculum_lessons.c.curriculum_unit_id)
tenant_curriculum_course_adoptions = Table(
    "tenant_curriculum_course_adoptions",
    metadata,
    identifier(primary_key=True),
    identifier("tenant_id", "tenants.id", ondelete="RESTRICT"),
    identifier("source_library_id"),
    identifier("curriculum_course_id"),
    identifier("adopted_by_user_id", "users.id", ondelete="RESTRICT"),
    Column("adopted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("retired_by_user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")),
    Column("retired_at", DateTime(timezone=True)),
    UniqueConstraint("tenant_id", "id", name="uq_tenant_course_adoptions_tenant_id"),
    ForeignKeyConstraint(
        ["source_library_id", "curriculum_course_id"],
        ["curriculum_courses.library_id", "curriculum_courses.id"],
        name="fk_tenant_course_adoptions_source_course",
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "(retired_at IS NULL) = (retired_by_user_id IS NULL)", name="retirement_actor_pair"
    ),
    CheckConstraint("retired_at IS NULL OR retired_at >= adopted_at", name="adoption_dates"),
)
Index(
    "uq_tenant_curriculum_course_adoptions_active",
    tenant_curriculum_course_adoptions.c.tenant_id,
    tenant_curriculum_course_adoptions.c.curriculum_course_id,
    unique=True,
    postgresql_where=tenant_curriculum_course_adoptions.c.retired_at.is_(None),
)
Index(
    "ix_tenant_curriculum_course_adoptions_tenant_source",
    tenant_curriculum_course_adoptions.c.tenant_id,
    tenant_curriculum_course_adoptions.c.curriculum_course_id,
)
curriculum_course_derivations = Table(
    "curriculum_course_derivations",
    metadata,
    identifier(primary_key=True),
    identifier("target_organization_id"),
    identifier("target_library_id"),
    identifier("target_course_id"),
    identifier("source_library_id"),
    identifier("source_course_id"),
    identifier("derived_by_user_id", "users.id", ondelete="RESTRICT"),
    created(),
    UniqueConstraint("target_course_id", name="uq_course_derivations_target"),
    ForeignKeyConstraint(
        ["target_organization_id", "target_library_id"],
        ["curriculum_libraries.owner_organization_id", "curriculum_libraries.id"],
        name="fk_course_derivations_target_org_library",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["target_library_id", "target_course_id"],
        ["curriculum_courses.library_id", "curriculum_courses.id"],
        name="fk_course_derivations_target_course",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["source_library_id", "source_course_id"],
        ["curriculum_courses.library_id", "curriculum_courses.id"],
        name="fk_course_derivations_source_course",
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "(target_library_id, target_course_id) <> (source_library_id, source_course_id)",
        name="source_differs_from_target",
    ),
)
curriculum_unit_derivations = Table(
    "curriculum_unit_derivations",
    metadata,
    identifier(primary_key=True),
    identifier("target_course_id"),
    identifier("target_unit_id"),
    identifier("source_course_id"),
    identifier("source_unit_id"),
    identifier("derived_by_user_id", "users.id", ondelete="RESTRICT"),
    created(),
    UniqueConstraint("target_unit_id", name="uq_unit_derivations_target"),
    ForeignKeyConstraint(
        ["target_course_id", "target_unit_id"],
        ["curriculum_units.curriculum_course_id", "curriculum_units.id"],
        name="fk_unit_derivations_target_unit",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["source_course_id", "source_unit_id"],
        ["curriculum_units.curriculum_course_id", "curriculum_units.id"],
        name="fk_unit_derivations_source_unit",
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "(target_course_id, target_unit_id) <> (source_course_id, source_unit_id)",
        name="source_differs_from_target",
    ),
)
Index("ix_curriculum_unit_derivations_source", curriculum_unit_derivations.c.source_unit_id)
curriculum_lesson_derivations = Table(
    "curriculum_lesson_derivations",
    metadata,
    identifier(primary_key=True),
    identifier("target_unit_id"),
    identifier("target_lesson_id"),
    identifier("source_unit_id"),
    identifier("source_lesson_id"),
    identifier("derived_by_user_id", "users.id", ondelete="RESTRICT"),
    created(),
    UniqueConstraint("target_lesson_id", name="uq_lesson_derivations_target"),
    ForeignKeyConstraint(
        ["target_unit_id", "target_lesson_id"],
        ["curriculum_lessons.curriculum_unit_id", "curriculum_lessons.id"],
        name="fk_lesson_derivations_target_lesson",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["source_unit_id", "source_lesson_id"],
        ["curriculum_lessons.curriculum_unit_id", "curriculum_lessons.id"],
        name="fk_lesson_derivations_source_lesson",
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "(target_unit_id, target_lesson_id) <> (source_unit_id, source_lesson_id)",
        name="source_differs_from_target",
    ),
)
Index("ix_curriculum_lesson_derivations_source", curriculum_lesson_derivations.c.source_lesson_id)

courses = Table(
    "courses",
    metadata,
    identifier(primary_key=True),
    Column("name", Text, nullable=False),
    Column("grade_level", Integer, nullable=False),
    Column("subject", Text, nullable=False),
    Column("tenant_id", UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT")),
    Column("curriculum_course_adoption_id", UUID(as_uuid=True)),
    created(),
    CheckConstraint(
        "(tenant_id IS NULL AND curriculum_course_adoption_id IS NULL) OR "
        "(tenant_id IS NOT NULL AND curriculum_course_adoption_id IS NOT NULL)",
        name="tenant_adoption_pair",
    ),
    ForeignKeyConstraint(
        ["tenant_id", "curriculum_course_adoption_id"],
        ["tenant_curriculum_course_adoptions.tenant_id", "tenant_curriculum_course_adoptions.id"],
        name="fk_courses_tenant_adoption",
        ondelete="RESTRICT",
    ),
)
Index("ix_courses_tenant", courses.c.tenant_id)
Index("ix_courses_curriculum_adoption", courses.c.curriculum_course_adoption_id)
enrollments = Table(
    "enrollments",
    metadata,
    identifier(primary_key=True),
    identifier("student_user_id", "users.id"),
    identifier("course_id", "courses.id"),
    Column("status", String(32), nullable=False),
    created(),
)
Index(
    "uq_enrollments_active",
    enrollments.c.student_user_id,
    enrollments.c.course_id,
    unique=True,
    postgresql_where=enrollments.c.status == "ACTIVE",
)
assignments = Table(
    "assignments",
    metadata,
    identifier(primary_key=True),
    identifier("course_id", "courses.id"),
    Column("title", Text, nullable=False),
    Column("description", Text, nullable=False),
    created(),
)
problems = Table(
    "problems",
    metadata,
    identifier(primary_key=True),
    identifier("course_id", "courses.id"),
    Column("prompt", Text, nullable=False),
    created(),
)
assignment_problems = Table(
    "assignment_problems",
    metadata,
    identifier("assignment_id", "assignments.id", True),
    identifier("problem_id", "problems.id", True),
    Column("sequence_order", Integer, nullable=False),
)
student_assignment_eligibility = Table(
    "student_assignment_eligibility",
    metadata,
    identifier("student_user_id", "users.id", True),
    identifier("assignment_id", "assignments.id", True),
    created(),
)
coaching_sessions = Table(
    "coaching_sessions",
    metadata,
    identifier(primary_key=True),
    identifier("student_user_id", "users.id"),
    identifier("course_id", "courses.id"),
    identifier("assignment_id", "assignments.id"),
    identifier("problem_id", "problems.id"),
    Column("status", String(16), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("ended_at", DateTime(timezone=True)),
    Column("next_message_sequence", BigInteger, nullable=False, server_default="1"),
    Column("closure_reason", String(24)),
    CheckConstraint("next_message_sequence > 0", name="next_message_sequence"),
    CheckConstraint(
        "(status = 'ACTIVE' AND closure_reason IS NULL) OR "
        "(status = 'CLOSED' AND closure_reason IS NOT NULL AND "
        "closure_reason IN ('NORMAL','ADMINISTRATIVE','UNKNOWN'))",
        name="closure_reason",
    ),
    created(),
    CheckConstraint("status IN ('ACTIVE', 'CLOSED')", name="status"),
)
messages = Table(
    "messages",
    metadata,
    identifier(primary_key=True),
    identifier("session_id", "coaching_sessions.id"),
    Column("author_type", String(16), nullable=False),
    Column("content", Text, nullable=False),
    Column("processing_status", String(16), nullable=False),
    Column("trace_id", String(32)),
    Column("session_sequence", BigInteger),
    Column("in_reply_to_message_id", UUID(as_uuid=True)),
    UniqueConstraint("session_id", "session_sequence", name="uq_messages_session_sequence"),
    UniqueConstraint("id", "session_id", name="uq_messages_id_session"),
    UniqueConstraint("in_reply_to_message_id", name="uq_messages_reply"),
    ForeignKeyConstraint(
        ["in_reply_to_message_id", "session_id"],
        ["messages.id", "messages.session_id"],
        name="fk_messages_reply_session",
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "(author_type = 'student' AND session_sequence IS NOT NULL AND "
        "session_sequence > 0 AND in_reply_to_message_id IS NULL) OR "
        "(author_type = 'tutor' AND session_sequence IS NULL AND "
        "in_reply_to_message_id IS NOT NULL AND processing_status = 'COMPLETED')",
        name="processing_shape",
    ),
    created(),
    CheckConstraint("author_type IN ('student', 'tutor')", name="author_type"),
    CheckConstraint(
        "processing_status IN ('PENDING','PROCESSING','COMPLETED','FAILED','CANCELLED')",
        name="processing_status",
    ),
    CheckConstraint("length(content) > 0", name="nonempty_content"),
)
Index("ix_messages_session_created", messages.c.session_id, messages.c.created_at)
idempotency_records = Table(
    "idempotency_records",
    metadata,
    identifier(primary_key=True),
    identifier("student_id", "users.id"),
    Column("operation", String(64), nullable=False),
    Column("idempotency_key", String(255), nullable=False),
    identifier("message_id", "messages.id"),
    created(),
    UniqueConstraint("student_id", "operation", "idempotency_key", name="uq_idempotency_scope"),
    UniqueConstraint("message_id"),
    CheckConstraint("length(idempotency_key) BETWEEN 1 AND 255", name="key_length"),
)

Index(
    "uq_messages_processing_session",
    messages.c.session_id,
    unique=True,
    postgresql_where=(messages.c.author_type == "student")
    & (messages.c.processing_status == "PROCESSING"),
)
Index(
    "ix_messages_unresolved_sequence",
    messages.c.session_id,
    messages.c.session_sequence,
    postgresql_where=(messages.c.author_type == "student")
    & messages.c.processing_status.in_(["PENDING", "PROCESSING", "FAILED"]),
)
message_processing_jobs = Table(
    "message_processing_jobs",
    metadata,
    Column(
        "message_id",
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("attempt_count", Integer, nullable=False, server_default="0"),
    Column("cycle_attempt_count", Integer, nullable=False, server_default="0"),
    Column("max_attempts", Integer, nullable=False, server_default="2"),
    Column("retry_generation", Integer, nullable=False, server_default="0"),
    Column("claim_token", UUID(as_uuid=True)),
    Column("worker_instance_id", UUID(as_uuid=True)),
    Column("claimed_at", DateTime(timezone=True)),
    Column("lease_expires_at", DateTime(timezone=True)),
    Column("attempt_deadline_at", DateTime(timezone=True)),
    Column("next_attempt_at", DateTime(timezone=True), server_default=func.clock_timestamp()),
    Column("last_error_code", String(64)),
    Column("last_error_at", DateTime(timezone=True)),
    Column("cancel_reason", String(32)),
    Column("finished_at", DateTime(timezone=True)),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()
    ),
    CheckConstraint(
        "attempt_count >= cycle_attempt_count AND cycle_attempt_count >= 0 AND "
        "max_attempts >= 1 AND cycle_attempt_count <= max_attempts AND retry_generation >= 0",
        name="attempt_counts",
    ),
    CheckConstraint("(last_error_code IS NULL) = (last_error_at IS NULL)", name="error_pair"),
    CheckConstraint(
        "last_error_code IN ('MODEL_TIMEOUT','MODEL_UNAVAILABLE','MODEL_RATE_LIMITED',"
        "'MODEL_INVALID_OUTPUT','MODEL_CONFIGURATION','POLICY_REJECTED','PROCESSING_ERROR',"
        "'LEASE_EXPIRED','DATABASE_FAILURE')",
        name="error_code",
    ),
    CheckConstraint(
        "cancel_reason IN ('ACCOUNT_DISABLED','ENROLLMENT_REVOKED','COURSEWORK_INELIGIBLE',"
        "'SESSION_ADMIN_CLOSED','SESSION_CLOSURE_UNKNOWN')",
        name="cancel_reason",
    ),
)
Index(
    "ix_jobs_due",
    message_processing_jobs.c.next_attempt_at,
    message_processing_jobs.c.message_id,
    postgresql_where=message_processing_jobs.c.next_attempt_at.is_not(None),
)
Index(
    "ix_jobs_expiring",
    message_processing_jobs.c.lease_expires_at,
    message_processing_jobs.c.message_id,
    postgresql_where=message_processing_jobs.c.lease_expires_at.is_not(None),
)
