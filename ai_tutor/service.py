from dataclasses import dataclass
from uuid import UUID

from ai_tutor.errors import ApplicationError, not_found, unauthenticated
from ai_tutor.repository import MessageRepository


@dataclass(frozen=True)
class Admission:
    student_message_id: UUID
    status: str
    created: bool


class MessageService:
    def __init__(self, sessions, tracer):
        self.sessions = sessions
        self.tracer = tracer

    @staticmethod
    def authorize_context(repo, session_id, student_id):
        context = repo.owned_session(session_id, student_id)
        if context is None or not repo.active_enrollment(student_id, context["course_id"]):
            raise not_found()
        return context

    def admit(self, student_id, session_id, content, key, trace_id):
        # Context manager commits on successful exit, rolls back on any failure (including commit).
        # Do not move the return inside this boundary or start any AI work here.
        with self.tracer.start_as_current_span(
            "student_message.transaction", record_exception=False, set_status_on_exception=False
        ):
            with self.sessions.begin() as session:
                repo = MessageRepository(session)
                user = repo.lock_user(student_id)
                if user is None or not user["is_active"]:
                    raise unauthenticated()
                if user["role"] != "STUDENT":
                    raise ApplicationError(403, "forbidden", "This action is not permitted.")
                context = self.authorize_context(repo, session_id, student_id)
                existing = repo.existing_message(student_id, key)
                if existing is not None:
                    if existing["session_id"] != session_id:
                        self.authorize_context(repo, existing["session_id"], student_id)
                    if existing["content"] != content:
                        raise ApplicationError(
                            409,
                            "idempotency_conflict",
                            "This key was already used for different content.",
                        )
                    result = Admission(existing["id"], existing["processing_status"], False)
                else:
                    if context["status"] != "ACTIVE":
                        raise ApplicationError(
                            409,
                            "session_state_conflict",
                            "This coaching session is no longer accepting messages.",
                        )
                    if not repo.eligible_coursework(student_id, context):
                        raise ApplicationError(403, "forbidden", "This action is not permitted.")
                    sequence = repo.allocate_sequence(session_id)
                    message_id = repo.insert_message(session_id, content, trace_id, sequence)
                    repo.insert_processing_job(message_id)
                    repo.associate_key(student_id, key, message_id)
                    result = Admission(message_id, "PENDING", True)
        return result

    def read_status(self, student_id, session_id, message_id):
        with self.sessions.begin() as session:
            row = MessageRepository(session).polling_snapshot(student_id, session_id, message_id)
            if row is None or not row["is_active"]:
                raise unauthenticated()
            if row["role"] != "STUDENT":
                raise ApplicationError(403, "forbidden", "This action is not permitted.")
            if row["message_id"] is None:
                raise not_found()
            status = row["processing_status"]
            if (
                status not in {"PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"}
                or (status == "COMPLETED") != (row["reply_id"] is not None)
                or (status == "COMPLETED" and not row["reply_content"])
            ):
                raise ApplicationError(500, "internal_error", "Unable to read message status.")
            result = {
                "student_message_id": message_id,
                "status": status,
                "tutor_response": None,
                "error": None,
            }
            if status == "COMPLETED":
                result["tutor_response"] = {
                    "tutor_message_id": row["reply_id"],
                    "content": row["reply_content"],
                }
            elif status == "FAILED":
                result["error"] = {
                    "code": "tutor_processing_failed",
                    "message": (
                        "Your message was saved, but the tutor could not complete a response."
                    ),
                }
            elif status == "CANCELLED":
                result["error"] = {
                    "code": "message_processing_cancelled",
                    "message": "Your message was saved, but processing has stopped.",
                }
        return result
