"""Prepare or explicitly execute a fixed local-only comparison; run mode defaults to fake."""

import argparse
import hashlib
import json
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from experiments.tutor_v1 import local, runner

CASE_IDS = ("03", "04", "05", "08", "10")
VERSIONS = ("v1", "v2")
SAMPLES = 3
ATTEMPT_BUDGET = 30
DEFAULT_SCHEDULE_SEED = 20261019
SAMPLING_PARAMETERS = {
    "presence_penalty": "1.5",
    "temperature": "1",
    "top_k": "20",
    "top_p": "0.95",
}
# Identical stopping categories to the existing local CLI; malformed/length-limited
# output is a failed observation, not a retry or a reason to add replacement slots.
STOP_ON = frozenset(
    (
        "MODEL_TIMEOUT",
        "LOCAL_INPUT_BOUND_EXCEEDED",
        "LOCAL_MODEL_MISMATCH",
        "LOCAL_OUTPUT_ALLOWANCE_EXCEEDED",
        "UNEXPECTED_THINKING_OR_ACTION",
        "LOCAL_RUNTIME_CONTEXT_UNVERIFIED",
        "LOCAL_REQUEST_FAILED",
    )
)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def schedule(seed):
    if type(seed) is not int:
        raise ValueError("Schedule seed must be an integer")
    slots = []
    for version in VERSIONS:
        for case_id in CASE_IDS:
            for sample in range(1, SAMPLES + 1):
                slot_id = f"{version}-{case_id}-s{sample:02}"
                slots.append(
                    {
                        "slot_id": slot_id,
                        "case_id": case_id,
                        "prompt_version": version,
                        "prompt_sha256": digest(runner.load_prompt(version)),
                        "sample_id": f"s{sample:02}",
                        "review_id": digest(f"review-id:{seed}:{slot_id}")[:20],
                    }
                )
    slots.sort(key=lambda s: (digest(f"schedule:{seed}:{s['slot_id']}"), s["slot_id"]))
    return [dict(slot, execution_position=i) for i, slot in enumerate(slots, 1)]


def spec(seed):
    return {
        "experiment": "tutor-v1-v2-repeatability",
        "case_ids": list(CASE_IDS),
        "prompt_versions": list(VERSIONS),
        "fresh_samples_per_case_per_prompt": SAMPLES,
        "scheduled_slots": ATTEMPT_BUDGET,
        "maximum_generation_attempts": ATTEMPT_BUDGET,
        "schedule_seed": seed,
        "schedule_algorithm": "sha256_sort_v1",
        "model_generation_seed": None,
        "model_generation_seed_policy": "No override; preserve existing model/runtime defaults.",
        "model": local.MODEL,
        "required_model_digest": local.BASELINE_MODEL_DIGEST,
        "config": deepcopy(local.CONFIG),
        "sampling_parameters": dict(SAMPLING_PARAMETERS),
        "dataset_version": "v1",
        "fixture_sha256": digest(runner.encode([asdict(c) for c in runner.CASES])),
        "prompts": {v: {"version": v, "sha256": digest(runner.load_prompt(v))} for v in VERSIONS},
        "stop_on": sorted(STOP_ON),
        "research_record": "docs/research/tutor-v1-v2-repeatability.json",
        "review_policy": (
            "Label-masked; not fully blinded independent review; baseline replies seen."
        ),
        "execution_authorization": (
            "Preparation only; real local execution requires a later instruction."
        ),
    }


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def pending_record(slot, identity=None, reason="AWAITING_EXECUTION"):
    case = next(c for c in runner.CASES if c.id == slot["case_id"])
    record = local.case_record(case, identity)
    request, bound, removed = local.prepare(case, runner.load_prompt(slot["prompt_version"]))
    record.update(
        slot,
        record_type="sample",
        mechanical_status="NOT_EXECUTED",
        skipped_reason=reason,
        input_token_upper_bound=bound,
        removed_exchanges=removed,
        supplied_context=json.loads(request["messages"][1]["content"]),
    )
    return record


