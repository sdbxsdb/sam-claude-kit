# Portable setup

Get Sam's Claude Code configuration into another environment with as little setup as possible. Nothing here needs your Mac or your `~/.claude`. Everything is installed inside the target repository, never in user-level Claude configuration.

## Which scenario am I in?

| You have | Scenario |
| --- | --- |
| A terminal on this machine, Python 3, and the kit folder | **A** |
| A remote editor or workspace where you can upload files and open a terminal | **B** |
| A remote terminal with outbound Git access to a repo that holds the kit | **C** |
| No file upload and no Git, but you can paste text (into a terminal, or only into a chat) | **D** |
| A Claude session that cannot install files at all | **E** |

## What each scenario can do

| | Custom subagents (`sam-review` and others) | Skills (`/sam-build-feature` and others) | Rules loaded from files | Tool restrictions enforced |
| --- | --- | --- | --- | --- |
| A, B, C | Yes | Yes | Yes | Yes (`sam-review` and `sam-learn-codebase` have only Read, Grep, Glob; `sam-implement-feature` and `sam-fix-failure` have Read, Grep, Glob, Edit, Write, Bash and no way to start other agents) |
| D, terminal paste | Yes, once decoded and installed | Yes | Yes | Yes |
| D, chat-only paste | No | No | No, pasted text only | No |
| E | No | No | No, pasted text only | No |

Pasting text never creates subagents, skills, or tool restrictions. In D (chat-only) and E, the assistant follows the instructions by choice, and there is no orchestrator/agent split: one conversation does everything, which is the fallback only for sessions that cannot install files.

## What the installer does

`bootstrap.py` is plain Python 3 with no packages. Run it from the root of the target repository.

- Adds `CLAUDE.local.md` (the rules), or `.claude/rules/sam-rules.md` if `CLAUDE.local.md` already exists, or skips the rules if both exist.
- Adds agents `sam-learn-codebase`, `sam-implement-feature`, `sam-review`, `sam-fix-failure` and skills `sam-build-feature`, `sam-fastapi-engineering`, `sam-python-engineering`, `sam-test-strategy`. The `sam-` prefix means they cannot collide with your project's own `review` agent or `build-feature` skill.
- Writes a manifest, `.claude/sam-claude-kit.manifest.json`, listing exactly the files it created with their hashes.
- Never overwrites a file, never edits application source, never touches `~/.claude` or `~/.cursor`, never installs hooks, credentials, settings, or MCP configuration.
- Checks every file after writing and reports `INSTALLED AND VERIFIED` only if all of them read back correctly. It also prints what it cannot verify (that Claude Code actually loads them).
- Exit code `0` success, `1` failed or unverified, `2` usage or validation error (nothing changed), `3` partial.

Commands (run in the target repo root):

```bash
python3 <kit>/bootstrap.py --dry-run        # show every proposed change, write nothing
python3 <kit>/bootstrap.py                  # install
python3 <kit>/bootstrap.py --verify         # re-check the installed files against the manifest
python3 <kit>/bootstrap.py --uninstall      # remove exactly what it installed
```

Options: `--git-exclude` hides the installed files from `git status` using `.git/info/exclude` (local only, reversed by uninstall). `--rules-mode local` or `rules` forces the rules location. `--here` installs in the current folder even when it is inside a larger Git repository (otherwise it refuses). `--force` with `--uninstall` also removes installed files you edited (otherwise they are kept and listed). `--kit <path>` points at the kit if the script was copied elsewhere.

`<kit>` is the folder holding `bootstrap.py`, for example `~/sam-claude-kit`.

**Upgrading.** Run the installer again from the same repo root. Files it installed earlier and you have not edited are updated in place, new files are created, files you edited are kept and reported, and the manifest is rewritten. A file an earlier version installed that the kit no longer ships (the old `sam-build-feature` agent, now `sam-implement-feature`) is labelled `retire` and removed if you have not edited it; if you have, it is kept, reported, and the run ends `PARTIAL` so you can delete it yourself. The `.git/info/exclude` block is refreshed to match. Check with `--dry-run` first: it labels each file `create`, `update`, `unchanged`, or `keep`. No uninstall is needed.

If your project's `CLAUDE.md` exists, it is not touched: the kit's rules load alongside it.

---

## A. Local VS Code with a terminal

