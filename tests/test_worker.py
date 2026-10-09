"""Stage 3 PostgreSQL worker tests; deterministic processors only, no model provider."""

import asyncio
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, delete, event, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from ai_tutor import models as m
from ai_tutor.processing_repository import ProcessingRepository
from ai_tutor.processing_service import ProcessingService, WorkerSettings
from ai_tutor.worker import ProcessingFailure, Worker


@pytest.fixture
def service(seeded):
    return ProcessingService(sessionmaker(seeded.db))


def admit(s, key="first", session_id=None, other=False):
    response = s.client.post(
        f"/api/v1/coaching/sessions/{session_id or s.ids['session']}/messages",
        json={"content": "PRIVATE synthetic student input"},
        headers={
            "Idempotency-Key": key,
            "Authorization": "Bearer " + s.tokens["other" if other else "student"],
        },
    )
    assert response.status_code == 201
    return UUID(response.json()["student_message_id"])


def snapshot(s, mid):
    with s.db.connect() as c:
        message = c.execute(select(m.messages).where(m.messages.c.id == mid)).mappings().one()
        job = (
            c.execute(
                select(m.message_processing_jobs).where(
                    m.message_processing_jobs.c.message_id == mid
                )
            )
            .mappings()
            .one()
        )
        replies = c.execute(
            select(m.messages).where(m.messages.c.in_reply_to_message_id == mid)
        ).all()
        return dict(message), dict(job), replies


def expire(s, mid):
    with s.db.begin() as c:
        c.execute(
            text("""UPDATE message_processing_jobs
            SET claimed_at=claimed_at-interval '100 seconds',
                lease_expires_at=lease_expires_at-interval '100 seconds',
                attempt_deadline_at=attempt_deadline_at-interval '100 seconds'
            WHERE message_id=:id"""),
            {"id": mid},
        )


def due(s, mid):
    with s.db.begin() as c:
        c.execute(
            update(m.message_processing_jobs)
            .where(m.message_processing_jobs.c.message_id == mid)
            .values(next_attempt_at=text("clock_timestamp() - interval '1 second'"))
        )


def close(s, reason):
    with s.db.begin() as c:
        c.execute(
            update(m.coaching_sessions)
            .where(m.coaching_sessions.c.id == s.ids["session"])
            .values(status="CLOSED", closure_reason=reason)
        )


def fast_settings(**overrides):
    settings = dict(
        model_timeout=0.3,
        lease_seconds=0.6,
        heartbeat_seconds=0.03,
        attempt_seconds=1.2,
        completion_margin=0.05,
        retry_delay=0.02,
        shutdown_seconds=0.1,
        poll_seconds=0.02,
    )
    settings.update(overrides)
    return WorkerSettings(**settings)


class FakeProcessor:
    def __init__(self, result="Synthetic persisted tutor response", failure=None, gate=None):
        self.result = result
        self.failure = failure
        self.gate = gate
        self.calls = 0
        self.entered = asyncio.Event()
        self.cancelled = False

    async def __call__(self, request):
        self.calls += 1
        self.entered.set()
        try:
            if self.gate is not None:
                await self.gate.wait()
            if self.failure is not None:
                raise self.failure
            return self.result
        except asyncio.CancelledError:
            self.cancelled = True
            raise


def test_claim_commit_single_response_and_idempotent_completion(seeded, service):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    assert claim.message_id == mid and claim.attempt == 1
    assert "PRIVATE" not in repr(claim) and str(claim.token) not in repr(claim)
    message, job, replies = snapshot(seeded, mid)
    assert message["processing_status"] == "PROCESSING" and not replies
    assert job["claim_token"] == claim.token
    assert job["attempt_count"] == job["cycle_attempt_count"] == 1
    assert job["retry_generation"] == 0
    assert (job["lease_expires_at"] - job["claimed_at"]).total_seconds() == 45
    assert (job["attempt_deadline_at"] - job["claimed_at"]).total_seconds() == 90
    completed = service.complete(claim, "  exact tutor output  ")
    assert completed.status == "completed"
    assert service.complete(claim, "must not replace output").response_id == completed.response_id
    message, job, replies = snapshot(seeded, mid)
    assert message["processing_status"] == "COMPLETED" and len(replies) == 1
    assert replies[0].content == "  exact tutor output  "
    assert job["claim_token"] == claim.token and job["lease_expires_at"] is None
    with seeded.db.connect() as c:
        assert (
            c.scalar(
                select(m.coaching_sessions.c.status).where(
                    m.coaching_sessions.c.id == seeded.ids["session"]
                )
            )
            == "ACTIVE"
        )


