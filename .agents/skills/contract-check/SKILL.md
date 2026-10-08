---
name: contract-check
description: Review changed implementation for requirements, API, schema, architecture, security, AI behavior, and evaluation drift.
---

# Contract check

Follow root AGENTS.md. Inspect the current task diff or explicit changed-file inventory if Git is unavailable. Read only relevant approved sections of docs/requirements.md, docs/api-contract.md, docs/schema.md, docs/architecture.md, docs/security.md, docs/ai-runtime.md where applicable, and docs/evals.md; consult docs/decisions.md for approval evidence. Compare implementation and verification evidence with these contracts. State reasons for domains not applicable or not checked.

Classify findings:

- MATCH: implementation follows the approved contract.
- IMPLEMENTATION_BUG: code violates the approved contract.
- DOCUMENTATION_DRIFT: evidence shows an already-approved implementation/decision changed without synchronized docs.
- DECISION_REQUIRED: missing/contradictory guidance or a discrepancy needs human engineering/product judgment. Missing approval evidence is not documentation drift.

Report a compact table with classification, exact implementation/test files and lines where available, exact document sections/contract IDs, evidence, impact, and required next action. Identify missing artifacts explicitly. Check API, schema, architecture, security, and AI behavior, not just API shape. An unresolved required contract is never an assumed match.

This review does not authorize automatic edits. Never automatically fix DECISION_REQUIRED or rewrite docs to ratify accidental code. Report the missing decision, why required, options/tradeoffs, and recommendation if useful; wait for human approval. Fix implementation bugs only within the authorized task and synchronize docs only from approval evidence.

Conclude with COMPLETE, PARTIAL, BLOCKED, or DECISION REQUIRED for the reviewed scope, including unchecked areas and verification limits. A procedural contract review is not an executed test or automated enforcement.
