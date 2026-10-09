"""Real PostgreSQL polling: protected consistent reads without scheduling work."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from ai_tutor import models as m
from ai_tutor.processing_service import ProcessingService
from ai_tutor.repository import MessageRepository


def admit(s):
    response = s.client.post(
        f"/api/v1/coaching/sessions/{s.ids['session']}/messages",
        json={"content": "PRIVATE input"},
        headers={"Authorization": "Bearer " + s.tokens["student"], "Idempotency-Key": "poll"},
    )
    assert response.status_code == 201
    return UUID(response.json()["student_message_id"])


def poll(s, mid, session=None, headers=None):
    return s.client.get(
        f"/api/v1/coaching/sessions/{session or s.ids['session']}/messages/{mid}/status",
        headers=headers
        if headers is not None
        else {"Authorization": "Bearer " + s.tokens["student"]},
    )


@pytest.mark.parametrize("status", ["PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"])
def test_all_states_are_read_only_safe_and_uncached(seeded, status):
    mid = admit(seeded)
    service = ProcessingService(sessionmaker(seeded.db))
    reply_id = None
    if status != "PENDING":
        claim = service.claim_next(uuid4())
        if status == "COMPLETED":
            reply_id = service.complete(claim, "Synthetic reply").response_id
        elif status == "FAILED":
            service.record_failure(claim, "MODEL_INVALID_OUTPUT")
        elif status == "CANCELLED":
            with seeded.db.begin() as conn:
                conn.execute(
                    update(m.coaching_sessions)
                    .where(m.coaching_sessions.c.id == seeded.ids["session"])
                    .values(status="CLOSED", closure_reason="ADMINISTRATIVE")
                )
            assert service.cancel(claim).status == "cancelled"
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        assert not statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))

    event.listen(seeded.db, "before_cursor_execute", capture)
    try:
        response = poll(seeded, mid)
    finally:
        event.remove(seeded.db, "before_cursor_execute", capture)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert set(data) == {"student_message_id", "status", "tutor_response", "error"}
    assert data["student_message_id"] == str(mid) and data["status"] == status
    assert len([s for s in statements if s.lstrip().upper().startswith("SELECT")]) == 1
    if status == "COMPLETED":
        assert data["tutor_response"] == {
            "tutor_message_id": str(reply_id),
            "content": "Synthetic reply",
        }
    else:
        assert data["tutor_response"] is None
    if status == "FAILED":
        assert data["error"] == {
            "code": "tutor_processing_failed",
            "message": "Your message was saved, but the tutor could not complete a response.",
        }
    elif status == "CANCELLED":
        assert data["error"] == {
            "code": "message_processing_cancelled",
            "message": "Your message was saved, but processing has stopped.",
        }
    else:
        assert data["error"] is None
    assert "PRIVATE" not in response.text and "claim_token" not in response.text


@pytest.mark.parametrize(
    "identity, expected",
    [("missing", 401), ("invalid", 401), ("other", 404), ("teacher", 403), ("duplicate", 401)],
)
def test_polling_authentication_and_non_disclosure(seeded, identity, expected):
    mid = admit(seeded)
    if identity == "missing":
        seeded.client.headers.pop("Authorization", None)
    headers = {} if identity == "missing" else {"Authorization": "Bearer invalid"}
    if identity in seeded.tokens:
        headers = {"Authorization": "Bearer " + seeded.tokens[identity]}
    if identity == "duplicate":
        headers = [("Authorization", "Bearer " + seeded.tokens["student"])] * 2
    response = poll(seeded, mid, headers=headers)
    assert response.status_code == expected
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "case, expected",
    [
        ("message", 404),
        ("session", 404),
        ("mismatch", 404),
        ("tutor", 404),
        ("bad_message", 422),
        ("bad_session", 422),
    ],
)
def test_resource_and_uuid_rules(seeded, case, expected):
    mid = admit(seeded)
    session = seeded.ids["session"]
    if case == "message":
        mid = uuid4()
    elif case == "session":
        session = uuid4()
    elif case == "mismatch":
        session = seeded.ids["other_session"]
    elif case == "tutor":
        service = ProcessingService(sessionmaker(seeded.db))
        mid = service.complete(service.claim_next(uuid4()), "Synthetic reply").response_id
    elif case == "bad_message":
        mid = "invalid"
    else:
        session = "invalid"
    assert poll(seeded, mid, session=session).status_code == expected


@pytest.mark.parametrize(
    "case, expected",
    [("disabled", 401), ("enrollment", 404), ("eligibility", 200), ("closed", 200)],
)
def test_read_authorization_distinct_from_new_work(seeded, case, expected):
    mid = admit(seeded)
    with seeded.db.begin() as conn:
        if case == "disabled":
            conn.execute(
                update(m.users).where(m.users.c.id == seeded.ids["student"]).values(is_active=False)
            )
        elif case == "enrollment":
            conn.execute(
                update(m.enrollments)
                .where(m.enrollments.c.student_user_id == seeded.ids["student"])
                .values(status="INACTIVE")
            )
        elif case == "eligibility":
            conn.execute(
                delete(m.student_assignment_eligibility).where(
                    m.student_assignment_eligibility.c.student_user_id == seeded.ids["student"]
                )
            )
        else:
            conn.execute(
                update(m.coaching_sessions)
                .where(m.coaching_sessions.c.id == seeded.ids["session"])
                .values(status="CLOSED", closure_reason="NORMAL")
            )
    assert poll(seeded, mid).status_code == expected


def test_polling_storage_failure_does_not_instruct_post_retry(seeded, monkeypatch):
    mid = admit(seeded)

    def fail(*args):
        raise OperationalError("PRIVATE SQL", {}, Exception("PRIVATE credentials"))

    monkeypatch.setattr(MessageRepository, "polling_snapshot", fail)
    response = poll(seeded, mid)
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "storage_unavailable",
            "message": "Status is temporarily unavailable. Please try again.",
        }
    }
    assert response.headers["cache-control"] == "no-store"


def test_unexpected_invariant_returns_safe_internal_error(seeded, monkeypatch):
    mid = admit(seeded)
    original = MessageRepository.polling_snapshot

    def corrupt(*args):
        row = dict(original(*args))
        row["processing_status"] = "COMPLETED"
        return row

    monkeypatch.setattr(MessageRepository, "polling_snapshot", corrupt)
    response = poll(seeded, mid)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "PRIVATE" not in response.text


def test_completion_between_snapshot_and_delivery_never_tears_response(seeded):
    mid = admit(seeded)
    service = ProcessingService(sessionmaker(seeded.db))
    claim = service.claim_next(uuid4())
    completed = []

    def finish_after_read(conn, cursor, statement, parameters, context, executemany):
        if "AS reply" in statement and not completed:
            completed.append(True)
            assert service.complete(claim, "Synthetic reply").status == "completed"

    event.listen(seeded.db, "after_cursor_execute", finish_after_read)
    try:
        response = poll(seeded, mid)
    finally:
        event.remove(seeded.db, "after_cursor_execute", finish_after_read)
    assert completed
    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSING"
    assert response.json()["tutor_response"] is None
    latest = poll(seeded, mid)
    assert latest.json()["status"] == "COMPLETED"
    assert latest.json()["tutor_response"]["content"] == "Synthetic reply"
