"""Organization, tenant, and reusable curriculum foundation.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(name) > 0", name=op.f("ck_organizations_name_nonempty")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(name) > 0", name=op.f("ck_tenants_name_nonempty")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_tenants_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
        sa.UniqueConstraint("organization_id", "id", name="uq_tenants_organization_id"),
    )
    op.create_index("ix_tenants_organization", "tenants", ["organization_id"])

    op.create_table(
        "tenant_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "activated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "deactivated_at IS NULL OR deactivated_at >= activated_at",
            name=op.f("ck_tenant_memberships_membership_dates"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_memberships_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_tenant_memberships_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_tenant_memberships_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_memberships")),
        sa.UniqueConstraint("tenant_id", "id", name="uq_tenant_memberships_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id", "id", "user_id", name="uq_tenant_memberships_tenant_id_user"
        ),
    )
    op.create_index(
        "uq_tenant_memberships_active",
        "tenant_memberships",
        ["tenant_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("deactivated_at IS NULL"),
    )
    op.create_index("ix_tenant_memberships_user", "tenant_memberships", ["user_id", "tenant_id"])

    op.create_table(
        "tenant_membership_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_code", sa.Text(), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "length(role_code) > 0", name=op.f("ck_tenant_membership_roles_role_code_nonempty")
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at",
            name=op.f("ck_tenant_membership_roles_role_dates"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "tenant_membership_id"],
            ["tenant_memberships.tenant_id", "tenant_memberships.id"],
            name="fk_tenant_membership_roles_membership_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_membership_roles_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            name=op.f("fk_tenant_membership_roles_granted_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_membership_roles")),
        sa.UniqueConstraint("tenant_id", "id", name="uq_tenant_membership_roles_scope"),
    )
    op.create_index(
        "uq_tenant_membership_roles_active",
        "tenant_membership_roles",
        ["tenant_membership_id", "role_code"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_tenant_membership_roles_scope",
        "tenant_membership_roles",
        ["tenant_id", "tenant_membership_id"],
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "activated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "deactivated_at IS NULL OR deactivated_at >= activated_at",
            name=op.f("ck_organization_memberships_membership_dates"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_memberships_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_organization_memberships_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_organization_memberships_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_memberships")),
        sa.UniqueConstraint("organization_id", "id", name="uq_organization_memberships_scope"),
    )
    op.create_index(
        "uq_organization_memberships_active",
        "organization_memberships",
        ["organization_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("deactivated_at IS NULL"),
    )
    op.create_index(
        "ix_organization_memberships_user",
        "organization_memberships",
        ["user_id", "organization_id"],
    )

    op.create_table(
        "organization_membership_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_code", sa.Text(), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "length(role_code) > 0",
            name=op.f("ck_organization_membership_roles_role_code_nonempty"),
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at",
            name=op.f("ck_organization_membership_roles_role_dates"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_membership_id"],
            ["organization_memberships.organization_id", "organization_memberships.id"],
            name="fk_organization_membership_roles_membership_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_membership_roles_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            name=op.f("fk_organization_membership_roles_granted_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_membership_roles")),
        sa.UniqueConstraint("organization_id", "id", name="uq_organization_membership_roles_scope"),
    )
    op.create_index(
        "uq_organization_membership_roles_active",
        "organization_membership_roles",
        ["organization_membership_id", "role_code"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_organization_membership_roles_scope",
        "organization_membership_roles",
        ["organization_id", "organization_membership_id"],
    )

    op.create_table(
        "organization_curriculum_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_code", sa.Text(), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "length(capability_code) > 0",
            name=op.f("ck_organization_curriculum_permissions_capability_code_nonempty"),
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at",
            name=op.f("ck_organization_curriculum_permissions_permission_dates"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_membership_id"],
            ["organization_memberships.organization_id", "organization_memberships.id"],
            name="fk_organization_curriculum_permissions_membership_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_curriculum_permissions_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            name=op.f("fk_organization_curriculum_permissions_granted_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_curriculum_permissions")),
    )
    op.create_index(
        "uq_organization_curriculum_permissions_active",
        "organization_curriculum_permissions",
        ["organization_membership_id", "capability_code"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_organization_curriculum_permissions_scope",
        "organization_curriculum_permissions",
        ["organization_id", "organization_membership_id"],
    )

    op.create_table(
        "curriculum_libraries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_kind", sa.String(length=16), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("owner_organization_id", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(owner_kind = 'SYSTEM' AND owner_user_id IS NULL AND "
            "owner_organization_id IS NULL) OR "
            "(owner_kind = 'PERSONAL' AND owner_user_id IS NOT NULL AND "
            "owner_organization_id IS NULL) OR "
            "(owner_kind = 'ORGANIZATION' AND owner_user_id IS NULL AND "
            "owner_organization_id IS NOT NULL)",
            name=op.f("ck_curriculum_libraries_owner_shape"),
        ),
        sa.CheckConstraint("length(name) > 0", name=op.f("ck_curriculum_libraries_name_nonempty")),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_curriculum_libraries_owner_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_organization_id"],
            ["organizations.id"],
            name=op.f("fk_curriculum_libraries_owner_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_libraries")),
        sa.UniqueConstraint("owner_organization_id", "id", name="uq_curriculum_libraries_org_id"),
    )
    op.create_table(
        "curriculum_courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("library_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(title) > 0", name=op.f("ck_curriculum_courses_title_nonempty")),
        sa.CheckConstraint(
            "length(subject) > 0", name=op.f("ck_curriculum_courses_subject_nonempty")
        ),
        sa.ForeignKeyConstraint(
            ["library_id"],
            ["curriculum_libraries.id"],
            name=op.f("fk_curriculum_courses_library_id_curriculum_libraries"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_curriculum_courses_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_courses")),
        sa.UniqueConstraint("library_id", "id", name="uq_curriculum_courses_library_id"),
    )
    op.create_index("ix_curriculum_courses_library", "curriculum_courses", ["library_id"])
    op.create_table(
        "curriculum_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("curriculum_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(title) > 0", name=op.f("ck_curriculum_units_title_nonempty")),
        sa.CheckConstraint(
            "sequence_order > 0", name=op.f("ck_curriculum_units_sequence_order_positive")
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_course_id"],
            ["curriculum_courses.id"],
            name=op.f("fk_curriculum_units_curriculum_course_id_curriculum_courses"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_curriculum_units_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_units")),
        sa.UniqueConstraint("curriculum_course_id", "id", name="uq_curriculum_units_course_id"),
        sa.UniqueConstraint(
            "curriculum_course_id", "sequence_order", name="uq_curriculum_units_course_order"
        ),
    )
    op.create_index("ix_curriculum_units_course", "curriculum_units", ["curriculum_course_id"])
    op.create_table(
        "curriculum_lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("curriculum_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(title) > 0", name=op.f("ck_curriculum_lessons_title_nonempty")),
        sa.CheckConstraint(
            "sequence_order > 0", name=op.f("ck_curriculum_lessons_sequence_order_positive")
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_unit_id"],
            ["curriculum_units.id"],
            name=op.f("fk_curriculum_lessons_curriculum_unit_id_curriculum_units"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_curriculum_lessons_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_lessons")),
        sa.UniqueConstraint("curriculum_unit_id", "id", name="uq_curriculum_lessons_unit_id"),
        sa.UniqueConstraint(
            "curriculum_unit_id", "sequence_order", name="uq_curriculum_lessons_unit_order"
        ),
    )
    op.create_index("ix_curriculum_lessons_unit", "curriculum_lessons", ["curriculum_unit_id"])

    op.create_table(
        "tenant_curriculum_course_adoptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_library_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("curriculum_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("adopted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "adopted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("retired_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "(retired_at IS NULL) = (retired_by_user_id IS NULL)",
            name=op.f("ck_tenant_curriculum_course_adoptions_retirement_actor_pair"),
        ),
        sa.CheckConstraint(
            "retired_at IS NULL OR retired_at >= adopted_at",
            name=op.f("ck_tenant_curriculum_course_adoptions_adoption_dates"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_curriculum_course_adoptions_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_library_id", "curriculum_course_id"],
            ["curriculum_courses.library_id", "curriculum_courses.id"],
            name="fk_tenant_course_adoptions_source_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["adopted_by_user_id"],
            ["users.id"],
            name=op.f("fk_tenant_curriculum_course_adoptions_adopted_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["retired_by_user_id"],
            ["users.id"],
            name=op.f("fk_tenant_curriculum_course_adoptions_retired_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_curriculum_course_adoptions")),
        sa.UniqueConstraint("tenant_id", "id", name="uq_tenant_course_adoptions_tenant_id"),
    )
    op.create_index(
        "uq_tenant_curriculum_course_adoptions_active",
        "tenant_curriculum_course_adoptions",
        ["tenant_id", "curriculum_course_id"],
        unique=True,
        postgresql_where=sa.text("retired_at IS NULL"),
    )
    op.create_index(
        "ix_tenant_curriculum_course_adoptions_tenant_source",
        "tenant_curriculum_course_adoptions",
        ["tenant_id", "curriculum_course_id"],
    )

    op.create_table(
        "curriculum_course_derivations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_library_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_library_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derived_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(target_library_id, target_course_id) <> (source_library_id, source_course_id)",
            name=op.f("ck_curriculum_course_derivations_source_differs_from_target"),
        ),
        sa.ForeignKeyConstraint(
            ["target_organization_id", "target_library_id"],
            ["curriculum_libraries.owner_organization_id", "curriculum_libraries.id"],
            name="fk_course_derivations_target_org_library",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_library_id", "target_course_id"],
            ["curriculum_courses.library_id", "curriculum_courses.id"],
            name="fk_course_derivations_target_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_library_id", "source_course_id"],
            ["curriculum_courses.library_id", "curriculum_courses.id"],
            name="fk_course_derivations_source_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["derived_by_user_id"],
            ["users.id"],
            name=op.f("fk_curriculum_course_derivations_derived_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_course_derivations")),
        sa.UniqueConstraint("target_course_id", name="uq_course_derivations_target"),
    )
    op.create_table(
        "curriculum_unit_derivations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derived_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(target_course_id, target_unit_id) <> (source_course_id, source_unit_id)",
            name=op.f("ck_curriculum_unit_derivations_source_differs_from_target"),
        ),
        sa.ForeignKeyConstraint(
            ["target_course_id", "target_unit_id"],
            ["curriculum_units.curriculum_course_id", "curriculum_units.id"],
            name="fk_unit_derivations_target_unit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_course_id", "source_unit_id"],
            ["curriculum_units.curriculum_course_id", "curriculum_units.id"],
            name="fk_unit_derivations_source_unit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["derived_by_user_id"],
            ["users.id"],
            name=op.f("fk_curriculum_unit_derivations_derived_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_unit_derivations")),
        sa.UniqueConstraint("target_unit_id", name="uq_unit_derivations_target"),
    )
    op.create_index(
        "ix_curriculum_unit_derivations_source", "curriculum_unit_derivations", ["source_unit_id"]
    )
    op.create_table(
        "curriculum_lesson_derivations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derived_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(target_unit_id, target_lesson_id) <> (source_unit_id, source_lesson_id)",
            name=op.f("ck_curriculum_lesson_derivations_source_differs_from_target"),
        ),
        sa.ForeignKeyConstraint(
            ["target_unit_id", "target_lesson_id"],
            ["curriculum_lessons.curriculum_unit_id", "curriculum_lessons.id"],
            name="fk_lesson_derivations_target_lesson",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_unit_id", "source_lesson_id"],
            ["curriculum_lessons.curriculum_unit_id", "curriculum_lessons.id"],
            name="fk_lesson_derivations_source_lesson",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["derived_by_user_id"],
            ["users.id"],
            name=op.f("fk_curriculum_lesson_derivations_derived_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_lesson_derivations")),
        sa.UniqueConstraint("target_lesson_id", name="uq_lesson_derivations_target"),
    )
    op.create_index(
        "ix_curriculum_lesson_derivations_source",
        "curriculum_lesson_derivations",
        ["source_lesson_id"],
    )

    op.add_column("courses", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "courses",
        sa.Column("curriculum_course_adoption_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "ALTER TABLE courses ADD CONSTRAINT ck_courses_tenant_adoption_pair "
        "CHECK ((tenant_id IS NULL AND curriculum_course_adoption_id IS NULL) OR "
        "(tenant_id IS NOT NULL AND curriculum_course_adoption_id IS NOT NULL)) NOT VALID"
    )
    op.execute(
        "ALTER TABLE courses ADD CONSTRAINT fk_courses_tenant_id_tenants "
        "FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT NOT VALID"
    )
    op.execute(
        "ALTER TABLE courses ADD CONSTRAINT fk_courses_tenant_adoption "
        "FOREIGN KEY (tenant_id, curriculum_course_adoption_id) "
        "REFERENCES tenant_curriculum_course_adoptions(tenant_id, id) "
        "ON DELETE RESTRICT NOT VALID"
    )
    op.create_index("ix_courses_tenant", "courses", ["tenant_id"])
    op.create_index("ix_courses_curriculum_adoption", "courses", ["curriculum_course_adoption_id"])
    op.execute("ALTER TABLE courses VALIDATE CONSTRAINT ck_courses_tenant_adoption_pair")
    op.execute("ALTER TABLE courses VALIDATE CONSTRAINT fk_courses_tenant_id_tenants")
    op.execute("ALTER TABLE courses VALIDATE CONSTRAINT fk_courses_tenant_adoption")

    op.execute(IMMUTABILITY_FUNCTIONS)
    for table in (
        "curriculum_courses",
        "curriculum_units",
        "curriculum_lessons",
        "curriculum_course_derivations",
        "curriculum_unit_derivations",
        "curriculum_lesson_derivations",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_immutable_curriculum_change()"
        )
    op.execute(
        "CREATE TRIGGER tenant_curriculum_course_adoptions_validate "
        "BEFORE INSERT ON tenant_curriculum_course_adoptions "
        "FOR EACH ROW EXECUTE FUNCTION validate_curriculum_adoption()"
    )
    op.execute(
        "CREATE TRIGGER tenant_curriculum_course_adoptions_immutable "
        "BEFORE UPDATE OR DELETE ON tenant_curriculum_course_adoptions "
        "FOR EACH ROW EXECUTE FUNCTION guard_curriculum_adoption_history()"
    )
    op.execute(
        "CREATE TRIGGER curriculum_unit_derivations_validate "
        "BEFORE INSERT ON curriculum_unit_derivations "
        "FOR EACH ROW EXECUTE FUNCTION validate_unit_derivation()"
    )
    op.execute(
        "CREATE TRIGGER curriculum_lesson_derivations_validate "
        "BEFORE INSERT ON curriculum_lesson_derivations "
        "FOR EACH ROW EXECUTE FUNCTION validate_lesson_derivation()"
    )
    for table in ("tenant_memberships", "organization_memberships"):
        op.execute(
            f"CREATE TRIGGER {table}_history_guard BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION guard_membership_history()"
        )
    for table in (
        "tenant_membership_roles",
        "organization_membership_roles",
        "organization_curriculum_permissions",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_history_guard BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION guard_grant_history()"
        )
    op.execute(
        "CREATE TRIGGER tenants_owner_guard BEFORE UPDATE OF organization_id ON tenants "
        "FOR EACH ROW EXECUTE FUNCTION guard_tenant_organization()"
    )
    op.execute(
        "CREATE TRIGGER curriculum_libraries_owner_guard "
        "BEFORE UPDATE OR DELETE ON curriculum_libraries "
        "FOR EACH ROW EXECUTE FUNCTION guard_library_owner()"
    )
    op.execute(
        "CREATE TRIGGER courses_adoption_guard BEFORE INSERT OR UPDATE OF tenant_id, "
        "curriculum_course_adoption_id ON courses "
        "FOR EACH ROW EXECUTE FUNCTION validate_course_offering_adoption()"
    )


def downgrade():
    op.execute(
        "LOCK TABLE organizations, tenants, tenant_memberships, tenant_membership_roles, "
        "organization_memberships, organization_membership_roles, "
        "organization_curriculum_permissions, curriculum_libraries, curriculum_courses, "
        "curriculum_units, curriculum_lessons, tenant_curriculum_course_adoptions, "
        "curriculum_course_derivations, curriculum_unit_derivations, "
        "curriculum_lesson_derivations, courses IN ACCESS EXCLUSIVE MODE"
    )
    op.execute(DOWNGRADE_GUARD)
    op.execute(
        "DROP TRIGGER curriculum_lesson_derivations_validate ON curriculum_lesson_derivations"
    )
    op.execute("DROP TRIGGER curriculum_unit_derivations_validate ON curriculum_unit_derivations")
    op.execute(
        "DROP TRIGGER tenant_curriculum_course_adoptions_immutable "
        "ON tenant_curriculum_course_adoptions"
    )
    op.execute(
        "DROP TRIGGER tenant_curriculum_course_adoptions_validate "
        "ON tenant_curriculum_course_adoptions"
    )
    op.execute("DROP TRIGGER courses_adoption_guard ON courses")
    op.execute("DROP TRIGGER curriculum_libraries_owner_guard ON curriculum_libraries")
    op.execute("DROP TRIGGER tenants_owner_guard ON tenants")
    for table in (
        "tenant_memberships",
        "organization_memberships",
        "tenant_membership_roles",
        "organization_membership_roles",
        "organization_curriculum_permissions",
    ):
        op.execute(f"DROP TRIGGER {table}_history_guard ON {table}")
    for table in (
        "curriculum_courses",
        "curriculum_units",
        "curriculum_lessons",
        "curriculum_course_derivations",
        "curriculum_unit_derivations",
        "curriculum_lesson_derivations",
    ):
        op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
    op.execute(
        "DROP FUNCTION validate_curriculum_adoption(); "
        "DROP FUNCTION guard_curriculum_adoption_history(); "
        "DROP FUNCTION validate_unit_derivation(); "
        "DROP FUNCTION validate_lesson_derivation(); "
        "DROP FUNCTION guard_membership_history(); "
        "DROP FUNCTION guard_grant_history(); "
        "DROP FUNCTION guard_tenant_organization(); "
        "DROP FUNCTION guard_library_owner(); "
        "DROP FUNCTION validate_course_offering_adoption(); "
        "DROP FUNCTION reject_immutable_curriculum_change();"
    )
    op.drop_index("ix_courses_curriculum_adoption", table_name="courses")
    op.drop_index("ix_courses_tenant", table_name="courses")
    op.drop_constraint("fk_courses_tenant_adoption", "courses", type_="foreignkey")
    op.drop_constraint("fk_courses_tenant_id_tenants", "courses", type_="foreignkey")
    # This CHECK was added with raw SQL; use its exact PostgreSQL identifier instead
    # of letting the metadata naming convention rewrite it.
    op.execute("ALTER TABLE courses DROP CONSTRAINT ck_courses_tenant_adoption_pair")
    op.drop_column("courses", "curriculum_course_adoption_id")
    op.drop_column("courses", "tenant_id")

    for table in (
        "curriculum_lesson_derivations",
        "curriculum_unit_derivations",
        "curriculum_course_derivations",
        "tenant_curriculum_course_adoptions",
        "curriculum_lessons",
        "curriculum_units",
        "curriculum_courses",
        "curriculum_libraries",
        "organization_curriculum_permissions",
        "organization_membership_roles",
        "organization_memberships",
        "tenant_membership_roles",
        "tenant_memberships",
        "tenants",
        "organizations",
    ):
        op.drop_table(table)


IMMUTABILITY_FUNCTIONS = """
CREATE FUNCTION reject_immutable_curriculum_change() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'curriculum record and derivation provenance are immutable'
        USING ERRCODE = '23514';
