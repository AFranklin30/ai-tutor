"""Stage 1 tests use direct transactional setup, never a pretend worker/admission implementation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from ai_tutor import models as m


def migrate(engine, revision, downgrade=False):
    config = Config("alembic.ini")
    with engine.begin() as c:
        config.attributes["connection"] = c
        (command.downgrade if downgrade else command.upgrade)(config, revision)


def add_input(c, s, message_id=None, with_job=True, session_id=None):
    message_id = message_id or uuid4()
    session_id = session_id or s.ids["session"]
    sequence = (
        c.scalar(
            update(m.coaching_sessions)
            .where(m.coaching_sessions.c.id == session_id)
            .values(next_message_sequence=m.coaching_sessions.c.next_message_sequence + 1)
            .returning(m.coaching_sessions.c.next_message_sequence)
        )
        - 1
    )
    c.execute(
        insert(m.messages).values(
            id=message_id,
            session_id=session_id,
            session_sequence=sequence,
            author_type="student",
            content="  Original synthetic input.  ",
            processing_status="PENDING",
        )
    )
    if with_job:
        c.execute(insert(m.message_processing_jobs).values(message_id=message_id))
    c.execute(
        insert(m.idempotency_records).values(
            id=uuid4(),
            student_id=s.ids["student"],
            operation="create_student_message",
            idempotency_key=str(message_id),
            message_id=message_id,
        )
    )
    return message_id


def processing(c, message_id):
    now = datetime.now(timezone.utc)
    token = uuid4()
    c.execute(
        update(m.messages)
        .where(m.messages.c.id == message_id)
        .values(processing_status="PROCESSING")
    )
    c.execute(
        update(m.message_processing_jobs)
        .where(m.message_processing_jobs.c.message_id == message_id)
        .values(
            claim_token=token,
            worker_instance_id=uuid4(),
            claimed_at=now,
            lease_expires_at=now + timedelta(seconds=45),
            attempt_deadline_at=now + timedelta(seconds=90),
            next_attempt_at=None,
            finished_at=None,
            cancel_reason=None,
            attempt_count=1,
            cycle_attempt_count=1,
        )
    )
    return token


def complete(c, s, message_id, response_id=None):
    response_id = response_id or uuid4()
    c.execute(
        insert(m.messages).values(
            id=response_id,
            session_id=s.ids["session"],
            author_type="tutor",
            content="Synthetic reply",
            processing_status="COMPLETED",
            in_reply_to_message_id=message_id,
        )
    )
    c.execute(
        update(m.messages)
        .where(m.messages.c.id == message_id)
        .values(processing_status="COMPLETED")
    )
    c.execute(
        update(m.message_processing_jobs)
        .where(m.message_processing_jobs.c.message_id == message_id)
        .values(
            lease_expires_at=None,
            attempt_deadline_at=None,
            finished_at=datetime.now(timezone.utc),
        )
    )
    return response_id


def job(c, message_id):
    return (
        c.execute(
            select(m.message_processing_jobs).where(
                m.message_processing_jobs.c.message_id == message_id
            )
        )
        .mappings()
        .one()
    )


def test_deferred_job_requirement_rolls_back_coupled_input_key_and_counter(seeded):
    s = seeded
    with pytest.raises(IntegrityError, match="requires a processing job"):
        with s.db.begin() as c:
            add_input(c, s, with_job=False)
            # Failure belongs to commit, not the intermediate insert.
            assert c.scalar(select(m.messages.c.id)) is not None
    with s.db.connect() as c:
        assert c.execute(select(m.messages)).all() == []
        assert c.execute(select(m.idempotency_records)).all() == []
        assert (
            c.scalar(
                select(m.coaching_sessions.c.next_message_sequence).where(
                    m.coaching_sessions.c.id == s.ids["session"]
                )
            )
            == 1
        )


def test_valid_pending_processing_completion_and_response_are_atomic(seeded):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
    with s.db.begin() as c:
        token = processing(c, mid)
    with s.db.begin() as c:
        rid = complete(c, s, mid)
    with s.db.connect() as c:
        assert job(c, mid)["claim_token"] == token
        assert (
            c.scalar(select(m.messages.c.in_reply_to_message_id).where(m.messages.c.id == rid))
            == mid
        )
        assert (
            c.scalar(select(m.messages.c.processing_status).where(m.messages.c.id == mid))
            == "COMPLETED"
        )


def test_missing_response_and_response_without_completion_both_roll_back(seeded):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
        processing(c, mid)
    with pytest.raises(IntegrityError, match="invariant violated"):
        with s.db.begin() as c:
            c.execute(
                update(m.messages)
                .where(m.messages.c.id == mid)
                .values(processing_status="COMPLETED")
            )
            c.execute(
                update(m.message_processing_jobs).values(
                    lease_expires_at=None,
                    attempt_deadline_at=None,
                    finished_at=datetime.now(timezone.utc),
                )
            )
    with pytest.raises(IntegrityError, match="invariant violated"):
        with s.db.begin() as c:
            c.execute(
                insert(m.messages).values(
                    id=uuid4(),
                    session_id=s.ids["session"],
                    author_type="tutor",
                    content="not committed",
                    processing_status="COMPLETED",
                    in_reply_to_message_id=mid,
                )
            )
    with s.db.connect() as c:
        assert c.scalar(select(m.messages.c.processing_status)) == "PROCESSING"
        assert len(c.execute(select(m.messages)).all()) == 1


@pytest.mark.parametrize(
    "corruption",
    [
        {"claim_token": None},
        {"worker_instance_id": None},
        {"claimed_at": None},
        {"lease_expires_at": None},
        {"attempt_deadline_at": None},
        {"next_attempt_at": datetime.now(timezone.utc)},
        {"finished_at": datetime.now(timezone.utc)},
        {"cancel_reason": "SESSION_ADMIN_CLOSED"},
        {"lease_expires_at": datetime(2000, 1, 1, tzinfo=timezone.utc)},
        {"attempt_deadline_at": datetime(2000, 1, 1, tzinfo=timezone.utc)},
    ],
)
def test_processing_shape_rejects_direct_sql_corruption(seeded, corruption):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
        processing(c, mid)
    with pytest.raises(IntegrityError, match="invariant violated"):
        with s.db.begin() as c:
            c.execute(
                update(m.message_processing_jobs)
                .where(m.message_processing_jobs.c.message_id == mid)
                .values(**corruption)
            )


@pytest.mark.parametrize(
    "values",
    [
        {"attempt_count": -1},
        {"cycle_attempt_count": -1},
        {"max_attempts": 0},
        {"cycle_attempt_count": 1},
        {"attempt_count": 3, "cycle_attempt_count": 3},
        {"retry_generation": -1},
        {"last_error_code": "MODEL_TIMEOUT"},
        {"last_error_at": datetime.now(timezone.utc)},
        {"last_error_code": "raw-provider-text", "last_error_at": datetime.now(timezone.utc)},
        {"cancel_reason": "guessed_reason"},
    ],
)
def test_job_checks_reject_invalid_counts_and_categories(seeded, values):
    with seeded.db.begin() as c:
        mid = add_input(c, seeded)
    with pytest.raises(IntegrityError):
        with seeded.db.begin() as c:
            c.execute(
                update(m.message_processing_jobs)
                .where(m.message_processing_jobs.c.message_id == mid)
                .values(**values)
            )


def test_retry_metadata_and_failed_cancelled_shapes(seeded):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
        processing(c, mid)
    now = datetime.now(timezone.utc)
    with s.db.begin() as c:
        c.execute(
            update(m.messages).where(m.messages.c.id == mid).values(processing_status="PENDING")
        )
        c.execute(
            update(m.message_processing_jobs).values(
                claim_token=None,
                worker_instance_id=None,
                claimed_at=None,
                lease_expires_at=None,
                attempt_deadline_at=None,
                next_attempt_at=now + timedelta(seconds=2),
                last_error_code="MODEL_TIMEOUT",
                last_error_at=now,
            )
        )
    with s.db.begin() as c:
        processing(c, mid)
        c.execute(
            update(m.messages).where(m.messages.c.id == mid).values(processing_status="FAILED")
        )
        c.execute(
            update(m.message_processing_jobs).values(
                lease_expires_at=None,
                attempt_deadline_at=None,
                finished_at=now,
            )
        )
    with s.db.begin() as c:
        c.execute(
            update(m.messages).where(m.messages.c.id == mid).values(processing_status="CANCELLED")
        )
        c.execute(
            update(m.message_processing_jobs).values(
                claim_token=None,
                cancel_reason="SESSION_ADMIN_CLOSED",
            )
        )
    with s.db.connect() as c:
        assert job(c, mid)["last_error_code"] == "MODEL_TIMEOUT"
    with pytest.raises(IntegrityError, match="invalid processing transition"):
        with s.db.begin() as c:
            processing(c, mid)


@pytest.mark.parametrize(
    "action", ["delete_job", "delete_message", "content", "sequence", "identity"]
)
def test_history_and_job_relationship_cannot_be_removed_or_rewritten(seeded, action):
    s = seeded
    with s.db.begin() as c:
        add_input(c, s)
    with pytest.raises(IntegrityError):
        with s.db.begin() as c:
            if action == "delete_job":
                c.execute(delete(m.message_processing_jobs))
            elif action == "delete_message":
                c.execute(delete(m.messages))
            elif action == "identity":
                c.execute(update(m.message_processing_jobs).values(message_id=uuid4()))
            else:
                c.execute(
                    update(m.messages).values(
                        **(
                            {"content": "rewritten"}
                            if action == "content"
                            else {"session_sequence": 9}
                        )
                    )
                )


def test_duplicate_job_and_duplicate_tutor_response_rejected(seeded):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
        processing(c, mid)
        complete(c, s, mid)
    with pytest.raises(IntegrityError):
        with s.db.begin() as c:
            c.execute(insert(m.message_processing_jobs).values(message_id=mid))
    with pytest.raises(IntegrityError, match="uq_messages_reply"):
        with s.db.begin() as c:
            c.execute(
                insert(m.messages).values(
                    id=uuid4(),
                    session_id=s.ids["session"],
                    author_type="tutor",
                    content="duplicate",
                    processing_status="COMPLETED",
                    in_reply_to_message_id=mid,
                )
            )


@pytest.mark.parametrize("wrong", ["session", "source_author", "tutor_job"])
def test_reply_relationship_and_tutor_job_guards(seeded, wrong):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
        processing(c, mid)
        rid = complete(c, s, mid)
    with pytest.raises(IntegrityError):
        with s.db.begin() as c:
            if wrong == "tutor_job":
                c.execute(insert(m.message_processing_jobs).values(message_id=rid))
            else:
                c.execute(
                    insert(m.messages).values(
                        id=uuid4(),
                        session_id=s.ids["other_session"]
                        if wrong == "session"
                        else s.ids["session"],
                        author_type="tutor",
                        content="invalid relationship",
                        processing_status="COMPLETED",
                        in_reply_to_message_id=mid if wrong == "session" else rid,
                    )
                )


def test_processing_unique_index_arbitrates_concurrent_transactions(seeded):
    s = seeded
    with s.db.begin() as c:
        first, second = add_input(c, s), add_input(c, s)
    entered = Event()

    def competing():
        with pytest.raises(IntegrityError, match="uq_messages_processing_session"):
            with s.db.begin() as c:
                c.execute(text("SET LOCAL lock_timeout = '5s'"))
                entered.set()
                processing(c, second)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with s.db.begin() as c:
            processing(c, first)
            future = pool.submit(competing)
            assert entered.wait(5)
        future.result(timeout=10)
    with s.db.connect() as c:
        assert (
            c.scalar(select(m.messages.c.processing_status).where(m.messages.c.id == second))
            == "PENDING"
        )


@pytest.mark.parametrize(
    "status,reason",
    [
        ("CLOSED", None),
        ("CLOSED", "GUESSED"),
        ("ACTIVE", "NORMAL"),
    ],
)
def test_session_closure_requires_representable_reason(seeded, status, reason):
    with pytest.raises(IntegrityError):
        with seeded.db.begin() as c:
            c.execute(update(m.coaching_sessions).values(status=status, closure_reason=reason))


def test_legacy_admission_write_remains_rejected(seeded, monkeypatch):
    from ai_tutor.repository import MessageRepository

    s = seeded

    def legacy_insert(repo, session_id, content, trace_id, session_sequence):
        # Simulate the obsolete writer deliberately; keep the Stage 1 negative assertions.
        mid = uuid4()
        repo.session.execute(
            insert(m.messages).values(
                id=mid,
                session_id=session_id,
                content=content,
                trace_id=trace_id,
                author_type="student",
                processing_status="PENDING",
            )
        )
        return mid

    monkeypatch.setattr(MessageRepository, "insert_message", legacy_insert)
    response = s.client.post(
        s.url, json={"content": "old admission"}, headers={"Idempotency-Key": "stage1-boundary"}
    )
    assert response.status_code == 503
    with s.db.connect() as c:
        assert c.execute(select(m.messages)).all() == []
        assert c.execute(select(m.idempotency_records)).all() == []
        assert c.execute(select(m.message_processing_jobs)).all() == []


def test_triggers_are_installed_and_deferred(database):
    with database.connect() as c:
        triggers = c.execute(
            text("""
            SELECT tgname, tgdeferrable, tginitdeferred FROM pg_trigger
            WHERE tgrelid IN ('messages'::regclass, 'message_processing_jobs'::regclass)
              AND NOT tgisinternal
        """)
        ).all()
        assert len(triggers) == 4
        for name, deferred, initially in triggers:
            assert (deferred, initially) == (
                (True, True) if name.endswith("consistency") else (False, False)
            )
        assert "status" not in m.message_processing_jobs.c


def legacy_input(c, s, mid=None, status="PENDING", author="student", key=True):
    mid = mid or uuid4()
    c.execute(
        text("""INSERT INTO messages
        (id, session_id, author_type, content, processing_status, created_at)
        VALUES (:id, :session, :author, '  Exact legacy input.  ', :status, '2026-10-01T00:00:00Z')
    """),
        dict(id=mid, session=s.ids["session"], author=author, status=status),
    )
    if key:
        c.execute(
            insert(m.idempotency_records).values(
                id=uuid4(),
                student_id=s.ids["student"],
                operation="create_student_message",
                idempotency_key=str(mid),
                message_id=mid,
            )
        )
    return mid


@pytest.mark.parametrize("database", ["0001"], indirect=True)
@pytest.mark.parametrize(
    "fault,reason",
    [
        (None, None),
        ("closed", "SESSION_CLOSURE_UNKNOWN"),
        ("disabled", "ACCOUNT_DISABLED"),
        ("enrollment", "ENROLLMENT_REVOKED"),
        ("eligibility", "COURSEWORK_INELIGIBLE"),
        ("problem", "COURSEWORK_INELIGIBLE"),
    ],
)
def test_legacy_pending_backfill_preserves_history_and_fails_closed(seeded, fault, reason):
    s = seeded
    ids = [UUID(int=2), UUID(int=1)]
    with s.db.begin() as c:
        for mid in ids:
            legacy_input(c, s, mid)
        if fault == "closed":
            c.execute(
                text("UPDATE coaching_sessions SET status='CLOSED' WHERE id=:id"),
                {"id": s.ids["session"]},
            )
        elif fault == "disabled":
            c.execute(
                update(m.users).where(m.users.c.id == s.ids["student"]).values(is_active=False)
            )
        elif fault == "enrollment":
            c.execute(
                delete(m.enrollments).where(m.enrollments.c.student_user_id == s.ids["student"])
            )
        elif fault == "eligibility":
            c.execute(delete(m.student_assignment_eligibility))
        elif fault == "problem":
            c.execute(delete(m.assignment_problems))
    migrate(s.db, "head")
    with s.db.connect() as c:
        rows = (
            c.execute(select(m.messages).order_by(m.messages.c.session_sequence)).mappings().all()
        )
        assert [r["id"] for r in rows] == list(reversed(ids))
        assert [r["session_sequence"] for r in rows] == [1, 2]
        assert all(r["content"] == "  Exact legacy input.  " for r in rows)
        assert all(r["processing_status"] == ("CANCELLED" if reason else "PENDING") for r in rows)
        assert all(job(c, mid)["cancel_reason"] == reason for mid in ids)
        assert len(c.execute(select(m.idempotency_records)).all()) == 2
        session = (
            c.execute(
                select(m.coaching_sessions).where(m.coaching_sessions.c.id == s.ids["session"])
            )
            .mappings()
            .one()
        )
        assert session["next_message_sequence"] == 3
        assert session["closure_reason"] == ("UNKNOWN" if fault == "closed" else None)


@pytest.mark.parametrize("database", ["0001"], indirect=True)
@pytest.mark.parametrize(
    "status,author,key",
    [
        ("PROCESSING", "student", True),
        ("FAILED", "student", True),
        ("COMPLETED", "student", True),
        ("COMPLETED", "tutor", True),
        ("PENDING", "student", False),
    ],
)
def test_ambiguous_legacy_history_aborts_migration_atomically(seeded, status, author, key):
    s = seeded
    with s.db.begin() as c:
        legacy_input(c, s, status=status, author=author, key=key)
    with pytest.raises(DBAPIError, match="requires review"):
        migrate(s.db, "head")
    with s.db.connect() as c:
        assert c.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        assert c.scalar(text("SELECT to_regclass('message_processing_jobs')")) is None
        assert c.scalar(text("SELECT processing_status FROM messages")) == status


def test_populated_downgrade_is_rejected_without_losing_history(seeded):
    with seeded.db.begin() as c:
        mid = add_input(c, seeded)
    with pytest.raises(DBAPIError, match="requires empty message history"):
        migrate(seeded.db, "0001", downgrade=True)
    with seeded.db.connect() as c:
        assert c.scalar(text("SELECT version_num FROM alembic_version")) == "0002"
        assert job(c, mid)["message_id"] == mid


@pytest.mark.parametrize("target", ["FAILED", "CANCELLED", "COMPLETED"])
def test_terminal_shapes_reject_missing_required_metadata(seeded, target):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
        processing(c, mid)
    with pytest.raises(IntegrityError, match="invariant violated"):
        with s.db.begin() as c:
            if target == "COMPLETED":
                complete(c, s, mid)
                c.execute(update(m.message_processing_jobs).values(claim_token=None))
            else:
                c.execute(
                    update(m.messages)
                    .where(m.messages.c.id == mid)
                    .values(processing_status=target)
                )
                c.execute(
                    update(m.message_processing_jobs).values(
                        claim_token=None,
                        lease_expires_at=None,
                        attempt_deadline_at=None,
                        finished_at=datetime.now(timezone.utc),
                        # FAILED has no error; CANCELLED has no cancellation reason.
                    )
                )
    with s.db.connect() as c:
        assert c.scalar(select(m.messages.c.processing_status)) == "PROCESSING"
        assert len(c.execute(select(m.messages)).all()) == 1


def test_sequence_uniqueness_and_pending_ownership_fields(seeded):
    s = seeded
    with s.db.begin() as c:
        mid = add_input(c, s)
    with pytest.raises(IntegrityError, match="uq_messages_session_sequence"):
        with s.db.begin() as c:
            c.execute(
                insert(m.messages).values(
                    id=uuid4(),
                    session_id=s.ids["session"],
                    session_sequence=1,
                    author_type="student",
                    content="duplicate sequence",
                    processing_status="PENDING",
                )
            )
    with pytest.raises(IntegrityError, match="invariant violated"):
        with s.db.begin() as c:
            c.execute(
                update(m.message_processing_jobs)
                .where(m.message_processing_jobs.c.message_id == mid)
                .values(claim_token=uuid4())
            )


@pytest.mark.parametrize("database", ["0001"], indirect=True)
def test_backfill_and_ddl_roll_back_on_late_migration_failure(seeded):
    from sqlalchemy import event

    s = seeded
    with s.db.begin() as c:
        legacy_input(c, s)
        c.execute(
            text("UPDATE coaching_sessions SET status='CLOSED' WHERE id=:id"),
            {"id": s.ids["session"]},
        )

    def fail_after_backfill(conn, cursor, statement, parameters, context, executemany):
        if "CREATE FUNCTION assert_message_processing" in statement:
            # Verify DDL/backfill actually ran before forcing failure.
            assert conn.scalar(text("SELECT processing_status FROM messages")) == "CANCELLED"
            raise RuntimeError("injected after backfill")

    event.listen(s.db, "before_cursor_execute", fail_after_backfill)
    try:
        with pytest.raises(RuntimeError, match="injected after backfill"):
            migrate(s.db, "head")
    finally:
        event.remove(s.db, "before_cursor_execute", fail_after_backfill)
    with s.db.connect() as c:
        assert c.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        assert c.scalar(text("SELECT processing_status FROM messages")) == "PENDING"
        assert c.scalar(text("SELECT to_regclass('message_processing_jobs')")) is None
        assert (
            c.scalar(
                text("""
            SELECT count(*) FROM pg_attribute WHERE attrelid='messages'::regclass
              AND attname='session_sequence' AND NOT attisdropped
        """)
            )
            == 0
        )


@pytest.mark.parametrize("database", ["0001"], indirect=True)
def test_upgraded_legacy_input_replays_and_new_admission_continues_sequence(seeded):
    s = seeded
    with s.db.begin() as c:
        mid = legacy_input(c, s)
    migrate(s.db, "head")
    with s.db.connect() as c:
        original_job = dict(job(c, mid))
    replay = s.client.post(
        s.url,
        json={"content": "  Exact legacy input.  "},
        headers={"Idempotency-Key": str(mid)},
    )
    assert replay.status_code == 200
    assert replay.json() == {"student_message_id": str(mid), "status": "PENDING"}
    created = s.client.post(
        s.url, json={"content": "next accepted input"}, headers={"Idempotency-Key": "after-upgrade"}
    )
    assert created.status_code == 201
    new_id = UUID(created.json()["student_message_id"])
    with s.db.connect() as c:
        assert dict(job(c, mid)) == original_job
        assert job(c, new_id)["attempt_count"] == 0
        assert c.scalar(select(m.messages.c.session_sequence).where(m.messages.c.id == new_id)) == 2
        assert (
            c.scalar(
                select(m.coaching_sessions.c.next_message_sequence).where(
                    m.coaching_sessions.c.id == s.ids["session"]
                )
            )
            == 3
        )
        assert len(c.execute(select(m.message_processing_jobs)).all()) == 2