**Transfer.** The kit folder is already on disk, or unzip `sam-claude-kit.zip` (`unzip -q sam-claude-kit.zip -d ~`).

**Install**

```bash
cd /path/to/repo
python3 ~/sam-claude-kit/bootstrap.py --dry-run
python3 ~/sam-claude-kit/bootstrap.py --git-exclude
```

**Activate.** Start a new Claude Code session in that folder (`claude`, or the VS Code extension; restart it if it was already open). Files load at session start.

**Confirm what Claude loaded**

```bash
python3 ~/sam-claude-kit/bootstrap.py --verify    # files match the manifest
git status --short                                # only the added files (none with --git-exclude); nothing in your source
```

In Claude Code: `/memory` lists `CLAUDE.local.md` (or `.claude/rules/sam-rules.md`), `/agents` lists the `sam-` agents, and typing `/sam-` lists the four skills. You can also ask: "Quote the first rule under Workflow in your loaded instructions."

**Use it by talking normally.** You never need to name an agent or skill. The rules loaded at session start tell Claude to route by what you ask:

```text
Explore this repository / explain the architecture      -> read-only exploration agent
Here's the task: add an endpoint that does X           -> the build workflow (scope, implement, one checkpoint, tests, review)
Review these changes                                   -> read-only review agent
Fix this bug / investigate this failure                -> fix agent
```

Automatic routing relies on Claude following the rules and the agent and skill descriptions. It is not guaranteed; if Claude does the work itself instead of delegating, say "use the agents" or use the optional explicit forms below.

