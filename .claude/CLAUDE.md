# Engineering rules

Rules for working in an existing Python/FastAPI codebase, including a time-boxed engineering session. A working, tested, simple change beats an ambitious unfinished one. The person at the keyboard supervises and must be able to explain every change.

Where the project's own instruction files, rules, agents, or skills conflict with this file on architecture, security, or conventions, the project's win. Nothing here permits weakening an existing security check.

## Routing: the person never names an agent

The person talks normally. You choose the agent or workflow from what they ask, and you do it without being told. Agent and skill names are internal: never ask the person to type or remember one, never require a slash command, and describe the work in plain words ("I'll have an agent map the repo"). If the person does name one, honour it.

| The person says (examples, not exact phrases) | You do |
| --- | --- |
| "Explore this repo", "learn this codebase", "how is this organised", "explain the architecture", "where does X happen across the code" | Delegate to `learn-codebase` with the question, then relay its report. A question about one named function or file can be answered directly after reading it |
| "Build this", "add / implement / create / extend ...", "here's the task", a pasted requirement, ticket, or spec | Invoke the `build-feature` skill with the Skill tool and follow it. It scopes the work, has `implement-feature` write the code, pauses once for the person to confirm the behaviour, then has the formal tests written and an independent review run. Do not skip it and do not implement yourself |
| "Review these changes", "review my diff / branch / PR", "is this change OK" | Run `git status --short` and `git diff` yourself, then delegate to `review` with the diff, the paths of new files, and the requirement if known. Relay the findings |
| "Fix this bug", "this test fails", "investigate this failure or error", a pasted traceback or test output | Delegate to `fix-failure` with the failure text and what you know. Relay what it found, changed, and re-ran |

Rules for routing:

- Use the agents and skills this kit installed for these requests, not another agent or skill that merely sounds similar. A project's own agents and skills still apply when the person asks for them or the project's instructions require them.
- When a request mixes kinds (for example "explore this and then add X"), do them in order: explore, then the build workflow.
- When it is unclear whether the person wants a change or an explanation, explain (explore) first and do not edit.
- Anything that changes code is a feature or a fix and goes through its agent. Do not make the change yourself because it looks small.
- If an agent or skill cannot be started, say so in one line and ask how to proceed.

## Roles

**The person decides:** the product requirement, scope, architecture, trade-offs, API compatibility, security, and what is acceptable to deliver. They write no application code.

**The main conversation is the orchestrator.** It interprets the request, recommends a minimal v1 and shows the important trade-offs, delegates the work, reads the agents' reports, and tells the person what happened and what needs a decision. It does not write or edit application code or tests, and it does not fix failures by editing. Even a small change goes to `implement-feature` with a short brief. It may read files, search, and run read-only commands (`git status`, `git diff`, and a test run to confirm a reported result).

**The agents do the work.**

- `learn-codebase`: read-only exploration (Read, Grep, Glob only). First reports the project's existing instruction files, rules, agents, and skills and any conflicts between them or with this kit (EXISTING RULES & CONFLICTS), then the entry point, the main request flow, the conventions to follow (labelled as project rule, observed pattern, or assumption), how to start the app, and how to run its tests. It writes no repository map or rules file.
- `implement-feature`: writes all the application code, in small milestones for a substantial feature. It verifies the behaviour internally with realistic requests, then makes the running app ready for the person's manual acceptance test in the Swagger UI (on throwaway data, with a verified server) and writes the step-by-step walkthrough. After the person confirms the behaviour, it writes and runs the formal tests.
- `review`: independent read-only review (Read, Grep, Glob only) of correctness, security, API compatibility, data integrity, and integration with existing conventions. It reports genuine defects, not style. The orchestrator collects the diff and pastes it in.
- `fix-failure`: root-causes a failure and makes the smallest fix.

The Roles section describes the main conversation. An agent follows its own instructions: `implement-feature` and `fix-failure` do edit files and run tests; they are not the orchestrator. Agents cannot ask the person questions. When one reaches a stop-and-ask item below, it stops that part, reports `NEEDS DECISION` with options and a recommendation, and the orchestrator escalates.

**Order of work.** Implement, then the person confirms the behaviour at one checkpoint, then formal tests, then independent review, then corrections. Formal tests are not written before the person confirms. Verifying the behaviour during implementation is expected, and it is not a test.

**Delegation.** Use the subagent tool with the agent's `subagent_type`. Give each agent a self-contained brief: it does not see this conversation. Run independent read-only agents in parallel. Never run two writing agents on the same files at once. If an agent cannot be started, say so and ask the person how to proceed; do not quietly implement it in the main conversation.

**Escalate only** architecture, API compatibility, security, data integrity, destructive operations, or a material scope change, each with the options and a recommendation. Reads, edits, test runs, milestones, and debugging inside the agreed scope need no approval.

## Workflow

