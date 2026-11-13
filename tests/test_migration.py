from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import insert, inspect, select, text, update
from sqlalchemy.exc import DBAPIError

from ai_tutor import models as m
from ai_tutor.models import metadata


def test_migration_matches_models_and_roundtrips(database):
    config = Config("alembic.ini")
    with database.begin() as conn:
        assert compare_metadata(MigrationContext.configure(conn), metadata) == []
        config.attributes["connection"] = conn
        command.downgrade(config, "base")
        assert inspect(conn).get_table_names() == ["alembic_version"]
        command.upgrade(config, "head")
        assert compare_metadata(MigrationContext.configure(conn), metadata) == []


def test_0003_preserves_legacy_course_rows_as_unscoped_offerings(database):
    config = Config("alembic.ini")
    user_id, course_id = uuid4(), uuid4()
    with database.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "0002")
        conn.execute(
            insert(m.users).values(id=user_id, role="STUDENT", display_name="Synthetic student")
        )
        conn.execute(
            insert(m.courses).values(
                id=course_id,
                name="Legacy course",
                grade_level=7,
                subject="Mathematics",
            )
        )
        command.upgrade(config, "head")
        row = conn.execute(select(m.courses).where(m.courses.c.id == course_id)).mappings().one()
        assert row["name"] == "Legacy course"
        assert row["tenant_id"] is None
        assert row["curriculum_course_adoption_id"] is None


def test_0003_upgrade_preserves_0002_message_processing_history(seeded):
    config = Config("alembic.ini")
    message_id, idempotency_id = uuid4(), uuid4()
    with seeded.db.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "0002")
        sequence = (
            conn.execute(
                update(m.coaching_sessions)
                .where(m.coaching_sessions.c.id == seeded.ids["session"])
                .values(next_message_sequence=m.coaching_sessions.c.next_message_sequence + 1)
                .returning(m.coaching_sessions.c.next_message_sequence)
            ).scalar_one()
            - 1
        )
        conn.execute(
            insert(m.messages).values(
                id=message_id,
                session_id=seeded.ids["session"],
                session_sequence=sequence,
                author_type="student",
                content="Synthetic legacy message",
                processing_status="PENDING",
                trace_id="00000000000000000000000000000003",
            )
        )
        conn.execute(insert(m.message_processing_jobs).values(message_id=message_id))
        conn.execute(
            insert(m.idempotency_records).values(
                id=idempotency_id,
                student_id=seeded.ids["student"],
                operation="create_student_message",
                idempotency_key="migration-0003-preservation",
                message_id=message_id,
            )
        )

    with seeded.db.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
        message = (
            conn.execute(select(m.messages).where(m.messages.c.id == message_id)).mappings().one()
        )
        job = (
            conn.execute(
                select(m.message_processing_jobs).where(
                    m.message_processing_jobs.c.message_id == message_id
                )
            )
            .mappings()
            .one()
        )
        idempotency = (
            conn.execute(
                select(m.idempotency_records).where(m.idempotency_records.c.id == idempotency_id)
            )
            .mappings()
            .one()
        )
        course = (
            conn.execute(select(m.courses).where(m.courses.c.id == seeded.ids["course"]))
            .mappings()
            .one()
        )
        assert message["content"] == "Synthetic legacy message"
        assert message["processing_status"] == "PENDING"
        assert message["session_sequence"] == sequence
        assert job["message_id"] == message_id
        assert job["attempt_count"] == 0
        assert idempotency["message_id"] == message_id
        assert idempotency["student_id"] == seeded.ids["student"]
        assert course["name"] == "Demo"
        assert course["tenant_id"] is None
        assert course["curriculum_course_adoption_id"] is None


def test_0003_refuses_downgrade_when_stage3_records_exist(database):
    config = Config("alembic.ini")
    with database.begin() as conn:
        conn.execute(insert(m.organizations).values(id=uuid4(), name="Synthetic org"))
        config.attributes["connection"] = conn
        try:
            with conn.begin_nested():
                command.downgrade(config, "0002")
        except DBAPIError as exc:
            assert "downgrade requires empty organization/curriculum records" in str(exc)
        else:
            raise AssertionError("populated Stage 3 downgrade should be rejected")
        assert conn.execute(select(m.organizations.c.id)).scalar_one() is not None
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003"
