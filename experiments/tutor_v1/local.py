"""Explicit Ollama-only evaluation: python -m experiments.tutor_v1.local --output NEW.jsonl."""

import argparse
import hashlib
import json
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from experiments.tutor_v1.runner import (
    CASES,
    DIMENSIONS,
    PROMPT,
    SCHEMA,
    ExperimentFailure,
    case_context,
    encode,
    load_prompt,
    response_envelope,
    validate_response,
)

MODEL = "qwen3.5:4b-q4_K_M"
# The v2 comparison must use the exact model recorded in the v1 baseline.
BASELINE_MODEL_DIGEST = "d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04"
HOST = "127.0.0.1:11435"
CONFIG = {
    "provider": "Ollama local",
    "model": MODEL,
    "api": "/api/chat",
    "host": HOST,
    "cloud_disabled": True,
    "think": False,
    "num_ctx": 12288,
    "max_input_tokens": 8000,
    "num_predict": 1000,
    "history_exchanges": 10,
    "timeout_seconds": 30,
    "retries": 0,
    "stream": False,
    "keep_alive": "5m",
    "sampling": "installed model defaults; parameters captured in runtime record",
}
TOKEN_POLICY = "qwen35_gpt2_utf8_wire_bytes_plus_1024_assumed_framing_bound"
COUNTERS = (
    "prompt_eval_count",
    "prompt_eval_cached_count",
    "eval_count",
    "total_duration",
    "load_duration",
    "prompt_eval_duration",
    "eval_duration",
)


def payload(case, history, prompt=PROMPT):
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": encode(case_context(case, history))},
        ],
        "format": SCHEMA,
        "think": False,
        "stream": False,
        "keep_alive": CONFIG["keep_alive"],
        "options": {"num_ctx": CONFIG["num_ctx"], "num_predict": CONFIG["num_predict"]},
    }


def token_bound(request):
    # Independently justified for verified qwen35 GPT-2 byte-level BPE metadata.
    # Wire bytes overcount text/schema; 1024 is an ASSUMED renderer/framing reserve,
    # not a measured tokenizer count. No images, tools, or extra system prompt allowed.
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


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaClient:
    """Fixed loopback transport; never downloads, redirects, uses proxies or API keys."""

    def __init__(self):
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def _request(self, path, body=None):
        if path not in ("/api/version", "/api/tags", "/api/show", "/api/chat", "/api/ps"):
            raise ExperimentFailure("LOCAL_INVALID_ENDPOINT")
        req = urllib.request.Request(
            "http://" + HOST + path,
            data=encode(body).encode("utf-8") if body is not None else None,
            headers={"Content-Type": "application/json"},
            method="POST" if body is not None else "GET",
        )
        try:
            with self._opener.open(req, timeout=CONFIG["timeout_seconds"]) as response:
                value = json.loads(response.read())
            if not isinstance(value, dict) or "error" in value:
                raise ExperimentFailure("LOCAL_REQUEST_FAILED")
            return value
        except TimeoutError:
            raise ExperimentFailure("MODEL_TIMEOUT") from None
        except (OSError, urllib.error.URLError, ValueError):
            raise ExperimentFailure("LOCAL_REQUEST_FAILED") from None

    def request(self, path, body=None):
        # Enforce a total deadline as well as socket timeouts; never retry a request.
        results = queue.Queue(maxsize=1)

        def invoke():
            try:
                results.put(self._request(path, body))
            except ExperimentFailure as exc:
                results.put(exc)
            except Exception:
                results.put(ExperimentFailure("LOCAL_REQUEST_FAILED"))

        threading.Thread(target=invoke, daemon=True).start()
        try:
            result = results.get(timeout=CONFIG["timeout_seconds"])
        except queue.Empty:
            raise ExperimentFailure("MODEL_TIMEOUT") from None
        if isinstance(result, ExperimentFailure):
            raise result
        return result

    def inspect(self):
        version = self.request("/api/version").get("version")
        tags = self.request("/api/tags").get("models", [])
        if not isinstance(tags, list):
            raise ExperimentFailure("LOCAL_MODEL_METADATA_INVALID")
        installed = next((m for m in tags if isinstance(m, dict) and m.get("name") == MODEL), {})
        digest = installed.get("digest")
        if not isinstance(digest, str) or not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest):
            raise ExperimentFailure("LOCAL_MODEL_NOT_INSTALLED")
        show = self.request("/api/show", {"model": MODEL})
        details = show.get("details", {})
        info = show.get("model_info", {})
        thinking_info = show.get("thinking")
        thinking = thinking_info.get("values", []) if isinstance(thinking_info, dict) else []
        if not isinstance(details, dict) or not isinstance(info, dict):
            raise ExperimentFailure("LOCAL_MODEL_METADATA_INVALID")
        if (
            details.get("quantization_level") != "Q4_K_M"
            or info.get("general.architecture") != "qwen35"
            or not re.fullmatch(r"4(?:\.\d+)?B", str(details.get("parameter_size", "")))
            or info.get("tokenizer.ggml.model") != "gpt2"
            or info.get("tokenizer.ggml.pre") != "qwen35"
            or not isinstance(show.get("system", ""), str)
            or show.get("system", "").strip()
            or show.get("messages")
            or show.get("remote_host")
        ):
            raise ExperimentFailure("LOCAL_MODEL_MISMATCH")
        if (
            type(info.get("qwen35.context_length")) is not int
            or info["qwen35.context_length"] < CONFIG["num_ctx"]
            or not isinstance(thinking, list)
            or not any(v is False for v in thinking)
        ):
            raise ExperimentFailure("LOCAL_SETTINGS_UNSUPPORTED")
        if not isinstance(version, str) or not re.fullmatch(r"[0-9][A-Za-z0-9.+_-]{0,63}", version):
            raise ExperimentFailure("LOCAL_RUNTIME_VERSION_INVALID")
        return {
            "record_type": "runtime",
            "version": version,
            "model": MODEL,
            "digest": digest,
            "quantization": details["quantization_level"],
            "parameter_size": details["parameter_size"],
            "model_context_length": info["qwen35.context_length"],
            "tokenizer": {k: info[k] for k in ("tokenizer.ggml.model", "tokenizer.ggml.pre")},
            "thinking_values": thinking,
            "model_parameters": show.get("parameters"),
            "renderer": show.get("renderer"),
            "parser": show.get("parser"),
            "template_source": show.get("template_source"),
            "template_sha256": hashlib.sha256(str(show.get("template", "")).encode()).hexdigest(),
            "model_size_bytes": installed.get("size"),
            "server_controls": "cloud disabled and loopback binding verified in owned server log",
        }

    def running_model(self, identity):
        models = self.request("/api/ps").get("models", [])
        if not isinstance(models, list):
            raise ExperimentFailure("LOCAL_RUNTIME_CONTEXT_UNVERIFIED")
        model = next((m for m in models if isinstance(m, dict) and m.get("name") == MODEL), {})
        if model.get("digest") != identity["digest"]:
            raise ExperimentFailure("LOCAL_MODEL_MISMATCH")
        if model.get("context_length") != CONFIG["num_ctx"]:
            raise ExperimentFailure("LOCAL_RUNTIME_CONTEXT_UNVERIFIED")
        return {
            k: model[k]
            for k in ("size", "size_vram", "context_length")
            if type(model.get(k)) is int and model[k] >= 0
        }


