"""Async worker runner with independent heartbeat and injected nonblocking processor.

No production model client is provided. Processor implementations must be async,
nonblocking, and return validated student-safe text. They must not spawn unbounded
retries; each claim invokes the processor once. Test fakes live in tests only.
"""

import asyncio
import random
import time
from typing import Protocol
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from ai_tutor.processing_service import ProcessingInput, Result


class Processor(Protocol):
    async def __call__(self, request: ProcessingInput) -> str: ...


class ProcessingFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__("processing failed")  # No provider exception text.


def discard(task):
    """Cancel local work without waiting indefinitely on cancellation-resistant providers."""
    if not task.done():
        task.cancel()

    def consumed(done):
        if not done.cancelled():
            done.exception()

    task.add_done_callback(consumed)


class Worker:
    def __init__(self, service, processor: Processor, worker_instance_id=None):
        self.service = service
        self.processor = processor
        self.worker_instance_id = worker_instance_id or uuid4()
        self.settings = service.settings
        self.telemetry = service.telemetry

    async def _heartbeat(self, claim):
        while True:
            await asyncio.sleep(self.settings.heartbeat_seconds)
            try:
                result = await asyncio.to_thread(self.service.renew_lease, claim)
            except SQLAlchemyError:
                return Result("database_unavailable")
            self.telemetry.emit(
                "heartbeat",
                message_id=str(claim.message_id),
                session_id=str(claim.session_id),
                status=result.status,
            )
            if result.status != "renewed":
                return result

    async def process_next(self, stop=None):
        stop = stop or asyncio.Event()
        if stop.is_set():
            return Result("stopped")
        claim = await asyncio.to_thread(self.service.claim_next, self.worker_instance_id)
        if claim is None:
            return Result("idle")
        # Claim commit and dispatch are separate: if stopping now, leave the committed
        # claim for bounded lease recovery; never invent a CANCELLED message for shutdown.
        if stop.is_set():
            return Result("stopped")
        try:
            ready = await asyncio.to_thread(self.service.renew_lease, claim)
        except SQLAlchemyError:
            return Result("database_unavailable")
        if ready.status != "renewed":
            return ready
        if ready.remaining_seconds < self.settings.model_timeout + self.settings.completion_margin:
            return Result("lost")  # Insufficient safe call window; lease recovery handles it.
        if stop.is_set():
            return Result("stopped")
        self.telemetry.emit(
            "claimed",
            message_id=str(claim.message_id),
            session_id=str(claim.session_id),
            trace_id=claim.input.trace_id,
            attempt=claim.attempt,
            queue_wait_ms=claim.queue_wait_seconds * 1000,
        )
        started = time.monotonic()
        processing = asyncio.create_task(self.processor(claim.input))
        heartbeat = asyncio.create_task(self._heartbeat(claim))
        stopping = asyncio.create_task(stop.wait())
        timeout = asyncio.create_task(asyncio.sleep(self.settings.model_timeout))
        grace = None
        result = Result("lost")
        try:
            watched = {processing, heartbeat, stopping, timeout}
            while True:
                done, _ = await asyncio.wait(watched, return_when=asyncio.FIRST_COMPLETED)
                # Prefer ownership loss to a simultaneous processor result.
                if heartbeat in done:
                    result = heartbeat.result()
                    break
                if stopping in done:
                    watched.remove(stopping)
                    grace = asyncio.create_task(asyncio.sleep(self.settings.shutdown_seconds))
                    watched.add(grace)
                if grace is not None and grace in done:
                    result = Result("stopped")
                    break
                if processing in done:
                    try:
                        content = processing.result()
                    except ProcessingFailure as exc:
                        result = await asyncio.to_thread(
                            self.service.record_failure, claim, exc.code
                        )
                    except asyncio.CancelledError:
                        result = Result("stopped")
                    except Exception:
                        result = await asyncio.to_thread(
                            self.service.record_failure, claim, "PROCESSING_ERROR"
                        )
                    else:
                        try:
                            result = await asyncio.to_thread(self.service.complete, claim, content)
                        except SQLAlchemyError:
                            # Read durable state after uncertain commit, never reinvoke processor.
                            result = await asyncio.to_thread(
                                self.service.reconcile_completion, claim
                            )
                            if result.status != "already_completed":
                                result = Result("database_unavailable")
                    break
                if timeout in done:
                    discard(processing)
                    result = await asyncio.to_thread(
                        self.service.record_failure, claim, "MODEL_TIMEOUT"
                    )
                    break
        except SQLAlchemyError:
            result = Result("database_unavailable")
        finally:
            for task in (processing, heartbeat, stopping, timeout, grace):
                if task is not None:
                    discard(task)
            self.telemetry.emit(
                "processed",
                message_id=str(claim.message_id),
                session_id=str(claim.session_id),
                trace_id=claim.input.trace_id,
                status=result.status,
                latency_ms=(time.monotonic() - started) * 1000,
                error_category="DATABASE_FAILURE"
                if result.status == "database_unavailable"
                else None,
            )
        return result

    async def run(self, stop):
        """Run until the supplied stop event is set; callers connect deployment signals to it."""
        backoff = 1
        while not stop.is_set():
            try:
                result = await self.process_next(stop)
            except SQLAlchemyError:
                result = Result("database_unavailable")
            if result.status == "database_unavailable":
                self.telemetry.emit("database_backoff", error_category="DATABASE_FAILURE")
                delay = backoff * random.uniform(0.8, 1.2)
                backoff = min(backoff * 2, 15)
            else:
                backoff = 1
                delay = self.settings.poll_seconds if result.status == "idle" else 0
            if delay:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
