"""Persistent reads and coupled writes. Transaction ownership stays in the service."""

from uuid import uuid4

from sqlalchemy import insert, select, update

from ai_tutor import models as m

OPERATION = "create_student_message"


class MessageRepository:
    def __init__(self, session):
        self.session = session

    def lock_user(self, user_id):
        # A student-wide lock covers keys reused concurrently across different sessions.
        return (
            self.session.execute(select(m.users).where(m.users.c.id == user_id).with_for_update())
            .mappings()
            .one_or_none()
        )

    def owned_session(self, session_id, student_id):
        return (
            self.session.execute(
                select(m.coaching_sessions)
                .where(
                    m.coaching_sessions.c.id == session_id,
                    m.coaching_sessions.c.student_user_id == student_id,
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )

    def active_enrollment(self, student_id, course_id):
        return (
            self.session.execute(
                select(m.enrollments.c.id)
                .where(
                    m.enrollments.c.student_user_id == student_id,
                    m.enrollments.c.course_id == course_id,
                    m.enrollments.c.status == "ACTIVE",
                )
                .with_for_update(read=True)
            ).first()
            is not None
        )

    def existing_message(self, student_id, key):
        return (
            self.session.execute(
                select(m.messages)
                .join(m.idempotency_records, m.idempotency_records.c.message_id == m.messages.c.id)
                .where(
                    m.idempotency_records.c.student_id == student_id,
                    m.idempotency_records.c.operation == OPERATION,
                    m.idempotency_records.c.idempotency_key == key,
                )
            )
            .mappings()
            .one_or_none()
        )

    def eligible_coursework(self, student_id, context):
        # Lock existing authorization rows through admission/commit. Missing rows deny admission.
        return (
            self.session.execute(
                select(m.assignments.c.id)
                .select_from(
                    m.assignments.join(m.assignment_problems)
                    .join(m.problems)
                    .join(
                        m.student_assignment_eligibility,
                        m.student_assignment_eligibility.c.assignment_id == m.assignments.c.id,
                    )
                )
                .where(
                    m.assignments.c.id == context["assignment_id"],
                    m.assignments.c.course_id == context["course_id"],
                    m.problems.c.id == context["problem_id"],
                    m.problems.c.course_id == context["course_id"],
                    m.student_assignment_eligibility.c.student_user_id == student_id,
                )
                .with_for_update(read=True)
            ).first()
            is not None
        )

    def allocate_sequence(self, session_id):
        # Admission already holds the session lock. Counter allocation rolls back with input.
        next_sequence = self.session.execute(
            update(m.coaching_sessions)
            .where(m.coaching_sessions.c.id == session_id)
            .values(next_message_sequence=m.coaching_sessions.c.next_message_sequence + 1)
            .returning(m.coaching_sessions.c.next_message_sequence)
        ).scalar_one()
        return next_sequence - 1

    def insert_message(self, session_id, content, trace_id, session_sequence):
        message_id = uuid4()
        self.session.execute(
            insert(m.messages).values(
                id=message_id,
                session_id=session_id,
                author_type="student",
                content=content,
                processing_status="PENDING",
                trace_id=trace_id,
                session_sequence=session_sequence,
            )
        )
        return message_id

    def insert_processing_job(self, message_id):
        # Database defaults create unclaimed work; this does not start processing.
        self.session.execute(insert(m.message_processing_jobs).values(message_id=message_id))

    def associate_key(self, student_id, key, message_id):
        self.session.execute(
            insert(m.idempotency_records).values(
                id=uuid4(),
                student_id=student_id,
                operation=OPERATION,
                idempotency_key=key,
                message_id=message_id,
            )
        )

    def polling_snapshot(self, student_id, session_id, message_id):
        # One statement snapshots account, visibility, status and response together.
        # Historical visibility matches admission replay, not new-work eligibility.
        reply = m.messages.alias("reply")
        enrolled = (
            select(m.enrollments.c.id)
            .where(
                m.enrollments.c.student_user_id == student_id,
                m.enrollments.c.course_id == m.coaching_sessions.c.course_id,
                m.enrollments.c.status == "ACTIVE",
            )
            .exists()
        )
        return (
            self.session.execute(
                select(
                    m.users.c.is_active,
                    m.users.c.role,
                    m.messages.c.id.label("message_id"),
                    m.messages.c.processing_status,
                    reply.c.id.label("reply_id"),
                    reply.c.content.label("reply_content"),
                )
                .select_from(
                    m.users.outerjoin(
                        m.coaching_sessions,
                        (m.coaching_sessions.c.id == session_id)
                        & (m.coaching_sessions.c.student_user_id == m.users.c.id)
                        & enrolled,
                    )
                    .outerjoin(
                        m.messages,
                        (m.messages.c.session_id == m.coaching_sessions.c.id)
                        & (m.messages.c.id == message_id)
                        & (m.messages.c.author_type == "student"),
                    )
                    .outerjoin(reply, reply.c.in_reply_to_message_id == m.messages.c.id)
                )
                .where(m.users.c.id == student_id)
            )
            .mappings()
            .one_or_none()
        )
