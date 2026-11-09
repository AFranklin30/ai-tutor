"""Ollama mechanics with mocked transport/processes: no downloads or live inference."""

import json
import sys
import threading
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import Mock

import pytest

from experiments.tutor_v1 import local, runner
from experiments.tutor_v1.cases import CASES, Exchange


@pytest.fixture
def identity():
    return {"digest": "a" * 64, "model": local.MODEL, "version": "0.40.2"}


@pytest.fixture
def reply():
    return {
        "model": local.MODEL,
        "message": {"role": "assistant", "content": '{"reply":"x = 12"}'},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 800,
        "eval_count": 12,
        "total_duration": 1_000_000_000,
        "load_duration": 100_000_000,
        "prompt_eval_duration": 200_000_000,
        "eval_duration": 700_000_000,
    }


@pytest.fixture
def metadata():
    return {
        "details": {"quantization_level": "Q4_K_M", "parameter_size": "4.2B"},
        "model_info": {
            "general.architecture": "qwen35",
            "general.parameter_count": 4_210_000_000,
            "qwen35.context_length": 262144,
            "tokenizer.ggml.model": "gpt2",
            "tokenizer.ggml.pre": "qwen35",
        },
        "thinking": {"values": [True, False], "default": True},
        "parameters": "temperature 1\ntop_p 0.95\ntop_k 20\npresence_penalty 1.5",
        "template": "{{ .Prompt }}",
    }


def mock_http(client, *responses):
    transports = []
    for response in responses:
        transport = Mock()
        transport.__enter__ = Mock(return_value=transport)
        transport.__exit__ = Mock(return_value=False)
        transport.read.return_value = local.encode(response).encode()
        transports.append(transport)
    client._opener = Mock()
    client._opener.open.side_effect = transports


def test_local_payload_and_independent_admission(monkeypatch):
    monkeypatch.setattr(runner, "token_bound", Mock(side_effect=AssertionError("OpenAI bound")))
    for case in CASES:
        request, bound, removed = local.prepare(case)
        assert request["model"] == "qwen3.5:4b-q4_K_M"
        assert request["think"] is False and request["stream"] is False
        assert request["format"] == runner.SCHEMA
        assert request["options"] == {"num_ctx": 12288, "num_predict": 1000}
        assert request["messages"][0] == {"role": "system", "content": runner.PROMPT}
        context = json.loads(request["messages"][1]["content"])
        assert context == runner.case_context(case, case.history)
        assert "expectation" not in context and "review" not in context
        assert removed == 0 and bound <= 8000
        assert "tools" not in request and "store" not in request
    assert runner.CONFIG["model"] == "gpt-6-luna"
    assert local.CONFIG["num_ctx"] >= 8000 + 1000 + 1024
    assert local.CONFIG["timeout_seconds"] == 30 and local.CONFIG["retries"] == 0


def test_local_whole_history_trimming_and_unicode_bound():
    history = tuple(Exchange(f"student {i}", f"tutor {i}") for i in range(12))
    request, _, removed = local.prepare(replace(CASES[2], history=history))
    assert removed == 2
    selected = json.loads(request["messages"][1]["content"])["selected_history"]
    assert len(selected) == 10 and selected[0]["student"] == "student 2"
    request, bound, removed = local.prepare(
        replace(CASES[2], history=(Exchange("é" * 4000, "古い"), history[-1]))
    )
    assert removed == 1
    assert json.loads(request["messages"][1]["content"])["selected_history"] == [
        {"student": "student 11", "tutor": "tutor 11"}
    ]
    assert bound == len(local.encode(request).encode("utf-8")) + 1024


@pytest.mark.parametrize("field", ["message", "problem"])
def test_overflow_no_local_transport(field, identity):
    client = Mock()
    result = local.run_case(replace(CASES[2], **{field: "é" * 8000}), client, identity)
    assert result["failure_category"] == "REQUIRED_CONTENT_OVERFLOW"
    client.request.assert_not_called()
    client.running_model.assert_not_called()