END $$;

CREATE FUNCTION validate_curriculum_adoption() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE kind VARCHAR(16);
BEGIN
    SELECT owner_kind INTO kind FROM curriculum_libraries WHERE id = NEW.source_library_id;
    IF kind IS NULL OR kind = 'PERSONAL' THEN
        RAISE EXCEPTION 'personal curriculum cannot be adopted by a tenant' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION guard_curriculum_adoption_history() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'curriculum adoption provenance cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF ROW(NEW.id, NEW.tenant_id, NEW.source_library_id, NEW.curriculum_course_id,
           NEW.adopted_by_user_id, NEW.adopted_at)
       IS DISTINCT FROM
       ROW(OLD.id, OLD.tenant_id, OLD.source_library_id, OLD.curriculum_course_id,
           OLD.adopted_by_user_id, OLD.adopted_at)
       OR OLD.retired_at IS NOT NULL OR NEW.retired_at IS NULL
       OR NEW.retired_by_user_id IS NULL THEN
        RAISE EXCEPTION 'adoption provenance is immutable; retirement may occur once'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION validate_unit_derivation() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE owner_kind VARCHAR(16);
BEGIN
    SELECT l.owner_kind INTO owner_kind
    FROM curriculum_units u
    JOIN curriculum_courses c ON c.id = u.curriculum_course_id
    JOIN curriculum_libraries l ON l.id = c.library_id
    WHERE u.id = NEW.target_unit_id AND u.curriculum_course_id = NEW.target_course_id;
    IF owner_kind IS DISTINCT FROM 'ORGANIZATION' THEN
        RAISE EXCEPTION 'unit derivative must belong to an organization library'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION validate_lesson_derivation() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE owner_kind VARCHAR(16);
