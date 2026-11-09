# Scoped prompt v2 experiment preparation

Status: **Prepared; real-model v2 generation not run or authorized by this preparation task.**
Authority: current human request, OFFLINE-EVAL-004, ai-runtime/evals prompt-v2 subsections.

The hypothesis is that explicitly distinguishing who supplied each step may reduce unsupported
student-method attribution in cases 3 and 8 while preserving recognition of student-supplied
methods in cases 4 and 10. This is not an established cause or proven fix.

`experiments/tutor_v1/prompt-v2.txt` contains only the requested paragraph added immediately
after rule 3 in v1. The original `prompt.txt` and twelve synthetic fixtures remain unchanged.
Both CLIs select v2 only with `--prompt-version v2`; omission selects v1. The original runner
still defaults to fake mode. Selected prompt version/hash are written into new evidence;
the fixture version stays v1. Prompt hashing retains the established convention of removing
trailing newlines before hashing the UTF-8 text actually sent to the model.

The local v2 preflight requires `qwen3.5:4b-q4_K_M` and baseline digest
`d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`.
No model download, hosted inference or fallback is introduced. Existing options remain:
thinking false, num_ctx 12288, input ceiling 8000 with the existing Qwen byte/framing
assumptions, num_predict 1000, timeout 30 seconds including cold load, zero retries,
one sample per case, exact reply schema, selected earlier whole exchanges (at most ten),
required-content overflow rejection, one parallel request and one loaded model. The fixed
cases select the same context under v1/v2; the prompt addition alone raises their input bounds.
Model-default sampling remains the same digest's parameters. Record any runtime/version,
load/cache or hardware differences as comparison limits rather than silently adjusting them.

After a separate instruction authorizes one real-model v2 run, complete the existing
[local setup/disconnection steps](../../experiments/tutor_v1/LOCAL_SETUP.md), stop the
preparation server, and run from the repository root with Ollama on PATH:

```sh
.venv/bin/python -m experiments.tutor_v1.local \
  --prompt-version v2 \
  --network-disconnected \
  --output artifacts/tutor-v2-local-qwen35-first-disconnected.jsonl
```

This is the exact prospective command, **not executed during preparation**. Its output filename
is new; existing evidence is refused rather than overwritten. The network flag is an operator
attestation: use it only after actually disconnecting external networking. No automatic rerun
of failures or prompt tuning is authorized. No paid call is needed for this command.

Compare against these unchanged files, with source hashes checked before review:

| Artifact | SHA-256 |
| --- | --- |
| `artifacts/tutor-v1-local-qwen35-first-disconnected.jsonl` | `acb0f1aebba92e1c61ca54a24930f0b37a76b591f40f018de32143eb2193e7e8` |
| `artifacts/tutor-v1-local-qwen35-first-human-review.json` | `d9a7764e399efc3df43e4ce368eb5625bff5b2885bf4cff340bf5537c40ce688` |

The human-review artifact's provenance is assistant-proposed scores reviewed with the human
in the planning chat, not independent reviewer agreement. Its case 4 valid-calculation PASS
retains the misleading “check” wording caveat; case 7 Teaching usefulness remains PASS with
the approved equal-groups explanation and learning/generalization limitation.

| Cases | Comparison focus using existing rubric/expectations |
| --- | --- |
| 3 and 8 | Evidence attribution: ask neutrally about an unknown method; recognize tutor-supplied guidance without attributing its choice independently to the student. |
| 4 and 10 | Preserve recognition of the student's explicitly supplied division method and, in case 10, the valid check; do not request supplied information again. |
| All twelve | Review each of the six existing dimensions for regressions and record mechanical failures separately. |

Match case IDs, model digest/settings, fixture hashes and selected context before interpreting
reply differences. Inspect original replies beside new replies. Record v2 dimension judgments
and context-grounded reasons in a separate future review artifact, leaving new run judgments
pending until human review. Do not copy baseline judgments into v2 or send expectations,
scoring notes or review judgments to the model. A mechanically valid JSON reply does not
establish instructional quality. No aggregate score, numeric weights, release threshold or
quality acceptance claim is part of this plan. One sample/case is an exploratory comparison,
not causal or statistical evidence of improvement; variability and runtime differences remain
limitations. Broader slicing and diagnosis are separate work, not outcomes of preparation.

Deterministic checks:

```sh
.venv/bin/pytest -q tests/test_offline_tutor_eval.py tests/test_local_tutor_eval.py tests/test_tutor_prompt_versions.py
```

[Handoff/contract review](../handoffs/offline-tutor-prompt-v2.md) records actual checks and
preservation evidence. `artifacts/tutor-prompt-v2-preparation-validation.json` records
preparation checks only; it is not generation evidence or instructional evaluation.
