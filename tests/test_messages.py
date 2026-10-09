import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, func, insert, select, update
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from ai_tutor import models as m
from ai_tutor.repository import MessageRepository


def send(s, content="I need a hint.", key="send-1", **kwargs):
    return s.client.post(
        s.url, json={"content": content}, headers={"Idempotency-Key": key}, **kwargs
    )


def counts(s):
    with s.db.connect() as c:
        result = tuple(
            c.scalar(select(func.count()).select_from(t))
            for t in (m.messages, m.idempotency_records)
        )
        # These admission tests create student inputs only: every input needs exactly one job.
        assert c.scalar(select(func.count()).select_from(m.message_processing_jobs)) == result[0]
        return result


def test_created_pending_visible_after_commit(seeded):
    s = seeded
    content = "  A hint?\n\tÉquation 🙂  "
    r = send(s, content)
    assert r.status_code == 201
    assert set(r.json()) == {"student_message_id", "status"}
    assert r.json()["status"] == "PENDING"
    with s.db.connect() as c:
        row = c.execute(select(m.messages)).mappings().one()
        assert row["id"] == UUID(r.json()["student_message_id"])
        assert row["content"] == content
        assert row["processing_status"] == "PENDING"
        assert row["author_type"] == "student"
        assert row["session_id"] == s.ids["session"]
        assert len(row["trace_id"]) == 32
        assert row["created_at"].tzinfo is not None
        assert c.execute(select(m.idempotency_records.c.message_id)).scalar_one() == row["id"]
        assert row["session_sequence"] == 1
        job = c.execute(select(m.message_processing_jobs)).mappings().one()
        assert job["message_id"] == row["id"]
        assert job["attempt_count"] == job["cycle_attempt_count"] == job["retry_generation"] == 0
        assert job["claim_token"] is None and job["lease_expires_at"] is None
        assert job["next_attempt_at"] is not None
        assert (
            c.scalar(
                select(m.coaching_sessions.c.next_message_sequence).where(
                    m.coaching_sessions.c.id == s.ids["session"]
                )
            )
            == 2
        )


@pytest.mark.parametrize(
    "authorization", [None, "Bearer unknown", "Basic abc", "Bearer", "Bearer a b"]
)
def test_authentication(seeded, authorization):
    s = seeded
    del s.client.headers["Authorization"]
    if authorization:
        s.client.headers["Authorization"] = authorization
    r = send(s)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert counts(s) == (0, 0)


def test_inactive_and_missing_user(seeded):
    s = seeded
    with s.db.begin() as c:
        c.execute(update(m.users).where(m.users.c.id == s.ids["student"]).values(is_active=False))
    assert send(s).status_code == 401
    assert counts(s) == (0, 0)


def test_teacher_cannot_send(seeded):
    s = seeded
    s.client.headers["Authorization"] = "Bearer " + s.tokens["teacher"]
    assert send(s).status_code == 403
    assert counts(s) == (0, 0)


def test_other_session_and_nonexistent_indistinguishable(seeded):
    s = seeded
    bodies = []
    for session_id in (s.ids["other_session"], uuid4()):
        r = s.client.post(
            f"/api/v1/coaching/sessions/{session_id}/messages",
            json={"content": "hint"},
            headers={"Idempotency-Key": "a"},
        )
        assert r.status_code == 404
        bodies.append(r.json())
    assert bodies[0] == bodies[1]
    assert counts(s) == (0, 0)


@pytest.mark.parametrize("fault", ["enrollment", "eligibility", "membership", "course"])
def test_business_authorization(seeded, fault):
    s = seeded
    with s.db.begin() as c:
        if fault == "enrollment":
            c.execute(
                delete(m.enrollments).where(m.enrollments.c.student_user_id == s.ids["student"])
            )
        elif fault == "eligibility":
            c.execute(
                delete(m.student_assignment_eligibility).where(
                    m.student_assignment_eligibility.c.student_user_id == s.ids["student"]
                )
            )
        elif fault == "membership":
            c.execute(delete(m.assignment_problems))
        else:
            other_course = uuid4()
            c.execute(
                insert(m.courses).values(
                    id=other_course, name="Other", grade_level=7, subject="Math"
                )
            )
            c.execute(update(m.problems).values(course_id=other_course))
    assert send(s).status_code == (404 if fault == "enrollment" else 403)
    assert counts(s) == (0, 0)


def test_closed_new_send_but_replay_allowed(seeded):
    s = seeded
    first = send(s)
    with s.db.begin() as c:
        c.execute(
            update(m.coaching_sessions)
            .where(m.coaching_sessions.c.id == s.ids["session"])
            .values(status="CLOSED", closure_reason="NORMAL")
        )
    replay = send(s)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert send(s, key="new-key").status_code == 409
    assert counts(s) == (1, 1)


