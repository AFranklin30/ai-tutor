---
name: handoff
description: Produce a concise task handoff with contracts, request/data flow, verification, decisions, risks, and next slice.
---

# Engineering handoff

Follow root AGENTS.md. Read the current task/diff or changed-file inventory, relevant contract references, and actual verification evidence. Do not reload all docs or replay the conversation. Cite paths/sections, commands/results, and approval evidence; never invent executed tests or approvals.

Use these concise fields, marking none/not applicable with a reason where needed:

- TASK: requested slice and COMPLETE, PARTIAL, BLOCKED, or DECISION REQUIRED status.
- IMPLEMENTED: actual behavior/artifacts; distinguish scaffolds from working features.
- FILES CHANGED: exact paths and purposes.
- CONTRACTS USED: document sections/IDs and approval evidence.
- REQUEST/DATA FLOW: entry → validation → business logic → data access → external/model/tool interactions → persistence → response; important failure/security boundaries. For documentation-only work describe workflow and mark runtime flow not applicable.
- TESTS/EVALS RUN: actual commands/checks executed; separately list what was not run, why, and resulting risk.
- RESULTS: observed outcomes, failures, and contract-check classifications.
- DECISIONS MADE: ordinary implementation choices and actual human approval references; unresolved decisions are not made decisions.
- APPROVED CONTRACT CHANGES: authoritative sections changed and approval evidence, or none.
- DEVIATIONS: scope/contract discrepancies, or none.
- KNOWN RISKS / TODO: assumptions, incomplete behavior, security concerns, mismatches, missing decisions, verification gaps.
- NEXT LOGICAL SLICE: smallest proposed next task and prerequisites; this does not authorize implementation.

After substantial implementation explain the architectural flow and boundaries clearly enough for another session or the human to understand and defend the system. Omit trivial syntax tutorials unless asked. Keep sufficient context without conversation replay.
