"""Opt-in offline runner. No application, database, SDK, tools, or retry integration."""

import argparse
import hashlib
import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from experiments.tutor_v1.cases import CASES

ROOT = Path(__file__).parent


def load_prompt(version="v1"):
    filenames = {"v1": "prompt.txt", "v2": "prompt-v2.txt", "v3": "prompt-v3.txt"}
    return (ROOT / filenames[version]).read_text(encoding="utf-8").rstrip("\n")


PROMPT = load_prompt()
CONFIG = {
    "provider": "OpenAI",
    "model": "gpt-6-luna",
    "api": "Responses",
    "reasoning_effort": "none",
    "max_input_tokens": 8000,
    "max_output_tokens": 1000,
    "history_exchanges": 10,
    "timeout_seconds": 30,
    "retries": 0,
    "store": False,
}
DIMENSIONS = (
    "Mathematical correctness",
    "Evidence discipline",
    "Context use",
    "Teaching usefulness",
    "Adaptation",
    "Coursework scope",
)
SCHEMA = {
    "type": "object",
    "properties": {"reply": {"type": "string"}},
    "required": ["reply"],
    "additionalProperties": False,
}


class ExperimentFailure(Exception):
    """Safe offline category; provider errors and credentials are never persisted."""


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def case_context(case, history):
    return {
        "grade": 7,
        "subject": "Mathematics",
        "authorized_problem": case.problem,
        "selected_history": [asdict(exchange) for exchange in history],
        "current_student_message": case.message,
    }


