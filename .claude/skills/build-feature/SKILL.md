---
name: build-feature
description: Orchestrate implementation or extension of a feature in an existing repository. Understand end-state architecture, identify expensive-to-reverse choices, choose a small working v1, deliver verifiable milestones, use implementation agents when available, then run live verification, automatic independent review and Swagger acceptance readiness without routine approval gates.
---

# Build a feature: architectural judgement, autonomous execution, observable slices

You are the orchestrator. Read the root and applicable project instructions, particularly `CLAUDE.md`. The human owns material architecture and acceptance. Claude does implementation, routine debugging and the operation of the development environment. Once scope and architecture are settled, you carry the feature through implementation, tests, live verification, independent review, correction and Swagger acceptance readiness without returning routine commands to the human.

## 1. Orient rapidly

If the code is unfamiliar, delegate to `learn-codebase` with the feature context and **exploration only**. It should return the closest end-to-end flow, project rules and relevant patterns (router, request/response models, auth, services, storage/transactions, tests), the documented startup, restart, database, migration, seeding and authentication procedures, docs/auth routes and genuine gotchas. For a feature build, avoid unrelated rule generation. Exploration does not start the server; the implementer does that. If the relevant context is already known, skip exploration agent. If agents unavailable, inspect with existing permitted tools directly and say you are using fallback.

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

Before asking anything, inspect the relevant models, schemas, services, existing behaviour and security boundaries. Make ordinary reversible decisions yourself. Do not stop for approval unless a genuine unresolved material product, security, data-contract or expensive-to-reverse architecture decision remains. Then ask one focused batched question with a recommended option and its trade-off, and continue safe independent work. The human may redirect after any report.

## 3. Milestones are vertical, verifiable and independent

For a substantial change use 2–4 coherent slices; the first should give working user-visible or API-visible behaviour as early as possible. Do **not** make “add schema”, “add service”, “add tests” separate stages if none works on its own. For each milestone specify:

- Observable contract or behaviour at completion.
- Changed components and dependencies (only those needed).
- Verification evidence: direct request/test plus important failure/permission/integrity condition.
- Which invariant and later-version option it preserves.

Small changes can be one milestone. Minimise handoffs: where feasible brief `implement-feature` once with all milestones and ask for intermediate reports/checks; if the environment only supports a complete agent return, ask the agent to execute the milestones sequentially and report evidence for each. Never run conflicting writing agents concurrently. Do not create human approval gates between routine milestones.

## 4. Delegate implementation with a self-contained brief

Agents may not see the conversation. Pass requirement, architecture/assumptions, chosen v1/exclusions, milestones, relevant source paths, project rules, and the startup, restart, DB, migration, seeding, auth and test conventions found earlier. Also pass what is known about running processes (for example a server the human started, which must not be killed) and state the authorised database scope: applying the feature's development migrations and seed data to the verified local development database is within the approved work unless the human said otherwise. Instruct `implement-feature` to write code **and focused tests when useful**, implement progressively, run and verify the application over real HTTP, investigate routine failures, avoid unrelated refactors/dependencies and complete Swagger acceptance readiness. If agent unavailable, follow the same procedure directly under available tools rather than stop the workflow.

Do not reflexively launch `fix-failure` for trivial issues implementer can correct; use it for stubborn or separately diagnosable failures. Run independent read-only work in parallel only when genuinely useful, never competing writers.

## 5. Keep human actively informed without bottlenecks

After a meaningful stage, relay: **What works / Important decision / Actual check and result / What's next**. Identify files and diff to inspect. Do not wait for “go” to run tests or routine next stages. The person can challenge or redirect work. Escalate a materially changed API contract, data model, auth policy, destructive step or unresolved scope conflict with options and recommendation.

## 6. Verify against the running application and be ready for Swagger acceptance

Verification prioritises: core workflow, significant failure case, auth/tenant isolation if relevant, persisted effects, backward compatibility. Use the repository's own testing strategy. Run focused checks early and adjacent regression tests before completion. Test failure is evidence, not a reason to weaken assertions.

Passing tests do not make the application ready. Before hand-back, the application must be running the latest implementation (see `CLAUDE.md` "Application lifecycle"). Where the environment supports it, make sure each of these was **observed**, not assumed:

- The server is running on a tracked port; if a server the human owns already uses the usual port, a separate instance runs on a free port and the human's process is untouched.
- The OpenAPI/Swagger endpoint responds and lists the new behaviour.
- A supported development user exists or was created in the verified local DB, and authentication works.
- The new behaviour works over real HTTP requests, including at least one meaningful failure scenario.

Then give the exact Swagger URL, login procedure, endpoint, request data and expected responses, so the human can open Swagger and start manual acceptance immediately. If Swagger is disabled or live verification genuinely cannot be completed, report the specific blocker and what was verified instead. Do not invent results.

Manual acceptance is the human's final check. It is **not** an approval checkpoint before tests, review or live verification. Do not return routine commands for the human to run.

## 7. Review, correct, finish

After meaningful feature changes and their tests, run `review` automatically. Do not ask whether the human wants it; skip it only for trivial edits. Supply requirements, v1 scope, alternatives/decisions, git diff plus new untracked paths, and observed evidence, and name any shared schema, model, dependency or router that changed so the reviewer can check existing endpoints. The reviewer flags real defects and *material, evidence-backed avoidable complexity*, not stylistic preferences.

Evaluate each finding against the code. Fix confirmed defects using `implement-feature` (or `fix-failure` for a stubborn failure), then rerun the affected tests and live checks, and make sure the server runs the corrected code. Note why any finding was rejected. One review round is the default. Run one more targeted round only if a fix touched auth, persisted data or an API contract, or a Blocker was fixed; then stop and report what remains. Do not loop.

Before the final report, confirm the server yourself with one literal localhost request. A server started inside a subagent may not outlive it; if it is gone, restart it as the lifecycle rules describe and recheck.

Final report in compact sections: **Delivered milestones; Design decisions and why; Verified evidence; Running application (URL, port, process, DB, owner, stop command); Swagger acceptance (URL, login, endpoint, request data, expected responses, failure case); Review and repairs; Deferred v2+; Risks and changed files.** Do not invent test results or commit unless asked.

## Safe fallback

When agent invocation, installation, model or hook availability differs, use the tools actually present, preserve restrictions, and deliver as much verifiable work as possible. Do not spend the session repairing toolkit wiring or bypassing protections. No repository code edits if the environment does not permit them.
