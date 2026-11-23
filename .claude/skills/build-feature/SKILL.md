---
name: build-feature
description: Use when the user asks to build, add, implement, create, or extend a feature, endpoint, flow, or data write, gives a task, requirement, ticket, or spec to implement, or says here is the task, in a Python/FastAPI service. Orchestrates the whole job in the main conversation. It scopes the work and decides trade-offs with the user, has the `implement-feature` agent build and smoke-check it, stops once for the user to confirm the behaviour, then has the formal tests written, an independent `review` run, and corrections made through `implement-feature` or `fix-failure`. Uses `learn-codebase` for exploration. The user never needs to name it or any agent.
---

# Orchestrate a feature

You are the orchestrator. The user decides the requirement, scope, architecture, and what is acceptable. The agents do the work. Follow `CLAUDE.md` (its Roles section applies to you). This skill coordinates; the `implement-feature` agent implements. They have different names and different jobs.

**Do not write or edit application code or tests yourself, and do not fix failures by editing.** Implementation, tests, and corrections go to the `implement-feature` and `fix-failure` agents through the subagent tool (`subagent_type`). You may read files, search, and run read-only commands (`git status`, `git diff`, a test run to confirm a result). If an agent cannot be started, say so and ask the user how to proceed; never quietly implement it yourself.

Agents do not see this conversation, so every brief must stand alone. Keep moving: make reasonable assumptions, do not ask for approval between steps, and keep status updates to one or two lines. There is exactly one planned pause (step 4).

The order is fixed: **implement, user confirms the behaviour, formal tests, review, corrections.** Do not start formal test writing before the user confirms.

## 1. Explore (agent)

If the code is not already understood, start the `learn-codebase` agent right away with the feature description and ask for: the entry point and router registration, the closest existing feature end to end, validation and error style, session and transaction handling, the auth dependency, test fixtures, and the commands to run one test and the file. It is read-only and budgeted at about 10 minutes. While it runs, interpret the request. Do not explore the code yourself and do not repeat files it already reported.

## 2. Frame and decide

Interpret the requirement (who calls it, what it reads or writes, what success and failure look like), then output this short block:

```
Feature: <one line>
Assumptions: <3-6 bullets>
V1 scope: <the smallest useful version>
Excluded: <what you are deliberately leaving out>
Decision: <the one or two choices that matter, each with the realistic alternative, the trade-off, and your recommendation>
```

Ask the user only when two readings would change the API contract, data model, security, or data integrity, or the scope materially. Ask one batched question with your recommended default. For everything else, state the assumption and continue. If the user is not answering (or the session is non-interactive), proceed on your recommended default and say so.

## 3. Implement (agent)

Start the `implement-feature` agent with a self-contained brief:

- **Phase: implement.** It writes the code and smoke-checks that it runs, and does not write formal tests;
- the feature, the assumptions, the decisions, the v1 scope and the exclusions;
- the exploration findings that matter: file paths, the closest existing implementation, conventions, the auth dependency, fixtures, and the test commands;
- the constraints: follow the repository's conventions, preserve auth, error handling, and transactions, no new dependencies or unrelated refactors, and no commit;
- the report format it must return (including how the user can try the behaviour), and an instruction to report `NEEDS DECISION` rather than guessing on anything from the stop-and-ask list.

Smoke checks are fine and expected: it confirms the app imports and starts, tries the new behaviour once or twice, and runs the existing tests for regressions. In an interactive session, run it in the background if the tool supports that, so the user can keep talking or redirect while it works; otherwise wait. Never start a second writing agent on the same files while it runs. If it reports `NEEDS DECISION`, put that decision to the user.

## 4. Checkpoint: the user confirms the behaviour

When implementation returns, stop and end your turn with this short message. Do not start formal tests.

```
Implemented: <feature, one line>
What it does: <2-3 bullets>
Try it: <the exact requests or commands from the agent's report, with expected results>
Smoke checks: <what the agent ran and saw; no formal tests exist yet>
Assumptions to confirm: <only the ones that matter>
Does it behave as you expect? Tell me what to change, or say "go" and the agents will write and run the formal tests, then review.
```

This is the single checkpoint. It is not approval of each edit, and the agent must not be interrupted for approvals while it works. Skip the pause only if the user already said to run straight through.

In a time-boxed session, keep the checkpoint to four lines, with the `Try it` command, and say how much time is left so the user can confirm quickly. Aim to reach it by about the 30-35 minute mark so tests and review still fit.

## 5. Adjustments

If the user asks for changes, send them to the `implement-feature` agent (phase: implement) with a self-contained brief: the change, what must stay true, and the files involved. When it returns, report what changed in two lines and ask only whether to move on to tests; if the user already said to proceed once the change is made, go straight to step 6. A change that alters the API contract, data model, or security is a new decision: say so and put it to the user.

## 6. Formal tests (agent)

Only after the user confirms. Start the `implement-feature` agent again with **Phase: formal tests**, a note that the behaviour is confirmed and must not change, the behaviours and cases to cover (happy path, validation failure, unauthenticated or forbidden with ownership or tenant isolation when auth exists, not found or conflict, one data-integrity edge case, list bounds), the test commands, and the report format. For a failure that is not obvious, use the `fix-failure` agent. Do not run `implement-feature` and `fix-failure` on the same files at once.

## 7. Review (agent)

For a new endpoint, a data write, or anything touching auth or private data, get an independent review with the `review` agent after the tests exist. Skip it for a trivial, low-risk edit.

Collect the input yourself, because the reviewer cannot run git: `git status --short`, `git diff`, and the content or paths of new untracked files. Send it the requirements, the decisions, what the user confirmed, the diff (code and tests), the new file paths, and the reported test results. You may run the reported test command yourself at the same time to confirm the result.

## 8. Correct and rerun

Take the reviewer's Blocker and Should-fix findings and judge them rather than applying them blindly. Send real defects to the `implement-feature` agent when behaviour is missing or wrong, or to the `fix-failure` agent for a failing test or a regression. Give each a self-contained brief with the finding, the file, and what must stay true, and tell it to rerun the affected tests. A fix that changes behaviour the user confirmed goes back to the user first. One review-and-correct round is the default; review again only if a Blocker was fixed.

## 9. Confirm

Run the relevant test command yourself (new test file, then the neighbouring tests) and read the result. Never say tests passed unless you or an agent ran them and you saw the result. If something fails or was not run, say so.

## 10. Report

Keep it short:

- **Implemented:** what the feature does now, and any adjustments the user requested.
- **Tested:** the exact commands and results, and what they prove.
- **Review:** findings and what was fixed or left open.
- **Decisions and assumptions:** the ones the user should be able to explain.
- **Deferred and risks:** what was left out and what could still be wrong.
- **Inspect:** `git diff --stat` and the list of changed files.

Do not commit unless asked.

## Time-boxed session

For a session of about 60 minutes: explore for about 10 minutes, implement and reach the checkpoint by about minute 30-35, then tests and review in the remaining time, with the last few minutes for the summary and discussion. A working, integrated v1 beats completeness. Say what you are cutting rather than letting the build run long, and keep the conversation free for the user to answer questions while the agents work.
