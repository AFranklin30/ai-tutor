"""Seven-case v1 diagnostic preparation and opt-in local execution; fake is default."""

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from experiments.tutor_v1 import local, runner
from experiments.tutor_v1.cases import Case, Exchange
from experiments.tutor_v1.repeatability import (
    SAMPLING_PARAMETERS,
    STOP_ON,
    client_session,
    digest,
    now,
    verify_identity,
    write_json,
)

DATASET = Path(__file__).parents[1] / "datasets" / "pilot-one-step-v2.json"
SAMPLES = 3
ATTEMPT_BUDGET = 21
DEFAULT_SCHEDULE_SEED = 20261019


def load_cases():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    if data["dataset_id"] != "pilot-one-step" or data["dataset_version"] != "v2":
        raise ValueError("Unexpected dataset identity")
    cases = []
    for row in data["cases"]:
        supplied = row["input"]
        cases.append(
            Case(
                id=row["id"],
                message=supplied["student_message"],
                expectation=row["review_only"]["successful_tutor_behavior"],
                problem=supplied["problem"],
                history=tuple(Exchange(**exchange) for exchange in supplied["history"]),
            )
        )
    if len(cases) != 7 or len({c.id for c in cases}) != 7:
        raise ValueError("Expected seven unique cases")
    return tuple(cases)


def schedule(seed):
    if type(seed) is not int:
        raise ValueError("Schedule seed must be an integer")
    slots = []
    for case in load_cases():
        for sample in range(1, SAMPLES + 1):
            slot_id = f"{case.id}-v1-s{sample:02}"
            slots.append(
                {
                    "slot_id": slot_id,
                    "case_id": case.id,
                    "prompt_version": "v1",
                    "prompt_sha256": digest(runner.load_prompt("v1")),
                    "sample_id": f"s{sample:02}",
                    "review_id": digest(f"pilot-diagnostic:{seed}:{slot_id}")[:20],
                }
            )
    slots.sort(key=lambda s: (digest(f"schedule:{seed}:{s['slot_id']}"), s["slot_id"]))
    return [dict(slot, execution_position=i) for i, slot in enumerate(slots, 1)]


def spec(seed):
    return {
        "experiment": "pilot-one-step-v1-diagnostic",
        "purpose": "DIAGNOSTIC_NOT_ACCEPTANCE",
        "dataset_id": "pilot-one-step",
        "dataset_version": "v2",
        "dataset_file": "experiments/datasets/pilot-one-step-v2.json",
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "case_ids": [c.id for c in load_cases()],
        "prompt_version": "v1",
        "prompt_sha256": digest(runner.load_prompt("v1")),
        "fresh_attempts_per_case": SAMPLES,
        "scheduled_slots": ATTEMPT_BUDGET,
        "maximum_generation_attempts": ATTEMPT_BUDGET,
        "schedule_seed": seed,
        "schedule_algorithm": "sha256_sort_v1",
        "model_generation_seed": None,
        "model_generation_seed_policy": "No override; existing runtime defaults.",
        "model": local.MODEL,
        "required_model_digest": local.BASELINE_MODEL_DIGEST,
        "config": deepcopy(local.CONFIG),
        "sampling_parameters": dict(SAMPLING_PARAMETERS),
        "token_policy": local.TOKEN_POLICY,
        "reply_schema": deepcopy(runner.SCHEMA),
        "stop_on": sorted(STOP_ON),
        "final_acceptance_procedure": None,
        "execution_authorization": "Prepared only; current task explicitly prohibits inference.",
        "review_policy": "All six dimensions pending human review; no automatic quality judge.",
    }


def pending_record(slot, identity=None, reason="AWAITING_EXECUTION"):
    case = next(c for c in load_cases() if c.id == slot["case_id"])
    record = local.case_record(case, identity)
    request, bound, removed = local.prepare(case, runner.load_prompt("v1"))
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
    return {
        "record_type": "diagnostic_review",
        "mode": mode,
        "purpose": "DIAGNOSTIC_NOT_ACCEPTANCE",
        "prompt_version": "v1",
        "dimensions": list(runner.DIMENSIONS),
        "items": [
            {
                k: deepcopy(record.get(k))
                for k in (
                    "review_id",
                    "case_id",
                    "sample_id",
                    "execution_position",
                    "supplied_context",
                    "reply",
                    "mechanical_status",
                    "failure_category",
                    "skipped_reason",
                    "quality_review_status",
                    "review",
                )
            }
            for record in records
        ],
    }


def prepare(directory, seed=DEFAULT_SCHEDULE_SEED):
    slots = schedule(seed)
    plan_spec = spec(seed)
    records = [pending_record(slot) for slot in slots]
    directory.mkdir(parents=True, exist_ok=False)
    write_json(
        directory / "plan.json",
        {
            "record_type": "prepared_diagnostic_plan",
            "recorded_at": now(),
            "spec": plan_spec,
            "schedule_sha256": digest(runner.encode(slots)),
        },
    )
    write_json(directory / "schedule.json", slots)
    write_json(directory / "review-view.json", review_view(records, "PREPARED_ONLY"))


def read_plan(directory):
    plan = json.loads((directory / "plan.json").read_text())
    slots = json.loads((directory / "schedule.json").read_text())
    seed = plan["spec"]["schedule_seed"]
    if plan["spec"] != spec(seed) or slots != schedule(seed):
        raise ValueError("Prepared plan, dataset, prompt, settings or schedule changed")
    if plan["schedule_sha256"] != digest(runner.encode(slots)):
        raise ValueError("Schedule hash mismatch")
    if len(slots) != 21 or Counter(s["case_id"] for s in slots) != {c.id: 3 for c in load_cases()}:
        raise ValueError("Expected three fresh attempts for each of seven cases")
    return plan, slots


def execute(plan_directory, output_directory, mode="fake", network_disconnected=False):
    plan, slots = read_plan(plan_directory)
    # Refuse every existing bundle before server startup or any generation.
    output_directory.mkdir(parents=True, exist_ok=False)
    write_json(output_directory / "schedule.json", slots)
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
                    case = next(c for c in load_cases() if c.id == slot["case_id"])
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
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--directory", type=Path, required=True)
    preparation.add_argument("--schedule-seed", type=int, default=DEFAULT_SCHEDULE_SEED)
    run = commands.add_parser("run")
    run.add_argument("--plan-directory", type=Path, required=True)
    run.add_argument("--output-directory", type=Path, required=True)
    run.add_argument("--mode", choices=("fake", "local"), default="fake")
    run.add_argument("--network-disconnected", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.directory, args.schedule_seed)
        print("Prepared 21 diagnostic slots; no generation.")
        return 0
    summary = execute(
        args.plan_directory, args.output_directory, args.mode, args.network_disconnected
    )
    print("Diagnostic mechanics: " + runner.encode(summary))
    return 1 if summary["setup_failure"] or summary["mechanical_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
