# Quick start: Sam's Claude Code Toolkit

How to use the toolkit in an existing Python/FastAPI codebase, including a time-boxed development session. Install first (`PORTABLE-SETUP.md` covers every environment; `python3 bootstrap.py` is the installer). If you cannot install files, paste `sam-claude-bootstrap.md`, `MINIMAL-PROMPT.txt`, or `session-prompt.txt`.

All names below are the installed `sam-` names. A project's own `review` agent or `build-feature` skill is never replaced.

## How it works

You decide. The agents do the work. You write no application code. **You never name an agent or type a command**: talk normally and Claude routes the request.

| You say | What happens |
| --- | --- |
| "Explore this repository", "learn this codebase", "explain the architecture" | `sam-learn-codebase` explores, read-only |
| "Build this", "here's the task", "implement this requirement" | The build workflow below, ending with `sam-implement-feature` doing the coding |
| "Review these changes" | The orchestrator collects the diff; `sam-review` reviews, read-only |
| "Fix this bug", "investigate this failure" | `sam-fix-failure` finds the root cause and fixes it |

The `sam-` prefix only avoids name collisions with a project's own agents and skills. Routing works through the always-loaded rules and the agent and skill descriptions; Claude Code documents automatic delegation from descriptions but does not guarantee it. If Claude does the work itself instead of delegating, say "use the agents for this", or use the explicit forms in "Direct commands" below.

| You | The main conversation (orchestrator) | The agents |
| --- | --- | --- |
| Requirement, scope, architecture, trade-offs, API compatibility, security, what is acceptable to deliver, the explanation | Interprets the request, recommends a v1, shows trade-offs, briefs the agents, reports back, collects the diff for review. Never edits application code or tests | `sam-learn-codebase` explores, `sam-build-feature` implements and tests, `sam-review` reviews, `sam-fix-failure` fixes |

| Item | Kind | Tools | Use it for |
| --- | --- | --- | --- |
| `/sam-build-feature` | skill (orchestration) | main conversation | Scoping a feature and driving the agents below. It is the skill; the agent that implements is `sam-implement-feature` |
| `sam-learn-codebase` | agent | Read, Grep, Glob | Read-only. Finds the project's existing rules and conflicts first, then maps the files that matter, about 10 minutes |
| `sam-implement-feature` | agent | Read, Grep, Glob, Edit, Write, Bash | Implements the agreed v1 (in small milestones when it is large) and shows it working with real requests; after you confirm the behaviour, writes and runs the formal tests |
| `sam-review` | agent | Read, Grep, Glob | Independent read-only review of the diff against the requirements |
| `sam-fix-failure` | agent | Read, Grep, Glob, Edit, Write, Bash | Root-causes a failure and makes the smallest fix |
| `/sam-test-strategy`, `/sam-fastapi-engineering`, `/sam-python-engineering` | skills | n/a | Reference the implementation agent reads when it needs them |
| `CLAUDE.local.md` (or `.claude/rules/sam-rules.md`) | rules | n/a | Roles, workflow, and the stop-and-ask list; loaded at session start |

Agents cannot start other agents and cannot ask you questions. When one reaches something on the stop-and-ask list (dependency, auth change, migration, contract change, destructive step) it stops that part and reports `NEEDS DECISION`; the orchestrator brings it to you. Only the main conversation delegates.

## The flow

Just describe what you want built (the build workflow starts by itself). The explicit form, if you ever want it, is:

```text
/sam-build-feature <what you want built>
```

