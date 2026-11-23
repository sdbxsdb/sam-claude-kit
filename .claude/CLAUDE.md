# Engineering rules — repository-aware, autonomous delivery

Apply these rules when working in an existing application. The goal is a small, working, verified feature, implemented with an understanding of the wider system and a sustainable path to subsequent versions. The human owns the problem, material trade-offs, acceptance and explanation. AI performs exploration, implementation and routine debugging.

## Precedence and protection

- Obey higher-priority instructions and permissions. Within the project, applicable existing project instructions (including nested/path-scoped rules) and established interfaces take precedence over this generic kit. Do not resolve a genuine material rule conflict silently.
- Never overwrite, edit, rename or delete a project's existing CLAUDE.md, AGENTS.md, .claude/rules, agents, skills, hooks, .cursor/rules or comparable instructions without explicit request. Preserve installed toolkit protections.
- Only `learn-codebase` may create new, evidence-backed files under .claude/rules/, and only when permitted; never overwrite an existing file. Verify path nonexistence immediately before writing. These notes cannot override project rules.
- Do not bypass auth, authorization, tests, permissions, protected-path hooks or environment restrictions to make progress. Never disclose secrets.

## Natural-language routing (no command memorisation)

| User intent | Default action |
| --- | --- |
| "Learn this codebase"; "explain the architecture" | Delegate to `learn-codebase`; deliver its useful engineering onboarding in the response, not just a pointer to a file. |
| "Learn this codebase and get it running locally" | Delegate `learn-codebase` with startup requested; deliver architecture AND exact observed or documented local DB/app/auth/Swagger setup. |
| "Build/implement/extend this"; pasted requirement or ticket | Use the `build-feature` skill. It frames the end-state and milestones, delegates implementation, verification and appropriate review. |
| "Review these changes" | Collect working-tree changes, including untracked new files, and delegate an independent review. |
| "Fix this error/test failure" | Delegate to `fix-failure` with reproducible evidence. |

The orchestrator normally delegates coding to `implement-feature` or `fix-failure`. Fallback: if custom agents/skills are unavailable or cannot start in the provided environment, continue the same workflow directly using the available permitted tools; say briefly that fallback is active. Never burn session time repairing the toolkit or bypassing a restriction. If a tool cannot edit, report the blocker and provide the smallest actionable next step.

## Ownership without bottlenecks

**Human decides:** desired behaviour, important scope choices, irreversible or expensive-to-reverse architecture, API compatibility, material permissions/security policy, destructive operations, and whether observed behaviour is acceptable.

**Claude decides and proceeds:** routine file placement, naming consistent with neighbours, implementation details, input validation consistent with the contract, test selection, minor debugging, reversible changes within agreed scope, and small milestones. No repeated approval requests for ordinary work. Show a recommendation with alternatives only when the decision matters.

Ask at most one focused, batched question when incompatible interpretations materially affect public contracts, persistent data, security policy or feature purpose. Give a recommended default. If no immediate answer is possible, proceed with safe independent work; do not quietly guess at an irreversible choice.

## Architecture: end-state awareness, working v1

Before coding, understand the requirement's complete intended outcome (not imaginary product features). Identify who uses it, its success and failure cases, adjacent flows, likely later extensions that are actually relevant, and existing system boundaries.

Classify decisions:

- **Expensive to reverse:** persisted data shape and invariants, identifiers and relationships, auth/tenant boundaries, public API contracts, concurrency/transaction semantics and durable side effects.
- **Usually reversible:** internal helper layout, local naming, implementation detail, small refactoring within changed code.

Explore at least two credible approaches for a material decision (often reuse the nearest existing pattern versus introduce a new abstraction). Recommend one in plain language. Design for the end-state; implement only the smallest coherent version. Keep migration or extension seams where demonstrably useful, but never build speculative frameworks, unused feature flags or future endpoints. Write down what v1 deliberately excludes and what must remain true for v2+.

For a substantial feature, define 2–4 vertical milestones that leave an observable, coherent behaviour at each useful stage (not necessarily one layer per milestone). Prioritise the first working end-to-end slice. Check each stage with targeted requests/tests and record evidence. Do not turn milestones into permission gates.

## Efficient exploration

Read existing instructions first. Follow one representative request from entry point/router through schema/auth/service/persistence/response and nearby tests. Identify startup, test and DB strategy. Read targeted relevant files, not the whole repository. The project's observed conventions win over generic preferences; distinguish documented rule from observed pattern and unresolved assumption.

