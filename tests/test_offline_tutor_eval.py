"""Offline mechanics only; no network, database fixture, or instructional claims."""

import json
from dataclasses import replace
from unittest.mock import Mock

import pytest

from experiments.tutor_v1.cases import CASES, Exchange
from experiments.tutor_v1.runner import (
    CONFIG,
    DIMENSIONS,
    ExperimentFailure,
    FakeClient,
    OpenAIClient,
    encode,
    prepare,
    response_envelope,
    run_case,
    validate_response,
)


def test_all_cases_fake_shape_only():
    client = FakeClient()
    results = [run_case(case, client) for case in CASES]
    assert client.calls == 12
    assert [r["case_id"] for r in results] == [f"{i:02}" for i in range(1, 13)]
    assert all(r["mechanical_status"] == "VALID_REPLY_SHAPE" for r in results)
    assert all(r["quality_review_status"] == "PENDING_HUMAN_REVIEW" for r in results)
    assert all(set(r["review"]) == set(DIMENSIONS) for r in results)
    assert all(v["judgment"] is None for r in results for v in r["review"].values())


def test_request_config_and_no_eval_material():
    request, bound, removed = prepare(CASES[0])
    assert request["model"] == "gpt-6-luna"
    assert request["reasoning"] == {"effort": "none"}
    assert request["max_output_tokens"] == 1000
    assert request["store"] is False
    assert request["truncation"] == "disabled"
    assert "tools" not in request and "previous_response_id" not in request
    context = json.loads(request["input"][0]["content"])
    assert context["authorized_problem"] is None
    assert context["grade"] == 7 and context["subject"] == "Mathematics"
    assert CASES[0].expectation not in encode(request)
    assert "expectation" not in context and "review" not in context
    assert 0 < bound <= CONFIG["max_input_tokens"] and removed == 0


def test_intended_selected_history():
    assert len(CASES[1].history) == 1
    assert "12" in CASES[1].history[0].student and "33" in CASES[1].history[0].student
    assert "inverse" in CASES[6].history[0].tutor
    assert "Divide both sides" in CASES[7].history[0].tutor
    assert CASES[8].history[0].tutor == "What undoes multiplication?"
    assert CASES[10].history == ()
    assert "3 × 12 = 36" in CASES[9].message


def test_history_limit_and_oldest_whole_exchange_removal():
    exchanges = tuple(Exchange(f"student {i}", f"tutor {i}") for i in range(12))
    request, _, removed = prepare(replace(CASES[2], history=exchanges))
    selected = json.loads(request["input"][0]["content"])["selected_history"]
    assert removed == 2 and len(selected) == 10
    assert selected[0] == {"student": "student 2", "tutor": "tutor 2"}
    large = (Exchange("old" * 3000, "old reply"), exchanges[-1])
    request, _, removed = prepare(replace(CASES[2], history=large))
    assert removed == 1
    assert json.loads(request["input"][0]["content"])["selected_history"] == [
        {"student": "student 11", "tutor": "tutor 11"}
    ]


@pytest.mark.parametrize("field", ["problem", "message"])
def test_required_overflow_never_calls_client(field):
    client = Mock()
    case = replace(CASES[2], **{field: "é" * 8000})
    result = run_case(case, client)
    assert result["failure_category"] == "REQUIRED_CONTENT_OVERFLOW"
    client.generate.assert_not_called()
    assert result["supplied_case"][field] == "é" * 8000


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '```json\n{"reply":"hello"}\n```',
        "{}",
        "[]",
        '{"reply":12}',
        '{"reply":null}',
        '{"reply":""}',
        '{"reply":"  "}',
        '{"reply":"a\\u0000b"}',
        '{"reply":"ok","score":1}',
        '{"reply":"a","reply":"b"}',
        '{"reply":"unfinished',
    ],
)
def test_invalid_json_rejected(raw):
    with pytest.raises(ExperimentFailure, match="INVALID_OUTPUT"):
        validate_response(response_envelope(raw))


def test_reply_preserved_exactly():
    text = "  Correct: 3 × 12 = 36.\n"
    assert validate_response(response_envelope(encode({"reply": text}))) == text


@pytest.mark.parametrize(
    "response",
    [
        {"status": "incomplete", "output": []},
        {"status": "failed"},
        {},
    ],
)
def test_incomplete_rejected(response):
    with pytest.raises(ExperimentFailure, match="INCOMPLETE_OUTPUT"):
        validate_response(response)


