"""Deterministic adapter tests; no network, provider, or tutoring-quality assertion."""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.orm import sessionmaker

from ai_tutor import models as m
from ai_tutor.model_client import FakeModelClient, ModelProcessor
from ai_tutor.processing_service import ProcessingInput, ProcessingService
from ai_tutor.worker import ProcessingFailure, Worker


def test_fake_requires_explicit_response_and_preserves_text():
    request = ProcessingInput(uuid4(), uuid4(), "PRIVATE student content")
    client = FakeModelClient("  Synthetic response\n")
    processor = ModelProcessor(client)
    assert asyncio.run(processor(request)) == "  Synthetic response\n"
    assert asyncio.run(processor(request)) == "  Synthetic response\n"
    assert client.calls == 2
    assert "PRIVATE" not in repr(client) and "PRIVATE" not in repr(request)
    assert not hasattr(client, "request")


@pytest.mark.parametrize("bad", [None, "", "  ", "\x00", {"content": "text"}])
def test_invalid_client_output_fails_without_coercion_or_retry(bad):
    class InvalidClient:
        calls = 0

        async def generate(self, request):
            self.calls += 1
            return bad

    client = InvalidClient()
    with pytest.raises(ProcessingFailure) as caught:
        asyncio.run(ModelProcessor(client)(ProcessingInput(uuid4(), uuid4(), "input")))
    assert caught.value.code == "MODEL_INVALID_OUTPUT"
    assert client.calls == 1
    with pytest.raises(ValueError):
        FakeModelClient(bad)


def test_adapter_propagates_cancellation():
    async def scenario():
        entered = asyncio.Event()
        cancelled = asyncio.Event()

        class BlockedClient:
            async def generate(self, request):
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

        task = asyncio.create_task(
            ModelProcessor(BlockedClient())(ProcessingInput(uuid4(), uuid4(), "input"))
        )
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelled.is_set()

    asyncio.run(scenario())


def send(seeded):
    return seeded.client.post(
        f"/api/v1/coaching/sessions/{seeded.ids['session']}/messages",
        json={"content": "Synthetic student input"},
        headers={
            "Authorization": "Bearer " + seeded.tokens["student"],
            "Idempotency-Key": "model-adapter",
        },
    )


def test_admission_worker_adapter_fake_completion_and_replay(seeded):
    response = send(seeded)
    assert response.status_code == 201
    mid = UUID(response.json()["student_message_id"])
    client = FakeModelClient("  Synthetic response\n")
    worker = Worker(ProcessingService(sessionmaker(seeded.db)), ModelProcessor(client))
    assert asyncio.run(worker.process_next()).status == "completed"
    assert asyncio.run(worker.process_next()).status == "idle"
    replay = send(seeded)
    assert replay.status_code == 200
    assert replay.json() == {"student_message_id": str(mid), "status": "COMPLETED"}
    assert client.calls == 1
    with seeded.db.connect() as conn:
        replies = (
            conn.execute(select(m.messages).where(m.messages.c.in_reply_to_message_id == mid))
            .mappings()
            .all()
        )
        assert len(replies) == 1 and replies[0]["content"] == "  Synthetic response\n"
        assert conn.scalar(select(m.message_processing_jobs.c.attempt_count)) == 1


@pytest.mark.parametrize("code", ["MODEL_TIMEOUT", "MODEL_UNAVAILABLE", "MODEL_RATE_LIMITED"])
def test_worker_owns_transient_budget_with_model_adapter(seeded, code):
    response = send(seeded)
    mid = UUID(response.json()["student_message_id"])

    class UnavailableClient:
        calls = 0

        async def generate(self, request):
            self.calls += 1
            raise ProcessingFailure(code)

    client = UnavailableClient()
    worker = Worker(ProcessingService(sessionmaker(seeded.db)), ModelProcessor(client))
    assert asyncio.run(worker.process_next()).status == "requeued"
    assert client.calls == 1
    assert asyncio.run(worker.process_next()).status == "idle"
    with seeded.db.begin() as conn:
        conn.execute(
            update(m.message_processing_jobs).values(next_attempt_at=text("clock_timestamp()"))
        )
    assert asyncio.run(worker.process_next()).status == "failed"
    assert client.calls == 2
    replay = send(seeded)
    assert replay.status_code == 200
    assert replay.json() == {"student_message_id": str(mid), "status": "FAILED"}
    assert asyncio.run(worker.process_next()).status == "idle"
    assert client.calls == 2
    with seeded.db.connect() as conn:
        job = conn.execute(select(m.message_processing_jobs)).mappings().one()
        assert job["cycle_attempt_count"] == job["attempt_count"] == 2
        assert job["last_error_code"] == code
        assert (
            conn.scalar(select(m.messages.c.id).where(m.messages.c.author_type == "tutor")) is None
        )