def test_head_backoff_failed_and_other_session_progress(seeded, service):
    first, second = admit(seeded), admit(seeded, "second")
    claim = service.claim_next(uuid4())
    assert claim.message_id == first
    assert service.claim_next(uuid4()) is None
    assert service.record_failure(claim, "MODEL_TIMEOUT").status == "requeued"
    assert service.claim_next(uuid4()) is None  # Delayed first must not be skipped.
    other = admit(seeded, session_id=seeded.ids["other_session"], other=True)
    other_claim = service.claim_next(uuid4())
    assert other_claim.message_id == other
    assert service.complete(other_claim, "other output").status == "completed"
    due(seeded, first)
    retry = service.claim_next(uuid4())
    assert retry.message_id == first and retry.token != claim.token and retry.attempt == 2
    assert service.record_failure(retry, "MODEL_TIMEOUT").status == "failed"
    assert service.claim_next(uuid4()) is None  # Permanent automatic exhaustion blocks second.
    assert snapshot(seeded, second)[0]["processing_status"] == "PENDING"
    assert snapshot(seeded, first)[1]["attempt_count"] == 2


def test_completed_head_releases_next_and_denied_cancellation_cancels_session(seeded, service):
    first, second = admit(seeded), admit(seeded, "second")
    claim = service.claim_next(uuid4())
    service.complete(claim, "first response")
    next_claim = service.claim_next(uuid4())
    assert next_claim.message_id == second
    close(seeded, "ADMINISTRATIVE")
    assert service.cancel(next_claim).status == "cancelled"
    assert snapshot(seeded, first)[0]["processing_status"] == "COMPLETED"
    assert snapshot(seeded, second)[0]["processing_status"] == "CANCELLED"


@pytest.mark.parametrize(
    "locked_table", [m.users, m.coaching_sessions, m.messages, m.message_processing_jobs]
)
def test_skip_locked_never_overtakes_head(seeded, service, locked_table):
    first, second = admit(seeded), admit(seeded, "second")
    lock_id = (
        seeded.ids["student"]
        if locked_table is m.users
        else seeded.ids["session"]
        if locked_table is m.coaching_sessions
        else first
    )
    key = (
        locked_table.c.message_id
        if locked_table is m.message_processing_jobs
        else locked_table.c.id
    )
    with seeded.db.begin() as c:
        c.execute(select(locked_table).where(key == lock_id).with_for_update())
        assert service.claim_next(uuid4()) is None
    assert snapshot(seeded, second)[0]["processing_status"] == "PENDING"
    assert service.claim_next(uuid4()).message_id == first


def _claim_in_process(url, search_path, barrier, results):
    engine = create_engine(url, connect_args={"options": f"-csearch_path={search_path}"})
    try:
        service = ProcessingService(sessionmaker(engine))
        barrier.wait(timeout=15)
        claim = service.claim_next(uuid4())
        results.put(str(claim.message_id) if claim else None)
    finally:
        engine.dispose()


def test_independent_worker_processes_claim_only_one_session_head(seeded):
    first, second = admit(seeded), admit(seeded, "second")
    with seeded.db.connect() as c:
        search_path = c.scalar(text("SHOW search_path"))
    ctx = multiprocessing.get_context("spawn")
    barrier, results = ctx.Barrier(3), ctx.Queue()
    processes = [
        ctx.Process(
            target=_claim_in_process,
            args=(
                seeded.db.url.render_as_string(hide_password=False),
                search_path,
                barrier,
                results,
            ),
        )
        for _ in range(3)
    ]
    for process in processes:
        process.start()
    try:
        outcomes = [results.get(timeout=25) for _ in processes]
        assert outcomes.count(str(first)) == 1 and outcomes.count(None) == 2
        for process in processes:
            process.join(timeout=5)
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()
    assert snapshot(seeded, second)[0]["processing_status"] == "PENDING"