BEGIN
    SELECT l.owner_kind INTO owner_kind
    FROM curriculum_lessons lesson
    JOIN curriculum_units u ON u.id = lesson.curriculum_unit_id
    JOIN curriculum_courses c ON c.id = u.curriculum_course_id
    JOIN curriculum_libraries l ON l.id = c.library_id
    WHERE lesson.id = NEW.target_lesson_id AND lesson.curriculum_unit_id = NEW.target_unit_id;
    IF owner_kind IS DISTINCT FROM 'ORGANIZATION' THEN
        RAISE EXCEPTION 'lesson derivative must belong to an organization library'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION guard_membership_history() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE lifecycle_column TEXT := 'deactivated_at';
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'membership history cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF (to_jsonb(NEW) - lifecycle_column) IS DISTINCT FROM
       (to_jsonb(OLD) - lifecycle_column)
       OR to_jsonb(OLD) ->> lifecycle_column IS NOT NULL
       OR to_jsonb(NEW) ->> lifecycle_column IS NULL THEN
        RAISE EXCEPTION 'membership attribution is immutable; deactivation may occur once'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION guard_grant_history() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE lifecycle_column TEXT := 'revoked_at';
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'role and permission history cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF (to_jsonb(NEW) - lifecycle_column) IS DISTINCT FROM
       (to_jsonb(OLD) - lifecycle_column)
       OR to_jsonb(OLD) ->> lifecycle_column IS NOT NULL
       OR to_jsonb(NEW) ->> lifecycle_column IS NULL THEN
        RAISE EXCEPTION 'grant attribution is immutable; revocation may occur once'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION guard_tenant_organization() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN
        RAISE EXCEPTION 'tenant organization ownership is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION guard_library_owner() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'curriculum library ownership history cannot be deleted'
            USING ERRCODE = '23514';
    END IF;
    IF ROW(NEW.id, NEW.owner_kind, NEW.owner_user_id, NEW.owner_organization_id)
       IS DISTINCT FROM ROW(
           OLD.id, OLD.owner_kind, OLD.owner_user_id, OLD.owner_organization_id
       ) THEN
        RAISE EXCEPTION 'curriculum library ownership is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION validate_course_offering_adoption() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE retired TIMESTAMPTZ;