def review_view(records, mode):
    # Separate review ordering and opaque IDs hide execution positions and prompt labels.
    items = []
    for record in sorted(records, key=lambda r: digest("review-order:" + r["review_id"])):
        item = {
            k: deepcopy(record.get(k))
            for k in (
                "review_id",
                "case_id",
                "supplied_context",
                "reply",
                "mechanical_status",
                "failure_category",
                "skipped_reason",
            )
        }
        item.update(
            quality_review_status="PENDING_HUMAN_REVIEW",
            review={d: {"judgment": None, "reason": ""} for d in runner.DIMENSIONS},
        )
        items.append(item)
    return {
        "record_type": "label_masked_review",
        "mode": mode,
        "description": "Prompt labels and execution order omitted; not fully blinded independent "
        "review. Reviewers have seen baseline replies; wording may reveal conditions.",
        "dimensions": list(runner.DIMENSIONS),
        "items": items,
    }


def mapping(slots):
    return {"record_type": "separate_version_mapping", "items": deepcopy(slots)}


def prepare(directory, seed):
    slots = schedule(seed)
    plan_spec = spec(seed)
    records = [pending_record(slot) for slot in slots]
    directory.mkdir(parents=True, exist_ok=False)
    write_json(
        directory / "plan.json",
        {
            "record_type": "prepared_repeatability_plan",
            "recorded_at": now(),
            "spec": plan_spec,
            "schedule_sha256": digest(runner.encode(slots)),
        },
    )
    write_json(directory / "schedule.json", slots)
    write_json(directory / "version-map.json", mapping(slots))
    write_json(directory / "review-view.json", review_view(records, "PREPARED_ONLY"))


def read_plan(directory):
    plan = json.loads((directory / "plan.json").read_text())
    saved = json.loads((directory / "schedule.json").read_text())
    seed = plan["spec"]["schedule_seed"]
    if plan["spec"] != spec(seed) or saved != schedule(seed):
        raise ValueError("Prepared plan, prompts, fixtures, settings or schedule changed")
    if plan["schedule_sha256"] != digest(runner.encode(saved)):
        raise ValueError("Schedule hash mismatch")
    if json.loads((directory / "version-map.json").read_text()) != mapping(saved):
        raise ValueError("Version mapping mismatch")
    return plan, saved


class FakeClient:
    """Local transport shape only; counters are absent, never fake measured usage."""

    def inspect(self):
        return {
            "model": local.MODEL,
            "digest": None,
            "version": None,
            "synthetic": True,
            "note": "Fake mechanics; no actual model/runtime inspected.",
        }

    def request(self, path, body):
        assert path == "/api/chat"
        return {
            "model": local.MODEL,
            "done": True,
            "done_reason": "stop",
            "message": {
                "role": "assistant",
                "content": '{"reply":"Synthetic mechanics-only response."}',
            },
        }

    def running_model(self, identity):
        return {}


@contextmanager
def client_session(mode):
    if mode == "fake":
        yield FakeClient()
    elif mode == "local":
        with local.local_server() as client:
            yield client
    else:
        raise ValueError("Only fake or local execution is supported")


def verify_identity(identity):
    if (
        identity.get("model") != local.MODEL
        or identity.get("digest") != local.BASELINE_MODEL_DIGEST
    ):
        raise runner.ExperimentFailure("LOCAL_BASELINE_DIGEST_MISMATCH")
    text = identity.get("model_parameters")
    if not isinstance(text, str):
        raise runner.ExperimentFailure("LOCAL_SAMPLING_SETTINGS_MISMATCH")
    rows = [line.split() for line in text.splitlines() if line.strip()]
    if sorted(rows) != sorted([[k, v] for k, v in SAMPLING_PARAMETERS.items()]):
        raise runner.ExperimentFailure("LOCAL_SAMPLING_SETTINGS_MISMATCH")