def test_http_success_usage_and_runtime_memory(reply, identity):
    client = local.OllamaClient()
    mock_http(
        client,
        reply,
        {
            "models": [
                {
                    "name": local.MODEL,
                    "digest": identity["digest"],
                    "context_length": 12288,
                    "size": 4_000_000_000,
                    "size_vram": 3_800_000_000,
                }
            ]
        },
    )
    result = local.run_case(CASES[2], client, identity)
    assert result["reply"] == "x = 12" and result["mechanical_status"] == "VALID_REPLY_SHAPE"
    assert result["usage"]["eval_count"] == 12
    assert result["usage"]["load_duration"] == 100_000_000
    assert result["runtime_memory"]["size_vram"] == 3_800_000_000
    request = client._opener.open.call_args_list[0].args[0]
    assert request.full_url == "http://127.0.0.1:11435/api/chat"
    assert "Authorization" not in request.headers
    assert json.loads(request.data)["think"] is False
    assert client._opener.open.call_args_list[0].kwargs == {"timeout": 30}
    assert client._opener.open.call_count == 2  # one generation, one memory/context query


def test_inspect_identity(metadata):
    client = local.OllamaClient()
    mock_http(
        client,
        {"version": "0.40.2"},
        {"models": [{"name": local.MODEL, "digest": "a" * 64, "size": 3_300_000_000}]},
        metadata,
    )
    identity = client.inspect()
    assert identity["quantization"] == "Q4_K_M" and identity["digest"] == "a" * 64
    assert identity["model_context_length"] == 262144
    assert identity["thinking_values"] == [True, False]
    assert identity["version"] == "0.40.2" and len(identity["template_sha256"]) == 64


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("details", "quantization_level", "Q8_0"),
        ("model_info", "general.architecture", "qwen3"),
        ("details", "parameter_size", "9.0B"),
        ("model_info", "tokenizer.ggml.model", "llama"),
        ("model_info", "tokenizer.ggml.pre", "qwen2"),
        ("model_info", "qwen35.context_length", 8192),
        ("thinking", "values", [True]),
    ],
)
def test_preflight_rejects_substitutions_and_unsupported_settings(metadata, section, key, value):
    metadata[section][key] = value
    client = local.OllamaClient()
    mock_http(
        client,
        {"version": "0.40.2"},
        {"models": [{"name": local.MODEL, "digest": "a" * 64}]},
        metadata,
    )
    with pytest.raises(local.ExperimentFailure):
        client.inspect()
    assert all(
        call.args[0].full_url.endswith(("/version", "/tags", "/show"))
        for call in client._opener.open.call_args_list
    )


def test_missing_model_never_pulls():
    client = local.OllamaClient()
    mock_http(client, {"version": "0.40.2"}, {"models": []})
    with pytest.raises(local.ExperimentFailure, match="LOCAL_MODEL_NOT_INSTALLED"):
        client.inspect()
    assert client._opener.open.call_count == 2
    with pytest.raises(local.ExperimentFailure, match="LOCAL_INVALID_ENDPOINT"):
        client.request("/api/pull", {"model": local.MODEL})


@pytest.mark.parametrize(
    "change,category",
    [
        ({"done": False}, "INCOMPLETE_OUTPUT"),
        ({"done_reason": "length"}, "INCOMPLETE_OUTPUT"),
        ({"model": "qwen3.5:9b"}, "LOCAL_MODEL_MISMATCH"),
        ({"prompt_eval_count": 9000}, "LOCAL_INPUT_BOUND_EXCEEDED"),
        ({"eval_count": 1001}, "LOCAL_OUTPUT_ALLOWANCE_EXCEEDED"),
        (
            {"message": {"role": "assistant", "thinking": "private", "content": "{}"}},
            "UNEXPECTED_THINKING_OR_ACTION",
        ),
        (
            {"message": {"role": "assistant", "tool_calls": [{"function": "x"}]}},
            "UNEXPECTED_THINKING_OR_ACTION",
        ),
    ],
)
def test_incomplete_or_invalid_runtime_evidence(reply, identity, change, category):
    reply.update(change)
    client = local.OllamaClient()
    mock_http(client, reply)
    result = local.run_case(CASES[2], client, identity)
    assert result["failure_category"] == category
    assert result["usage"]["eval_count"] == reply["eval_count"]
    assert "private" not in local.encode(result)
    assert client._opener.open.call_count == 1


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"reply":"ok","extra":true}',
        '{"reply":"a","reply":"b"}',
        '{"reply":" "}',
        '{"reply":"a\\u0000b"}',
        '{"reply":null}',
        '```json\n{"reply":"ok"}\n```',
    ],
)
def test_exact_reply_schema(reply, content):
    reply["message"]["content"] = content
    with pytest.raises(local.ExperimentFailure, match="INVALID_OUTPUT"):
        local.validate_local(reply, 8000)


