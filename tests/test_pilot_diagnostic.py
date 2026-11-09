"""Diagnostic preparation and execution controls; transport is always mocked."""

import json
from collections import Counter
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from experiments.tutor_v1 import diagnostic as diag
from experiments.tutor_v1 import local, runner


def test_dataset_preserves_membership_expectations_and_exact_history():
    old = json.loads(diag.DATASET.with_name("pilot-one-step-v1.json").read_text())
    new = json.loads(diag.DATASET.read_text())
    assert len(new["cases"]) == 7
    for a, b in zip(old["cases"], new["cases"]):
        assert (a["id"], a["name"]) == (b["id"], b["name"])
        for key in ("problem_context", "student_message"):
            assert a["input"][key] == b["input"][key]
        for key in ("successful_tutor_behavior", "rubric_dimensions", "approved_blockers"):
            assert a["review_only"][key] == b["review_only"][key]
    cases = diag.load_cases()
    assert cases[4].message == "8."
    assert [(e.student, e.tutor) for e in cases[4].history] == [
        ("How do I solve x + 6 = 14?", "Try subtracting 6 from both sides.")
    ]
    assert cases[4].problem == "x + 6 = 14"
    assert cases[5].problem is None
    assert cases[6].problem == "Existing assigned problem completed"
    assert all(not c.history for i, c in enumerate(cases) if i != 4)


def test_plan_no_transport_balanced_and_exclusive(tmp_path, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("no model access"))
    monkeypatch.setattr(diag, "client_session", forbidden)
    plan = tmp_path / "plan"
    diag.prepare(plan)
    parsed, slots = diag.read_plan(plan)
    assert len(slots) == len({s["slot_id"] for s in slots}) == 21
    assert len({s["review_id"] for s in slots}) == 21
    assert Counter(s["case_id"] for s in slots) == {c.id: 3 for c in diag.load_cases()}
    assert [s["execution_position"] for s in slots] == list(range(1, 22))
    assert all(s["prompt_version"] == "v1" for s in slots)
    assert slots == diag.schedule(diag.DEFAULT_SCHEDULE_SEED)
    assert slots != diag.schedule(diag.DEFAULT_SCHEDULE_SEED + 1)
    spec = parsed["spec"]
    assert spec["config"] == local.CONFIG
    assert spec["required_model_digest"] == local.BASELINE_MODEL_DIGEST
    assert spec["model_generation_seed"] is None
    assert spec["final_acceptance_procedure"] is None
    view = json.loads((plan / "review-view.json").read_text())
    assert len(view["items"]) == 21
    assert all(len(r["review"]) == 6 for r in view["items"])
    assert all(j["judgment"] is None for r in view["items"] for j in r["review"].values())
    before = {p: p.read_bytes() for p in plan.iterdir()}
    with pytest.raises(FileExistsError):
        diag.prepare(plan)
    assert all(p.read_bytes() == value for p, value in before.items())
    forbidden.assert_not_called()


def mock_session(monkeypatch, timeout=False, mismatch=False):
    from experiments.tutor_v1.repeatability import FakeClient

    client = FakeClient()
    client.inspect = Mock(
        return_value={
            "model": local.MODEL,
            "digest": "bad" if mismatch else local.BASELINE_MODEL_DIGEST,
            "model_parameters": "presence_penalty 1.5\ntemperature 1\ntop_k 20\ntop_p 0.95",
        }
    )
    client.request = Mock(
        side_effect=runner.ExperimentFailure("MODEL_TIMEOUT") if timeout else None,
        wraps=client.request,
    )

    @contextmanager
    def session(mode):
        assert mode == "local"
        yield client

    monkeypatch.setattr(diag, "client_session", session)
    return client


def samples(out):
    return [
        json.loads(row)
        for row in (out / "samples.jsonl").read_text().splitlines()
        if json.loads(row).get("record_type") == "sample"
    ]


def test_21_fresh_isolated_requests_no_review_leakage(tmp_path, monkeypatch):
    plan, out = tmp_path / "plan", tmp_path / "out"
    diag.prepare(plan)
    client = mock_session(monkeypatch)
    summary = diag.execute(plan, out, "local")
    assert summary["attempt_budget_reserved"] == client.request.call_count == 21
    assert summary["mechanical_failures"] == summary["unexecuted_slots"] == 0
    records = samples(out)
    assert len(records) == 21
    for record, call in zip(records, client.request.call_args_list):
        request = call.args[1]
        case = next(c for c in diag.load_cases() if c.id == record["case_id"])
        expected, _, _ = local.prepare(case, runner.load_prompt("v1"))
        assert request == expected
        assert request["messages"][0]["content"] == runner.load_prompt("v1")
        context = json.loads(request["messages"][1]["content"])
        assert set(context) == {
            "grade",
            "subject",
            "authorized_problem",
            "selected_history",
            "current_student_message",
        }
        assert request["options"] == {"num_ctx": 12288, "num_predict": 1000}
        assert request["think"] is False
        assert all(j["judgment"] is None for j in record["review"].values())
    with pytest.raises(FileExistsError):
        diag.execute(plan, out, "local")
    assert client.request.call_count == 21


@pytest.mark.parametrize(
    "timeout,mismatch,attempts,unexecuted",
    [
        (True, False, 1, 20),
        (False, True, 0, 21),
    ],
)
def test_stop_and_no_replacement(tmp_path, monkeypatch, timeout, mismatch, attempts, unexecuted):
    plan, out = tmp_path / "plan", tmp_path / "out"
    diag.prepare(plan)
    client = mock_session(monkeypatch, timeout=timeout, mismatch=mismatch)
    summary = diag.execute(plan, out, "local")
    assert client.request.call_count == summary["attempt_budget_reserved"] == attempts
    assert summary["unexecuted_slots"] == unexecuted
    assert len(samples(out)) == 21


@pytest.mark.parametrize("filename", ["plan.json", "schedule.json"])
def test_tamper_rejected_before_transport(tmp_path, monkeypatch, filename):
    plan = tmp_path / "plan"
    diag.prepare(plan)
    p = plan / filename
    data = json.loads(p.read_text())
    if filename == "plan.json":
        data["spec"]["config"]["timeout_seconds"] = 31
    else:
        data.reverse()
    p.write_text(json.dumps(data))
    forbidden = Mock(side_effect=AssertionError("no transport"))
    monkeypatch.setattr(diag, "client_session", forbidden)
    with pytest.raises(ValueError):
        diag.execute(plan, tmp_path / "out", "local")
    forbidden.assert_not_called()
    assert not (tmp_path / "out").exists()


def test_fake_default_does_not_start_server(tmp_path, monkeypatch):
    import sys

    plan = tmp_path / "plan"
    diag.prepare(plan)
    forbidden = Mock(side_effect=AssertionError("no real server or paid client"))
    monkeypatch.setattr(local, "local_server", forbidden)
    monkeypatch.setattr(runner, "OpenAIClient", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diagnostic",
            "run",
            "--plan-directory",
            str(plan),
            "--output-directory",
            str(tmp_path / "fake"),
        ],
    )
    assert diag.main() == 0
    forbidden.assert_not_called()
