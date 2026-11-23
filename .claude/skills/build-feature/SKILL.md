---
name: build-feature
description: Orchestrate implementation or extension of a feature in an existing repository. Understand end-state architecture, identify expensive-to-reverse choices, choose a small working v1, deliver verifiable milestones, use implementation agents when available, and arrange manual acceptance and independent review without routine approval gates.
---

# Build a feature: architectural judgement, autonomous execution, observable slices

You are the orchestrator. Read the root and applicable project instructions, particularly `CLAUDE.md`. The human owns material architecture and acceptance; the agent does implementation and routine debugging.

## 1. Orient rapidly

If the code is unfamiliar, delegate to `learn-codebase` with the feature context and **exploration only**. It should return the closest end-to-end flow, project rules and relevant patterns (router, request/response models, auth, services, storage/transactions, tests), startup/DB/docs/auth routes and genuine gotchas. For a feature build, avoid unrelated rule generation or server startup unless requested. If the relevant context is already known, skip exploration agent. If agents unavailable, inspect with existing permitted tools directly and say you are using fallback.

## 2. Architecture before coding, but briefly

From the *actual requirement*, define:
- Intended complete behaviour: actors, triggers, data, permissions, lifecycle, side effects, failure and success semantics.
- **V1 invariant(s):** what must be true now and across likely later iterations.
- **Expensive-to-reverse choices:** data model, identity, API contracts, auth/tenancy, concurrency, transactions, integration interfaces. Identify genuine v2/v3 extensions; do not invent a product roadmap.
- Two plausible approaches for each **material** choice, preferably extending existing architecture versus a new pattern. Choose and recommend based on reuse, reversibility and clarity. Do not create future layers without a current consumer.
- The **smallest coherent, demonstrable v1** and explicit deferred scope; plan the extension path and any known migration cost.

Present a concise block (not a long essay):

```
Goal / end-state: ...
V1 now: ...
Design: ... (alternative ...; chose this because ...)
Avoiding future debt: ... (invariant / extension seam / migration concern)
Milestones: 1) ... 2) ... [3) ...]
Deferred: ...
Assumptions: ...
```

Do not stop for approval unless a genuine unresolved expensive-to-reverse decision materially changes contract/data/security/business behaviour. Ask one focused batched question with a recommendation; continue safe independent work. The human may redirect after any report.

## 3. Milestones are vertical, verifiable and independent

For a substantial change use 2–4 coherent slices; the first should give working user-visible or API-visible behaviour as early as possible. Do **not** make “add schema”, “add service”, “add tests” separate stages if none works on its own. For each milestone specify:

- Observable contract or behaviour at completion.
- Changed components and dependencies (only those needed).
- Verification evidence: direct request/test plus important failure/permission/integrity condition.
- Which invariant and later-version option it preserves.

Small changes can be one milestone. Minimise handoffs: where feasible brief `implement-feature` once with all milestones and ask for intermediate reports/checks; if the environment only supports a complete agent return, ask the agent to execute the milestones sequentially and report evidence for each. Never run conflicting writing agents concurrently. Do not create human approval gates between routine milestones.

## 4. Delegate implementation with a self-contained brief

Agents may not see the conversation. Pass requirement, architecture/assumptions, chosen v1/exclusions, milestones, relevant source paths, project rules, DB/auth/test conventions and startup limits. Instruct `implement-feature` to write code **and focused tests when useful**, implement progressively, verify each slice with observed evidence, investigate routine failures, avoid unrelated refactors/dependencies and produce final manual acceptance instructions. If agent unavailable, follow the same procedure directly under available tools rather than stop the workflow.

Do not reflexively launch `fix-failure` for trivial issues implementer can correct; use it for stubborn or separately diagnosable failures. Run independent read-only work in parallel only when genuinely useful, never competing writers.

## 5. Keep human actively informed without bottlenecks

After a meaningful stage, relay: **What works / Important decision / Actual check and result / What's next**. Identify files and diff to inspect. Do not wait for “go” to run tests or routine next stages. The person can challenge or redirect work. Escalate a materially changed API contract, data model, auth policy, destructive step or unresolved scope conflict with options and recommendation.

## 6. Verify and offer a real manual demonstration

Verification prioritises: core workflow, significant failure case, auth/tenant isolation if relevant, persisted effects, backward compatibility. Use the repository's own testing strategy. Run focused checks early and adjacent regression tests before completion. Test failure is evidence, not a reason to weaken assertions.

Where permitted and useful, start the app via documented safe local configuration with disposable or verified local test data. Read actual OpenAPI/docs/auth config. Give a precise Swagger UI walkthrough: real docs URL, **how to obtain a test account/token without secrets**, exactly how to Authorize, known test IDs, exact JSON/actions, observed statuses/body, meaningful failure case, stop command. If Swagger is disabled/inaccessible or local DB is blocked, do not hallucinate. Give equivalent in-process verification and `USER ACTION NEEDED` with the smallest exact safe step.

Manual acceptance matters, but is **not** a blocking approval checkpoint before formal tests or review. The engineer does the primary happy-path and one failure case when possible.

## 7. Review, correct, finish

For substantive endpoints, writes, security or architecture changes run `review` independently. Supply requirements, v1 scope, alternatives/decisions, git diff plus new untracked paths, and observed evidence. Reviewer flags real defects and *material, evidence-backed avoidable complexity*, not stylistic preferences. Fix genuine findings using `implement-feature` or `fix-failure`, rerun the affected checks. One review round by default, another if a serious blocker was corrected.

Final report in compact sections: **Delivered milestones; Design decisions and why; Verified evidence; Manual acceptance; Review and repairs; Deferred v2+; Risks and changed files.** Do not invent test results or commit unless asked.

## Safe fallback

When agent invocation, installation, model or hook availability differs, use the tools actually present, preserve restrictions, and deliver as much verifiable work as possible. Do not spend the assessment repairing toolkit wiring or bypassing protections. No repository code edits if the environment does not permit them.