**Optional explicit forms** (the `sam-` prefix only avoids name collisions with a project's own items)

```text
/sam-build-feature add an endpoint that does X     (orchestrates the four agents below)
/sam-test-strategy
/sam-fastapi-engineering
/sam-python-engineering
Use the sam-learn-codebase agent to map the files relevant to <task>.
Use the sam-implement-feature agent to implement <agreed change>. Test command: <cmd>.
Use the sam-review agent on this diff and these requirements: <paste>
Use the sam-fix-failure agent on this failure: <paste the error>
```

`sam-review` and `sam-learn-codebase` cannot run commands, so the orchestrator (or you) pastes the diff for review. `sam-implement-feature` and `sam-fix-failure` edit files and run tests. Agents cannot start other agents, so only the main conversation delegates.

**Unavailable.** Nothing from the kit is unavailable here. Running Claude Code at all requires its own login, which the kit does not touch.

**If setup fails.** The installer states why and writes nothing (exit 2) or rolls back. Read the line starting `NOT INSTALLED`. Common causes: not inside the repo root (use `--here` only if you mean it), a symlinked `.claude` (refused), Python older than 3.8. Fallback: scenario E.

**Remove**

```bash
python3 ~/sam-claude-kit/bootstrap.py --uninstall
```

---

## B. Remote VS Code with file upload

**Transfer.** Upload `sam-claude-kit.zip` through the editor's upload or drag-and-drop into any folder outside the repo, for example your home folder.

**Install** (in the remote terminal)

```bash
python3 -m zipfile -e ~/sam-claude-kit.zip ~          # or: unzip -q ~/sam-claude-kit.zip -d ~
cd /path/to/repo
python3 ~/sam-claude-kit/bootstrap.py --dry-run
python3 ~/sam-claude-kit/bootstrap.py --git-exclude
```

If home is not writable, extract to `/tmp` and use `/tmp/sam-claude-kit/bootstrap.py` instead.

**Activate, confirm, invoke, remove:** identical to A. Run Claude Code in the remote terminal or the remote-side extension; local-side `~/.claude` is not used and not needed.

**Unavailable.** If the remote has no `python3`, the installer cannot run. Use E.

**If setup fails.** `python3 -m zipfile -l ~/sam-claude-kit.zip` shows whether the upload is intact (expect 17 files). Re-upload if not. If extraction works but the installer reports a problem, re-run with `--dry-run` and read the first problem line.

**Clean up the transfer** after uninstalling: `rm -rf ~/sam-claude-kit ~/sam-claude-kit.zip`.

---

## C. Remote environment with Git access

**Transfer.** Keep the kit in a private repo of your own (do not put it in a work repo). Then:

```bash
git clone <your-private-kit-repo> ~/sam-claude-kit
```

**Install, activate, confirm, invoke, remove:** as in A. The cloned folder must have `bootstrap.py` and `.claude/` at its top level.

**Unavailable.** Nothing, if outbound Git to that repo is allowed. Do not paste credentials into the environment to make this work; if authentication is a problem, use B or D.

**If setup fails.** `git clone` fails: use B or D. Clone works but the installer exits 2: it prints which kit file is missing or invalid, so confirm you cloned the whole repo.

---

## D. Only text can be pasted

There are two different cases. Pick by what you can paste *into*.

### D1. You can paste into a remote terminal (full install is possible)

**Transfer.** On your own machine, encode the kit. Lines are wrapped at 76 characters because terminals can truncate very long pasted lines.

```bash
cd ~ && COPYFILE_DISABLE=1 tar czf - --exclude VALIDATION-REPORT.md --exclude .DS_Store sam-claude-kit | base64 | fold -w 76 > /tmp/kit.b64
pbcopy < /tmp/kit.b64        # Linux: xclip -sel clip < /tmp/kit.b64
```

The result is about 55 KB of text, 720 lines. On the remote terminal, paste it between the markers:

```bash
cat > ~/kit.b64 <<'EOF'
<paste here>
EOF
```

If the shell mangles the heredoc, paste into a file in the remote editor instead and save it as `~/kit.b64`.

**Decode** (either works; the second needs only Python 3)

```bash
mkdir -p ~/kit-extract && cd ~/kit-extract && base64 -d < ~/kit.b64 | tar xzf -        # macOS: base64 -D
# or
cd ~ && python3 -c "import base64,io,tarfile; tarfile.open(fileobj=io.BytesIO(base64.b64decode(open('kit.b64').read())),mode='r:gz').extractall('kit-extract')"
```

This creates `~/kit-extract/sam-claude-kit/`. **Install** from your repo root with `python3 ~/kit-extract/sam-claude-kit/bootstrap.py --dry-run`, then without `--dry-run`.

**Confirm, invoke, activate, remove:** as in A, with that path.

**Unavailable.** Nothing once decoded. Transfer is slower than B or C.

**If setup fails.** `base64: invalid input` means the paste was truncated or altered: check `wc -l ~/kit.b64` (expect about 720) and paste again. Remove transfer files afterwards: `rm -rf ~/kit.b64 ~/kit-extract`.

### D2. You can only paste into a chat (no terminal, no files)

Nothing can be installed. Paste the contents of **`sam-claude-bootstrap.md`** as your first message, then send your task. It covers the workflow, standards, FastAPI and Python conventions, tests, security, debugging, and review.

- **Confirm:** the assistant is told to reply with one line saying which tools it has. Ask "Quote the rule about when to ask a question" to check it read the text.
- **Unavailable:** custom subagents, skills, slash commands, and any tool restriction. The assistant follows the text by choice only.
- **If the text is too long for the chat:** use scenario E.

---

## E. Restricted session with no file-install capability

**Transfer.** Open `MINIMAL-PROMPT.txt` (about 20 lines) and paste it as the first message. If the session accepts more, paste `sam-claude-bootstrap.md` instead.

**Activate.** Sending the message is the whole setup. Then send your task.

**Confirm what Claude loaded.** The prompt asks for a one-line reply naming the tools it has. Then ask "List the things you must ask me before doing" and check it names dependencies, auth changes, migrations, API contract changes, deletions, commits, and external calls.

**Invoke.** There are no skills or agents. Use plain requests: "Explore the files relevant to X first, read-only", "Review this diff: <paste>", "Find the root cause of this failure: <paste>".

**Unavailable.** Subagents, skills, slash commands, file-based rules, tool restrictions, and anything needing file or shell access that the session lacks. If it cannot read files, it must say so and work from pasted code.

**If it does not follow the instructions.** Re-paste the prompt and remind it of the specific rule that was missed. Do not rely on it for guarantees: nothing enforces the "ask first" list in this scenario.

---

## Verify the kit itself (before you travel)

```bash
cd ~/sam-claude-kit && python3 bootstrap.py --help >/dev/null && echo "installer runs"
unzip -l ~/sam-claude-kit.zip | tail -1                     # expect 17 files
unzip -Z1 ~/sam-claude-kit.zip | grep -iE 'abnormal|interview|assessment|nisos|samdb|/Users/' || echo CLEAN
```

The last check uses `grep` because `rg` is not always installed.
