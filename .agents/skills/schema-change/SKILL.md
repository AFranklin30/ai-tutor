---
name: schema-change
description: Propose and implement a requirement-driven schema change after human approval of schema design.
---

# Schema change

Follow root AGENTS.md. Code wanting another field is not approval for schema evolution. Read only affected contracts.

1. Identify the approved requirement requiring change and inspect docs/schema.md.
2. Inspect affected access patterns/API contracts in docs/api-contract.md, security/ownership rules, architecture boundaries, and existing migration patterns.
3. Identify migration implications, constraints/indexes, backward compatibility, data conversion/backfill, deployment ordering, and rollback/recovery concerns. Do not invent a database or migration framework.
4. Propose the precise change, options/tradeoffs, rationale, affected contracts, migration approach, and tests. Require human approval for schema-design decisions. STOP before schema/migration edits if approval is missing; report why required and wait. Cite existing explicit approvals rather than asking again.
5. After approval implement only the approved migration and required affected behavior. Update docs/schema.md and other affected authoritative docs in the same change; log important decisions with approval evidence.
6. Test migration and affected behavior, constraints, compatibility, and recovery where applicable using established tooling and suitable test data. Report exact outcomes and checks not run with reasons/risks.
7. Load ../contract-check/SKILL.md and check the change; load ../handoff/SKILL.md and produce the handoff. Expose unresolved data concerns and untested migration behavior.