def execute(plan_directory, output_directory, mode="fake", network_disconnected=False):
    plan, slots = read_plan(plan_directory)
    # Refuse every existing bundle before server startup or any generation.
    output_directory.mkdir(parents=True, exist_ok=False)
    write_json(output_directory / "schedule.json", slots)
    write_json(output_directory / "version-map.json", mapping(slots))
    results = []
    reserved = 0
    identity = None
    stop_reason = "AWAITING_EXECUTION"
    setup_failure = None
    with (output_directory / "samples.jsonl").open("x", encoding="utf-8") as stream:

        def write(record):
            stream.write(runner.encode(record) + "\n")
            stream.flush()

        write(
            {
                "record_type": "run",
                "mode": mode,
                "started_at": now(),
                "spec": plan["spec"],
                "schedule_sha256": plan["schedule_sha256"],
                "plan_file_sha256": hashlib.sha256(
                    (plan_directory / "plan.json").read_bytes()
                ).hexdigest(),
                "network_disconnection": "OPERATOR_ATTESTED"
                if network_disconnected
                else "UNVERIFIED",
                "scheduled_slots": slots,
                "note": "New samples only; no baseline replies reused.",
            }
        )
        try:
            with client_session(mode) as client:
                identity = client.inspect()
                write({"record_type": "runtime", "identity": identity})
                if mode == "local":
                    verify_identity(identity)
                for slot in slots:
                    if reserved >= ATTEMPT_BUDGET:
                        raise runner.ExperimentFailure("ATTEMPT_BUDGET_EXHAUSTED")
                    # Reserve and flush before the one call. No resume/replacement path exists.
                    # A hard process kill can leave this reservation's outcome unknown.
                    reserved += 1
                    write(
                        dict(
                            slot,
                            record_type="slot_start",
                            attempt_budget_reserved=True,
                            started_at=now(),
                        )
                    )
                    case = next(c for c in runner.CASES if c.id == slot["case_id"])
                    try:
                        record = local.run_case(
                            case, client, identity, runner.load_prompt(slot["prompt_version"])
                        )
                    except (KeyboardInterrupt, Exception):
                        record = pending_record(slot, identity)
                        record.pop("skipped_reason", None)
                        record.update(
                            mechanical_status="FAILED",
                            failure_category="LOCAL_EXECUTION_INTERRUPTED",
                            generation_attempted=None,
                            attempt_outcome_note="Reserved attempt may have reached runtime.",
                        )
                    record.update(slot, record_type="sample")
                    results.append(record)
                    write(record)
                    if record.get("failure_category") in STOP_ON | {"LOCAL_EXECUTION_INTERRUPTED"}:
                        stop_reason = record["failure_category"]
                        break
        except runner.ExperimentFailure as exc:
            setup_failure = str(exc)
            stop_reason = setup_failure
            write({"record_type": "failure", "failure_category": setup_failure})
        except (KeyboardInterrupt, Exception):
            setup_failure = "LOCAL_SETUP_OR_CLEANUP_FAILED"
            stop_reason = setup_failure
            write({"record_type": "failure", "failure_category": setup_failure})
        finally:
            for slot in slots[len(results) :]:
                record = pending_record(slot, identity, stop_reason)
                results.append(record)
                write(record)
            summary = {
                "record_type": "summary",
                "scheduled_slots": len(slots),
                "attempt_budget_reserved": reserved,
                "generation_requests_confirmed": sum(
                    r.get("generation_attempted") is True for r in results
                ),
                "mechanical_failures": sum(r["mechanical_status"] == "FAILED" for r in results),
                "unexecuted_slots": sum(r["mechanical_status"] == "NOT_EXECUTED" for r in results),
                "setup_failure": setup_failure,
                "finished_at": now(),
                "paid_api_calls": 0,
                "quality_review_status": "PENDING_HUMAN_REVIEW",
            }
            write(summary)
    write_json(output_directory / "review-view.json", review_view(results, mode))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--directory", type=Path, required=True)
    prepare_parser.add_argument("--schedule-seed", type=int, default=DEFAULT_SCHEDULE_SEED)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--plan-directory", type=Path, required=True)
    run_parser.add_argument("--output-directory", type=Path, required=True)
    run_parser.add_argument("--mode", choices=("fake", "local"), default="fake")
    run_parser.add_argument("--network-disconnected", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.directory, args.schedule_seed)
        print("Prepared 30 slots and separate label-masked view/mapping; no generation.")
        return 0
    summary = execute(
        args.plan_directory, args.output_directory, args.mode, args.network_disconnected
    )
    print("Repeatability mechanics: " + runner.encode(summary))
    return 1 if summary["setup_failure"] or summary["mechanical_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