def payload(case, history, prompt=PROMPT):
    context = case_context(case, history)
    return {
        "model": CONFIG["model"],
        "instructions": prompt,
        "input": [{"role": "user", "content": encode(context)}],
        "reasoning": {"effort": "none"},
        "max_output_tokens": 1000,
        "store": False,
        "truncation": "disabled",
        "text": {
            "format": {
                "type": "json_schema",
                "name": "tutor_reply",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }


def token_bound(request):
    # Deliberately conservative local bound, NOT an exact tokenizer count.
    # Byte-level text tokens cannot exceed UTF-8 bytes. Count the entire wire JSON,
    # including schema/keys, and reserve 1024 tokens for provider message framing.
    # This text-only single-user-message experiment never sends tools/images/audio.
    return len(encode(request).encode("utf-8")) + 1024


def prepare(case, prompt=PROMPT):
    history = list(case.history[-CONFIG["history_exchanges"] :])
    removed = len(case.history) - len(history)
    while True:
        request = payload(case, history, prompt)
        bound = token_bound(request)
        if bound <= CONFIG["max_input_tokens"]:
            return request, bound, removed
        if not history:
            raise ExperimentFailure("REQUIRED_CONTENT_OVERFLOW")
        history.pop(0)
        removed += 1


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def validate_response(response):
    if (
        not isinstance(response, dict)
        or response.get("status") != "completed"
        or response.get("incomplete_details") is not None
    ):
        raise ExperimentFailure("INCOMPLETE_OUTPUT")
    output = response.get("output")
    if not isinstance(output, list) or len(output) != 1:
        raise ExperimentFailure("INVALID_OUTPUT")
    message = output[0]
    if (
        not isinstance(message, dict)
        or message.get("type") != "message"
        or message.get("role") != "assistant"
        or message.get("status") != "completed"
    ):
        raise ExperimentFailure("INVALID_OUTPUT")
    content = message.get("content")
    if (
        not isinstance(content, list)
        or len(content) != 1
        or not isinstance(content[0], dict)
        or content[0].get("type") != "output_text"
    ):
        raise ExperimentFailure("INVALID_OUTPUT")
    raw = content[0].get("text")
    try:
        if not isinstance(raw, str):
            raise ValueError("Not text")
        value = json.loads(raw, object_pairs_hook=unique_object)
        if not isinstance(value, dict) or set(value) != {"reply"}:
            raise ValueError("Wrong shape")
        reply = value["reply"]
        if not isinstance(reply, str) or not reply.strip() or "\x00" in reply:
            raise ValueError("Invalid reply")
    except (ValueError, TypeError):
        raise ExperimentFailure("INVALID_OUTPUT") from None
    return reply


def response_envelope(text):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


class FakeClient:
    """Mechanics only; never supplies a quality baseline or real-client fallback."""

    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        return response_envelope(encode({"reply": "Synthetic mechanics-only response."}))


class OpenAIClient:
    """One standard-library HTTP request, fixed endpoint, no SDK or retries."""

    def __init__(self):
        self._key = os.environ["OPENAI_API_KEY"]
        if not self._key.strip():
            raise ValueError("OPENAI_API_KEY is required")

        # No redirects: credentials cannot follow an unexpected provider redirect.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        self._opener = urllib.request.build_opener(NoRedirect())

    def _request(self, request):
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=encode(request).encode("utf-8"),
            headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(req, timeout=30) as response:
                return json.loads(response.read())
        except TimeoutError:
            raise ExperimentFailure("MODEL_TIMEOUT") from None
        except (OSError, urllib.error.URLError, ValueError):
            raise ExperimentFailure("PROVIDER_REQUEST_FAILED") from None

    def generate(self, request):
        # Socket timeouts alone are not a total-call deadline. A daemon transport
        # thread lets local consumption stop at 30 seconds even during DNS/read.
        # Local timeout cannot guarantee remote cancellation or prevent billing.
        results = queue.Queue(maxsize=1)

        def invoke():
            try:
                results.put(self._request(request))
            except ExperimentFailure as exc:
                results.put(exc)
            except Exception:
                results.put(ExperimentFailure("PROVIDER_REQUEST_FAILED"))

        threading.Thread(target=invoke, daemon=True).start()
        try:
            result = results.get(timeout=CONFIG["timeout_seconds"])
        except queue.Empty:
            raise ExperimentFailure("MODEL_TIMEOUT") from None
        if isinstance(result, ExperimentFailure):
            raise result
        return result


def run_case(case, client, prompt=PROMPT):
    record = {
        "case_id": case.id,
        "expectation": case.expectation,
        "supplied_case": asdict(case),
        "review": {name: {"judgment": None, "reason": ""} for name in DIMENSIONS},
        "quality_review_status": "PENDING_HUMAN_REVIEW",
    }
    started = time.monotonic()
    try:
        request, bound, removed = prepare(case, prompt)
        record.update(
            input_token_upper_bound=bound,
            removed_exchanges=removed,
            supplied_context=json.loads(request["input"][0]["content"]),
        )
        response = client.generate(request)
        record["reply"] = validate_response(response)
        usage = response.get("usage", {})
        record["usage"] = {
            key: usage[key]
            for key in ("input_tokens", "output_tokens", "total_tokens")
            if isinstance(usage, dict) and type(usage.get(key)) is int
        }
        model = response.get("model")
        record["returned_model"] = (
            model
            if isinstance(model, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,100}", model)
            else None
        )
        # Provider metadata only; do not retain arbitrary provider payload/errors.
        record["mechanical_status"] = "VALID_REPLY_SHAPE"
    except ExperimentFailure as exc:
        record["mechanical_status"] = "FAILED"
        record["failure_category"] = str(exc)
    record["elapsed_seconds"] = round(time.monotonic() - started, 4)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fake", "paid"), default="fake")
    parser.add_argument("--prompt-version", choices=("v1", "v2", "v3"), default="v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prompt = load_prompt(args.prompt_version)
    # Open exclusively before any provider request: never overwrite existing evidence.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        header = {
            "record_type": "run",
            "experiment": "tutor-v1",
            "dataset_version": "v1",
            "prompt_version": args.prompt_version,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "fixture_sha256": hashlib.sha256(
                encode([asdict(c) for c in CASES]).encode()
            ).hexdigest(),
            "config": CONFIG,
            "mode": args.mode,
            "samples_per_case": 1,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "token_policy": "wire_utf8_bytes_plus_1024_upper_bound",
            "acceptance_claim": None,
        }
        stream.write(encode(header) + "\n")
        stream.flush()
        try:
            client = FakeClient() if args.mode == "fake" else OpenAIClient()
        except (KeyError, ValueError):
            stream.write(
                encode(
                    {"record_type": "failure", "failure_category": "MISSING_PROVIDER_CREDENTIAL"}
                )
                + "\n"
            )
            print("Offline configuration failure: OPENAI_API_KEY is required for paid mode.")
            return 1
        failures = 0
        for case in CASES:
            result = run_case(case, client, prompt)
            failures += result["mechanical_status"] == "FAILED"
            stream.write(encode(result) + "\n")
            stream.flush()
    print(f"Recorded {len(CASES)} cases; {failures} mechanical failures; human review pending.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
