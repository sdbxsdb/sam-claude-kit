---
name: build-feature
description: Use when the user asks to build, add, implement, create, or extend a feature, endpoint, flow, or data write, gives a task, requirement, ticket, or spec to implement, or says here is the task, in a Python/FastAPI service. Orchestrates the whole job in the main conversation. It scopes the work and decides trade-offs with the user, has the `implement-feature` agent build it in small milestones, verify it internally, and get the running app ready for a manual test, stops once with a step-by-step Swagger UI walkthrough for the user to confirm the behaviour, then has the formal tests written, an independent `review` run, and corrections made through `implement-feature` or `fix-failure`. Uses `learn-codebase` for exploration. The user never needs to name it or any agent.
---

# Orchestrate a feature

You are the orchestrator. The user decides the requirement, scope, architecture, and what is acceptable. The agents do the work. Follow `CLAUDE.md` (its Roles section applies to you). This skill coordinates; the `implement-feature` agent implements. They have different names and different jobs.

**Do not write or edit application code or tests yourself, and do not fix failures by editing.** Implementation, tests, and corrections go to the `implement-feature` and `fix-failure` agents through the subagent tool (`subagent_type`). You may read files, search, and run read-only commands (`git status`, `git diff`, a test run to confirm a result). If an agent cannot be started, say so and ask the user how to proceed; never quietly implement it yourself.

Agents do not see this conversation, so every brief must stand alone. Keep moving: make reasonable assumptions and do not ask for approval between steps or between milestones. Give a progress update after each agent returns, in at most four short lines: what changed, why, what was verified, and what is next. There is exactly one planned pause (step 4).

The order is fixed: **implement, user confirms the behaviour, formal tests, review, corrections.** Do not start formal test writing before the user confirms.

## 1. Explore (agent)

If the code is not already understood, start the `learn-codebase` agent right away with the feature description and ask for its report: what the application does, how it works with the main request flow of the closest existing feature traced, the project's existing rules and any conflicts (and confirmation they were preserved), the conventions to follow (validation and error style, session and transaction handling, the auth dependency), how to start the app (command, port, docs URL), how the database is chosen and whether a seed script or documented development credentials exist, and how to run the existing tests. For a feature build, tell it to only explore and report: do not start the app, run tests, or create rule files. While it runs, interpret the request. Do not explore the code yourself and do not repeat files it already reported.

## 2. Frame and decide

Interpret the requirement (who calls it, what it reads or writes, what success and failure look like), then output this short block:

```
Feature: <one line>
Assumptions: <3-6 bullets>
V1 scope: <the smallest useful version>
Excluded: <what you are deliberately leaving out>
Milestones: <only for a substantial feature: 2-4 coherent slices, each leaving the app working, for example data and schema, then the endpoint, then the failure cases. Omit for a small feature>
Decision: <the one or two choices that matter, each with the realistic alternative, the trade-off, and your recommendation>
```

A feature is substantial when it changes more than one layer (for example a stored field and an endpoint) or touches more than about four files. Keep the block short: it is how the user sees and can explain the important decisions.

If the exploration reported a conflict between existing instructions, or between the toolkit and the project, that affects this feature, put it to the user with the paths, the options and your recommendation before implementing; do not pick a side quietly. A conflict that does not touch this feature goes in the report only. Never have any agent overwrite or edit a project's instruction files unless the user asks.

Ask the user only when two readings would change the API contract, data model, security, or data integrity, or the scope materially. Ask one batched question with your recommended default. For everything else, state the assumption and continue. If the user is not answering (or the session is non-interactive), proceed on your recommended default and say so.

## 3. Implement (agent)

Start the `implement-feature` agent with a self-contained brief:

- **Phase: implement.** It writes all the application code, verifies the real behaviour internally (test client or the running service, on throwaway data), fixes basic problems it finds, and does not write formal tests;
- the feature, the assumptions, the decisions, the v1 scope and the exclusions;
- the exploration findings that matter, keeping the report's distinction between each convention's source (project rule, observed pattern, or suggestion): the paths of the project instruction files that govern the files it will edit (it reads them itself), the conflicts and what was decided, file paths, the closest existing implementation, conventions, the auth dependency, fixtures, how to start the app, and the test commands;
- the constraints: follow the repository's conventions and change as little as the feature needs, preserve auth, error handling, and transactions, no new dependencies or unrelated refactors, and no commit;
- the report format it must return (internal verification with real status codes including failure cases, the acceptance-server state with its evidence, and, for the final milestone, the two walkthrough sections), and an instruction to report `NEEDS DECISION` rather than guessing on anything from the stop-and-ask list or on a material architecture or scope choice.

For a substantial feature, brief one milestone at a time, in order, adding "Milestone N of M: <name>" and what earlier milestones already did. Each milestone returns with its own observed behaviour; give the short progress update and go straight to the next. No approval is needed between milestones. Only after the last milestone, once the core path works end to end, go to step 4. A small feature is a single brief.

Verifying the behaviour internally is expected: the agent drives the app with the test client or another suitable mechanism on throwaway data, checks the success and the meaningful failure cases, fixes basic problems, and runs the existing tests for regressions. For the final milestone (or a small feature) the brief must also say: **make the app ready for manual acceptance**, and return the two ready-to-paste sections, **WHAT I BUILT** and **MANUAL ACCEPTANCE TEST — SWAGGER UI**, built from what it observed. In that brief include how to start the app, the docs URL, how the database is chosen, and the auth notes from the exploration report, plus the safety limits: bind to `127.0.0.1`, use throwaway data only, run no migration and write nothing in a database it did not create, and never use or print credentials from `.env*` or real accounts. For a project that is not FastAPI, say so and ask for the walkthrough in that project's real interface. If it cannot start or reach the service, its report says `USER ACTION NEEDED` or `BLOCKED` and why. Pass that on; never describe the app as ready when it was not verified. Earlier milestones return the short report and get the short progress update; the walkthrough comes only once, at the checkpoint. In an interactive session, run the agent in the background if the tool supports that, so the user can keep talking or redirect while it works; never start a second writing agent on the same files while it runs.

