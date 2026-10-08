"""Small allow-listed JSON log formatter; no SQL, credentials, content, or exception text."""

import json
import logging

FIELDS = (
    "trace_id",
    "message_id",
    "session_id",
    "content_length",
    "status",
    "latency_ms",
    "error_category",
)


class MetadataFormatter(logging.Formatter):
    def format(self, record):
        data = {"event": "student_message_request"}
        data.update({field: getattr(record, field, None) for field in FIELDS})
        return json.dumps(data)


def configure_logging():
    logger = logging.getLogger("ai_tutor.requests")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(MetadataFormatter())
        logger.addHandler(handler)
