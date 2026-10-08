---
name: ai-eval
description: Evaluate AI behavior against approved criteria, separating deterministic tests from probabilistic evidence.
---

# Evaluate AI behavior

Follow root AGENTS.md. Evaluation contracts belong to humans.

1. Identify behavior and requested scope; read relevant docs/ai-runtime.md and docs/evals.md. Load requirements, security, schema, or API sections only as needed.
2. Identify approved criteria, rubrics/metrics, reference cases, important slices, pass thresholds, baseline, and sampling/repeat policy. Missing necessary criteria require human decision: report why required, options/tradeoffs, and recommendation if useful; wait before acceptance claims. Do not invent thresholds.
3. Distinguish deterministic tests (validation, access, persistence, orchestration invariants) from probabilistic evaluation (model output quality/variability). Use existing reference cases where available. Proposed new criteria/cases remain proposals until approval.
4. Run applicable approved checks within authorized data/model/tool access. Record commands, dataset/case versions, runtime/prompt/policy/model identifiers and relevant settings, sample counts, scores, failures, baseline comparisons, and evidence locations where available. Follow approved privacy/logging boundaries; do not expose secrets or sensitive raw data.
5. Evaluate important approved slices where applicable, identify regressions, and report uncertainty, variability, coverage limits, skipped checks, and risks. A single observed success is not guaranteed behavior.
6. Never change criteria, references, rubrics, thresholds, or baselines merely to make a failing implementation pass. AI behavioral policy and mastery authority require human approval. Synchronize documentation only for approved changes.
7. Load ../contract-check/SKILL.md and then ../handoff/SKILL.md. Separate observed results, interpretations, and approved acceptance conclusions.