1. **Explore.** The orchestrator starts `sam-learn-codebase` with your request. It does not read the code itself.
2. **Frame and decide.** You get a short block: feature, assumptions, v1 scope, what is excluded, and the one or two decisions that matter with a recommendation. It asks only when two readings change the API contract, data model, security, or scope; otherwise it states its assumption and proceeds. Answer, or redirect, at any time.
3. **Implement.** The orchestrator briefs `sam-implement-feature`, which writes the code (in small milestones for a large feature) and verifies it internally with the test client (success and failure cases, existing tests still pass), then gets the app ready for you: it runs it on `127.0.0.1` against a throwaway database, seeds test data, works out authentication, confirms the Swagger docs page responds and lists the new endpoints, and runs each walkthrough case itself to record the real results. If it cannot start the server it says so and gives you the one safe step; it never claims Swagger is ready unless it checked. It writes no formal tests yet.
4. **Checkpoint (the one planned pause).** You get **WHAT I BUILT**, then **MANUAL ACCEPTANCE TEST — SWAGGER UI** (the URL to open, how to authorise, test data, numbered steps with the exact status and values to expect, a failure case, and a checklist), then **YOUR DECISION**. Follow the steps in the Swagger UI, then either describe changes or say "go". This is not approval of each edit.
5. **Adjust.** Changes you ask for go back to `sam-implement-feature`. You are asked only whether to move on.
6. **Formal tests.** Only after you confirm, `sam-implement-feature` writes and runs the tests (happy path, validation, auth and isolation, not found or conflict, one integrity edge case, list bounds).
7. **Review.** For a new endpoint, a write, or anything touching auth, the orchestrator collects `git diff` and sends it with the requirements to `sam-review`. Trivial edits skip this.
8. **Correct.** Real findings go to `sam-implement-feature` (missing or wrong behaviour) or `sam-fix-failure` (failing test, regression), and the affected tests are rerun. One round by default.
9. **Confirm and report.** The orchestrator runs the relevant tests itself and reports what was implemented, what ran with what result, review findings, decisions, deferred work, and risks.

Not every task needs every agent. Skip exploration when the code is understood. Skip review for a trivial change.

## Redirecting while it works

Ask your question or change direction in the same session. The orchestrator is not the one writing code, so it can answer you while an agent works (in an interactive session it starts the implementation agent in the background when the tool supports it). If you change the requirement, the orchestrator stops sending work that conflicts and re-briefs. Two agents never edit the same files at once.

## Direct commands (optional; routing makes these unnecessary)

```text
Use the sam-learn-codebase agent to map the files relevant to <task>.
Use the sam-implement-feature agent to implement <agreed change>. Phase: implement (exercise the behaviour, no formal tests). Scope: <v1>. Test command: <cmd>.
Use the sam-implement-feature agent. Phase: formal tests. The behaviour is confirmed. Cover: <cases>. Test command: <cmd>.
Use the sam-review agent on this diff: <paste git diff> Requirements: <paste>
Use the sam-fix-failure agent on this failure: <paste the error>
```

`sam-review` cannot run git. Collect the diff yourself: `git diff | pbcopy` (Linux: `git diff | xclip -sel clip`), plus the paths of new files.

## Minimum review of what lands

Read the diff (`git diff --stat`, then the hunks). Reject new dependencies, new layers, edits to unrelated files, changed existing tests, and auth or migration changes you did not ask for. Check that every claimed test run appears in the agent's report with a result line, and that a smoke check is never presented as a test.

## Time-boxed session (about 60 minutes)

| Minutes | Phase | What happens |
| --- | --- | --- |
| 0-10 | Explore | `sam-learn-codebase` maps the repo while you read the requirement and prepare questions |
| 10-15 | Decide | You choose between the options the orchestrator shows; v1 scope and exclusions are fixed |
| 15-35 | Implement | `sam-implement-feature` builds and demonstrates; you stay free to answer questions |
| about 35 | Checkpoint | The Swagger walkthrough; you follow it, then confirm or ask for changes |
| 35-52 | Tests and review | Formal tests, then `sam-review`, then corrections and reruns |
| 52-60 | Verify and discuss | The orchestrator confirms tests and summarises; you explain decisions, tests, and limits |

A working, integrated v1 beats completeness. Say what you are cutting.

## Be able to explain (the engineering signals)

- **Taste:** the options compared, why the simplest fit won, what was left out.
- **Agency:** the assumptions made and why no approval was needed.
- **Correctness:** validation, permissions, error cases, transaction behaviour, what the tests cover and do not.
- **Integration:** the existing feature copied, reused dependencies and fixtures, nothing unrelated touched.
- **Ownership:** how you supervised the diff, what the reviewer found, what is unfinished.

## Security and conventions

- The project's own conventions and security rules win over this kit.
- Existing authentication and authorization on every new route that reads or writes private data. No new scheme, no loosened check.
- Propose, then wait, before any change to auth, secrets, CORS, dependencies, or migrations.
- Never log secrets or PII, and never read credential files.
- Never say a test passed unless it ran.

## Fast searches

```bash
rg -n "FastAPI\(|include_router|APIRouter" .
rg -n "Depends\(" . | head -30
# no rg installed? use grep:
grep -rnE "FastAPI\(|include_router|APIRouter" --include='*.py' .
```
