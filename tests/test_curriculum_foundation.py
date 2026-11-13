"""Stage 3 organization/curriculum persistence constraints (PostgreSQL)."""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import IntegrityError

from ai_tutor import models as m


def add_user(conn, *, role="STUDENT"):
    user_id = uuid4()
    conn.execute(insert(m.users).values(id=user_id, role=role, display_name="Synthetic fixture"))
    return user_id


def add_organization(conn, name="Synthetic organization"):
    org_id = uuid4()
    conn.execute(insert(m.organizations).values(id=org_id, name=name))
    return org_id


def add_tenant(conn, org_id, name="Synthetic tenant"):
    tenant_id = uuid4()
    conn.execute(insert(m.tenants).values(id=tenant_id, organization_id=org_id, name=name))
    return tenant_id


def add_library(conn, owner_kind, name, *, user_id=None, organization_id=None):
    library_id = uuid4()
    conn.execute(
        insert(m.curriculum_libraries).values(
            id=library_id,
            owner_kind=owner_kind,
            owner_user_id=user_id,
            owner_organization_id=organization_id,
            name=name,
        )
    )
    return library_id


def add_curriculum_course(conn, library_id, title="Synthetic template"):
    course_id = uuid4()
    conn.execute(
        insert(m.curriculum_courses).values(
            id=course_id,
            library_id=library_id,
            title=title,
            description="Synthetic description",
            subject="Synthetic subject",
            grade_level=7,
            created_by_user_id=conn.execute(select(m.users.c.id).limit(1)).scalar_one(),
        )
    )
    return course_id


def test_organization_tenant_membership_and_role_scope(database):
    with database.begin() as conn:
        user_id = add_user(conn)
        grantor_id = add_user(conn, role="TEACHER")
        org_a = add_organization(conn, "Org A")
        org_b = add_organization(conn, "Org B")
        tenant_a1 = add_tenant(conn, org_a, "Tenant A1")
        tenant_a2 = add_tenant(conn, org_a, "Tenant A2")
        tenant_b = add_tenant(conn, org_b, "Tenant B")
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.tenants)
                    .where(m.tenants.c.id == tenant_a2)
                    .values(organization_id=org_b)
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.tenants).values(
                        id=uuid4(), organization_id=uuid4(), name="Unknown owner"
                    )
                )

        membership_a1 = uuid4()
        membership_a2 = uuid4()
        conn.execute(
            insert(m.tenant_memberships),
            [
                {
                    "id": membership_a1,
                    "tenant_id": tenant_a1,
                    "user_id": user_id,
                    "created_by_user_id": grantor_id,
                },
                {
                    "id": membership_a2,
                    "tenant_id": tenant_a2,
                    "user_id": user_id,
                    "created_by_user_id": grantor_id,
                },
            ],
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.tenant_memberships).values(
                        id=uuid4(),
                        tenant_id=tenant_a1,
                        user_id=user_id,
                        created_by_user_id=grantor_id,
                    )
                )

        org_membership_id = uuid4()
        conn.execute(
            insert(m.organization_memberships).values(
                id=org_membership_id,
                organization_id=org_a,
                user_id=user_id,
                created_by_user_id=grantor_id,
            )
        )
        conn.execute(
            insert(m.organization_memberships).values(
                id=uuid4(),
                organization_id=org_b,
                user_id=user_id,
                created_by_user_id=grantor_id,
            )
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.organization_memberships).values(
                        id=uuid4(),
                        organization_id=org_a,
                        user_id=user_id,
                        created_by_user_id=grantor_id,
                    )
                )
        # Codes remain opaque storage values; no product role vocabulary is seeded here.
        role_id = uuid4()
        conn.execute(
            insert(m.tenant_membership_roles).values(
                id=role_id,
                tenant_id=tenant_a1,
                tenant_membership_id=membership_a1,
                role_code="test-only-opaque-code",
                granted_by_user_id=grantor_id,
            )
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.tenant_membership_roles).values(
                        id=uuid4(),
                        tenant_id=tenant_b,
                        tenant_membership_id=membership_a1,
                        role_code="test-only-opaque-code",
                        granted_by_user_id=grantor_id,
                    )
                )
        conn.execute(
            insert(m.organization_membership_roles).values(
                id=uuid4(),
                organization_id=org_a,
                organization_membership_id=org_membership_id,
                role_code="test-only-opaque-code",
                granted_by_user_id=grantor_id,
            )
        )
        conn.execute(
            insert(m.organization_curriculum_permissions).values(
                id=uuid4(),
                organization_id=org_a,
                organization_membership_id=org_membership_id,
                capability_code="test-only-opaque-code",
                granted_by_user_id=grantor_id,
            )
        )
        conn.execute(
            update(m.tenant_memberships)
            .where(m.tenant_memberships.c.id == membership_a2)
            .values(deactivated_at=func.now())
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.tenant_memberships)
                    .where(m.tenant_memberships.c.id == membership_a2)
                    .values(created_by_user_id=user_id)
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.organization_membership_roles).values(
                        id=uuid4(),
                        organization_id=org_b,
                        organization_membership_id=org_membership_id,
                        role_code="test-only-opaque-code",
                        granted_by_user_id=grantor_id,
                    )
                )
        assert len(conn.execute(select(m.tenants.c.id)).all()) == 3