@contextmanager
def local_server():
    """Own a fresh server on a dedicated port; never trust an existing daemon's settings."""
    binary = shutil.which("ollama")
    if binary is None:
        raise ExperimentFailure("OLLAMA_NOT_INSTALLED")
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 11435))
    except OSError:
        raise ExperimentFailure("LOCAL_PORT_UNAVAILABLE") from None
    env = os.environ.copy()
    env.update(
        OLLAMA_HOST=HOST,
        OLLAMA_NO_CLOUD="1",
        OLLAMA_NUM_PARALLEL="1",
        OLLAMA_MAX_LOADED_MODELS="1",
        OLLAMA_CONTEXT_LENGTH=str(CONFIG["num_ctx"]),
        OLLAMA_DEBUG="0",
    )
    # Startup output is used only to verify cloud/bind controls, never copied to evidence.
    with tempfile.TemporaryFile(mode="w+b") as log:
        try:
            process = subprocess.Popen([binary, "serve"], env=env, stdout=log, stderr=log)
        except OSError:
            raise ExperimentFailure("LOCAL_SERVER_START_FAILED") from None
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    raise ExperimentFailure("LOCAL_SERVER_START_FAILED")
                # pread does not move the shared file offset used by the child.
                startup = os.pread(log.fileno(), 1_048_576, 0).decode("utf-8", errors="replace")
                if "Ollama cloud disabled: true" in startup and f"Listening on {HOST}" in startup:
                    break
                if time.monotonic() >= deadline:
                    raise ExperimentFailure("LOCAL_SERVER_CONTROLS_UNVERIFIED")
                time.sleep(0.1)
            yield OllamaClient()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def response_metadata(response):
    return {k: response[k] for k in COUNTERS if type(response.get(k)) is int and response[k] >= 0}


def validate_local(response, bound):
    if response.get("done") is not True or response.get("done_reason") != "stop":
        raise ExperimentFailure("INCOMPLETE_OUTPUT")
    if response.get("model") != MODEL:
        raise ExperimentFailure("LOCAL_MODEL_MISMATCH")
    message = response.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        raise ExperimentFailure("INVALID_OUTPUT")
    if message.get("thinking") or message.get("tool_calls") or message.get("images"):
        raise ExperimentFailure("UNEXPECTED_THINKING_OR_ACTION")
    # Actual prompt counts are post-hoc evidence, not an exact preflight tokenizer.
    count = response.get("prompt_eval_count")
    if type(count) is int and (count > CONFIG["max_input_tokens"] or count > bound):
        raise ExperimentFailure("LOCAL_INPUT_BOUND_EXCEEDED")
    count = response.get("eval_count")
    if type(count) is int and count > CONFIG["num_predict"]:
        raise ExperimentFailure("LOCAL_OUTPUT_ALLOWANCE_EXCEEDED")
    return validate_response(response_envelope(message.get("content")))


