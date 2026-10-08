# Engineering constitution

## Authority

`docs/` contains approved engineering contracts. Only explicitly approved content is authoritative; TODO/UNRESOLVED markers and proposals are not approval. Code implements contracts and must not silently redefine them.

| Document | Authority |
| --- | --- |
| `docs/requirements.md` | Product/system requirements |
| `docs/architecture.md` | Architecture and component boundaries |
| `docs/schema.md` | Database/data model |
| `docs/api-contract.md` | Public/internal API contracts |
| `docs/ai-runtime.md` | AI orchestration/runtime behavior |
| `docs/security.md` | Security and authorization rules |
| `docs/evals.md` | Tests/evaluation policy |
| `docs/decisions.md` | Approved architectural/product decisions |

## Human decision boundary

Do not independently approve or silently change requirements, architecture, schema design, API contracts, authentication/authorization, security boundaries, AI behavioral policy, mastery authority, evaluation criteria, important business rules, or major dependencies/infrastructure choices.

When required approved guidance is missing or contradictory, STOP dependent implementation. Report the missing decision, why it is required, reasonable options, tradeoffs, and a recommendation if useful. Wait for human approval. Existing explicit approval need not be requested again; reference its evidence. Ordinary implementation choices (names, private helpers, existing patterns, mechanical refactoring, test organization, details behind approved interfaces) do not require approval.

## Scope and context

Implement only the requested vertical slice. Use the simplest implementation satisfying its approved contract (YAGNI). No future endpoints, speculative abstractions, neighboring redesigns, unnecessary dependencies, unrelated refactors, extra features, or contract changes for convenience.

Load context in order: `AGENTS.md` → relevant `.agents/skills/<name>/SKILL.md` → relevant doc sections → relevant source → apply the current task. The task defines relevance throughout. Do not load every document, repeatedly summarize contracts, or carry long conversation histories; cite paths/sections and use concise handoffs. Stable rules belong here, workflows in skills, system knowledge in docs, implementation in code.

## Contract-first implementation

Before inspecting implementation, identify the relevant requirement, API contract, schema, architecture components, security rules, AI-runtime rules if applicable, and tests/evals. Mark domains genuinely not applicable with a reason. Then inspect code and plan the requested slice. Unresolved required contracts block implementation; existing code is not approval evidence.

Use `implement-endpoint`, `schema-change`, or `ai-eval` when applicable. Run `contract-check` and produce `handoff` after implementation. Skills are in `.agents/skills/` and may be explicitly invoked as `$<name>`.

## Drift and synchronization

Never silently reconcile disagreement. Classify each finding:

- **MATCH**: implementation follows the approved contract.
- **IMPLEMENTATION_BUG**: code violates the approved contract.
- **DOCUMENTATION_DRIFT**: evidence shows an already-approved implementation/decision changed without synchronized documentation.
- **DECISION_REQUIRED**: resolution requires a human engineering/product decision; escalate and wait.

Include exact code files and doc sections, evidence, and implications. Missing approval evidence is DECISION_REQUIRED, not DOCUMENTATION_DRIFT. Do not rewrite docs to legitimize accidental behavior.

Approved contract changes must update the relevant authority document in the same change: API → api-contract; schema → schema; architecture → architecture; security → security; AI behavior → ai-runtime; evaluations → evals; requirements/business rules → requirements. Record important approved decisions in decisions.md with date, context, options, rationale, consequences, and approval evidence. Do not log trivial coding choices as architectural decisions.

## Verification and handoff

Run applicable formatting/lint, type checks, unit/integration tests, AI evals, and contract check using established tooling. Report actual commands and outcomes. For any check not run, state what, why, and resulting risk. Never claim unexecuted tests passed.

Report status as COMPLETE, PARTIAL, BLOCKED, or DECISION REQUIRED. Expose failures, TODOs, assumptions, incomplete behavior, unresolved decisions, security concerns, and mismatches. Placeholder behavior is not feature completion.

Use the handoff skill's concise structure. After substantial implementation, explain request entry, validation, business logic, data access, external/model/tool interactions, persistence, response path, and failure/security boundaries so the human can understand and defend the system. Avoid syntax tutorials unless asked.
