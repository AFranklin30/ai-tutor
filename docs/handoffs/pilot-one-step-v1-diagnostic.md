# Seven-case prompt-v1 diagnostic handoff

- TASK: COMPLETE — approved clarifications recorded, revised dataset and executable diagnostic plan prepared; no inference performed. Final pilot acceptance remains unresolved.
- IMPLEMENTED: `experiments/datasets/pilot-one-step-v2.json` preserves all seven case IDs, messages, source summaries, expectations and rubric/blocker mappings; adds the exact approved synthetic exchange and executable context fields. Original dataset v1 is unchanged. `experiments/tutor_v1/diagnostic.py` provides separate preparation/run commands with fake default and explicit local mode, reusing existing transport, identity/settings verification, token/context handling and response validation.
- FILES CHANGED: requirements.md §2.1 (division notation and current dataset); ai-runtime.md Sessions and scope (cross-reference); evals.md PILOT-EVAL-002/003 (resolved questions, bounded diagnostic design); decisions.md appended PILOT-EVAL-003 (current human approval). New dataset, diagnostic module, `tests/test_pilot_diagnostic.py`, `docs/experiments/pilot-one-step-v1-diagnostic-01/{plan.json,schedule.json,review-view.json}`, and this handoff. No existing source, prompt, fixture, settings or evidence files modified. Prior working-tree changes preserved.
- CONTRACTS USED / APPROVED CHANGES: Current human clarification request, recorded 2026-10-19 America/Chicago as PILOT-EVAL-003. Include written `x/d = b` with positive whole-number divisor/right-hand side; explicit fractional-coefficient forms remain deferred. Exact history: Student “How do I solve x + 6 = 14?”; Tutor “Try subtracting 6 from both sides.”; current Student “8.” Prompt v1, three fresh attempts per case, 21 total scheduled slots. Prior three blockers, generated-practice exclusion/blocker, unnecessary-question quality distinction and all six rubric dimensions unchanged.
- REQUEST/DATA FLOW: Dataset → allowlisted Case/Exchange input fields → unchanged prompt-v1/local preparation and context trimming/overflow → fresh request per slot → unchanged exact reply-schema validation → append-only sample journal and separate review view. Expected behaviors and scoring guidance are recorded only in review/evidence, never submitted to the model. Case 6 has null problem; case 7 passes only the supplied completed-work summary, with no invented equation, transcript or next assignment. Runtime does not carry sample conversation forward.
- FAILURE/SECURITY BOUNDARIES: Local-only command; no paid path. Existing owned loopback/cloud-disabled Ollama server, exact model digest and sampling checks, no automatic retries, 30-second deadline and stop categories reused. Reserve/journal each attempt before request; preserve failures and unexecuted slots; never replace a failure. Early stopping can leave fewer than 21 actual requests. Exclusive plan/output directories refuse overwrites before server startup. Hard termination can leave a journaled slot outcome unknown; do not resume or replace it automatically. Backend, worker, public API, database and student records are untouched.
- MODEL / SETTINGS: `qwen3.5:4b-q4_K_M`, digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`; unchanged installed defaults verified before local generation (presence_penalty 1.5, temperature 1, top_k 20, top_p 0.95). Input ceiling 8,000, context 12,288, output allowance 1,000, timeout 30 seconds, thinking off, no retries. Existing conservative Qwen UTF-8 wire-byte bound plus assumed 1,024 framing reserve remains an estimate, not an exact token count; actual available usage/timing and runtime metadata are recorded on execution.
- SCHEDULE: Reproducible SHA-256 ordering with schedule seed 20261019; no model-generation seed override. Three distinct sample IDs per case, 21 unique slots/review IDs. All 126 instructional review entries are pending. This is diagnostic evidence, not final pilot acceptance, statistical evidence of reliability, or a deployment authorization.

## Verification

- `.venv/bin/python -m experiments.tutor_v1.diagnostic prepare --directory docs/experiments/pilot-one-step-v1-diagnostic-01 --schedule-seed 20261019` — prepared 21 slots, no transport/model access.
- `.venv/bin/python -m pytest -q tests/test_pilot_diagnostic.py tests/test_offline_tutor_eval.py tests/test_local_tutor_eval.py tests/test_tutor_prompt_versions.py tests/test_tutor_repeatability.py` — **104 passed**. New tests cover unchanged membership/expectations, exact history, isolated requests/no review leakage, balanced schedule, exclusive creation, pending judgments, fake default, mismatch before generation, stop-on-timeout and tamper rejection. All transport in execution tests is mocked/fake; no real server or paid client.
- `.venv/bin/ruff check experiments/tutor_v1/diagnostic.py tests/test_pilot_diagnostic.py` — passed. `.venv/bin/ruff format --check` on those files — passed after applying formatting. Initial format check requested formatting; corrected before final test run.
- Standard-library hash and persisted-plan validation — all 32 pre-existing experiment/evidence files unchanged, including original seven-case dataset, twelve fixtures, both prompts, local/Luna code/settings and historical artifacts. Existing rubric text unchanged. Persisted plan: seven cases × three slots; 126 pending entries. `git diff --check` — passed.
- Dataset SHA-256: `7f57092e025dd1acdcbcc324e1be0006a292a5538847142610a5a891658d5dc3`.
- Prompt-v1 SHA-256 (existing effective load_prompt text, trailing newlines stripped): `f432e56a2a7f56caaab8e12fbe7c01c15bcca19f5495bd4413cf4ba91ff16bed`.
- Schedule SHA-256 (canonical runner JSON encoding): `998405bc65744faf39960561101452fee1625ddc768cacad93d12f971f1ea114`.
- NOT RUN: standalone diagnostic evidence execution (fake or local), local or paid inference, new installation, runtime/network-disconnection verification, application/backend tests or separate type checks. Execution tests use mocked transport only. No application code changed; runtime speed, memory and teaching quality remain unmeasured. No configured separate type-check command was identified in pyproject.toml.

## Contract check

| Classification | Exact files / contracts | Evidence / implication |
| --- | --- | --- |
| MATCH | requirements §2.1; decisions PILOT-EVAL-003; dataset v2 cases 3/5 | Approved notation and exact synthetic history preserved; v1 source dataset retained. Historical unresolved decision text remains historical and is explicitly superseded only where now approved. |
| MATCH | diagnostic.py load_cases/pending_record/execute; tests/test_pilot_diagnostic.py; evals PILOT-EVAL-003 | Prompt v1 only, 7×3 fresh isolated slots, review metadata excluded from requests, local-only/fake default, identity/settings gate, no retries, exclusive output and pending reviews verified deterministically. |
| MATCH | original experiment/artifact files; evals six-dimension rubric | All 32 protected hashes and rubric text unchanged. No historical runs mixed into new evidence. |
| MATCH | architecture initial controlled-demo/one-unit boundary; security Identity and relationships; ai-runtime Sessions and scope | Synthetic offline-only preparation, assigned-work scope, human authority and all application/security boundaries preserved. No infrastructure or dependency change. |
| DECISION_REQUIRED | evals PILOT-EVAL-003 / plan.spec.final_acceptance_procedure | Final pilot acceptance, any additional required coverage, curriculum source/objectives and actual execution authorization remain unresolved. They do not block this diagnostic preparation; no acceptance claim or execution follows. |
| NOT APPLICABLE | API and schema contracts | No endpoint, payload contract, database access, persistence schema or migration changed. Artifact JSON is isolated experiment evidence, not a public API/database schema. |

- RESULTS: Prepared plan and deterministic checks pass; all judgments pending. No current documentation conflict found after synchronizing the approved clarifications. No model behavior or quality result exists for this plan.
- DECISIONS MADE: Only current human approvals above; ordinary implementation choices are separate versioned dataset/module and reproducible schedule using the existing algorithm. Stable case IDs intentionally retain their original v1-prefixed names while dataset identity/version is recorded separately.
- DEVIATIONS: None within preparation scope. This task does not authorize actual generation.
- KNOWN RISKS / TODO: Final acceptance procedure and broader required coverage remain unresolved. Exact curriculum source/objectives and pilot deployment prerequisites remain unresolved. Offline inference cannot be verified without execution; prior evidence does not establish this run's disconnected status. Schema validity will not establish mathematical correctness or instructional safety.
- NEXT LOGICAL SLICE: Separately authorize the prepared diagnostic execution; preserve every outcome, then conduct six-dimension human review. Final acceptance requires its own approved procedure.

## Exact local execution command (prepared, not run)

After a separate execution instruction, ensure the approved Ollama model is already installed (see `experiments/tutor_v1/LOCAL_SETUP.md`). Disconnect Wi-Fi and any Ethernet/tethering/VPN network path before launching the run if recording disconnected execution. The flag records operator attestation, not automated proof; omit it if disconnection cannot be attested and report offline status UNVERIFIED. Run from repository root:

```sh
.venv/bin/python -m experiments.tutor_v1.diagnostic run \
  --plan-directory docs/experiments/pilot-one-step-v1-diagnostic-01 \
  --output-directory artifacts/pilot-one-step-v1-diagnostic-local-01 \
  --mode local \
  --network-disconnected
```

The output directory was absent at preparation; exclusive creation will refuse it if it later exists. Evidence will be `samples.jsonl`, `schedule.json` and `review-view.json`. The command may stop early under preserved failure rules; do not rerun or replace failures without further instruction.
