# Install guide: Sam's Claude Code Toolkit

> **Preferred installer:** `python3 bootstrap.py` (see `PORTABLE-SETUP.md`). It installs prefixed `sam-` names, records a hash manifest, verifies what it wrote, and uninstalls exactly. This file documents the older shell-helper install, which uses the **unprefixed** names (`/build-feature`, `review` agent) and would sit beside, not replace, a project's own files of the same name. Do not use both installers in one repository. This helper has no upgrade logic: to move from an older copy, run `sam_kit_cleanup` first (or use `bootstrap.py`, which retires renamed files itself).

The toolkit is the `.claude/` folder inside `sam-claude-kit/`: one rules file (`CLAUDE.md`), four agents (`learn-codebase`, `implement-feature`, `fix-failure`, `review`), and four skills (`build-feature`, `fastapi-engineering`, `python-engineering`, `test-strategy`). It contains only Markdown and text files, with no executable code.

Guarantees of the installer below:

- It never overwrites or edits an existing file. An existing file with the same name is kept and ours is skipped.
- It only adds files under the repo's `.claude/`. It does not touch your user-level Claude Code configuration or anything outside the repo's `.claude/`. The one existing file it edits is `.claude/settings.local.json`, where it merges seven narrow Bash allow rules for `pytest` (`pytest *`, and `python -m pytest *` or `python3 -m pytest *`, with or without a `venv/` or `.venv/` interpreter) and keeps everything already in the file. It adds no rule for `cat`, `grep`, `rg`, `python`, `curl`, or `uvicorn`: file reading and searching use Claude Code's own Read, Grep and Glob tools. Skip that with `--no-permissions`; `--uninstall` removes only the rules it added.
- It records every file it added in `.claude/.sam-claude-kit-added`, so cleanup removes exactly those files.
- If the repo already has `CLAUDE.md` (in `.claude/` or at the repo root), ours is installed as `.claude/sam-rules.md` and loaded with `--append-system-prompt-file`.

Works from any directory inside a repo (it finds the repo root with git, or uses the current folder if it is not a git repo). Commands are for bash or zsh.

---

## Step 0. Define the helpers (once per terminal)

Set `SAM_KIT` to the folder that contains `.claude/`, then paste the three functions. The default is `$HOME/sam-claude-kit`.

```bash
export SAM_KIT="${SAM_KIT:-$HOME/sam-claude-kit}"

sam_kit_install() {
  local repo f
  repo="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  [ -d "$SAM_KIT/.claude" ] || { echo "kit not found at $SAM_KIT (set SAM_KIT)"; return 1; }
  mkdir -p "$repo/.claude" || return 1
  ( cd "$SAM_KIT/.claude" && find . -type f | sort ) | while IFS= read -r f; do
    f="${f#./}"
    if [ "$f" = "CLAUDE.md" ] && [ -e "$repo/CLAUDE.md" ]; then
      echo "kept yours : CLAUDE.md (repo root)"; continue
    fi
    if [ -e "$repo/.claude/$f" ]; then
      echo "kept yours : .claude/$f"
    else
      mkdir -p "$repo/.claude/$(dirname "$f")" \
        && cp "$SAM_KIT/.claude/$f" "$repo/.claude/$f" \
        && echo "$f" >> "$repo/.claude/.sam-claude-kit-added" \
        && echo "added      : .claude/$f"
    fi
  done
  if { [ -e "$repo/CLAUDE.md" ] || [ -e "$repo/.claude/CLAUDE.md" ]; } \
     && ! cmp -s "$SAM_KIT/.claude/CLAUDE.md" "$repo/.claude/CLAUDE.md" 2>/dev/null \
     && [ ! -e "$repo/.claude/sam-rules.md" ]; then
    cp "$SAM_KIT/.claude/CLAUDE.md" "$repo/.claude/sam-rules.md" \
      && echo "sam-rules.md" >> "$repo/.claude/.sam-claude-kit-added" \
      && echo "added      : .claude/sam-rules.md  (your CLAUDE.md was kept; start Claude with --append-system-prompt-file .claude/sam-rules.md)"
  fi
}

sam_kit_verify() {
  local repo f
  repo="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  echo "--- files added by the kit"; cat "$repo/.claude/.sam-claude-kit-added" 2>/dev/null || echo "(none)"
  echo "--- agents and skills present"
  find "$repo/.claude" -type f \( -path '*/agents/*.md' -o -name SKILL.md \) | sort | while IFS= read -r f; do
    printf '%s: %s\n' "${f#$repo/}" "$(sed -n '2p' "$f")"
  done
  echo "--- tracked files changed (must be empty)"
  git -C "$repo" diff --stat 2>/dev/null
}

sam_kit_cleanup() {
  local repo m f d
  repo="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  m="$repo/.claude/.sam-claude-kit-added"
  [ -f "$m" ] || { echo "nothing to clean (no manifest at $m)"; return 0; }
  while IFS= read -r f; do
    rm -f "$repo/.claude/$f"
    d="$(dirname "$repo/.claude/$f")"
    while [ "$d" != "$repo/.claude" ] && rmdir "$d" 2>/dev/null; do d="$(dirname "$d")"; done
  done < "$m"
  rm -f "$m"
  rmdir "$repo/.claude" 2>/dev/null
  echo "removed the files the kit added"
}
```

