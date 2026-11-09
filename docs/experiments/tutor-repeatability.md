# Focused v1/v2 repeatability experiment

**Prepared only; no local generation or paid calls performed.** Current human request and
OFFLINE-EVAL-005 approve preparation, not execution. The preserved
[research record](../research/tutor-v1-v2-repeatability.json) includes the research question,
exact addition/hashes, settings, baseline source hashes and linked observations, plus unknown
historical approval dates explicitly left unknown. The prior
[v2 comparison plan](tutor-prompt-v2.md) remains unchanged.

**Historical-state note:** The preparation-only status in the original plan below records the
state when it was prepared. A later completed V1/V2 run, finalized human review, and
descriptive comparison are documented in the addendum at the end of this file. The plan,
schedule, and original preparation evidence remain unchanged.

The current conclusion is **mixed/inconclusive**. V1 case 3 asserts a student method; v2 asks
about one (approved Evidence discipline FAIL → PASS), but its leading question remains a
teaching-usefulness failure. Case 8 still fails attribution/context/adaptation review. Case 4
changes a repeated what question into a why question, but retains an unnecessary follow-up.
Case 10 recognizes the method/check in both samples. V2 case 5 incorrectly rejects the correct
answer 12. These are linked observations, not evidence that the addition caused the changes.
Baseline sources and the complete approved reasons are preserved in the research record.

| Scope | Cases | Purpose |
| --- | --- | --- |
| Method unknown | 3 | Observe unsupported method attribution and neutral elicitation. |
| Student-supplied method | 4, 10 | Check recognition of supplied method and, in case 10, check. |
| Tutor-supplied method | 8 | Distinguish guided success from student-selected steps; do not invent speed. |
| Regression check | 5 | Separate correct answer from an invalid reported method. |

Three fresh samples for each case and each prompt create exactly thirty scheduled slots.
The old one-sample baselines are not new observations and do not consume or enlarge this new
budget. Every slot is distinct even when the request text repeats. Failed slots are never
retried, replaced or silently dropped. Existing stop-on-timeout/control/transport failure
halts remaining calls and preserves NOT_EXECUTED slots; other invalid/incomplete outputs
remain failed observations and execution proceeds only to the next pre-existing slot.
No warmup, verification generation, resume or automatic extra attempt exists.

The existing prompts, fixture/rubric files and baseline evidence/reviews remain unchanged.
Local model is `qwen3.5:4b-q4_K_M`, required digest
`d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`.
The unchanged model default sampling parameters are inspected before local execution;
no temperature/seed tuning is introduced. Keep 8000 input admission, 12288 runtime context,
1000 generation allowance, thinking false, 30-second deadline including cold load, exact
reply schema, no retries, cloud disabled and loopback-only serving. Record actual runtime
version, available usage, load/prompt/generation timing and memory rather than assuming
repeatable performance. Prompt caching may affect timing but does not authorize conversation
carryover. Every request contains only the selected prompt and that case's selected context.

Prepared bundle (new, exclusive):

- `artifacts/tutor-v1-v2-repeatability-plan-01/plan.json`: fixed design, hashes/settings,
  maximum budget, schedule seed and algorithm; model-generation seed explicitly unspecified.
- `schedule.json`: all thirty ordered slots with case/version/hash/sample/position/opaque ID.
- `version-map.json`: separate mapping for the later review join.
- `review-view.json`: thirty pending label-masked review placeholders with case context;
  no replies have been generated.

Schedule seed **20261019** is an ordinary recorded scheduling choice, not a model seed.
SHA-256 sort of `schedule:<seed>:<slot ID>` defines stable pseudorandom order; explicit slot ID
breaks any hash tie. The complete schedule is retained and validated, so reproducibility does
not rely on a particular Python shuffle implementation. Model seed defaults are unmodified,
not assumed known. Review ID/order derivations use different hash domains.

After a later instruction authorizes execution, with Ollama on PATH and external networking
actually disconnected as described in [local setup](../../experiments/tutor_v1/LOCAL_SETUP.md),
run exactly once from the repository root:

```sh
.venv/bin/python -m experiments.tutor_v1.repeatability run \
  --plan-directory artifacts/tutor-v1-v2-repeatability-plan-01 \
  --output-directory artifacts/tutor-v1-v2-repeatability-local-01 \
  --mode local \
  --network-disconnected
```

**This command was not executed.** `--network-disconnected` is operator attestation, not an
automatic network check. Omit `--mode local` and the run defaults to a mechanics-only fake;
there is no paid mode. The output directory must not exist, preventing overwrite of either
baselines or any prior repeatability attempt. Do not rerun after partial execution without
instruction, including when an interruption leaves an outcome unknown.

The future output bundle contains `samples.jsonl`, `schedule.json`, `version-map.json` and
`review-view.json`. Raw evidence includes the complete schedule, one flushed slot-start per
reserved attempt, one outcome for each slot during normal/caught-stop completion, selected
context, actual available usage/timing and all pending judgments. Reserving before calling
conservatively bounds the budget even on interruption. A hard kill/power loss can leave a
reserved outcome unknown and no finished review export: the full schedule/start event remain,
and there is no automatic resume or replacement.

For initial human review, provide **only `review-view.json`**. It includes exact available
reply wording, required case context, mechanical outcome and six pending judgments per item.
It hides prompt version/hash, slot/sample IDs, execution position and timing metadata, and
uses a separate deterministic review order. Keep raw `samples.jsonl`, schedule and version
mapping out of that initial view; mapping is retained separately for joining approved reviews.
Wording can reveal conditions, reviewers have seen baseline replies, and no independent
reviewer agreement is claimed: describe this as **label-masked review**, not fully blinded
independent review. Missing/invalid replies remain visible as mechanical outcomes; no fake
text or inferred judgment replaces them.

Review all new observations across the existing six dimensions, leaving judgments pending
until human review. Keep raw evidence and later completed review artifacts separate. No
automated judge, aggregate score, numeric weights, release threshold, significance claim or
new precision/recall metric is part of this protocol. This measures variation on five known
cases only, not full regression coverage, held-out evaluation or proof of generalization.
Any later promotion decision must revisit broader regression coverage. Exact review approval
dates not supplied in prior artifacts are not reconstructed from execution timestamps.

See the [handoff/contract check](../handoffs/offline-tutor-repeatability.md) for actual
verification and [preparation integrity evidence](../../artifacts/tutor-repeatability-preparation-validation.json).

## Subsequent V1/V2 execution and review

The prepared schedule was later executed locally for cases 03/04/05/08/10 × prompts v1/v2 ×
three fresh samples, producing 30 observations. The run recorded no mechanical failures or
unexecuted slots. The finalized label-masked review contains 180 approved judgments (six
existing dimensions for each of 30 observations). A separate descriptive comparison found
mixed, slice-dependent results and declared neither prompt better overall. It makes no causal,
statistical-significance, generalization, or pilot-readiness claim; the review was label-masked,
not fully blinded independent review.

Preserved evidence: [raw samples](../../artifacts/tutor-v1-v2-repeatability-local-01/samples.jsonl),
[finalized human review](../../artifacts/tutor-repeatability-label-masked-human-review-finalized-01.json),
[machine-readable comparison](../../artifacts/tutor-repeatability-slice-comparison-01.json), and
[descriptive report](../../artifacts/tutor-repeatability-slice-comparison-01.md). This later
evidence does not alter the preparation authorization or authorize a new run.