@pytest.mark.parametrize("key", [None, "", "has space", "tab\tkey", "x" * 256])
def test_invalid_idempotency_key(seeded, key):
    s = seeded
    r = s.client.post(
        s.url, json={"content": "hint"}, headers={} if key is None else {"Idempotency-Key": key}
    )
    assert r.status_code == 422
    assert counts(s) == (0, 0)


@pytest.mark.parametrize("key", ["!", "~" * 255])
def test_key_boundaries(seeded, key):
    assert send(seeded, key=key).status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {"content": ""},
        {"content": " \n\t"},
        {"content": 1},
        {},
        {"content": "x" * 4001},
        {"content": "hint", "student_id": "another-student"},
        {"content": "hint", "teacher_id": "teacher"},
    ],
)
def test_invalid_body_before_auth_without_echo(seeded, body):
    s = seeded
    del s.client.headers["Authorization"]
    r = s.client.post(s.url, json=body, headers={"Idempotency-Key": "key"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert "another-student" not in r.text
    assert counts(s) == (0, 0)


def test_authenticated_client_cannot_override_identity(seeded):
    s = seeded
    r = s.client.post(
        s.url,
        json={"content": "hint", "student_id": str(s.ids["other"])},
        headers={"Idempotency-Key": "key"},
    )
    assert r.status_code == 422
    assert counts(s) == (0, 0)


def test_replay_canonical_json_and_exact_content_conflict(seeded):
    s = seeded
    first = send(s, "é  ")
    r = s.client.post(
        s.url,
        content=' { "content" : "\\u00e9  " } ',
        headers={"Idempotency-Key": "send-1", "Content-Type": "application/json"},
    )
    assert r.status_code == 200
    assert r.json() == first.json()
    assert send(s, "é").status_code == 409
    assert counts(s) == (1, 1)


def test_key_scope_is_student_and_operation_not_session(seeded):
    s = seeded
    first = send(s)
    new_session = uuid4()
    with s.db.begin() as c:
        c.execute(
            insert(m.coaching_sessions).values(
                id=new_session,
                student_user_id=s.ids["student"],
                course_id=s.ids["course"],
                assignment_id=s.ids["assignment"],
                problem_id=s.ids["problem"],
                status="ACTIVE",
            )
        )
    s.url = f"/api/v1/coaching/sessions/{new_session}/messages"
    assert send(s).json() == first.json()
    assert counts(s) == (1, 1)
    s.client.headers["Authorization"] = "Bearer " + s.tokens["other"]
    s.url = f"/api/v1/coaching/sessions/{s.ids['other_session']}/messages"
    other = send(s)
    assert other.status_code == 201
    assert other.json()["student_message_id"] != first.json()["student_message_id"]
    assert counts(s) == (2, 2)


def test_replay_still_checks_authorization(seeded):
    s = seeded
    send(s)
    with s.db.begin() as c:
        c.execute(delete(m.enrollments).where(m.enrollments.c.student_user_id == s.ids["student"]))
    assert send(s).status_code == 404
    assert counts(s) == (1, 1)


def test_replay_reads_current_processing_state_without_processing(seeded, mark_message_failed):
    s = seeded
    first = send(s)
    with s.db.begin() as c:
        mark_message_failed(c, UUID(first.json()["student_message_id"]))
    r = send(s)
    assert r.status_code == 200
    assert r.json() == {
        "student_message_id": first.json()["student_message_id"],
        "status": "FAILED",
    }
    assert counts(s) == (1, 1)


@pytest.mark.parametrize("session_status", ["ACTIVE", "CLOSED"])
def test_failed_replay_returns_200_without_processing_writes(
    seeded, session_status, mark_message_failed
):
    s = seeded
    first = send(s)
    assert first.status_code == 201
    message_id = UUID(first.json()["student_message_id"])
    with s.db.begin() as c:
        mark_message_failed(c, message_id)
        c.execute(
            update(m.coaching_sessions)
            .where(m.coaching_sessions.c.id == s.ids["session"])
            .values(
                status=session_status,
                closure_reason="NORMAL" if session_status == "CLOSED" else None,
            )
        )

    def stored_operation():
        with s.db.connect() as c:
            return (
                c.execute(select(m.messages)).all(),
                c.execute(select(m.idempotency_records)).all(),
                c.execute(select(m.message_processing_jobs)).all(),
                c.execute(select(m.coaching_sessions)).all(),
            )

    before = stored_operation()

    def reject_processing_write(conn, cursor, statement, parameters, context, executemany):
        # Replay may lock/read rows, but must not insert work or update processing state.
        # Trap writes to jobs/counters as well as messages; no worker is running.
        assert not (context.isinsert or context.isupdate or context.isdelete)
        assert statement.lstrip().split(None, 1)[0].upper() not in {
            "INSERT",
            "UPDATE",
            "DELETE",
            "MERGE",
            "CALL",
            "WITH",
        }

    event.listen(s.db, "before_cursor_execute", reject_processing_write)
    try:
        for _ in range(2):
            replay = send(s)
            assert replay.status_code == 200
            assert replay.json() == {
                "student_message_id": str(message_id),
                "status": "FAILED",
            }
    finally:
        event.remove(s.db, "before_cursor_execute", reject_processing_write)

    assert stored_operation() == before
    assert counts(s) == (1, 1)


def test_concurrent_duplicate_requests(seeded):
    s = seeded
    barrier = Barrier(6)

    def submit(_):
        with TestClient(s.app) as client:
            barrier.wait(timeout=10)
            return client.post(
                s.url,
                json={"content": "concurrent"},
                headers={
                    "Authorization": "Bearer " + s.tokens["student"],
                    "Idempotency-Key": "same-key",
                },
            )

    with ThreadPoolExecutor(max_workers=6) as pool:
        replies = list(pool.map(submit, range(6)))
    assert sorted(r.status_code for r in replies) == [200, 200, 200, 200, 200, 201]
    assert len({r.json()["student_message_id"] for r in replies}) == 1
    assert counts(s) == (1, 1)


def test_database_unique_constraint_protects_without_service_lock(seeded):
    s = seeded
    send(s)
    with pytest.raises(IntegrityError, match="uq_idempotency_scope"):
        with Session(s.db).begin() as tx:
            repo = MessageRepository(tx.session)
            sequence = repo.allocate_sequence(s.ids["session"])
            message_id = repo.insert_message(s.ids["session"], "duplicate", None, sequence)
            repo.insert_processing_job(message_id)
            repo.associate_key(s.ids["student"], "send-1", message_id)
    assert counts(s) == (1, 1)


def test_rollback_between_message_and_idempotency_insert(seeded, monkeypatch):
    s = seeded
    original = MessageRepository.associate_key

    def fail(*args):
        raise SQLAlchemyError("sensitive-internal-failure")

    monkeypatch.setattr(MessageRepository, "associate_key", fail)
    response = send(s)
    assert response.status_code == 503
    assert "sensitive" not in response.text
    assert counts(s) == (0, 0)
    monkeypatch.setattr(MessageRepository, "associate_key", original)
    assert send(s).status_code == 201


def test_commit_failure_never_returns_success(seeded):
    s = seeded

    def fail_commit(conn):
        raise OperationalError("COMMIT", {}, Exception("simulated commit failure"))

    event.listen(s.db, "commit", fail_commit)
    try:
        response = send(s)
        assert response.status_code == 503
    finally:
        event.remove(s.db, "commit", fail_commit)
    assert counts(s) == (0, 0)
    assert send(s).status_code == 201


def test_lost_response_replay_and_metadata_logs(seeded, caplog):
    s = seeded
    caplog.set_level(logging.INFO, logger="ai_tutor.requests")
    content = "PRIVATE-STUDENT-CONTENT-123"
    # Deliberately discard the successful HTTP response as a lost-delivery simulation.
    send(s, content)
    r = send(s, content)
    assert r.status_code == 200
    assert counts(s) == (1, 1)
    records = [r for r in caplog.records if r.name == "ai_tutor.requests"]
    assert len(records) == 2
    assert all(r.trace_id and r.message_id and r.content_length == len(content) for r in records)
    assert content not in json.dumps([r.__dict__ for r in records], default=str)
    assert s.tokens["student"] not in caplog.text


def test_missing_mapped_user_is_unauthenticated(seeded):
    import hashlib

    from ai_tutor.api import create_app
    from ai_tutor.config import Settings

    settings = Settings(str(seeded.db.url), {hashlib.sha256(b"ghost").hexdigest(): uuid4()})
    with TestClient(create_app(settings, seeded.db)) as client:
        r = client.post(
            seeded.url,
            json={"content": "hint"},
            headers={"Authorization": "Bearer ghost", "Idempotency-Key": "key"},
        )
    assert r.status_code == 401
    assert counts(seeded) == (0, 0)


def test_configurable_length_and_maximum(seeded):
    import hashlib

    from ai_tutor.api import create_app
    from ai_tutor.config import Settings

    s = seeded
    assert send(s, "x" * 4000).status_code == 201
    settings = Settings(
        str(s.db.url),
        {hashlib.sha256(s.tokens["student"].encode()).hexdigest(): s.ids["student"]},
        max_message_characters=3,
    )
    with TestClient(create_app(settings, s.db)) as client:
        r = client.post(
            s.url,
            json={"content": "four"},
            headers={"Authorization": "Bearer " + s.tokens["student"], "Idempotency-Key": "next"},
        )
    assert r.status_code == 422
    assert counts(s) == (1, 1)


def test_duplicate_headers_and_non_ascii_keys(seeded):
    s = seeded
    for headers in (
        [("Idempotency-Key", "a"), ("Idempotency-Key", "b")],
        [(b"Idempotency-Key", b"\xff")],
    ):
        r = s.client.post(s.url, json={"content": "hint"}, headers=headers)
        assert r.status_code == 422
    assert counts(s) == (0, 0)


def test_trace_context_and_error_spans_do_not_capture_private_exception(seeded, monkeypatch):
    import hashlib

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from ai_tutor.api import create_app
    from ai_tutor.config import Settings

    s = seeded
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    settings = Settings(
        str(s.db.url), {hashlib.sha256(s.tokens["student"].encode()).hexdigest(): s.ids["student"]}
    )

    def fail(*args):
        raise SQLAlchemyError("PRIVATE-CONTENT-AND-CREDENTIAL")

    monkeypatch.setattr(MessageRepository, "associate_key", fail)
    trace_id = "1234567890abcdef1234567890abcdef"
    with TestClient(create_app(settings, s.db, provider)) as client:
        response = client.post(
            s.url,
            json={"content": "private message"},
            headers={
                "Authorization": "Bearer " + s.tokens["student"],
                "Idempotency-Key": "key",
                "traceparent": f"00-{trace_id}-1234567890abcdef-01",
            },
        )
    assert response.status_code == 503
    spans = exporter.get_finished_spans()
    assert len(spans) == 2
    assert all(format(span.context.trace_id, "032x") == trace_id for span in spans)
    assert all(not span.events for span in spans)
    assert "PRIVATE-CONTENT" not in "".join(span.to_json() for span in spans)
    provider.shutdown()


def test_distinct_keys_allow_distinct_messages(seeded):
    s = seeded
    first = send(s, key="first")
    second = send(s, key="second")
    assert first.status_code == second.status_code == 201
    assert first.json()["student_message_id"] != second.json()["student_message_id"]
    assert counts(s) == (2, 2)


def test_concurrent_same_key_different_payload(seeded):
    s = seeded
    barrier = Barrier(2)

    def submit(content):
        with TestClient(s.app) as client:
            barrier.wait(timeout=10)
            return client.post(
                s.url,
                json={"content": content},
                headers={
                    "Authorization": "Bearer " + s.tokens["student"],
                    "Idempotency-Key": "race",
                },
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(submit, ["first content", "second content"]))
    assert sorted(r.status_code for r in replies) == [201, 409]
    assert counts(s) == (1, 1)


@pytest.mark.parametrize(
    "boundary", ["allocate_sequence", "insert_message", "insert_processing_job", "associate_key"]
)
def test_admission_rolls_back_every_coupled_write(seeded, monkeypatch, boundary):
    s = seeded
    original = getattr(MessageRepository, boundary)

    def fail_after_write(repo, *args):
        original(repo, *args)
        raise SQLAlchemyError("injected admission write failure")

    monkeypatch.setattr(MessageRepository, boundary, fail_after_write)
    assert send(s).status_code == 503
    assert counts(s) == (0, 0)
    with s.db.connect() as c:
        assert (
            c.scalar(
                select(m.coaching_sessions.c.next_message_sequence).where(
                    m.coaching_sessions.c.id == s.ids["session"]
                )
            )
            == 1
        )
    monkeypatch.setattr(MessageRepository, boundary, original)
    assert send(s).status_code == 201
    with s.db.connect() as c:
        assert c.scalar(select(m.messages.c.session_sequence)) == 1
    assert counts(s) == (1, 1)


def test_concurrent_distinct_admissions_allocate_unique_session_sequences(seeded):
    s = seeded
    barrier = Barrier(6)

    def submit(n):
        with TestClient(s.app) as client:
            barrier.wait(timeout=10)
            return client.post(
                s.url,
                json={"content": f"Distinct input {n}"},
                headers={
                    "Authorization": "Bearer " + s.tokens["student"],
                    "Idempotency-Key": f"distinct-{n}",
                },
            )

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(submit, range(6)))
    assert all(r.status_code == 201 for r in results)
    assert len({r.json()["student_message_id"] for r in results}) == 6
    assert counts(s) == (6, 6)
    with s.db.connect() as c:
        assert c.scalars(
            select(m.messages.c.session_sequence).order_by(m.messages.c.session_sequence)
        ).all() == list(range(1, 7))
        assert (
            c.scalar(
                select(m.coaching_sessions.c.next_message_sequence).where(
                    m.coaching_sessions.c.id == s.ids["session"]
                )
            )
            == 7
        )
        assert set(c.scalars(select(m.message_processing_jobs.c.attempt_count))) == {0}
