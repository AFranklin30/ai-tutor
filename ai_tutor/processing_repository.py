"""PostgreSQL processing reads/writes. Callers own short transactions and lock order."""

from sqlalchemy import func, insert, select, update

from ai_tutor import models as m
from ai_tutor.repository import MessageRepository

UNRESOLVED = ("PENDING", "PROCESSING", "FAILED")


class ProcessingRepository(MessageRepository):
    def __init__(self, session):
        super().__init__(session)
        self.events = []

    def candidates(self):
        # Read heads before testing readiness. FAILED/backoff heads must not be skipped.
        heads = (
            select(m.messages.c.id, m.messages.c.session_id)
            .where(
                m.messages.c.author_type == "student",
                m.messages.c.processing_status.in_(UNRESOLVED),
            )
            .distinct(m.messages.c.session_id)
            .order_by(m.messages.c.session_id, m.messages.c.session_sequence)
            .subquery()
        )
        # Include blocked heads so revoked/closed sessions can be cancelled too. No LIMIT
        # that would let a fixed prefix of FAILED sessions starve other sessions in this MVP.
        return self.session.execute(
            select(m.coaching_sessions.c.id, m.coaching_sessions.c.student_user_id)
            .join(heads, heads.c.session_id == m.coaching_sessions.c.id)
            .join(m.message_processing_jobs, m.message_processing_jobs.c.message_id == heads.c.id)
            .order_by(
                func.coalesce(
                    m.message_processing_jobs.c.next_attempt_at,
                    m.message_processing_jobs.c.lease_expires_at,
                    m.message_processing_jobs.c.created_at,
                ),
                m.coaching_sessions.c.id,
            )
        ).all()

    def lock_context(self, student_id, session_id, skip=False):
        user = (
            self.session.execute(
                select(m.users).where(m.users.c.id == student_id).with_for_update(skip_locked=skip)
            )
            .mappings()
            .one_or_none()
        )
        if user is None:
            return None
        context = (
            self.session.execute(
                select(m.coaching_sessions)
                .where(
                    m.coaching_sessions.c.id == session_id,
                    m.coaching_sessions.c.student_user_id == student_id,
                )
                .with_for_update(skip_locked=skip)
            )
            .mappings()
            .one_or_none()
        )
        if context is None:
            return None
        reason = None
        if not user["is_active"] or user["role"] != "STUDENT":
            reason = "ACCOUNT_DISABLED"
        elif not self.active_enrollment(student_id, context["course_id"]):
            reason = "ENROLLMENT_REVOKED"
        elif not self.eligible_coursework(student_id, context):
            reason = "COURSEWORK_INELIGIBLE"
        elif context["status"] == "CLOSED":
            if context["closure_reason"] == "ADMINISTRATIVE":
                reason = "SESSION_ADMIN_CLOSED"
            elif context["closure_reason"] != "NORMAL":
                reason = "SESSION_CLOSURE_UNKNOWN"
        elif context["status"] != "ACTIVE":
            reason = "SESSION_CLOSURE_UNKNOWN"
        return context, reason

    def head(self, session_id):
        return self.session.scalar(
            select(m.messages.c.id)
            .where(
                m.messages.c.session_id == session_id,
                m.messages.c.author_type == "student",
                m.messages.c.processing_status.in_(UNRESOLVED),
            )
            .order_by(m.messages.c.session_sequence)
            .limit(1)
        )

    def lock_work(self, message_id, skip=False):
        message = (
            self.session.execute(
                select(m.messages)
                .where(m.messages.c.id == message_id)
                .with_for_update(skip_locked=skip)
            )
            .mappings()
            .one_or_none()
        )
        if message is None:
            return None
        job = (
            self.session.execute(
                select(m.message_processing_jobs)
                .where(m.message_processing_jobs.c.message_id == message_id)
                .with_for_update(skip_locked=skip)
            )
            .mappings()
            .one_or_none()
        )
        return (message, job) if job is not None else None

    def now(self):
        return self.session.scalar(select(func.clock_timestamp()))

    def transition(self, message_id, status, now, **metadata):
        self.session.execute(
            update(m.message_processing_jobs)
            .where(m.message_processing_jobs.c.message_id == message_id)
            .values(updated_at=now, **metadata)
        )
        self.session.execute(
            update(m.messages).where(m.messages.c.id == message_id).values(processing_status=status)
        )

        context = self.session.execute(
            select(m.messages.c.session_id, m.messages.c.trace_id).where(
                m.messages.c.id == message_id
            )
        ).one()
        self.events.append(
            dict(
                message_id=str(message_id),
                session_id=str(context.session_id),
                trace_id=context.trace_id,
                status=status,
                error_category=metadata.get("cancel_reason") or metadata.get("last_error_code"),
            )
        )

    def response_id(self, message_id):
        return self.session.scalar(
            select(m.messages.c.id).where(m.messages.c.in_reply_to_message_id == message_id)
        )

    def insert_response(self, message, response_id, content):
        self.session.execute(
            insert(m.messages).values(
                id=response_id,
                session_id=message["session_id"],
                author_type="tutor",
                content=content,
                processing_status="COMPLETED",
                trace_id=message["trace_id"],
                in_reply_to_message_id=message["id"],
            )
        )

    def cancel_session(self, session_id, reason):
        # Caller holds user/session and checked current server-owned policy. Cancel all
        # unfinished inputs in this session, never free its head to run later denied work.
        ids = self.session.scalars(
            select(m.messages.c.id)
            .where(
                m.messages.c.session_id == session_id,
                m.messages.c.author_type == "student",
                m.messages.c.processing_status.in_(UNRESOLVED),
            )
            .order_by(m.messages.c.session_sequence)
        ).all()
        for message_id in ids:
            self.lock_work(message_id)
            now = self.now()
            self.transition(
                message_id,
                "CANCELLED",
                now,
                claim_token=None,
                lease_expires_at=None,
                attempt_deadline_at=None,
                next_attempt_at=None,
                cancel_reason=reason,
                finished_at=now,
            )
        return len(ids)
