"""Repeatability protocol checks with fake/mocked transport only."""

import json
import sys
from collections import Counter
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from experiments.tutor_v1 import local, runner
from experiments.tutor_v1 import repeatability as repeat


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_schedule_fixed_balanced_reproducible_and_separate_seeds():
    first = repeat.schedule(20261019)
    assert first == repeat.schedule(20261019)
    assert first != repeat.schedule(20261020)
    assert len(first) == 30 and len({s["slot_id"] for s in first}) == 30
    assert len({s["review_id"] for s in first}) == 30
    assert [s["execution_position"] for s in first] == list(range(1, 31))
    assert Counter((s["case_id"], s["prompt_version"]) for s in first) == {
        (c, v): 3 for c in ("03", "04", "05", "08", "10") for v in ("v1", "v2")
    }
    assert repeat.spec(20261019)["schedule_seed"] == 20261019
    assert repeat.spec(20261019)["model_generation_seed"] is None
    assert repeat.spec(20261019)["config"] == local.CONFIG
    assert repeat.spec(20261019)["required_model_digest"] == local.BASELINE_MODEL_DIGEST


def test_prepare_no_transport_all_pending_and_exclusive(tmp_path, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("no transport in preparation"))
    monkeypatch.setattr(repeat, "client_session", forbidden)
    plan = tmp_path / "plan"
    repeat.prepare(plan, 20261019)
    parsed, slots = repeat.read_plan(plan)
    assert parsed["spec"]["scheduled_slots"] == 30 and len(slots) == 30
    view = json.loads((plan / "review-view.json").read_text())
    assert len(view["items"]) == 30
    assert all(r["mechanical_status"] == "NOT_EXECUTED" for r in view["items"])
    assert all(v["judgment"] is None for r in view["items"] for v in r["review"].values())
    original = {p: p.read_bytes() for p in plan.iterdir()}
    with pytest.raises(FileExistsError):
        repeat.prepare(plan, 20261019)
    assert all(p.read_bytes() == data for p, data in original.items())
    forbidden.assert_not_called()


def test_fake_default_cli_30_independent_requests_and_separate_review(tmp_path, monkeypatch):
    plan = tmp_path / "plan"
    out = tmp_path / "fake"
    repeat.prepare(plan, 20261019)
    client = repeat.FakeClient()
    requests = []
    real_request = client.request

    def capture(path, body):
        requests.append(body)
        return real_request(path, body)

    client.request = capture
    monkeypatch.setattr(repeat, "FakeClient", lambda: client)
    forbidden = Mock(side_effect=AssertionError("real server forbidden"))
    monkeypatch.setattr(local, "local_server", forbidden)
    monkeypatch.setattr(runner, "OpenAIClient", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        ["repeatability", "run", "--plan-directory", str(plan), "--output-directory", str(out)],
    )
    assert repeat.main() == 0
    evidence = rows(out / "samples.jsonl")
    samples = [r for r in evidence if r.get("record_type") == "sample"]
    assert len(samples) == len(requests) == 30
    assert evidence[0]["mode"] == "fake"
    assert evidence[-1]["attempt_budget_reserved"] == 30
    assert evidence[-1]["generation_requests_confirmed"] == 30
    assert evidence[-1]["unexecuted_slots"] == 0
    assert all(s["usage"] == {} and s["runtime_memory"] == {} for s in samples)
    for sample, request in zip(samples, requests):
        case = next(c for c in runner.CASES if c.id == sample["case_id"])
        version = sample["prompt_version"]
        expected, _, _ = local.prepare(case, runner.load_prompt(version))
        assert request == expected  # Only this case, no previous sample conversation.
        assert request["options"] == {"num_ctx": 12288, "num_predict": 1000}
        assert "seed" not in request["options"]
        assert sample["prompt_sha256"] == repeat.digest(runner.load_prompt(version))
        assert sample["review"]["Evidence discipline"]["judgment"] is None
        assert set(json.loads(request["messages"][1]["content"])) == {
            "grade",
            "subject",
            "authorized_problem",
            "selected_history",
            "current_student_message",
        }
    view = json.loads((out / "review-view.json").read_text())
    mapping = json.loads((out / "version-map.json").read_text())
    assert {r["review_id"] for r in view["items"]} == {r["review_id"] for r in mapping["items"]}
    forbidden_keys = {
        "prompt_version",
        "prompt_sha256",
        "execution_position",
        "sample_id",
        "slot_id",
    }
    by_id = {r["review_id"]: r for r in samples}
    for item in view["items"]:
        assert not forbidden_keys & item.keys()
        assert item["reply"] == by_id[item["review_id"]]["reply"]
        assert item["supplied_context"] == by_id[item["review_id"]]["supplied_context"]
    before = {p: p.read_bytes() for p in out.iterdir()}
    with pytest.raises(FileExistsError):
        repeat.main()
    assert len(requests) == 30 and all(p.read_bytes() == data for p, data in before.items())
    forbidden.assert_not_called()


