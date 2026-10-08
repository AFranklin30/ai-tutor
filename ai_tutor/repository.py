"""Persistent reads and coupled writes. Transaction ownership stays in the service."""

from uuid import uuid4

from sqlalchemy import insert, select

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

    def insert_message(self, session_id, content, trace_id):
        message_id = uuid4()
        self.session.execute(
            insert(m.messages).values(
                id=message_id,
                session_id=session_id,
                author_type="student",
                content=content,
                processing_status="PENDING",
                trace_id=trace_id,
            )
        )
        return message_id

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