def test_proxy_redirect_and_timeout_no_retry(monkeypatch, identity):
    monkeypatch.setenv("HTTP_PROXY", "http://invalid.example")
    client = local.OllamaClient()
    # Explicit empty proxy configuration prevents environment proxy discovery.
    assert not any(
        isinstance(h, local.urllib.request.ProxyHandler) and h.proxies
        for h in client._opener.handlers
    )
    assert local.NoRedirect().redirect_request(None, None, 302, "", {}, "https://remote") is None
    client._opener = Mock()
    client._opener.open.side_effect = TimeoutError("private transport error")
    result = local.run_case(CASES[2], client, identity)
    assert result["failure_category"] == "MODEL_TIMEOUT"
    assert "private" not in local.encode(result)
    client._opener.open.assert_called_once()


def test_total_deadline_no_retry(monkeypatch):
    client = local.OllamaClient()
    release = threading.Event()
    monkeypatch.setitem(local.CONFIG, "timeout_seconds", 0.01)
    client._request = Mock(side_effect=lambda *args: release.wait(1))
    try:
        with pytest.raises(local.ExperimentFailure, match="MODEL_TIMEOUT"):
            client.request("/api/chat", {})
        client._request.assert_called_once()
    finally:
        release.set()


def test_managed_server_controls_and_cleanup(monkeypatch):
    monkeypatch.setattr(local.shutil, "which", lambda name: "/mock/ollama")
    probe = Mock()
    probe.__enter__ = Mock(return_value=probe)
    probe.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(local.socket, "socket", Mock(return_value=probe))
    process = Mock()
    process.poll.return_value = None

    def start(command, **kwargs):
        assert command == ["/mock/ollama", "serve"]
        env = kwargs["env"]
        assert env["OLLAMA_HOST"] == "127.0.0.1:11435"
        assert env["OLLAMA_NO_CLOUD"] == "1" and env["OLLAMA_NUM_PARALLEL"] == "1"
        assert env["OLLAMA_CONTEXT_LENGTH"] == "12288"
        kwargs["stdout"].write(b"Ollama cloud disabled: true\nListening on 127.0.0.1:11435\n")
        kwargs["stdout"].flush()
        return process

    monkeypatch.setattr(local.subprocess, "Popen", Mock(side_effect=start))
    with local.local_server() as client:
        assert isinstance(client, local.OllamaClient)
    probe.bind.assert_called_once_with(("127.0.0.1", 11435))
    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=5)


def test_missing_install_does_not_launch(monkeypatch):
    monkeypatch.setattr(local.shutil, "which", lambda name: None)
    launch = Mock(side_effect=AssertionError("launch forbidden"))
    monkeypatch.setattr(local.subprocess, "Popen", launch)
    with pytest.raises(local.ExperimentFailure, match="OLLAMA_NOT_INSTALLED"):
        with local.local_server():
            pytest.fail("no server")
    launch.assert_not_called()


def test_occupied_port_does_not_attach_or_launch(monkeypatch):
    monkeypatch.setattr(local.shutil, "which", lambda name: "/mock/ollama")
    probe = Mock()
    probe.__enter__ = Mock(return_value=probe)
    probe.__exit__ = Mock(return_value=False)
    probe.bind.side_effect = OSError("occupied")
    monkeypatch.setattr(local.socket, "socket", Mock(return_value=probe))
    launch = Mock(side_effect=AssertionError("launch forbidden"))
    monkeypatch.setattr(local.subprocess, "Popen", launch)
    with pytest.raises(local.ExperimentFailure, match="LOCAL_PORT_UNAVAILABLE"):
        with local.local_server():
            pytest.fail("no server")
    launch.assert_not_called()