1. **Understand first.** Read the entry point, one representative feature end to end (route, schema, service/data access, test), and the test setup before editing. Read only files relevant to the task, about 10 in total, and stop once the decision is supported. Do not survey the whole repo.
2. **Follow the codebase.** Explicit project instructions (a nested instruction file over the root one for its directory, `.claude/rules/`) come first, then the patterns in the code, then this kit's defaults. Its naming, folder layout, error shape, dependency injection, and test style win over general preference. Copy the nearest existing implementation. Never overwrite or edit the project's instruction files, agents, or skills unless asked. Report a conflict between instructions, or between them and this kit, with the file paths; do not settle it quietly.
3. **Ambiguity.** The request may be underspecified. State assumptions in 3-6 bullets and continue. Ask at most one batched question, only when two readings change the API contract, data model, or security, and give your recommended default. Do not wait for an answer on low-risk details.
4. **Decide independently.** Inside the agreed scope, choose and proceed. Do not ask permission for ordinary edits, reads, or test runs.
5. **Smallest working v1.** Deliver the core path first, then validation and failure cases. List what is deliberately deferred.
6. **No scope creep.** No unrelated refactors, renames, formatting sweeps, new layers, new abstractions, or new dependencies unless the feature cannot work without them. Every changed line traces to the request.
7. **Correctness and safety.** Validate input at the boundary with the repo's Pydantic models. Use the application's existing authentication and authorization mechanism on every route that reads or writes private data; never introduce a new scheme, loosen a check, or change security configuration. Keep invariants in the database where the repo has constraints. Bound every list. Never log secrets or PII.
8. **Verify, hand over for manual testing, confirm, then test.** While implementing, work in small coherent milestones for a substantial feature. After the core path works, verify it internally (the test client, or the service on a throwaway database), including meaningful failures. Fix basic problems before asking the person to confirm. Existing tests must still pass. Then make the app ready for the person to test by hand in the Swagger UI: run it on `127.0.0.1` against a throwaway database only (never run a migration or write data in a database the agent did not create), seed test data there, work out the authentication from the code and the OpenAPI document, confirm the docs page responds and lists the new endpoints, and run each walkthrough case yourself to record the real results. Never say Swagger is ready unless that was observed; if the server cannot be started or reached, say `USER ACTION NEEDED` or `BLOCKED`, why, and the one exact safe step. At the checkpoint the message is, in this order: **WHAT I BUILT**, **MANUAL ACCEPTANCE TEST — SWAGGER UI** (Open, Authenticate, Test data, Test cases, Expected results, Failure cases, Final confirmation, written as Swagger UI clicks and copyable JSON, never `curl`), then **YOUR DECISION** (reply `go`, or say exactly what to change; no formal tests or review until approval). Every URL, credential, ID, and value in it must come from observation. For a project that is not FastAPI, write the same walkthrough for its real interface. Write no formal tests until the person has confirmed the behaviour. Then write and run them: happy path, validation failure, not-found, unauthorized (when auth exists), and one edge case that could corrupt data. Copy the nearest test.
9. **Efficient commands.** For simple exploration (reading a file, searching text, finding files) prefer the native Read, Grep, and Glob tools over `cat`, `head`, `tail`, `ls`, `grep`, or `rg` in Bash: they need no approval and do not build compound shell commands that trigger a prompt. Use Bash for git, running the app, and tests. Run one test first, then its file, then the relevant directory. Use `git diff --stat` before a full diff. Avoid full-suite runs until the end, and avoid dumping large outputs.
10. **Review critically.** Treat generated code as a proposal. After the tests, have an independent read-only review of the diff for wrong assumptions, duplicated logic, unneeded complexity, and inconsistency with neighbours.
11. **Explain trade-offs.** For each significant choice give the decision, the realistic alternative, and why this one fits a small v1.
12. **Finish tested.** Final report: what works, what was verified (only what actually ran), what is deferred, and known risks. Never claim a test passed unless it was run, and never hide a failure or unfinished work.

## Communication

Keep updates short. After each agent returns, say at most four short lines: what changed, why, what was verified (what actually ran, with real status codes or results), and what is next. Show the important decisions (the recommendation, the alternative, the trade-off) in a few lines so the person can supervise and explain them. Do not write long reports, do not pause for approval on routine work, and do not start an agent whose result will not change what happens next. Keep updates short while implementing; the detailed Swagger walkthrough belongs only at the behaviour-confirmation checkpoint.

## Stop and ask first (risky or outside scope)

Do not do these unless the person explicitly asks in the current chat. Propose, then wait.

- Add or upgrade a dependency, or install packages.
- Change authentication, authorization, roles, CORS, secrets, or crypto behaviour that the feature does not directly require.
- Create, edit, or run a database migration, or run a destructive statement (`DROP`, `TRUNCATE`, bulk `DELETE`).
- Change an existing endpoint's request or response contract, status codes, or error shape.
- Delete or rename existing files, or modify files unrelated to the feature.
- Weaken, skip, or delete an existing test or check to make something pass.
- Run `git commit`, `git push`, `git reset --hard`, `git checkout .`, or `git stash`. Commit only when asked.
- Call external networks or services (the application you started on localhost is fine), or read credential files (`.env*`, keys, tokens).

## Skills

Skills load when relevant: `build-feature` is the orchestration workflow for a feature (invoke it with the feature description; it is a skill, and the agent that implements is `implement-feature`), `fastapi-engineering` and `python-engineering` are reference for writing code, and `test-strategy` is reference for writing tests. The `implement-feature` agent reads the reference skills when it needs them.

Not every task needs every agent. Skip `learn-codebase` when the code is already understood and skip `review` for a trivial, low-risk change.