def test_crash_recovery_new_token_and_all_stale_callbacks_fenced(seeded, service):
    mid = admit(seeded)
    stale = service.claim_next(uuid4())
    expire(seeded, mid)
    assert service.renew_lease(stale).status == "lost"  # Even before replacement exists.
    assert service.claim_next(uuid4()) is None  # Recover and back off, not immediate execution.
    assert snapshot(seeded, mid)[1]["last_error_code"] == "LEASE_EXPIRED"
    due(seeded, mid)
    live = service.claim_next(uuid4())
    assert live.token != stale.token and live.attempt == 2
    before = snapshot(seeded, mid)
    assert service.complete(stale, "late response").status == "lost"
    assert service.record_failure(stale, "MODEL_TIMEOUT").status == "lost"
    assert service.cancel(stale).status == "lost"
    assert service.renew_lease(stale).status == "lost"
    assert snapshot(seeded, mid) == before
    service.complete(live, "winning response")
    assert len(snapshot(seeded, mid)[2]) == 1


def test_second_crash_exhausts_shared_budget_without_another_claim(seeded, service):
    mid = admit(seeded)
    service.claim_next(uuid4())
    expire(seeded, mid)
    service.claim_next(uuid4())
    due(seeded, mid)
    service.claim_next(uuid4())
    expire(seeded, mid)
    assert service.claim_next(uuid4()) is None
    message, job, _ = snapshot(seeded, mid)
    assert message["processing_status"] == "FAILED"
    assert job["attempt_count"] == job["cycle_attempt_count"] == 2
    assert job["retry_generation"] == 0


def test_renewal_cannot_extend_fixed_deadline(seeded, service):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    with seeded.db.begin() as c:
        c.execute(
            text("""UPDATE message_processing_jobs SET
            claimed_at=clock_timestamp()-interval '80 seconds',
            lease_expires_at=clock_timestamp()+interval '5 seconds',
            attempt_deadline_at=clock_timestamp()+interval '10 seconds' WHERE message_id=:id
        """),
            {"id": mid},
        )
    deadline = snapshot(seeded, mid)[1]["attempt_deadline_at"]
    renewal = service.renew_lease(claim)
    assert renewal.status == "renewed" and 0 < renewal.remaining_seconds <= 10
    job = snapshot(seeded, mid)[1]
    assert job["lease_expires_at"] == job["attempt_deadline_at"] == deadline


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("disabled", "ACCOUNT_DISABLED"),
        ("enrollment", "ENROLLMENT_REVOKED"),
        ("eligibility", "COURSEWORK_INELIGIBLE"),
        ("membership", "COURSEWORK_INELIGIBLE"),
        ("ADMINISTRATIVE", "SESSION_ADMIN_CLOSED"),
        ("UNKNOWN", "SESSION_CLOSURE_UNKNOWN"),
    ],
)
@pytest.mark.parametrize("phase", ["before_claim", "before_complete"])
def test_current_authorization_and_closure_cancel_unfinished_scope(
    seeded, service, fault, reason, phase
):
    mids = [admit(seeded), admit(seeded, "second")]
    claim = service.claim_next(uuid4()) if phase == "before_complete" else None
    with seeded.db.begin() as c:
        if fault == "disabled":
            c.execute(
                update(m.users).where(m.users.c.id == seeded.ids["student"]).values(is_active=False)
            )
        elif fault == "enrollment":
            c.execute(
                delete(m.enrollments).where(
                    m.enrollments.c.student_user_id == seeded.ids["student"]
                )
            )
        elif fault == "eligibility":
            c.execute(delete(m.student_assignment_eligibility))
        elif fault == "membership":
            c.execute(delete(m.assignment_problems))
        else:
            c.execute(
                update(m.coaching_sessions)
                .where(m.coaching_sessions.c.id == seeded.ids["session"])
                .values(status="CLOSED", closure_reason=fault)
            )
    if claim:
        assert service.complete(claim, "must not persist").status == "cancelled"
    else:
        assert service.claim_next(uuid4()) is None
    for mid in mids:
        message, job, replies = snapshot(seeded, mid)
        assert message["processing_status"] == "CANCELLED" and not replies
        assert job["cancel_reason"] == reason
    assert service.claim_next(uuid4()) is None