`sam_kit_verify` and `sam_kit_cleanup` only read the manifest and remove files listed in it.

---

## A. Install into a local repository

**Install**

```bash
cd /path/to/your/repo          # any folder inside the repo works
sam_kit_install
```

**Verify**

```bash
sam_kit_verify
git status --short             # new files appear under .claude/; nothing else
```

**Start Claude Code** (restart it if it was already running; files load at session start)

```bash
claude
# if the install output said "your CLAUDE.md was kept":
claude --append-system-prompt-file .claude/sam-rules.md
```

Inside Claude Code: `/agents` shows `learn-codebase`, `implement-feature`, `fix-failure`, `review`. `/memory` shows the loaded instructions. Typing `/` lists the four skills.

**Invoke skills and agents.** Normally just describe the task in plain words; the rules route it. The explicit forms:

```text
/build-feature add an endpoint that does X
/fastapi-engineering            (reference; also loads automatically for FastAPI work)
/python-engineering             (reference; also loads automatically for Python work)
/test-strategy                  (plan and write tests for the current change)

Use the learn-codebase agent to map the files relevant to <task>.
Use the implement-feature agent to implement <agreed change>.
Use the review agent on this diff: <paste output of: git diff>
Use the fix-failure agent on this failure: <paste the error>
```

One-shot from the shell, without opening the interface:

```bash
claude -p "Use the learn-codebase agent to map the files relevant to adding an endpoint for X"
```

**Clean up**

```bash
cd /path/to/your/repo
sam_kit_cleanup
git status --short             # the added .claude files are gone
```

---

## B. Transfer and install into a remote development environment

Use only transfer methods the environment permits. After the files are on the remote machine, install exactly as in A.

**Transfer (pick one)**

```bash
# 1. scp from your machine
scp ~/sam-claude-kit.zip user@host:~/

# 2. git, if you keep the kit in a private repo and outbound git is allowed
git clone <your-private-kit-repo> ~/sam-claude-kit

# 3. text only (terminal paste). On your machine:
base64 < ~/sam-claude-kit.zip | fold -w 76 | pbcopy        # Linux: base64 -w0 < file | fold -w 76 | xclip -sel clip
# On the remote machine:
cat > ~/sam-claude-kit.b64 <<'EOF'
<paste, then a line containing only EOF>
EOF
base64 -d < ~/sam-claude-kit.b64 > ~/sam-claude-kit.zip     # macOS: base64 -D
```

**Install (on the remote machine)**

```bash
unzip -q ~/sam-claude-kit.zip -d "$HOME"      # creates ~/sam-claude-kit; no unzip? python3 -m zipfile -e ~/sam-claude-kit.zip "$HOME"
# if $HOME is not writable, extract to /tmp and set the path: unzip -q ~/sam-claude-kit.zip -d /tmp; export SAM_KIT=/tmp/sam-claude-kit
```

Then run Step 0 (paste the helpers), and:

```bash
cd /path/to/remote/repo
sam_kit_install
```

**Verify**

```bash
sam_kit_verify
(cd "$HOME/sam-claude-kit" && find . -type f | sort)   # the kit itself: 17 files
```

**Start Claude Code**

```bash
cd /path/to/remote/repo
claude                                                  # or: claude --append-system-prompt-file .claude/sam-rules.md
```

**Invoke skills and agents:** same as A.

**Clean up**

```bash
cd /path/to/remote/repo && sam_kit_cleanup              # project files added by the kit
rm -f ~/sam-claude-kit.zip ~/sam-claude-kit.b64         # transfer files
rm -rf ~/sam-claude-kit                                 # the extracted kit (only if you no longer need it on this machine)
```

