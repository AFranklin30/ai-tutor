"""Stage 6 connected lifecycle validation; PostgreSQL and configured synthetic model only."""

import asyncio
import multiprocessing
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from ai_tutor import models as m
from ai_tutor.model_client import FakeModelClient, ModelProcessor
from ai_tutor.processing_repository import ProcessingRepository
from ai_tutor.processing_service import ProcessingService
from ai_tutor.worker import ProcessingFailure, Worker

CONTENT = "PRIVATE synthetic input"
REPLY = "Synthetic persisted response"


def post(s, key="one", content=CONTENT):
    return s.client.post(
        f"/api/v1/coaching/sessions/{s.ids['session']}/messages",
        json={"content": content},
        headers={"Authorization": "Bearer " + s.tokens["student"], "Idempotency-Key": key},
    )


def poll(s, mid, identity="student"):
    return s.client.get(
        f"/api/v1/coaching/sessions/{s.ids['session']}/messages/{mid}/status",
        headers={"Authorization": "Bearer " + s.tokens[identity]},
    )


def snapshot(s):
    with s.db.connect() as conn:
        return {
            table.name: sorted(
                [dict(row) for row in conn.execute(select(table)).mappings()], key=str
            )
            for table in (
                m.messages,
                m.message_processing_jobs,
                m.idempotency_records,
                m.coaching_sessions,
            )
        }


def due(s, mid):
    with s.db.begin() as conn:
        conn.execute(
            update(m.message_processing_jobs)
            .where(m.message_processing_jobs.c.message_id == mid)
            .values(next_attempt_at=text("clock_timestamp() - interval '1 second'"))
        )


def test_connected_lifecycle_competing_workers_replay_and_immutable_polling(seeded):
    accepted = post(seeded)
    assert accepted.status_code == 201
    mid = UUID(accepted.json()["student_message_id"])
    assert accepted.json()["status"] == "PENDING"
    committed = snapshot(seeded)
    assert (
        len(committed["messages"])
        == len(committed["message_processing_jobs"])
        == len(committed["idempotency_records"])
        == 1
    )
    assert committed["message_processing_jobs"][0]["message_id"] == mid
    assert committed["idempotency_records"][0]["message_id"] == mid
    assert poll(seeded, mid).json()["status"] == "PENDING"

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        class GatedFake(FakeModelClient):
            async def generate(self, request):
                entered.set()
                await release.wait()
                return await super().generate(request)

        fake = GatedFake(REPLY)
        first = Worker(ProcessingService(sessionmaker(seeded.db)), ModelProcessor(fake))
        rival = Worker(
            ProcessingService(sessionmaker(seeded.db)),
            ModelProcessor(FakeModelClient("Must not win")),
        )
        work = asyncio.create_task(first.process_next())
        try:
            await asyncio.wait_for(entered.wait(), 3)
            assert poll(seeded, mid).json()["status"] == "PROCESSING"
            assert (await rival.process_next()).status == "idle"
            before_replay = snapshot(seeded)
            replay = post(seeded)
            assert replay.status_code == 200 and replay.json()["student_message_id"] == str(mid)
            assert post(seeded, content="Different payload").status_code == 409
            assert snapshot(seeded) == before_replay
            release.set()
            assert (await asyncio.wait_for(work, 3)).status == "completed"
            assert fake.calls == 1
        finally:
            release.set()
            if not work.done():
                work.cancel()
            await asyncio.gather(work, return_exceptions=True)

    asyncio.run(scenario())
    before_poll = snapshot(seeded)
    result = poll(seeded, mid).json()
    assert result["status"] == "COMPLETED" and result["tutor_response"]["content"] == REPLY
    for _ in range(5):
        response = poll(seeded, mid)
        assert response.status_code == 200 and response.json() == result
        assert response.headers["cache-control"] == "no-store"
    assert poll(seeded, mid, "other").status_code == 404
    assert poll(seeded, mid, "teacher").status_code == 403
    assert snapshot(seeded) == before_poll
    assert len(before_poll["messages"]) == 2


def _worker_until_killed(url, search_path, ready):
    engine = create_engine(
        url, hide_parameters=True, connect_args={"options": f"-csearch_path={search_path}"}
    )
    service = ProcessingService(sessionmaker(engine))
    claims = []
    original = service.claim_next

    def capture(worker_id):
        claim = original(worker_id)
        claims.append(claim)
        return claim

    service.claim_next = capture

    class HangingFake(FakeModelClient):
        async def generate(self, request):
            ready.send(claims[-1])  # Parent observes committed claim, then terminates this process.
            await asyncio.Event().wait()
            return await super().generate(request)

    try:
        asyncio.run(Worker(service, ModelProcessor(HangingFake(REPLY))).process_next())
    finally:
        engine.dispose()
        ready.close()