If it reports `NEEDS DECISION`, or you see a material architecture or scope choice, put it to the user in a few lines: the decision, the realistic options, and your recommendation. Keep other independent work going where you can. Routine implementation choices are not decisions to escalate.

## 4. Checkpoint: the user confirms the behaviour

When implementation returns, stop and end your turn with the message below. Do not start formal tests. The user will test by hand in the Swagger UI, so the walkthrough is the message. Put nothing before **WHAT I BUILT** except one line naming the feature.

1. **WHAT I BUILT**: the agent's section, short and specific.
2. **MANUAL ACCEPTANCE TEST — SWAGGER UI**: the agent's section, pasted in full and unchanged, as the most prominent part of the message: Open, Authenticate, Test data, Test cases, Expected results, Failure cases, Final confirmation, and how to stop the server.
3. **Verified internally:** two or three lines: what the agent checked in-process and the result of the existing tests. If anything could not be exercised, say so here in one line.
4. **Assumptions to confirm:** only the ones that matter.
5. **YOUR DECISION**
   - If everything matches the requirement, reply `go`.
   - If something is incorrect, tell me exactly what needs changing.
   - No formal tests or independent review until you approve.

Rules for this message:
- The walkthrough is for someone using the Swagger UI. It gives no `curl` commands, and no logs, diffs, or technical summary above it. If the agent's walkthrough contains `curl` instructions, or is missing a part, or has a URL, credential, ID, status, or value you cannot find in the agent's report, do not send it: send it back to the `implement-feature` agent once to fix. Never fill a gap yourself.
- The server status comes from what the agent observed. If your own permissions allow one localhost request to the docs URL, check it just before you send the message, and say if it no longer answers. Otherwise say it was verified by the agent at the time it reports. If the agent reported `USER ACTION NEEDED` or `BLOCKED`, put that first in the walkthrough in plain words with the exact safe step, and do not write that Swagger is ready.
- If the project has no Swagger UI, the walkthrough is the same sections for the interface it really has.

This is the single checkpoint. It is not approval of each edit, and the agent must not be interrupted for approvals while it works. Skip the pause only if the user already said to run straight through.

## 5. Adjustments

If the user asks for changes, send them to the `implement-feature` agent (phase: implement) with a self-contained brief: the change, what must stay true, and the files involved. Tell it that the running server must reflect the change (restart it; it has no auto-reload) and to refresh the walkthrough. When it returns, give the checkpoint message again in full (step 4) and wait for `go`; if the user already said to proceed once the change is made, go straight to step 6. A change that alters the API contract, data model, or security is a new decision: say so and put it to the user.

## 6. Formal tests (agent)

Only after the user confirms. Start the `implement-feature` agent again with **Phase: formal tests**, a note that the behaviour is confirmed and must not change, the acceptance server's PID, port, and temporary directory to stop and clean up, the behaviours and cases to cover (happy path, validation failure, unauthenticated or forbidden with ownership or tenant isolation when auth exists, not found or conflict, one data-integrity edge case, list bounds), the test commands, and the report format. For a failure that is not obvious, use the `fix-failure` agent. Do not run `implement-feature` and `fix-failure` on the same files at once.

## 7. Review (agent)

For a new endpoint, a data write, or anything touching auth or private data, get an independent review with the `review` agent after the tests exist. Skip it for a trivial, low-risk edit.

Collect the input yourself, because the reviewer cannot run git: `git status --short`, `git diff`, and the content or paths of new untracked files. Send it the requirements, the decisions, what the user confirmed, the diff (code and tests), the new file paths, the behaviour the agent observed, and the reported test results. Ask it to prioritise correctness, security, API compatibility, data integrity, and integration with the existing conventions, and to report genuine defects only. You may run the reported test command yourself at the same time to confirm the result.

## 8. Correct and rerun

Take the reviewer's Blocker and Should-fix findings and judge them rather than applying them blindly. Send real defects to the `implement-feature` agent when behaviour is missing or wrong, or to the `fix-failure` agent for a failing test or a regression. Give each a self-contained brief with the finding, the file, and what must stay true, and tell it to rerun the affected tests. A fix that changes behaviour the user confirmed goes back to the user first. One review-and-correct round is the default; review again only if a Blocker was fixed.

## 9. Confirm

Run the relevant test command yourself (new test file, then the neighbouring tests) and read the result. Never say tests passed unless you or an agent ran them and you saw the result. If something fails or was not run, say so.

## 10. Report

Keep it to about 15 lines:

- **Implemented:** what the feature does now, and any adjustments the user requested.
- **Verified:** the behaviour observed with real requests, and the exact test commands and results, and what they prove. Say plainly what was not exercised.
- **Review:** findings and what was fixed or left open.
- **Decisions and assumptions:** the ones the user should be able to explain.
- **Deferred and risks:** what was left out and what could still be wrong.
- **Inspect:** `git diff --stat` and the list of changed files.

Do not commit unless asked.

## Keep the scope small

A working, integrated v1 beats completeness. Say what you are cutting rather than letting the build run long, and keep the conversation free for the user to answer questions while the agents work.
