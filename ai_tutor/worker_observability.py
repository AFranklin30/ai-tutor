"""Metadata-only worker events and optional OpenTelemetry metrics; no exporter/platform."""

import json
import logging

from opentelemetry import metrics

FIELDS = (
    "message_id",
    "session_id",
    "trace_id",
    "status",
    "error_category",
    "latency_ms",
    "attempt",
    "queue_wait_ms",
)


class WorkerFormatter(logging.Formatter):
    def format(self, record):
        data = {"event": "worker", "operation": getattr(record, "operation", "unknown")}
        data.update({key: getattr(record, key, None) for key in FIELDS})
        return json.dumps(data)


class WorkerTelemetry:
    def __init__(self, meter=None):
        self.logger = logging.getLogger("ai_tutor.worker")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(WorkerFormatter())
            self.logger.addHandler(handler)
        meter = meter or metrics.get_meter("ai_tutor.worker")
        self.events = meter.create_counter("worker.events")
        self.latency = meter.create_histogram("worker.processing.duration", unit="s")
        self.queue_wait = meter.create_histogram("worker.queue.wait", unit="s")

    def emit(self, operation, **metadata):
        # Do not accept exception objects, content, credentials, or claim tokens.
        safe = {key: value for key, value in metadata.items() if key in FIELDS}
        self.logger.info("worker", extra={"operation": operation, **safe})
        labels = {
            "operation": operation,
            "status": safe.get("status") or "none",
            "error_category": safe.get("error_category") or "none",
        }
        self.events.add(1, labels)
        if "latency_ms" in safe:
            self.latency.record(safe["latency_ms"] / 1000, labels)
        if "queue_wait_ms" in safe:
            self.queue_wait.record(safe["queue_wait_ms"] / 1000)
