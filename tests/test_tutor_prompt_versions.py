"""Prompt selection and v2 comparison mechanics; all generation transport is mocked."""

import hashlib
import json
import sys
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import Mock

import pytest

from experiments.tutor_v1 import local, runner

ADDITION = (
    "Distinguish who supplied each step. A valid mathematical method is not evidence that the "
    "student used it. A step suggested by the tutor is not evidence that the student independently "
    "chose it. If the student’s method is unknown, ask neutrally how they reached their answer."
)
ANCHOR = (
    "3. When a student gives only an answer, confirm correctness when it can be established and "
    "ask about their method. Do not attribute steps they have not shown.\n"
)


def test_prompt_diff_is_only_authorized_addition():
    original = (runner.ROOT / "prompt.txt").read_bytes()
    updated = (runner.ROOT / "prompt-v2.txt").read_bytes()
    assert original.count(ANCHOR.encode()) == 1
    assert updated == original.replace(ANCHOR.encode(), (ANCHOR + ADDITION + "\n").encode(), 1)
    assert runner.load_prompt() == runner.PROMPT == runner.load_prompt("v1")
    assert runner.load_prompt("v2") == updated.decode().rstrip("\n")
    assert runner.load_prompt("v2").count(ADDITION) == 1
    with pytest.raises(KeyError):
        runner.load_prompt("v999")


@pytest.mark.parametrize("module", [runner, local])
def test_only_model_instructions_change_for_all_twelve_cases(module):
    v2 = runner.load_prompt("v2")
    for case in runner.CASES:
        original, _, original_removed = module.prepare(case)
        updated, bound, removed = module.prepare(case, v2)
        assert removed == original_removed == 0 and bound <= 8000
        if module is runner:
            assert updated.pop("instructions") == v2
            assert original.pop("instructions") == runner.PROMPT
        else:
            assert updated["messages"][0]["content"] == v2
            updated["messages"][0]["content"] = original["messages"][0]["content"]
        assert updated == original
        # Exact request equality apart from the prompt also excludes all review/expectation data.
        assert case.expectation not in runner.encode(updated)


@pytest.mark.parametrize("module", [runner, local])
def test_v2_required_overflow_still_rejects_before_generation(module):
    with pytest.raises(runner.ExperimentFailure, match="REQUIRED_CONTENT_OVERFLOW"):
        module.prepare(replace(runner.CASES[0], message="é" * 8000), runner.load_prompt("v2"))


@pytest.mark.parametrize("mode", ["fake", "paid"])
def test_runner_v2_header_and_fake_default_or_mock_luna(tmp_path, monkeypatch, mode):
    target = tmp_path / "v2.jsonl"
    client = runner.FakeClient()
    client.generate = Mock(wraps=client.generate)
    paid = Mock(return_value=client)
    monkeypatch.setattr(runner, "OpenAIClient", paid)
    monkeypatch.setattr(runner, "FakeClient", Mock(return_value=client))
    argv = ["runner", "--prompt-version", "v2", "--output", str(target)]
    if mode == "paid":
        argv.extend(["--mode", "paid"])
    monkeypatch.setattr(sys, "argv", argv)
    assert runner.main() == 0
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    assert rows[0]["mode"] == mode
    assert rows[0]["prompt_version"] == "v2"
    assert rows[0]["prompt_sha256"] == hashlib.sha256(runner.load_prompt("v2").encode()).hexdigest()
    assert rows[0]["samples_per_case"] == 1 and rows[0]["dataset_version"] == "v1"
    assert client.generate.call_count == 12
    assert all(
        c.args[0]["instructions"] == runner.load_prompt("v2")
        for c in client.generate.call_args_list
    )
    assert all(c.args[0]["model"] == "gpt-6-luna" for c in client.generate.call_args_list)
    assert all(v["judgment"] is None for r in rows[1:] for v in r["review"].values())
    if mode == "fake":
        paid.assert_not_called()
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        runner.main()
    assert target.read_bytes() == original and client.generate.call_count == 12


@pytest.mark.parametrize("digest_matches", [True, False])
def test_local_v2_selection_and_baseline_digest_gate(tmp_path, monkeypatch, digest_matches):
    client = Mock()
    digest = local.BASELINE_MODEL_DIGEST if digest_matches else "a" * 64
    client.inspect.return_value = {"digest": digest, "model": local.MODEL, "version": "0.40.6"}
    client.request.return_value = {
        "model": local.MODEL,
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": '{"reply":"Mock mechanics only."}'},
        "prompt_eval_count": 800,
        "eval_count": 12,
    }
    client.running_model.return_value = {"context_length": 12288}

    @contextmanager
    def server():
        yield client

    monkeypatch.setattr(local, "local_server", server)
    paid = Mock(side_effect=AssertionError("paid transport forbidden"))
    monkeypatch.setattr(runner, "OpenAIClient", paid)
    target = tmp_path / "local-v2.jsonl"
    monkeypatch.setattr(sys, "argv", ["local", "--prompt-version", "v2", "--output", str(target)])
    assert local.main() == (0 if digest_matches else 1)
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    assert rows[0]["prompt_version"] == "v2"
    assert rows[0]["prompt_sha256"] == hashlib.sha256(runner.load_prompt("v2").encode()).hexdigest()
    assert rows[0]["required_model_digest"] == local.BASELINE_MODEL_DIGEST
    assert rows[0]["config"] == local.CONFIG
    cases = [r for r in rows if "case_id" in r]
    assert len(cases) == 12
    assert all(v["judgment"] is None for r in cases for v in r["review"].values())
    if digest_matches:
        assert client.request.call_count == 12
        assert all(
            c.args[1]["messages"][0]["content"] == runner.load_prompt("v2")
            for c in client.request.call_args_list
        )
    else:
        client.request.assert_not_called()
        assert any(r.get("failure_category") == "LOCAL_BASELINE_DIGEST_MISMATCH" for r in rows)
        assert all(r["mechanical_status"] == "NOT_EXECUTED" for r in cases)
    paid.assert_not_called()
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        local.main()
    assert target.read_bytes() == original
