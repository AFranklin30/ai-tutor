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


def identifier(name="id", target=None, primary_key=False):
    args = [ForeignKey(target)] if target else []
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
courses = Table(
    "courses",
    metadata,
    identifier(primary_key=True),
    Column("name", Text, nullable=False),
    Column("grade_level", Integer, nullable=False),
    Column("subject", Text, nullable=False),
    created(),
)
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