def test_actual_worker_process_crash_recovery_and_stale_completion(seeded):
    accepted = post(seeded)
    mid = UUID(accepted.json()["student_message_id"])
    with seeded.db.connect() as conn:
        search_path = conn.scalar(text("SHOW search_path"))
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_worker_until_killed,
        args=(seeded.db.url.render_as_string(hide_password=False), search_path, child),
    )
    process.start()
    child.close()
    try:
        assert parent.poll(15), "Worker did not reach its processor"
        stale = parent.recv()
        assert poll(seeded, mid).json()["status"] == "PROCESSING"
        process.terminate()
        process.join(timeout=5)
        assert not process.is_alive() and process.exitcode != 0
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
        parent.close()
    # Advance persisted claim timestamps, preserving constraints; do not wait 45s in tests.
    with seeded.db.begin() as conn:
        conn.execute(
            text("""UPDATE message_processing_jobs SET
            claimed_at=claimed_at-interval '100 seconds',
            lease_expires_at=lease_expires_at-interval '100 seconds',
            attempt_deadline_at=attempt_deadline_at-interval '100 seconds'
            WHERE message_id=:mid"""),
            {"mid": mid},
        )
    service = ProcessingService(sessionmaker(seeded.db))
    fake = FakeModelClient(REPLY)
    worker = Worker(service, ModelProcessor(fake))
    assert asyncio.run(worker.process_next()).status == "idle"  # Recovered to delayed PENDING.
    assert poll(seeded, mid).json()["status"] == "PENDING"
    assert service.complete(stale, "Stale output").status == "lost"
    due(seeded, mid)
    assert asyncio.run(worker.process_next()).status == "completed"
    before = snapshot(seeded)
    assert service.complete(stale, "Stale output").status == "lost"
    assert service.record_failure(stale, "MODEL_TIMEOUT").status == "lost"
    assert snapshot(seeded) == before
    assert before["message_processing_jobs"][0]["attempt_count"] == 2
    assert poll(seeded, mid).json()["tutor_response"]["content"] == REPLY
    assert fake.calls == 1


@pytest.mark.parametrize(
    "mode", ["transient_recovers", "exhausted", "permanent", "unknown", "invalid_output"]
)
def test_processor_failures_fifo_barriers_and_safe_polling(seeded, mode):
    first = UUID(post(seeded).json()["student_message_id"])
    second = UUID(post(seeded, "two").json()["student_message_id"])

    class FaultFake(FakeModelClient):
        invocations = 0

        async def generate(self, request):
            self.invocations += 1
            if mode == "transient_recovers" and self.invocations > 1:
                return await super().generate(request)
            if mode in {"transient_recovers", "exhausted"}:
                raise ProcessingFailure("MODEL_UNAVAILABLE")
            if mode == "permanent":
                raise ProcessingFailure("POLICY_REJECTED")
            if mode == "unknown":
                raise RuntimeError("PRIVATE provider credentials")
            return {"unvalidated": "PRIVATE provider output"}

    fake = FaultFake(REPLY)
    worker = Worker(ProcessingService(sessionmaker(seeded.db)), ModelProcessor(fake))
    transient = mode in {"transient_recovers", "exhausted"}
    assert asyncio.run(worker.process_next()).status == ("requeued" if transient else "failed")
    assert poll(seeded, second).json()["status"] == "PENDING"
    assert asyncio.run(worker.process_next()).status == "idle"
    assert fake.invocations == 1
    if transient:
        due(seeded, first)
        assert asyncio.run(worker.process_next()).status == (
            "completed" if mode == "transient_recovers" else "failed"
        )
    if mode == "transient_recovers":
        assert poll(seeded, first).json()["tutor_response"]["content"] == REPLY
        assert asyncio.run(worker.process_next()).status == "completed"
        assert poll(seeded, second).json()["status"] == "COMPLETED"
    else:
        response = poll(seeded, first)
        assert response.status_code == 200 and response.json()["status"] == "FAILED"
        assert response.json()["error"]["code"] == "tutor_processing_failed"
        assert "PRIVATE" not in response.text and "MODEL_" not in response.text
        before = snapshot(seeded)
        assert post(seeded).status_code == 200
        assert asyncio.run(worker.process_next()).status == "idle"
        assert snapshot(seeded) == before
        assert poll(seeded, second).json()["status"] == "PENDING"


