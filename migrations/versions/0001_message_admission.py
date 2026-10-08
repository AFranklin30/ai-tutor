"""Initial Slice 1 schema. Downgrade destroys these tables; use only on disposable DBs."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "courses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('STUDENT', 'TEACHER')", name=op.f("ck_users_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_assignments_course_id_courses")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignments")),
    )
    op.create_table(
        "enrollments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_enrollments_course_id_courses")
        ),
        sa.ForeignKeyConstraint(
            ["student_user_id"], ["users.id"], name=op.f("fk_enrollments_student_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollments")),
    )
    op.create_index(
        "uq_enrollments_active",
        "enrollments",
        ["student_user_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_table(
        "problems",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_problems_course_id_courses")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problems")),
    )
    op.create_table(
        "assignment_problems",
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column("problem_id", sa.UUID(), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_assignment_problems_assignment_id_assignments"),
        ),
        sa.ForeignKeyConstraint(
            ["problem_id"], ["problems.id"], name=op.f("fk_assignment_problems_problem_id_problems")
        ),
        sa.PrimaryKeyConstraint("assignment_id", "problem_id", name=op.f("pk_assignment_problems")),
    )
    op.create_table(
        "coaching_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column("problem_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'CLOSED')", name=op.f("ck_coaching_sessions_status")
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_coaching_sessions_assignment_id_assignments"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_coaching_sessions_course_id_courses")
        ),
        sa.ForeignKeyConstraint(
            ["problem_id"], ["problems.id"], name=op.f("fk_coaching_sessions_problem_id_problems")
        ),
        sa.ForeignKeyConstraint(
            ["student_user_id"],
            ["users.id"],
            name=op.f("fk_coaching_sessions_student_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coaching_sessions")),
    )
    op.create_table(
        "student_assignment_eligibility",
        sa.Column("student_user_id", sa.UUID(), nullable=False),
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_student_assignment_eligibility_assignment_id_assignments"),
        ),
        sa.ForeignKeyConstraint(
            ["student_user_id"],
            ["users.id"],
            name=op.f("fk_student_assignment_eligibility_student_user_id_users"),
        ),
        sa.PrimaryKeyConstraint(
            "student_user_id", "assignment_id", name=op.f("pk_student_assignment_eligibility")
        ),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("author_type", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("processing_status", sa.String(length=16), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "author_type IN ('student', 'tutor')", name=op.f("ck_messages_author_type")
        ),
        sa.CheckConstraint(
            "processing_status IN ('PENDING','PROCESSING','COMPLETED','FAILED')",
            name=op.f("ck_messages_processing_status"),
        ),
        sa.CheckConstraint("length(content) > 0", name=op.f("ck_messages_nonempty_content")),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["coaching_sessions.id"],
            name=op.f("fk_messages_session_id_coaching_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(
        "ix_messages_session_created", "messages", ["session_id", "created_at"], unique=False
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(idempotency_key) BETWEEN 1 AND 255",
            name=op.f("ck_idempotency_records_key_length"),
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], name=op.f("fk_idempotency_records_message_id_messages")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], name=op.f("fk_idempotency_records_student_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_records")),
        sa.UniqueConstraint("message_id", name=op.f("uq_idempotency_records_message_id")),
        sa.UniqueConstraint(
            "student_id", "operation", "idempotency_key", name="uq_idempotency_scope"
        ),
    )


def downgrade():
    op.drop_table("idempotency_records")
    op.drop_index("ix_messages_session_created", table_name="messages")
    op.drop_table("messages")
    op.drop_table("student_assignment_eligibility")
    op.drop_table("coaching_sessions")
    op.drop_table("assignment_problems")
    op.drop_table("problems")
    op.drop_index("uq_enrollments_active", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_table("assignments")
    op.drop_table("users")
    op.drop_table("courses")
