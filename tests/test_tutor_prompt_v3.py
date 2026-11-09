"""Example-only prompt branch: deterministic admission and mocked selection checks."""

import hashlib
import json
import sys
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import Mock

import pytest

from experiments.tutor_v1 import diagnostic, local, runner

ADDITION = (
    "Example: For x + 4 = 11, the student says, “7, because I added 4.”\n"
    "Appropriate response: “7 is the correct answer. Can you show me where you added 4?”\n"
    "Confirm the result without endorsing the conflicting explanation or assuming what the "
    "student actually did.\n\n"
)


def test_v3_exact_addition_to_v1_and_default_unchanged():
    base = (runner.ROOT / "prompt.txt").read_bytes()
    variant = (runner.ROOT / "prompt-v3.txt").read_bytes()
    anchor = b"Return only a JSON object with exactly one field:\n"
    assert base.count(anchor) == 1
    assert variant == base.replace(anchor, ADDITION.encode() + anchor, 1)
    assert variant.replace(ADDITION.encode(), b"", 1) == base
    assert runner.load_prompt("v3") == variant.decode().rstrip("\n")
    assert runner.load_prompt() == runner.load_prompt("v1") == runner.PROMPT
    assert "Distinguish who supplied each step." not in runner.load_prompt("v3")


@pytest.mark.parametrize("module", [runner, local])
def test_v3_changes_only_instructions_preserves_context_and_overflow(module):
    for case in runner.CASES + diagnostic.load_cases():
        base, _, removed = module.prepare(case)
        updated, bound, updated_removed = module.prepare(case, runner.load_prompt("v3"))
        assert removed == updated_removed == 0 and bound <= 8000
        if module is runner:
            assert updated.pop("instructions") == runner.load_prompt("v3")
            base.pop("instructions")
        else:
            assert updated["messages"][0]["content"] == runner.load_prompt("v3")
            updated["messages"][0]["content"] = base["messages"][0]["content"]
        assert updated == base
        assert case.expectation not in runner.encode(updated)
    with pytest.raises(runner.ExperimentFailure, match="REQUIRED_CONTENT_OVERFLOW"):
        module.prepare(replace(runner.CASES[0], message="é" * 8000), runner.load_prompt("v3"))


def test_fake_cli_records_v3_hash_and_keeps_paid_transport_unused(tmp_path, monkeypatch):
    target = tmp_path / "fake-v3.jsonl"
    forbidden = Mock(side_effect=AssertionError("paid transport forbidden"))
    monkeypatch.setattr(runner, "OpenAIClient", forbidden)
    monkeypatch.setattr(sys, "argv", ["runner", "--prompt-version", "v3", "--output", str(target)])
    assert runner.main() == 0
    rows = [json.loads(row) for row in target.read_text().splitlines()]
    assert rows[0]["mode"] == "fake" and rows[0]["prompt_version"] == "v3"
    assert rows[0]["prompt_sha256"] == hashlib.sha256(runner.load_prompt("v3").encode()).hexdigest()
    assert all(j["judgment"] is None for r in rows[1:] for j in r["review"].values())
    with pytest.raises(FileExistsError):
        runner.main()
    forbidden.assert_not_called()


@pytest.mark.parametrize("matches", [True, False])
def test_local_v3_digest_gate_and_request_selection_mocked(tmp_path, monkeypatch, matches):
    client = Mock()
    client.inspect.return_value = {
        "model": local.MODEL,
        "digest": local.BASELINE_MODEL_DIGEST if matches else "a" * 64,
    }
    client.request.return_value = {
        "model": local.MODEL,
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": '{"reply":"Mock mechanics only."}'},
    }
    client.running_model.return_value = {}

    @contextmanager
    def server():
        yield client

    monkeypatch.setattr(local, "local_server", server)
    target = tmp_path / "local-v3.jsonl"
    monkeypatch.setattr(sys, "argv", ["local", "--prompt-version", "v3", "--output", str(target)])
    assert local.main() == (0 if matches else 1)
    rows = [json.loads(row) for row in target.read_text().splitlines()]
    assert rows[0]["prompt_version"] == "v3"
    assert rows[0]["required_model_digest"] == local.BASELINE_MODEL_DIGEST
    assert rows[0]["config"] == local.CONFIG
    assert rows[0]["prompt_sha256"] == hashlib.sha256(runner.load_prompt("v3").encode()).hexdigest()
    if matches:
        assert client.request.call_count == 12
        assert all(
            call.args[1]["messages"][0]["content"] == runner.load_prompt("v3")
            for call in client.request.call_args_list
        )
    else:
        client.request.assert_not_called()
        assert any(r.get("failure_category") == "LOCAL_BASELINE_DIGEST_MISMATCH" for r in rows)