def test_unverified_server_controls_stop_and_cleanup(monkeypatch):
    monkeypatch.setattr(local.shutil, "which", lambda name: "/mock/ollama")
    probe = Mock()
    probe.__enter__ = Mock(return_value=probe)
    probe.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(local.socket, "socket", Mock(return_value=probe))
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [local.subprocess.TimeoutExpired("serve", 5), 0]
    monkeypatch.setattr(local.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(local.time, "monotonic", Mock(side_effect=[0, 31]))
    with pytest.raises(local.ExperimentFailure, match="LOCAL_SERVER_CONTROLS_UNVERIFIED"):
        with local.local_server():
            pytest.fail("unverified server")
    process.terminate.assert_called_once()
    process.kill.assert_called_once()


@pytest.mark.parametrize(
    "change",
    [
        {"context_length": 4096},
        {"digest": "b" * 64},
    ],
)
def test_effective_runtime_context_or_digest_mismatch(identity, change):
    model = {"name": local.MODEL, "digest": identity["digest"], "context_length": 12288}
    model.update(change)
    client = local.OllamaClient()
    mock_http(client, {"models": [model]})
    with pytest.raises(local.ExperimentFailure):
        client.running_model(identity)


@pytest.mark.parametrize(
    "change",
    [
        {"system": "extra prompt"},
        {"messages": [{"role": "user", "content": "hidden"}]},
        {"remote_host": "https://cloud.example"},
        {"thinking": None},
    ],
)
def test_preflight_rejects_hidden_context_remote_or_missing_thinking(metadata, change):
    metadata.update(change)
    client = local.OllamaClient()
    mock_http(
        client,
        {"version": "0.40.2"},
        {"models": [{"name": local.MODEL, "digest": "a" * 64}]},
        metadata,
    )
    with pytest.raises(local.ExperimentFailure):
        client.inspect()


def test_provider_error_payload_not_retained_or_retried(identity):
    client = local.OllamaClient()
    mock_http(client, {"error": "private runtime detail"})
    result = local.run_case(CASES[2], client, identity)
    assert result["failure_category"] == "LOCAL_REQUEST_FAILED"
    assert "private" not in local.encode(result)
    client._opener.open.assert_called_once()


def test_cli_new_evidence_and_no_paid_access(tmp_path, monkeypatch, identity, reply):
    client = Mock()
    client.inspect.return_value = identity
    client.request.return_value = reply
    client.running_model.return_value = {"context_length": 12288}

    @contextmanager
    def server():
        yield client

    monkeypatch.setattr(local, "local_server", server)
    monkeypatch.setattr(runner, "OpenAIClient", Mock(side_effect=AssertionError("paid forbidden")))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    target = tmp_path / "local.jsonl"
    monkeypatch.setattr(sys, "argv", ["local", "--output", str(target), "--network-disconnected"])
    assert local.main() == 0
    records = [json.loads(s) for s in target.read_text().splitlines()]
    assert records[0]["network_disconnection"] == "OPERATOR_ATTESTED"
    assert records[0]["prompt_sha256"] == local.hashlib.sha256(runner.PROMPT.encode()).hexdigest()
    cases = [r for r in records if "case_id" in r]
    assert len(cases) == 12 and client.request.call_count == 12
    assert all(v["judgment"] is None for r in cases for v in r["review"].values())
    assert records[-1]["unexecuted_cases"] == 0
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        local.main()
    assert target.read_bytes() == original
    runner.OpenAIClient.assert_not_called()


def test_cli_stops_after_timeout_without_rerun(tmp_path, monkeypatch, identity):
    client = Mock()
    client.inspect.return_value = identity
    client.request.side_effect = local.ExperimentFailure("MODEL_TIMEOUT")

    @contextmanager
    def server():
        yield client

    monkeypatch.setattr(local, "local_server", server)
    target = tmp_path / "timeout.jsonl"
    monkeypatch.setattr(sys, "argv", ["local", "--output", str(target)])
    assert local.main() == 1
    records = [json.loads(s) for s in target.read_text().splitlines()]
    assert records[-1]["unexecuted_cases"] == 11
    assert len([r for r in records if r.get("mechanical_status") == "NOT_EXECUTED"]) == 11
    client.request.assert_called_once()


def test_cli_setup_blocked_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(local.shutil, "which", lambda name: None)
    target = tmp_path / "blocked.jsonl"
    monkeypatch.setattr(sys, "argv", ["local", "--output", str(target)])
    assert local.main() == 1
    records = [json.loads(s) for s in target.read_text().splitlines()]
    assert records[-1]["unexecuted_cases"] == 12
    assert records[0]["network_disconnection"] == "UNVERIFIED"
    assert records[1]["failure_category"] == "OLLAMA_NOT_INSTALLED"