def test_library_owner_shape_and_curriculum_hierarchy_are_preserved(database):
    with database.begin() as conn:
        user_id = add_user(conn)
        org_id = add_organization(conn)
        other_org_id = add_organization(conn, "Other organization")
        system_library = add_library(conn, "SYSTEM", "System library")
        personal_library = add_library(conn, "PERSONAL", "Personal library", user_id=user_id)
        org_library = add_library(
            conn, "ORGANIZATION", "Organization library", organization_id=org_id
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.curriculum_libraries)
                    .where(m.curriculum_libraries.c.id == org_library)
                    .values(owner_organization_id=other_org_id)
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.curriculum_libraries).values(
                        id=uuid4(),
                        owner_kind="PERSONAL",
                        owner_user_id=user_id,
                        owner_organization_id=org_id,
                        name="Invalid mixed owner",
                    )
                )

        course_id = add_curriculum_course(conn, org_library)
        unit_id = uuid4()
        conn.execute(
            insert(m.curriculum_units).values(
                id=unit_id,
                curriculum_course_id=course_id,
                title="Synthetic unit",
                description="Synthetic unit description",
                sequence_order=1,
                created_by_user_id=user_id,
            )
        )
        lesson_id = uuid4()
        conn.execute(
            insert(m.curriculum_lessons).values(
                id=lesson_id,
                curriculum_unit_id=unit_id,
                title="Synthetic lesson",
                content="Synthetic lesson content",
                sequence_order=1,
                created_by_user_id=user_id,
            )
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.curriculum_courses)
                    .where(m.curriculum_courses.c.id == course_id)
                    .values(title="In-place edit is rejected")
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.curriculum_units)
                    .where(m.curriculum_units.c.id == unit_id)
                    .values(title="In-place unit edit is rejected")
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.curriculum_lessons)
                    .where(m.curriculum_lessons.c.id == lesson_id)
                    .values(content="In-place lesson edit is rejected")
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.curriculum_units).values(
                        id=uuid4(),
                        curriculum_course_id=uuid4(),
                        title="Orphan unit",
                        description="Invalid parent",
                        sequence_order=2,
                        created_by_user_id=user_id,
                    )
                )
        assert conn.execute(select(m.curriculum_lessons.c.id)).scalar_one() == lesson_id
        assert len({system_library, personal_library, org_library}) == 3