def mock_local(monkeypatch, outcome=None, digest=None, parameters=None):
    client = repeat.FakeClient()
    identity = {
        "model": local.MODEL,
        "digest": digest or local.BASELINE_MODEL_DIGEST,
        "model_parameters": parameters
        if parameters is not None
        else "presence_penalty 1.5\ntemperature 1\ntop_k 20\ntop_p 0.95",
        "version": "0.40.6",
    }
    client.inspect = Mock(return_value=identity)
    client.request = (
        Mock(side_effect=outcome, wraps=client.request) if outcome else Mock(wraps=client.request)
    )

    @contextmanager
    def session(mode):
        assert mode == "local"
        yield client

    monkeypatch.setattr(repeat, "client_session", session)
    return client


def test_timeout_stops_no_replacements_and_retains_every_slot(tmp_path, monkeypatch):
    plan, out = tmp_path / "plan", tmp_path / "timeout"
    repeat.prepare(plan, 9)
    client = mock_local(monkeypatch, runner.ExperimentFailure("MODEL_TIMEOUT"))
    summary = repeat.execute(plan, out, "local")
    assert summary["attempt_budget_reserved"] == 1
    assert summary["unexecuted_slots"] == 29
    samples = [r for r in rows(out / "samples.jsonl") if r.get("record_type") == "sample"]
    assert len(samples) == 30
    assert samples[0]["failure_category"] == "MODEL_TIMEOUT"
    assert all(s["mechanical_status"] == "NOT_EXECUTED" for s in samples[1:])
    assert all(s["skipped_reason"] == "MODEL_TIMEOUT" for s in samples[1:])
    client.request.assert_called_once()


def test_output_failures_are_observations_not_replacements(tmp_path, monkeypatch):
    plan, out = tmp_path / "plan", tmp_path / "invalid"
    repeat.prepare(plan, 9)
    client = mock_local(monkeypatch)
    invalid = {
        "model": local.MODEL,
        "done": True,
        "done_reason": "length",
        "message": {"role": "assistant", "content": "{}"},
        "eval_count": 1000,
    }
    valid = {
        "model": local.MODEL,
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": '{"reply":"original  \\nwording"}'},
    }
    client.request = Mock(side_effect=[invalid] + [valid] * 29)
    summary = repeat.execute(plan, out, "local")
    assert client.request.call_count == summary["attempt_budget_reserved"] == 30
    assert summary["mechanical_failures"] == 1 and summary["unexecuted_slots"] == 0
    samples = [r for r in rows(out / "samples.jsonl") if r.get("record_type") == "sample"]
    assert len({s["slot_id"] for s in samples}) == 30
    assert samples[0]["failure_category"] == "INCOMPLETE_OUTPUT"
    assert samples[0]["usage"]["eval_count"] == 1000
    view = json.loads((out / "review-view.json").read_text())
    assert sum(r["reply"] == "original  \nwording" for r in view["items"]) == 29


@pytest.mark.parametrize(
    "digest,parameters,category",
    [
        ("b" * 64, None, "LOCAL_BASELINE_DIGEST_MISMATCH"),
        (None, "temperature 0", "LOCAL_SAMPLING_SETTINGS_MISMATCH"),
    ],
)
def test_identity_or_sampling_mismatch_zero_generation(
    tmp_path, monkeypatch, digest, parameters, category
):
    plan, out = tmp_path / "plan", tmp_path / "mismatch"
    repeat.prepare(plan, 9)
    client = mock_local(monkeypatch, digest=digest, parameters=parameters)
    summary = repeat.execute(plan, out, "local")
    assert summary["setup_failure"] == category and summary["unexecuted_slots"] == 30
    assert summary["attempt_budget_reserved"] == 0
    client.request.assert_not_called()


def test_missing_setup_and_interrupt_preserved(tmp_path, monkeypatch):
    plan, out = tmp_path / "plan", tmp_path / "missing"
    repeat.prepare(plan, 9)

    @contextmanager
    def unavailable(mode):
        raise runner.ExperimentFailure("OLLAMA_NOT_INSTALLED")
        yield  # pragma: no cover - contextmanager shape only

    monkeypatch.setattr(repeat, "client_session", unavailable)
    summary = repeat.execute(plan, out, "local")
    assert summary["unexecuted_slots"] == 30 and summary["attempt_budget_reserved"] == 0
    client = mock_local(monkeypatch, KeyboardInterrupt())
    summary = repeat.execute(plan, tmp_path / "interrupted", "local")
    assert summary["attempt_budget_reserved"] == 1 and summary["unexecuted_slots"] == 29
    client.request.assert_called_once()


@pytest.mark.parametrize("filename", ["plan.json", "schedule.json", "version-map.json"])
def test_tampered_preparation_rejected_before_server(tmp_path, monkeypatch, filename):
    plan = tmp_path / "plan"
    repeat.prepare(plan, 9)
    path = plan / filename
    data = json.loads(path.read_text())
    if filename == "plan.json":
        data["spec"]["maximum_generation_attempts"] = 31
    elif filename == "schedule.json":
        data.reverse()
    else:
        data["items"][0]["prompt_version"] = "unapproved"
    path.write_text(json.dumps(data))
    forbidden = Mock(side_effect=AssertionError("server forbidden"))
    monkeypatch.setattr(repeat, "client_session", forbidden)
    with pytest.raises(ValueError):
        repeat.execute(plan, tmp_path / "out", "local")
    forbidden.assert_not_called()
    assert not (tmp_path / "out").exists()