def test_normal_closure_allows_accepted_work_but_no_new_input(seeded, service):
    mid = admit(seeded)
    close(seeded, "NORMAL")
    claim = service.claim_next(uuid4())
    assert claim.message_id == mid
    assert service.cancel(claim).status == "not_cancelled"
    assert service.complete(claim, "accepted work").status == "completed"
    assert (
        seeded.client.post(
            seeded.url, json={"content": "new"}, headers={"Idempotency-Key": "new"}
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "code,expected",
    [
        ("MODEL_TIMEOUT", "requeued"),
        ("MODEL_UNAVAILABLE", "requeued"),
        ("MODEL_RATE_LIMITED", "requeued"),
        ("MODEL_INVALID_OUTPUT", "failed"),
        ("MODEL_CONFIGURATION", "failed"),
        ("POLICY_REJECTED", "failed"),
        ("PROCESSING_ERROR", "failed"),
        ("PRIVATE unknown exception", "failed"),
    ],
)
def test_retry_eligibility_uses_controlled_categories(seeded, service, code, expected):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    assert service.record_failure(claim, code).status == expected
    assert "PRIVATE" not in str(snapshot(seeded, mid)[1])


def test_generation_mismatch_and_stale_cancellation_have_no_authority(seeded, service):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    forged = replace(claim, generation=claim.generation + 1)
    close(seeded, "ADMINISTRATIVE")
    before = snapshot(seeded, mid)
    for operation in [
        lambda: service.complete(forged, "bad"),
        lambda: service.record_failure(forged, "MODEL_TIMEOUT"),
        lambda: service.cancel(forged),
        lambda: service.renew_lease(forged),
    ]:
        assert operation().status == "lost"
    assert snapshot(seeded, mid) == before
    assert service.cancel(claim).status == "cancelled"


def test_failure_between_reply_insert_and_completion_rolls_back(seeded, service, monkeypatch):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    original = ProcessingRepository.insert_response

    def fail_after_insert(repo, *args):
        original(repo, *args)
        raise OperationalError("synthetic", {}, Exception("PRIVATE failure"))

    monkeypatch.setattr(ProcessingRepository, "insert_response", fail_after_insert)
    with pytest.raises(OperationalError):
        service.complete(claim, "must roll back")
    message, job, replies = snapshot(seeded, mid)
    assert message["processing_status"] == "PROCESSING" and not replies
    assert job["claim_token"] == claim.token


def test_concurrent_completion_returns_same_logical_response(seeded, service):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    barrier = Barrier(2)

    def finish(_):
        barrier.wait(timeout=5)
        return service.complete(claim, "same logical output")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(finish, range(2)))
    assert sorted(r.status for r in results) == ["already_completed", "completed"]
    assert len({r.response_id for r in results}) == len(snapshot(seeded, mid)[2]) == 1


def test_runner_external_work_has_no_database_locks_and_heartbeats(seeded):
    mid = admit(seeded)
    service = ProcessingService(
        sessionmaker(seeded.db), fast_settings(model_timeout=0.6, lease_seconds=0.9)
    )
    renewals = []
    original = service.renew_lease

    def record(claim):
        result = original(claim)
        renewals.append(result)
        return result

    service.renew_lease = record

    async def scenario():
        gate = asyncio.Event()
        fake = FakeProcessor(gate=gate)
        task = asyncio.create_task(Worker(service, fake).process_next())
        await asyncio.wait_for(fake.entered.wait(), 2)
        # A separate connection can lock every admission/claim row while external work waits.
        with seeded.db.begin() as c:
            c.execute(
                select(m.users)
                .where(m.users.c.id == seeded.ids["student"])
                .with_for_update(nowait=True)
            )
            c.execute(
                select(m.coaching_sessions)
                .where(m.coaching_sessions.c.id == seeded.ids["session"])
                .with_for_update(nowait=True)
            )
            c.execute(select(m.messages).where(m.messages.c.id == mid).with_for_update(nowait=True))
            c.execute(
                select(m.message_processing_jobs)
                .where(m.message_processing_jobs.c.message_id == mid)
                .with_for_update(nowait=True)
            )
        for _ in range(100):
            if len(renewals) >= 3:
                break
            await asyncio.sleep(0.005)
        assert len(renewals) >= 3
        gate.set()
        assert (await task).status == "completed"
        assert fake.calls == 1

    asyncio.run(scenario())