def test_shared_adoption_derivation_and_tenant_offering_integrity(database):
    with database.begin() as conn:
        user_id = add_user(conn)
        org_id = add_organization(conn)
        adopting_org_id = add_organization(conn, "Adopting organization")
        tenant_a = add_tenant(conn, org_id, "Tenant A")
        tenant_b = add_tenant(conn, adopting_org_id, "Tenant B")
        system_library = add_library(conn, "SYSTEM", "Shared system library")
        personal_library = add_library(conn, "PERSONAL", "Private library", user_id=user_id)
        org_library = add_library(conn, "ORGANIZATION", "Org library", organization_id=org_id)
        source_course = add_curriculum_course(conn, system_library, "Shared course")
        adoption_a = uuid4()
        conn.execute(
            insert(m.tenant_curriculum_course_adoptions).values(
                id=adoption_a,
                tenant_id=tenant_a,
                source_library_id=system_library,
                curriculum_course_id=source_course,
                adopted_by_user_id=user_id,
            )
        )
        offering_id = uuid4()
        conn.execute(
            insert(m.courses).values(
                id=offering_id,
                name="Tenant A offering",
                grade_level=7,
                subject="Mathematics",
                tenant_id=tenant_a,
                curriculum_course_adoption_id=adoption_a,
            )
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.courses).values(
                        id=uuid4(),
                        name="Cross-tenant offering",
                        grade_level=7,
                        subject="Mathematics",
                        tenant_id=tenant_b,
                        curriculum_course_adoption_id=adoption_a,
                    )
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.tenant_curriculum_course_adoptions).values(
                        id=uuid4(),
                        tenant_id=tenant_a,
                        source_library_id=personal_library,
                        curriculum_course_id=add_curriculum_course(
                            conn, personal_library, "Private course"
                        ),
                        adopted_by_user_id=user_id,
                    )
                )

        organization_source_course = add_curriculum_course(
            conn, org_library, "Organization-owned shared course"
        )
        adoption_b = uuid4()
        conn.execute(
            insert(m.tenant_curriculum_course_adoptions).values(
                id=adoption_b,
                tenant_id=tenant_b,
                source_library_id=org_library,
                curriculum_course_id=organization_source_course,
                adopted_by_user_id=user_id,
            )
        )
        conn.execute(
            insert(m.courses).values(
                id=uuid4(),
                name="Cross-organization reference offering",
                grade_level=7,
                subject="Mathematics",
                tenant_id=tenant_b,
                curriculum_course_adoption_id=adoption_b,
            )
        )

        target_course = add_curriculum_course(conn, org_library, "Org derivative")
        conn.execute(
            insert(m.curriculum_course_derivations).values(
                id=uuid4(),
                target_organization_id=org_id,
                target_library_id=org_library,
                target_course_id=target_course,
                source_library_id=system_library,
                source_course_id=source_course,
                derived_by_user_id=user_id,
            )
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.curriculum_course_derivations)
                    .where(m.curriculum_course_derivations.c.target_course_id == target_course)
                    .values(source_course_id=uuid4())
                )
        source_unit = uuid4()
        target_unit = uuid4()
        for unit_id, course_id, title in (
            (source_unit, source_course, "Source unit"),
            (target_unit, target_course, "Derived unit"),
        ):
            conn.execute(
                insert(m.curriculum_units).values(
                    id=unit_id,
                    curriculum_course_id=course_id,
                    title=title,
                    description=title,
                    sequence_order=1,
                    created_by_user_id=user_id,
                )
            )
        conn.execute(
            insert(m.curriculum_unit_derivations).values(
                id=uuid4(),
                target_course_id=target_course,
                target_unit_id=target_unit,
                source_course_id=source_course,
                source_unit_id=source_unit,
                derived_by_user_id=user_id,
            )
        )
        source_lesson = uuid4()
        target_lesson = uuid4()
        for lesson_id, unit_id, title in (
            (source_lesson, source_unit, "Source lesson"),
            (target_lesson, target_unit, "Derived lesson"),
        ):
            conn.execute(
                insert(m.curriculum_lessons).values(
                    id=lesson_id,
                    curriculum_unit_id=unit_id,
                    title=title,
                    content=title,
                    sequence_order=1,
                    created_by_user_id=user_id,
                )
            )
        conn.execute(
            insert(m.curriculum_lesson_derivations).values(
                id=uuid4(),
                target_unit_id=target_unit,
                target_lesson_id=target_lesson,
                source_unit_id=source_unit,
                source_lesson_id=source_lesson,
                derived_by_user_id=user_id,
            )
        )
        conn.execute(
            update(m.tenant_curriculum_course_adoptions)
            .where(m.tenant_curriculum_course_adoptions.c.id == adoption_a)
            .values(retired_at=func.now(), retired_by_user_id=user_id)
        )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    update(m.tenant_curriculum_course_adoptions)
                    .where(m.tenant_curriculum_course_adoptions.c.id == adoption_a)
                    .values(curriculum_course_id=organization_source_course)
                )
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(
                    insert(m.courses).values(
                        id=uuid4(),
                        name="Offering through retired adoption",
                        grade_level=7,
                        subject="Mathematics",
                        tenant_id=tenant_a,
                        curriculum_course_adoption_id=adoption_a,
                    )
                )
        assert (
            conn.execute(
                select(m.courses.c.curriculum_course_adoption_id).where(
                    m.courses.c.id == offering_id
                )
            ).scalar_one()
            == adoption_a
        )


def test_adoption_retirement_serializes_with_new_course_offering(database):
    tenant_id, adoption_id = uuid4(), uuid4()
    with database.begin() as conn:
        user_id = add_user(conn)
        org_id = add_organization(conn)
        tenant_id = add_tenant(conn, org_id)
        library_id = add_library(conn, "SYSTEM", "Shared system library")
        course_id = add_curriculum_course(conn, library_id)
        conn.execute(
            insert(m.tenant_curriculum_course_adoptions).values(
                id=adoption_id,
                tenant_id=tenant_id,
                source_library_id=library_id,
                curriculum_course_id=course_id,
                adopted_by_user_id=add_user(conn),
            )
        )

    retirement = database.connect()
    transaction = retirement.begin()
    retirement.execute(
        update(m.tenant_curriculum_course_adoptions)
        .where(m.tenant_curriculum_course_adoptions.c.id == adoption_id)
        .values(retired_at=func.now(), retired_by_user_id=user_id)
    )
    started = Event()

    def insert_offering():
        with database.begin() as conn:
            conn.execute(text("SET LOCAL application_name = 'm3_adoption_race'"))
            started.set()
            conn.execute(
                insert(m.courses).values(
                    id=uuid4(),
                    name="Concurrent offering",
                    grade_level=7,
                    subject="Mathematics",
                    tenant_id=tenant_id,
                    curriculum_course_adoption_id=adoption_id,
                )
            )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(insert_offering)
            assert started.wait(timeout=3)
            deadline = time.monotonic() + 3
            wait_event = None
            while time.monotonic() < deadline and not future.done():
                with database.connect() as observer:
                    wait_event = observer.scalar(
                        text(
                            "SELECT wait_event_type FROM pg_stat_activity "
                            "WHERE application_name = 'm3_adoption_race' AND state = 'active'"
                        )
                    )
                if wait_event == "Lock":
                    break
                time.sleep(0.01)
            transaction.commit()
            assert wait_event == "Lock"
            with pytest.raises(IntegrityError):
                future.result(timeout=3)
    finally:
        if transaction.is_active:
            transaction.rollback()
        retirement.close()