@pytest.mark.parametrize("change", ["tool", "refusal", "extra", "unfinished"])
def test_nonfinal_or_extra_output_rejected(change):
    response = response_envelope('{"reply":"ok"}')
    if change == "tool":
        response["output"][0]["type"] = "function_call"
    elif change == "refusal":
        response["output"][0]["content"][0]["type"] = "refusal"
    elif change == "extra":
        response["output"].append(response["output"][0])
    else:
        response["output"][0]["status"] = "in_progress"
    with pytest.raises(ExperimentFailure, match="INVALID_OUTPUT"):
        validate_response(response)


def test_failure_recorded_without_retry_or_secret_error():
    client = Mock()
    client.generate.side_effect = ExperimentFailure("PROVIDER_REQUEST_FAILED")
    result = run_case(CASES[2], client)
    assert result["failure_category"] == "PROVIDER_REQUEST_FAILED"
    assert "reply" not in result
    client.generate.assert_called_once()


def test_http_config_and_sanitized_timeout(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-secret")
    client = OpenAIClient()
    client._opener = Mock()
    client._opener.open.side_effect = TimeoutError("synthetic-secret private error")
    result = run_case(CASES[2], client)
    assert result["failure_category"] == "MODEL_TIMEOUT"
    assert "synthetic-secret" not in encode(result)
    client._opener.open.assert_called_once()
    req = client._opener.open.call_args.args[0]
    assert req.full_url == "https://api.openai.com/v1/responses"
    assert client._opener.open.call_args.kwargs == {"timeout": 30}
    assert json.loads(req.data)["store"] is False


def test_total_deadline_without_retry(monkeypatch):
    import threading

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-secret")
    monkeypatch.setitem(CONFIG, "timeout_seconds", 0.01)
    client = OpenAIClient()
    release = threading.Event()
    client._request = Mock(side_effect=lambda request: release.wait(1))
    try:
        result = run_case(CASES[2], client)
        assert result["failure_category"] == "MODEL_TIMEOUT"
        client._request.assert_called_once()
    finally:
        release.set()


def test_default_cli_fake_no_key_and_no_overwrite(tmp_path, monkeypatch, capsys):
    import sys

    from experiments.tutor_v1 import runner

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(runner, "OpenAIClient", Mock(side_effect=AssertionError("Paid forbidden")))
    target = tmp_path / "run.jsonl"
    monkeypatch.setattr(sys, "argv", ["runner", "--output", str(target)])
    assert runner.main() == 0
    records = [json.loads(line) for line in target.read_text().splitlines()]
    assert len(records) == 13
    assert records[0]["mode"] == "fake" and records[0]["samples_per_case"] == 1
    assert len(records[0]["prompt_sha256"]) == 64
    assert records[0]["acceptance_claim"] is None
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        runner.main()
    assert target.read_bytes() == original
    runner.OpenAIClient.assert_not_called()
    assert "human review pending" in capsys.readouterr().out


def test_http_success_response_and_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-secret")
    client = OpenAIClient()
    response = response_envelope('{"reply":"x = 12"}')
    response.update(
        model="gpt-6-luna",
        usage={
            "input_tokens": 100,
            "output_tokens": 10,
            "total_tokens": 110,
            "private_unneeded": "not retained",
        },
    )
    transport = Mock()
    transport.__enter__ = Mock(return_value=transport)
    transport.__exit__ = Mock(return_value=False)
    transport.read.return_value = encode(response).encode()
    client._opener = Mock()
    client._opener.open.return_value = transport
    result = run_case(CASES[2], client)
    assert result["reply"] == "x = 12"
    assert result["usage"] == {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}
    assert result["returned_model"] == "gpt-6-luna"
    client._opener.open.assert_called_once()


def test_paid_missing_key_fails_without_transport(tmp_path, monkeypatch, capsys):
    import sys

    from experiments.tutor_v1 import runner

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    transport = Mock(side_effect=AssertionError("Network forbidden"))
    monkeypatch.setattr(runner.urllib.request, "build_opener", transport)
    target = tmp_path / "run.jsonl"
    monkeypatch.setattr(sys, "argv", ["runner", "--mode", "paid", "--output", str(target)])
    assert runner.main() == 1
    records = [json.loads(line) for line in target.read_text().splitlines()]
    assert records[-1]["failure_category"] == "MISSING_PROVIDER_CREDENTIAL"
    transport.assert_not_called()
    assert "configuration failure" in capsys.readouterr().out