BEGIN
    IF NEW.tenant_id IS NULL AND NEW.curriculum_course_adoption_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT retired_at INTO retired FROM tenant_curriculum_course_adoptions
    WHERE tenant_id = NEW.tenant_id AND id = NEW.curriculum_course_adoption_id
    FOR SHARE;
    IF NOT FOUND OR retired IS NOT NULL THEN
        RAISE EXCEPTION 'course offering requires an active curriculum adoption in its tenant'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
"""

DOWNGRADE_GUARD = """
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM organizations) OR EXISTS (SELECT 1 FROM tenants)
       OR EXISTS (SELECT 1 FROM tenant_memberships)
       OR EXISTS (SELECT 1 FROM tenant_membership_roles)
       OR EXISTS (SELECT 1 FROM organization_memberships)
       OR EXISTS (SELECT 1 FROM organization_membership_roles)
       OR EXISTS (SELECT 1 FROM organization_curriculum_permissions)
       OR EXISTS (SELECT 1 FROM curriculum_libraries) OR EXISTS (SELECT 1 FROM curriculum_courses)
       OR EXISTS (SELECT 1 FROM curriculum_units) OR EXISTS (SELECT 1 FROM curriculum_lessons)
       OR EXISTS (SELECT 1 FROM tenant_curriculum_course_adoptions)
       OR EXISTS (SELECT 1 FROM curriculum_course_derivations)
       OR EXISTS (SELECT 1 FROM curriculum_unit_derivations)
       OR EXISTS (SELECT 1 FROM curriculum_lesson_derivations)
       OR EXISTS (
           SELECT 1 FROM courses
           WHERE tenant_id IS NOT NULL OR curriculum_course_adoption_id IS NOT NULL
       )
    THEN RAISE EXCEPTION '0003 downgrade requires empty organization/curriculum records'; END IF;
END $$;
"""