def case_record(case, identity):
    return {
        "case_id": case.id,
        "expectation": case.expectation,
        "supplied_case": asdict(case),
        "quality_review_status": "PENDING_HUMAN_REVIEW",
        "review": {d: {"judgment": None, "reason": ""} for d in DIMENSIONS},
        "model_identity": identity,
        "generation_attempted": False,
    }


def run_case(case, client, identity, prompt=PROMPT):
    record = case_record(case, identity)
    started = time.monotonic()
    try:
        request, bound, removed = prepare(case, prompt)
        record.update(
            input_token_upper_bound=bound,
            removed_exchanges=removed,
            supplied_context=json.loads(request["messages"][1]["content"]),
        )
        record["generation_attempted"] = True
        response = client.request("/api/chat", request)
        # Retain usage even for invalid/incomplete replies; do not retain thinking/errors.
        record["usage"] = response_metadata(response)
        record["done_reason"] = (
            response.get("done_reason")
            if response.get("done_reason") in ("stop", "length", "load", "unload")
            else None
        )
        record["thinking_present"] = (
            bool(response.get("message", {}).get("thinking"))
            if isinstance(response.get("message"), dict)
            else False
        )
        record["reply"] = validate_local(response, bound)
        record["runtime_memory"] = client.running_model(identity)
        record["mechanical_status"] = "VALID_REPLY_SHAPE"
    except ExperimentFailure as exc:
        record.update(mechanical_status="FAILED", failure_category=str(exc))
    record["elapsed_seconds"] = round(time.monotonic() - started, 4)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-version", choices=("v1", "v2", "v3"), default="v1")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--network-disconnected",
        action="store_true",
        help="Record operator attestation; does not disconnect or verify networking.",
    )
    args = parser.parse_args()
    prompt = load_prompt(args.prompt_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:

        def write(record):
            stream.write(encode(record) + "\n")
            stream.flush()

        write(
            {
                "record_type": "run",
                "experiment": "tutor-v1",
                "mode": "local",
                "config": CONFIG,
                "prompt_version": args.prompt_version,
                "dataset_version": "v1",
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "required_model_digest": BASELINE_MODEL_DIGEST
                if args.prompt_version in ("v2", "v3")
                else None,
                "fixture_sha256": hashlib.sha256(
                    encode([asdict(c) for c in CASES]).encode()
                ).hexdigest(),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "samples_per_case": 1,
                "token_policy": TOKEN_POLICY,
                "acceptance_claim": None,
                "network_disconnection": "OPERATOR_ATTESTED"
                if args.network_disconnected
                else "UNVERIFIED",
                "host_platform": platform.system(),
                "host_architecture": platform.machine(),
            }
        )
        failures = 0
        executed = 0
        generation_requests = 0
        identity = None
        skipped_reason = "LOCAL_SETUP_FAILED"
        try:
            with local_server() as client:
                identity = client.inspect()
                write(identity)
                if (
                    args.prompt_version in ("v2", "v3")
                    and identity["digest"] != BASELINE_MODEL_DIGEST
                ):
                    raise ExperimentFailure("LOCAL_BASELINE_DIGEST_MISMATCH")
                for case in CASES:
                    result = run_case(case, client, identity, prompt)
                    write(result)
                    executed += 1
                    generation_requests += result["generation_attempted"]
                    failures += result["mechanical_status"] == "FAILED"
                    if result.get("failure_category") in (
                        "MODEL_TIMEOUT",
                        "LOCAL_INPUT_BOUND_EXCEEDED",
                        "LOCAL_MODEL_MISMATCH",
                        "LOCAL_OUTPUT_ALLOWANCE_EXCEEDED",
                        "UNEXPECTED_THINKING_OR_ACTION",
                        "LOCAL_RUNTIME_CONTEXT_UNVERIFIED",
                        "LOCAL_REQUEST_FAILED",
                    ):
                        # Stop rather than overlapping a timed-out generation or continuing
                        # after evidence that a required runtime control was ineffective.
                        skipped_reason = result["failure_category"]
                        break
        except ExperimentFailure as exc:
            write({"record_type": "failure", "failure_category": str(exc)})
            skipped_reason = str(exc)
            failures += 1
        for case in CASES[executed:]:
            record = case_record(case, identity)
            record.update(mechanical_status="NOT_EXECUTED", skipped_reason=skipped_reason)
            write(record)
        write(
            {
                "record_type": "summary",
                "attempted_cases": executed,
                "generation_requests": generation_requests,
                "unexecuted_cases": len(CASES) - executed,
                "mechanical_failures": failures,
                "quality_review_status": "PENDING_HUMAN_REVIEW",
                "paid_api_calls": 0,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    print(
        f"Local evaluation: {executed} cases attempted; {failures} failures; human review pending."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
