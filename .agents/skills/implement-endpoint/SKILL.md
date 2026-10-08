---
name: implement-endpoint
description: Implement one requested endpoint from approved contracts with scoped tests, a contract check, and handoff.
---

# Implement one endpoint

Follow root AGENTS.md. Load only sections relevant to the requested endpoint.

1. Identify the approved requirement and endpoint section in docs/api-contract.md.
2. Read relevant docs/schema.md and docs/security.md, then docs/architecture.md, docs/ai-runtime.md if applicable, and docs/evals.md. Record reasons for non-applicability; consult docs/decisions.md for approval evidence as needed.
3. Inspect existing implementation and test patterns. Identify missing decisions and produce a concise plan with contract references, affected files, and verification.
4. If a human decision is required, STOP dependent implementation, report the missing decision, why required, reasonable options, tradeoffs, and recommendation if useful; wait for approval. Reference existing explicit approvals rather than requesting them again.
5. Implement only the requested endpoint and necessary private details. Do not add future endpoints, speculative abstractions, neighboring features, unrelated refactors, unnecessary dependencies, or change contracts for convenience.
6. Add/update tests for approved success, validation, error, and authorization behavior. Run applicable established formatting/lint, type checks, unit/integration tests, and AI evals. Report actual outcomes and skipped checks with reasons/risks.
7. Synchronize any human-approved contract changes in the same change and record important approved decisions.
8. Load ../contract-check/SKILL.md and check the slice; then load ../handoff/SKILL.md and produce a concise handoff. Unresolved behavior is not complete.
