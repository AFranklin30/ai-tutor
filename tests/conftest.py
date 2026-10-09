import hashlib
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, text, update

from ai_tutor import models as m
from ai_tutor.api import create_app
from ai_tutor.config import Settings


@pytest.fixture
def database(request):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL must point to a disposable PostgreSQL database")
    admin = create_engine(url, hide_parameters=True)
    schema = "slice1_test_" + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url, hide_parameters=True, connect_args={"options": f"-csearch_path={schema}"}
    )
    config = Config("alembic.ini")
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, getattr(request, "param", "head"))
    try:
        yield engine
    finally:
        engine.dispose()
        # Only this fixture's randomly named schema; never application data/public schema.
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def seeded(database):
    ids = {
        k: uuid4()
        for k in (
            "student",
            "other",
            "teacher",
            "course",
            "assignment",
            "problem",
            "session",
            "other_session",
        )
    }
    with database.begin() as c:
        for who in ("student", "other", "teacher"):
            c.execute(
                insert(m.users).values(
                    id=ids[who],
                    role="TEACHER" if who == "teacher" else "STUDENT",
                    display_name=who,
                )
            )
        c.execute(
            insert(m.courses).values(
                id=ids["course"], name="Demo", grade_level=7, subject="Mathematics"
            )
        )
        c.execute(
            insert(m.assignments).values(
                id=ids["assignment"], course_id=ids["course"], title="Demo", description="Demo"
            )
        )
        c.execute(
            insert(m.problems).values(
                id=ids["problem"], course_id=ids["course"], prompt="Synthetic problem"
            )
        )
        c.execute(
            insert(m.assignment_problems).values(
                assignment_id=ids["assignment"], problem_id=ids["problem"], sequence_order=1
            )
        )
        for who, session in (("student", "session"), ("other", "other_session")):
            c.execute(
                insert(m.enrollments).values(
                    id=uuid4(), student_user_id=ids[who], course_id=ids["course"], status="ACTIVE"
                )
            )
            c.execute(
                insert(m.student_assignment_eligibility).values(
                    student_user_id=ids[who], assignment_id=ids["assignment"]
                )
            )
            c.execute(
                insert(m.coaching_sessions).values(
                    id=ids[session],
                    student_user_id=ids[who],
                    course_id=ids["course"],
                    assignment_id=ids["assignment"],
                    problem_id=ids["problem"],
                    status="ACTIVE",
                )
            )
    tokens = {who: f"synthetic-{who}-credential" for who in ("student", "other", "teacher")}
    settings = Settings(
        str(database.url),
        {hashlib.sha256(token.encode()).hexdigest(): ids[who] for who, token in tokens.items()},
    )
    app = create_app(settings, database)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + tokens["student"]
        yield SimpleNamespace(
            db=database,
            ids=ids,
            tokens=tokens,
            client=client,
            app=app,
            url=f"/api/v1/coaching/sessions/{ids['session']}/messages",
        )


@pytest.fixture
def mark_message_failed():
    """Create valid committed failure data for replay tests, not a worker implementation."""

    def mark(conn, message_id):
        # Follow allowed transitions; deferred triggers inspect the final coupled state.
        conn.execute(
            update(m.messages)
            .where(m.messages.c.id == message_id)
            .values(processing_status="PROCESSING")
        )
        conn.execute(
            update(m.messages)
            .where(m.messages.c.id == message_id)
            .values(processing_status="FAILED")
        )
        now = datetime.now(timezone.utc)
        conn.execute(
            update(m.message_processing_jobs)
            .where(m.message_processing_jobs.c.message_id == message_id)
            .values(
                attempt_count=1,
                cycle_attempt_count=1,
                claim_token=uuid4(),
                worker_instance_id=uuid4(),
                claimed_at=now,
                next_attempt_at=None,
                last_error_code="MODEL_TIMEOUT",
                last_error_at=now,
                finished_at=now,
                updated_at=now,
            )
        )

    return mark
