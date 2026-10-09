import logging
import re
import time
from typing import Literal, Optional
from uuid import UUID

from fastapi import FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry.propagate import extract
from opentelemetry.sdk.trace import TracerProvider
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ai_tutor.auth import resolve_principal
from ai_tutor.config import Settings
from ai_tutor.errors import ApplicationError
from ai_tutor.observability import configure_logging
from ai_tutor.service import MessageService

logger = logging.getLogger("ai_tutor.requests")


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: StrictStr

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or "\x00" in value:
            raise ValueError("Content must be nonblank PostgreSQL text")
        return value


class PublicError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: PublicError


class MessageResponse(BaseModel):
    student_message_id: UUID
    status: str


class TutorResponse(BaseModel):
    tutor_message_id: UUID
    content: str


class PollingResponse(BaseModel):
    student_message_id: UUID
    status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]
    tutor_response: Optional[TutorResponse] = None
    error: Optional[PublicError] = None


def create_app(settings: Optional[Settings] = None, engine=None, trace_provider=None):
    configure_logging()
    settings = settings or Settings.from_environment()
    engine = engine or create_engine(
        settings.database_url, hide_parameters=True, pool_pre_ping=True
    )
    sessions = sessionmaker(engine)
    # No exporter or external telemetry platform; compatible spans and valid trace IDs only.
    tracer = (trace_provider or TracerProvider()).get_tracer("ai_tutor.slice1")
    service = MessageService(sessions, tracer)
    app = FastAPI(title="AI Tutor — Slice 1")
    app.state.engine = engine
    app.state.service = service

    @app.middleware("http")
    async def request_metadata(request: Request, call_next):
        started = time.monotonic()
        with tracer.start_as_current_span(
            "http.student_message",
            context=extract(request.headers),
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            request.state.trace_id = format(span.get_span_context().trace_id, "032x")
            request.state.error_category = None
            request.state.message_id = None
            request.state.session_id = None
            request.state.content_length = None
            request.state.processing_status = None
            try:
                response = await call_next(request)
                if request.method == "GET":
                    response.headers["Cache-Control"] = "no-store"
                span.set_attribute("http.response.status_code", response.status_code)
                return response
            finally:
                logger.info(
                    "student_message_request",
                    extra={
                        "trace_id": request.state.trace_id,
                        "message_id": request.state.message_id,
                        "session_id": request.state.session_id,
                        "content_length": request.state.content_length,
                        "status": request.state.processing_status,
                        "error_category": request.state.error_category,
                        "latency_ms": round((time.monotonic() - started) * 1000, 3),
                    },
                )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc):
        # Never echo Pydantic's input/ctx fields, which can include credentials or content.
        request.state.error_category = "validation_error"
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "The request contains invalid data.",
                }
            },
        )

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError):
        request.state.error_category = exc.code
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc):
        request.state.error_category = "database_failure"
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "storage_unavailable",
                    "message": (
                        "Status is temporarily unavailable. Please try again."
                        if request.method == "GET"
                        else "Unable to confirm the request. Retry with the same Idempotency-Key."
                    ),
                }
            },
        )

    @app.post(
        "/api/v1/coaching/sessions/{session_id}/messages",
        response_model=MessageResponse,
        status_code=201,
        responses={
            200: {"model": MessageResponse, "description": "Authorized idempotent replay"},
            **{code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)},
        },
    )
    def create_message(
        session_id: UUID,
        body: MessageRequest,
        request: Request,
        response: Response,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
        authorization: Optional[str] = Header(default=None),
    ):
        request.state.session_id = str(session_id)
        request.state.content_length = len(body.content)
        if (
            len(request.headers.getlist("idempotency-key")) != 1
            or idempotency_key is None
            or not re.fullmatch(r"[\x21-\x7e]{1,255}", idempotency_key)
            or len(body.content) > settings.max_message_characters
        ):
            raise ApplicationError(422, "validation_error", "The request contains invalid data.")
        if len(request.headers.getlist("authorization")) > 1:
            authorization = None
        principal = resolve_principal(authorization, settings)
        result = service.admit(
            principal,
            session_id,
            body.content,
            idempotency_key,
            request.state.trace_id,
        )
        response.status_code = 201 if result.created else 200
        request.state.message_id = str(result.student_message_id)
        request.state.processing_status = result.status
        return MessageResponse(student_message_id=result.student_message_id, status=result.status)

    @app.get(
        "/api/v1/coaching/sessions/{session_id}/messages/{message_id}/status",
        response_model=PollingResponse,
        responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 422, 500, 503)},
    )
    def get_message_status(
        session_id: UUID,
        message_id: UUID,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        request.state.session_id = str(session_id)
        request.state.message_id = str(message_id)
        if len(request.headers.getlist("authorization")) > 1:
            authorization = None
        principal = resolve_principal(authorization, settings)
        result = service.read_status(principal, session_id, message_id)
        request.state.processing_status = result["status"]
        return result

    return app