def test_runner_timeout_is_bounded_and_cancels_local_processor(seeded):
    mid = admit(seeded)
    service = ProcessingService(sessionmaker(seeded.db), fast_settings())

    async def scenario():
        fake = FakeProcessor(gate=asyncio.Event())
        result = await Worker(service, fake).process_next()
        await asyncio.sleep(0)
        assert result.status == "requeued" and fake.cancelled and fake.calls == 1

    asyncio.run(scenario())
    assert snapshot(seeded, mid)[1]["last_error_code"] == "MODEL_TIMEOUT"


def test_runner_discards_result_after_heartbeat_authorization_loss(seeded):
    mid = admit(seeded)
    service = ProcessingService(sessionmaker(seeded.db), fast_settings())

    async def scenario():
        fake = FakeProcessor(gate=asyncio.Event())
        task = asyncio.create_task(Worker(service, fake).process_next())
        await asyncio.wait_for(fake.entered.wait(), 2)
        close(seeded, "ADMINISTRATIVE")
        assert (await task).status == "cancelled"
        await asyncio.sleep(0)
        assert fake.cancelled

    asyncio.run(scenario())
    assert not snapshot(seeded, mid)[2]


def test_shutdown_does_not_cancel_durable_work_or_claim_next(seeded):
    mids = [admit(seeded), admit(seeded, "second")]
    service = ProcessingService(sessionmaker(seeded.db), fast_settings(shutdown_seconds=0.05))

    async def scenario():
        stop = asyncio.Event()
        fake = FakeProcessor(gate=asyncio.Event())
        running = asyncio.create_task(Worker(service, fake).run(stop))
        await asyncio.wait_for(fake.entered.wait(), 2)
        stop.set()
        await asyncio.wait_for(running, 2)
        await asyncio.sleep(0)
        assert fake.calls == 1 and fake.cancelled

    asyncio.run(scenario())
    assert snapshot(seeded, mids[0])[0]["processing_status"] == "PROCESSING"
    assert snapshot(seeded, mids[1])[0]["processing_status"] == "PENDING"


def test_uncertain_commit_is_read_back_without_another_processor_call(seeded, service, monkeypatch):
    mid = admit(seeded)
    original = service.complete

    def lose_ack(*args):
        original(*args)
        raise OperationalError("synthetic lost acknowledgement", {}, Exception("PRIVATE"))

    monkeypatch.setattr(service, "complete", lose_ack)

    async def scenario():
        fake = FakeProcessor()
        worker = Worker(service, fake)
        assert (await worker.process_next()).status == "already_completed"
        assert (await worker.process_next()).status == "idle"
        assert fake.calls == 1

    asyncio.run(scenario())
    assert len(snapshot(seeded, mid)[2]) == 1


def test_sanitized_failure_logs_and_invalid_output(seeded, service, caplog):
    mid = admit(seeded)
    caplog.set_level(logging.INFO, logger="ai_tutor.worker")

    async def scenario():
        assert (
            await Worker(
                service, FakeProcessor(failure=RuntimeError("PRIVATE provider body"))
            ).process_next()
        ).status == "failed"

    asyncio.run(scenario())
    assert snapshot(seeded, mid)[1]["last_error_code"] == "PROCESSING_ERROR"
    records = [r for r in caplog.records if r.name == "ai_tutor.worker"]
    assert records and "PRIVATE" not in str([r.__dict__ for r in records])
    assert str(snapshot(seeded, mid)[1]["claim_token"]) not in str([r.__dict__ for r in records])


@pytest.mark.parametrize("bad", ["", "  ", "\x00", None, {"content": "unvalidated"}])
def test_invalid_processor_output_never_persists_reply(seeded, service, bad):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    assert service.complete(claim, bad).status == "failed"
    assert not snapshot(seeded, mid)[2]