@pytest.mark.parametrize(
    "change", ["NORMAL", "ADMINISTRATIVE", "UNKNOWN", "disabled", "enrollment"]
)
@pytest.mark.parametrize("when", ["before_claim", "before_finalize"])
def test_policy_changes_across_connected_lifecycle(seeded, change, when):
    mid = UUID(post(seeded).json()["student_message_id"])

    def change_policy():
        with seeded.db.begin() as conn:
            conn.execute(
                select(m.users).where(m.users.c.id == seeded.ids["student"]).with_for_update()
            )
            conn.execute(
                select(m.coaching_sessions)
                .where(m.coaching_sessions.c.id == seeded.ids["session"])
                .with_for_update()
            )
            if change == "disabled":
                conn.execute(
                    update(m.users)
                    .where(m.users.c.id == seeded.ids["student"])
                    .values(is_active=False)
                )
            elif change == "enrollment":
                conn.execute(
                    update(m.enrollments)
                    .where(m.enrollments.c.student_user_id == seeded.ids["student"])
                    .values(status="INACTIVE")
                )
            else:
                conn.execute(
                    update(m.coaching_sessions)
                    .where(m.coaching_sessions.c.id == seeded.ids["session"])
                    .values(status="CLOSED", closure_reason=change)
                )

    class PolicyFake(FakeModelClient):
        async def generate(self, request):
            change_policy()
            return await super().generate(request)

    if when == "before_claim":
        change_policy()
        fake = FakeModelClient(REPLY)
    else:
        fake = PolicyFake(REPLY)
    worker = Worker(ProcessingService(sessionmaker(seeded.db)), ModelProcessor(fake))
    outcome = asyncio.run(worker.process_next())
    expected = (
        "completed" if change == "NORMAL" else ("idle" if when == "before_claim" else "cancelled")
    )
    assert outcome.status == expected
    response = poll(seeded, mid)
    if change in {"disabled", "enrollment"}:
        assert response.status_code == (401 if change == "disabled" else 404)
    else:
        assert response.status_code == 200
        assert response.json()["status"] == ("COMPLETED" if change == "NORMAL" else "CANCELLED")
        assert post(seeded, "new").status_code == 409
    state = snapshot(seeded)
    assert state["messages"][0]["content"] in {CONTENT, REPLY}
    students = [r for r in state["messages"] if r["author_type"] == "student"]
    assert len(students) == 1 and students[0]["content"] == CONTENT
    assert students[0]["processing_status"] == ("COMPLETED" if change == "NORMAL" else "CANCELLED")
    assert fake.calls == (0 if when == "before_claim" and change != "NORMAL" else 1)


def test_polling_cannot_see_uncommitted_tutor_response(seeded):
    mid = UUID(post(seeded).json()["student_message_id"])
    observations = []

    def before_commit(conn):
        if observations:
            return
        status = conn.scalar(select(m.messages.c.processing_status).where(m.messages.c.id == mid))
        if status == "COMPLETED":
            observations.append("observing")
            response = poll(seeded, mid)
            assert response.status_code == 200
            observations.append(response.json())

    event.listen(seeded.db, "commit", before_commit)
    try:
        worker = Worker(
            ProcessingService(sessionmaker(seeded.db)), ModelProcessor(FakeModelClient(REPLY))
        )
        assert asyncio.run(worker.process_next()).status == "completed"
    finally:
        event.remove(seeded.db, "commit", before_commit)
    assert observations[1]["status"] == "PROCESSING"
    assert observations[1]["tutor_response"] is None
    assert poll(seeded, mid).json()["tutor_response"]["content"] == REPLY


def test_failed_finalization_preserves_input_and_withholds_output(seeded, monkeypatch):
    mid = UUID(post(seeded).json()["student_message_id"])
    original = ProcessingRepository.insert_response

    def failed_insert(repo, *args):
        original(repo, *args)
        raise OperationalError("PRIVATE SQL", {}, Exception("PRIVATE detail"))

    fake = FakeModelClient(REPLY)
    worker = Worker(ProcessingService(sessionmaker(seeded.db)), ModelProcessor(fake))
    monkeypatch.setattr(ProcessingRepository, "insert_response", failed_insert)
    assert asyncio.run(worker.process_next()).status == "database_unavailable"
    response = poll(seeded, mid)
    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSING"
    assert response.json()["tutor_response"] is None
    state = snapshot(seeded)
    assert len(state["messages"]) == 1 and state["messages"][0]["content"] == CONTENT
    assert len(state["idempotency_records"]) == len(state["message_processing_jobs"]) == 1
    assert "PRIVATE" not in response.text
    assert fake.calls == 1
