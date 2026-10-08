"""SQLAlchemy Core models for the admission slice; no future AI tables."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
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
    created(),
    CheckConstraint("author_type IN ('student', 'tutor')", name="author_type"),
    CheckConstraint(
        "processing_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')",
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