def test_commit_failure_does_not_expose_claim(seeded, service):
    mid = admit(seeded)

    # Candidate lookup commits a read-only transaction too; fail only the write commit.
    def fail_commit(conn):
        if (
            conn.scalar(select(m.messages.c.processing_status).where(m.messages.c.id == mid))
            == "PROCESSING"
        ):
            raise OperationalError("synthetic commit", {}, Exception("failure"))

    event.listen(seeded.db, "commit", fail_commit)
    try:
        with pytest.raises(OperationalError):
            service.claim_next(uuid4())
    finally:
        event.remove(seeded.db, "commit", fail_commit)
    assert snapshot(seeded, mid)[0]["processing_status"] == "PENDING"
    assert snapshot(seeded, mid)[1]["attempt_count"] == 0


@pytest.mark.parametrize(
    "code, status",
    [("MODEL_UNAVAILABLE", "requeued"), ("POLICY_REJECTED", "failed"), ({}, "failed")],
)
def test_typed_processor_failure(seeded, service, code, status):
    mid = admit(seeded)

    async def scenario():
        fake = FakeProcessor(failure=ProcessingFailure(code))
        assert (await Worker(service, fake).process_next()).status == status
        assert fake.calls == 1

    asyncio.run(scenario())
    assert not snapshot(seeded, mid)[2]


def test_expired_claim_cannot_finalize_before_recovery(seeded, service):
    mid = admit(seeded)
    claim = service.claim_next(uuid4())
    expire(seeded, mid)
    assert service.complete(claim, "late output").status == "lost"
    assert service.record_failure(claim, "MODEL_TIMEOUT").status == "lost"
    assert not snapshot(seeded, mid)[2]


def test_stop_before_claim_does_not_start_work(seeded, service):
    mid = admit(seeded)

    async def scenario():
        stop = asyncio.Event()
        stop.set()
        fake = FakeProcessor()
        assert (await Worker(service, fake).process_next(stop)).status == "stopped"
        assert fake.calls == 0

    asyncio.run(scenario())
    assert snapshot(seeded, mid)[1]["attempt_count"] == 0


def test_heartbeat_database_failure_discards_result(seeded, monkeypatch):
    mid = admit(seeded)
    service = ProcessingService(sessionmaker(seeded.db), fast_settings())
    original = service.renew_lease
    renewals = []

    def renew(claim):
        renewals.append(claim)
        if len(renewals) > 1:
            raise OperationalError("synthetic heartbeat outage", {}, Exception("private"))
        return original(claim)

    monkeypatch.setattr(service, "renew_lease", renew)

    async def scenario():
        fake = FakeProcessor(gate=asyncio.Event())
        assert (await Worker(service, fake).process_next()).status == "database_unavailable"
        await asyncio.sleep(0)
        assert fake.cancelled and fake.calls == 1

    asyncio.run(scenario())
    message, job, replies = snapshot(seeded, mid)
    assert message["processing_status"] == "PROCESSING"
    assert job["attempt_count"] == 1 and not replies


def test_graceful_shutdown_allows_inflight_completion(seeded, service):
    mid = admit(seeded)

    async def scenario():
        stop, gate = asyncio.Event(), asyncio.Event()
        fake = FakeProcessor(gate=gate)
        runner = asyncio.create_task(Worker(service, fake).run(stop))
        await asyncio.wait_for(fake.entered.wait(), 3)
        stop.set()
        await asyncio.sleep(0.02)
        gate.set()
        await asyncio.wait_for(runner, 3)
        assert fake.calls == 1

    asyncio.run(scenario())
    assert snapshot(seeded, mid)[0]["processing_status"] == "COMPLETED"


def test_database_backoff_is_interruptible(seeded, service, monkeypatch):
    calls = []

    def unavailable(_worker):
        calls.append(1)
        raise OperationalError("synthetic unavailable", {}, Exception("private"))

    monkeypatch.setattr(service, "claim_next", unavailable)

    async def scenario():
        stop = asyncio.Event()
        runner = asyncio.create_task(Worker(service, FakeProcessor()).run(stop))
        await asyncio.sleep(0.1)
        stop.set()
        await asyncio.wait_for(runner, 1)

    asyncio.run(scenario())
    assert len(calls) == 1