---

## C. Use `session-prompt.txt` when installing files is not possible

Nothing is added to the repo. The prompt carries the workflow and standards without skills or agents.

**Install**

Get `session-prompt.txt` to the machine (paste it, or copy it anywhere writable). Pick one:

```bash
# paste mode: copy the file, then paste it as the first message of the session
pbcopy < "$HOME/sam-claude-kit/session-prompt.txt"          # Linux: xclip -sel clip < file

# file mode: put it somewhere writable, outside the repo
cp "$HOME/sam-claude-kit/session-prompt.txt" /tmp/session-prompt.txt
```

**Verify**

After starting, ask: `Summarise your workflow in 7 bullets.` It should list explore, frame, plan, implement-and-test, run tests, review diff, summarise. Check the repo is untouched:

```bash
cd /path/to/your/repo && git status --short                 # nothing from the kit
```

**Start Claude Code**

```bash
cd /path/to/your/repo
claude --append-system-prompt-file /tmp/session-prompt.txt  # file mode
claude                                                       # paste mode: paste the prompt as your first message
```

**Invoke skills and agents:** there are none in this mode. Ask in plain language:

```text
Explore only the files relevant to <task> and report the patterns to follow.
Build <task> as a minimal v1 and show it working with real requests (no formal tests yet), then wait for me to confirm the behaviour before writing tests.
Review my diff for correctness and integration only: <paste git diff>
Find the root cause of this failure and make the smallest fix: <paste error>
```

**Clean up**

```bash
rm -f /tmp/session-prompt.txt
```

---

## D. Install alongside existing `CLAUDE.md`, rules, skills, or agents

The installer in Step 0 is already non-overwriting. This scenario shows how to preview collisions, prove nothing of yours changed, and run with your existing setup.

**Preview (changes nothing)**

```bash
cd /path/to/your/repo
REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
[ -e "$REPO/CLAUDE.md" ] && echo "collision: CLAUDE.md at repo root (kit rules go to .claude/sam-rules.md)"
( cd "$SAM_KIT/.claude" && find . -type f | sort ) | while IFS= read -r f; do
  f="${f#./}"; [ -e "$REPO/.claude/$f" ] && echo "collision: .claude/$f (yours is kept)" || echo "new      : .claude/$f"
done
```

**Install, with a before and after proof**

```bash
cd /path/to/your/repo
REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
BK=/tmp/sam-kit-before; rm -rf "$BK"; mkdir -p "$BK"
[ -d "$REPO/.claude" ] && cp -R "$REPO/.claude/." "$BK/"      # snapshot of your existing .claude/
sam_kit_install
( cd "$BK" && find . -type f | sort ) | while IFS= read -r f; do
  cmp -s "$BK/$f" "$REPO/.claude/$f" && echo "unchanged: $f" || echo "CHANGED: $f"     # must never print CHANGED
done
```

Your existing `.claude/rules/`, `.claude/settings.json`, other skills, and other agents are never written; `.claude/settings.local.json` only gets the pytest allow rules merged in. A same-named agent or skill of yours is kept and the kit's version is not installed.

**Verify**

```bash
sam_kit_verify
git status --short
```

**Start Claude Code**

```bash
claude                                                  # your own CLAUDE.md applies
claude --append-system-prompt-file .claude/sam-rules.md # when the installer said your CLAUDE.md was kept: adds the kit rules for this session only
```

Inside Claude Code, run `/memory` to see exactly which instruction files loaded, and `/agents` to see which agents are active.

**Invoke skills and agents:** same as A. If a skill or agent with the same name was kept as yours, the invocation runs yours.

**Clean up**

```bash
cd /path/to/your/repo
REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; BK=/tmp/sam-kit-before
sam_kit_cleanup
( cd "$BK" && find . -type f | sort ) | while IFS= read -r f; do
  cmp -s "$BK/$f" "$REPO/.claude/$f" && echo "unchanged: $f" || echo "CHANGED or missing: $f"
done
rm -rf /tmp/sam-kit-before
```

---

## Notes

- `.claude/` files are read when a session starts. Restart `claude` after installing or cleaning up.
- Optional: hide the added files from `git status` for this clone only (local, untracked):

  ```bash
  mkdir -p .git/info && echo ".claude/" >> .git/info/exclude
  ```

  This does not hide files that git already tracks.
- The installer writes nothing outside the repo's `.claude/` folder. It does not need network access.
