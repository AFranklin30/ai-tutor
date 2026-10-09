"""Fenced processing operations; no external work within transaction boundaries."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import text

from ai_tutor.processing_repository import ProcessingRepository
from ai_tutor.worker_observability import WorkerTelemetry

TRANSIENT = frozenset({"MODEL_TIMEOUT", "MODEL_UNAVAILABLE", "MODEL_RATE_LIMITED"})
FAILURES = TRANSIENT | {
    "MODEL_INVALID_OUTPUT",
    "MODEL_CONFIGURATION",
    "POLICY_REJECTED",
    "PROCESSING_ERROR",
    "DATABASE_FAILURE",
    "LEASE_EXPIRED",
}


@dataclass(frozen=True)
class WorkerSettings:
    model_timeout: float = 30
    lease_seconds: float = 45
    heartbeat_seconds: float = 10
    attempt_seconds: float = 90
    completion_margin: float = 5
    retry_delay: float = 2
    shutdown_seconds: float = 35
    poll_seconds: float = 1

    def __post_init__(self):
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("Worker timings must be positive")
        if not (
            self.heartbeat_seconds < self.lease_seconds
            and self.model_timeout + self.completion_margin
            < self.lease_seconds
            <= self.attempt_seconds
        ):
            raise ValueError("Worker lease/timeout/deadline timings are incompatible")


@dataclass(frozen=True)
class ProcessingInput:
    message_id: UUID
    session_id: UUID
    content: str = field(repr=False)
    trace_id: Optional[str] = None


@dataclass(frozen=True)
class Claim:
    message_id: UUID
    session_id: UUID
    student_id: UUID
    token: UUID = field(repr=False)
    generation: int
    attempt: int
    expires_at: datetime
    deadline: datetime
    input: ProcessingInput = field(repr=False)
    queue_wait_seconds: float = 0


@dataclass(frozen=True)
class Result:
    status: str
    response_id: Optional[UUID] = None
    remaining_seconds: Optional[float] = None


class ProcessingService:
    def __init__(self, sessions, settings=None, telemetry=None):
        self.sessions = sessions
        self.settings = settings or WorkerSettings()
        self.telemetry = telemetry or WorkerTelemetry()

    @contextmanager
    def transaction(self):
        with self.sessions.begin() as session:
            # Bound lock contention/query time, especially for heartbeats. These are
            # local transaction controls, not additional model/retry budgets.
            session.execute(text("SET LOCAL lock_timeout = '1s'"))
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            repo = ProcessingRepository(session)
            yield repo
        # A rollback must not emit a durable state-change event.
        for metadata in repo.events:
            self.telemetry.emit("state_saved", **metadata)

    @staticmethod
    def _owned(message, job, claim, now):
        return (
            message["id"] == claim.message_id
            and message["session_id"] == claim.session_id
            and message["author_type"] == "student"
            and message["processing_status"] == "PROCESSING"
            and job["claim_token"] == claim.token
            and job["retry_generation"] == claim.generation
            and job["lease_expires_at"] is not None
            and job["lease_expires_at"] > now
            and job["attempt_deadline_at"] is not None
            and job["attempt_deadline_at"] > now
        )

    def _retry_or_fail(self, repo, message, job, now, code, eligible):
        if eligible and job["cycle_attempt_count"] < job["max_attempts"]:
            repo.transition(
                message["id"],
                "PENDING",
                now,
                claim_token=None,
                worker_instance_id=None,
                claimed_at=None,
                lease_expires_at=None,
                attempt_deadline_at=None,
                finished_at=None,
                next_attempt_at=now + timedelta(seconds=self.settings.retry_delay),
                last_error_code=code,
                last_error_at=now,
                cancel_reason=None,
            )
            return Result("requeued")
        repo.transition(
            message["id"],
            "FAILED",
            now,
            lease_expires_at=None,
            attempt_deadline_at=None,
            next_attempt_at=None,
            last_error_code=code,
            last_error_at=now,
            cancel_reason=None,
            finished_at=now,
        )
        return Result("failed")

    def claim_next(self, worker_instance_id):
        # Candidate read ends before locking. Each candidate gets its own short transaction.
        with self.transaction() as repo:
            candidates = repo.candidates()
        for session_id, student_id in candidates:
            claim = None
            with self.transaction() as repo:
                locked = repo.lock_context(student_id, session_id, skip=True)
                if locked is None:
                    continue
                _, reason = locked
                if reason:
                    repo.cancel_session(session_id, reason)
                    continue
                head_id = repo.head(session_id)  # Fresh snapshot under session lock.
                if head_id is None:
                    continue
                work = repo.lock_work(head_id, skip=True)
                if work is None:
                    continue  # Never try the next message in this session.
                message, job = work
                now = repo.now()
                status = message["processing_status"]
                if status == "PROCESSING":
                    if job["lease_expires_at"] <= now or job["attempt_deadline_at"] <= now:
                        self._retry_or_fail(repo, message, job, now, "LEASE_EXPIRED", True)
                    continue
                if status != "PENDING" or job["next_attempt_at"] > now:
                    continue
                # Exhaustion becomes FAILED during processing failure/recovery. A PENDING
                # row with no budget is not claimable (never increment beyond the DB check).
                if job["cycle_attempt_count"] >= job["max_attempts"]:
                    continue
                token = uuid4()
                expires = now + timedelta(seconds=self.settings.lease_seconds)
                deadline = now + timedelta(seconds=self.settings.attempt_seconds)
                repo.transition(
                    head_id,
                    "PROCESSING",
                    now,
                    claim_token=token,
                    worker_instance_id=worker_instance_id,
                    claimed_at=now,
                    lease_expires_at=expires,
                    attempt_deadline_at=deadline,
                    next_attempt_at=None,
                    finished_at=None,
                    cancel_reason=None,
                    attempt_count=job["attempt_count"] + 1,
                    cycle_attempt_count=job["cycle_attempt_count"] + 1,
                )
                claim = Claim(
                    head_id,
                    session_id,
                    student_id,
                    token,
                    job["retry_generation"],
                    job["cycle_attempt_count"] + 1,
                    expires,
                    deadline,
                    ProcessingInput(head_id, session_id, message["content"], message["trace_id"]),
                    max(0, (now - message["created_at"]).total_seconds()),
                )
            if claim is not None:
                return claim  # After commit, never expose an uncommitted claim.
        return None

    def _operate(self, claim, action, content=None, code=None):
        result = Result("lost")
        with self.transaction() as repo:
            locked = repo.lock_context(claim.student_id, claim.session_id)
            if locked is None:
                return result
            _, reason = locked
            work = repo.lock_work(claim.message_id)
            if work is None:
                return result
            message, job = work
            now = repo.now()
            # Only reconcile a prior completion for the exact winning token/generation,
            # and never reveal it after current access is revoked.
            if (
                action == "complete"
                and not reason
                and message["session_id"] == claim.session_id
                and message["processing_status"] == "COMPLETED"
                and job["claim_token"] == claim.token
                and job["retry_generation"] == claim.generation
            ):
                result = Result("already_completed", repo.response_id(claim.message_id))
            elif not self._owned(message, job, claim, now):
                result = Result("lost")
            elif reason:
                # Check the token first: stale claim callbacks cannot cancel replacement work.
                repo.cancel_session(claim.session_id, reason)
                result = Result("cancelled")
            elif action == "cancel":
                # Cancellation uses persisted policy, not caller-supplied reasons.
                result = Result("not_cancelled")
            elif action == "renew":
                expires = min(
                    now + timedelta(seconds=self.settings.lease_seconds), job["attempt_deadline_at"]
                )
                repo.transition(claim.message_id, "PROCESSING", now, lease_expires_at=expires)
                result = Result("renewed", remaining_seconds=(expires - now).total_seconds())
            elif action == "failure":
                result = self._retry_or_fail(repo, message, job, now, code, code in TRANSIENT)
            elif action == "complete":
                response_id = uuid4()
                repo.insert_response(message, response_id, content)
                repo.transition(
                    claim.message_id,
                    "COMPLETED",
                    now,
                    lease_expires_at=None,
                    attempt_deadline_at=None,
                    next_attempt_at=None,
                    finished_at=now,
                    cancel_reason=None,
                )
                result = Result("completed", response_id)
        return result

    def renew_lease(self, claim):
        return self._operate(claim, "renew")

    def complete(self, claim, content):
        # The injected processor must already validate semantic/policy output. This
        # boundary checks the concrete persisted text shape, not tutoring policy.
        if not isinstance(content, str) or not content.strip() or "\x00" in content:
            return self.record_failure(claim, "MODEL_INVALID_OUTPUT")
        return self._operate(claim, "complete", content=content)

    def record_failure(self, claim, code):
        if not isinstance(code, str) or code not in FAILURES:
            code = "PROCESSING_ERROR"
        return self._operate(claim, "failure", code=code)

    def cancel(self, claim):
        return self._operate(claim, "cancel")

    def reconcile_completion(self, claim):
        """Read back an uncertain completion; never start processing or write state."""
        with self.transaction() as repo:
            context = repo.lock_context(claim.student_id, claim.session_id)
            if context is None or context[1]:
                return Result("lost")
            work = repo.lock_work(claim.message_id)
            if work is None:
                return Result("lost")
            message, job = work
            if (
                message["session_id"] == claim.session_id
                and message["processing_status"] == "COMPLETED"
                and job["claim_token"] == claim.token
                and job["retry_generation"] == claim.generation
            ):
                return Result("already_completed", repo.response_id(claim.message_id))
            return Result("unconfirmed")