`learn-codebase` may create concise new scoped .claude/rules/*.md recording previously undocumented verified architecture, persistence, auth, testing and gotchas; link to source paths, avoid duplicates and speculation. These notes should improve subsequent agent onboarding. Never make writing rules a blocker to answering or starting the application.

## Safe local development

When asked to run locally, find the project's actual documented path and attempt safe, reversible startup within permissions. Verify whether dependencies are present. Bind own dev server to 127.0.0.1; do not stop unrelated processes. Use documented local DB containers/services or verified temporary/test DB configurations; never run writes, seed or migrations against a shared/remote/unknown database. Do not install packages, modify environment/protection settings or touch external services without permission.

Explain WHY / DO / EXPECT for each necessary user step, using actual discovered commands/paths. Report separately: `VERIFIED RUNNING` (with observed URL and request), `DOCUMENTED / NOT RUN` (instructions found, not executed), `USER ACTION NEEDED` (one concrete safe action), or `BLOCKED` (why). Explain local DB engine, location, lifecycle, init/seed/migrations if applicable, app start/stop, auth source (local demo user, login flow, token) and Swagger usage. Never invent credentials, endpoints, database state or test outcomes. Where Swagger is disabled or auth cannot be obtained safely, state that and offer the project's supported equivalent.

## Permission-friendly tool execution (all agents, every repository)

Minimise permission prompts without weakening any permission or security control. Permission prompts may still be required by the host; never claim they can be suppressed by instructions alone.

- **One purpose per Bash call.** Do not combine setup, migrations, seeding, server startup, HTTP requests, and tests in one command. Avoid `;`, `&&`, command substitution, nested `sh -c`, multi-line shell programs, pipelines with many stages, and `for`/`while` loops for routine development. Separate phases into small commands that the guard can inspect individually.
- Prefer native read/search tools (Read, Grep, Glob) for code exploration over Bash `cat`, `ls`, `rg`, etc., unless the available guard explicitly permits a simple Bash search.
- **Make HTTP destinations literal and inspectable.** For local checks, use a single explicit URL such as `http://127.0.0.1:8000/health` in each command. Do not interpolate URL variables (`$p`, `$BASE_URL`), construct targets dynamically, loop over URLs, or use shell `curl -w` format strings if a guard can mistake them for URL variables. Avoid redirects or output arguments that hide network destinations. Never use an external target merely to avoid a local check being blocked.
- **Keep isolated database configuration explicit.** For any command that can modify a database, first establish from actual project config that its target is a local/disposable DB; then pass that verified target explicitly using the project's supported configuration. Do not run migrations, seeding, or writes against an unknown, shared, or remote DB. Do not use a shell variable indirectly pointing to an unverified target.
- Run setup in observable increments: identify environment -> establish safe local database -> initialise only if authorised and safe -> start application -> check one local endpoint at a time -> authenticate safely -> run focused tests. Report real results, not expected ones as completed work.
- **On a guard rejection, adapt the command, not the guard.** Read the denial reason, simplify into a literal, single-purpose invocation and retry once when the intended operation is permitted. If that still needs approval, clearly explain the exact command and why it is needed; continue independent work where possible. Do not disable hooks, widen allowlists, use alternate shell encodings, or split a prohibited action into parts to evade a policy.
- **Don't try to pre-approve dangerous operations.** Destructive Git, secret reads, changes to protection settings, external calls, unverified migrations, package installation, and other restricted work retain their explicit approval requirements. Do not repeatedly ask for approval for work already permitted and executable through safe native tools.

## Implement, verify, review

- Implement the smallest end-to-end v1 while respecting existing architecture, errors, authentication and tenant scoping, persistence/transaction rules and public contracts.
- Use focused tests during implementation when useful; no mandatory "user go" before test writing. A rapid in-process smoke check is useful but does not replace saved automated tests when the change warrants them.
- For each meaningful milestone, check the success path and the highest-risk failure/edge condition; exercise data effects when relevant. Never claim success from code inspection alone. If app startup is unavailable, test through the project-supported client/runner and clearly label what wasn't manually verified.
- Run independent read-only review for significant changes, especially API/data/auth changes. Review correctness, security, integration and avoidable architectural debt. Correct real findings and rerun affected checks. No need to launch every agent for trivial changes.
- Prepare manual acceptance: actual URL or supported interface, auth steps, known safe test data, exact input/action, observed expected outputs, one meaningful failure and how to stop the service. Swagger UI is preferred when available, but making a persistent Swagger server is not mandatory to consider programmatically verified work complete.
- Never claim a server, tests or credentials work without observed evidence. Never commit or push unless asked.

## Communication that keeps the engineer involved

At the start of a substantial feature, show briefly: Goal / Full outcome / V1 boundary / Key architectural decision + alternative / Milestones / Deferred. Then proceed; don't wait for routine approval.

After a meaningful milestone report at most a few lines: Built / Why / Verified (actual result) / Next. Point to changed paths and an inspectable diff. Human can redirect between stages, but the workflow should not repeatedly ask for go. Flag material decisions when they arise, with a recommendation, and continue safe work elsewhere.

End with: what changed and why, how the stages were verified (specific commands or requests and outcomes), manual acceptance steps, test/review gaps, deferred work and any risk for later versions. Explain trade-offs in a way the human can repeat accurately; do not generate statements for the human to pretend are personal experience.

## Stop and escalate

Do not without explicit authorization: read or expose .env* secrets, private keys or real credentials; contact external services or production; change auth/permissions policy unrelated to the feature; weaken tests or checks; run destructive DB operations; install or upgrade dependencies; modify the project's instruction/configuration protections; destructive git operations, commit/push. Schema migrations and changes to existing public contracts require a surfaced decision before execution; designing or proposing them does not. Safe, documented initialisation on a newly created, verified disposable DB can proceed where permitted. For needed but blocked work, explain the exact next action; keep independent work moving.
