#!/usr/bin/env python3
"""Portable installer for Sam's Claude Code Toolkit (sam-claude-kit).

Run it from the root of the target repository:

    python3 /path/to/sam-claude-kit/bootstrap.py --dry-run     # show every change, write nothing
    python3 /path/to/sam-claude-kit/bootstrap.py               # install
    python3 /path/to/sam-claude-kit/bootstrap.py --verify      # re-check an installed copy
    python3 /path/to/sam-claude-kit/bootstrap.py --uninstall   # remove exactly what it installed

What it does
  * Validates every kit source file before it writes anything.
  * Installs the kit's agents and skills under `sam-` names, so they never collide with the
    project's own `review`, `build-feature`, and so on.
  * Installs the engineering rules as CLAUDE.local.md (preferred) or .claude/rules/sam-rules.md.
  * Merges a short list of narrow Bash allow rules (pytest, in its common invocations) into
    .claude/settings.local.json, keeping everything already in that file. Skip this with
    --no-permissions.
  * Records every file it creates, with a SHA-256, in .claude/sam-claude-kit.manifest.json, and
    exactly which permission rules it added, so --uninstall removes only those.
  * Never overwrites or edits any other existing project file.

What it never does
  * Touch application source, ~/.claude, ~/.cursor, any other settings file, or the network.
  * Install hooks, credentials, MCP configuration, or any permission beyond the list above.
  * Add an unrestricted Bash rule, a rule for python, curl, or uvicorn, or any write, edit, or
    network permission. Reading and searching files uses Claude Code's native Read, Grep and
    Glob tools, which need no rule.
  * Run other programs.

Standard library only. Python 3.8 or newer.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

VERSION = "1.3.0"
PREFIX = "sam-"
MANIFEST_REL = ".claude/sam-claude-kit.manifest.json"
GIT_EXCLUDE_REL = ".git/info/exclude"
EXCLUDE_BEGIN = "# >>> sam-claude-kit (managed by bootstrap.py) >>>"
EXCLUDE_END = "# <<< sam-claude-kit <<<"

AGENTS = ("learn-codebase", "implement-feature", "review", "fix-failure")
SKILLS = ("build-feature", "fastapi-engineering", "python-engineering", "test-strategy")
SKILL_REFERENCES = {"python-engineering": ("references/pytest-and-async.md",)}
NAMES = tuple(dict.fromkeys(AGENTS + SKILLS))  # an agent and a skill may share a name

# Read-only agents must keep exactly these restrictions, or the kit is rejected.
READ_ONLY_AGENTS = ("learn-codebase", "review")
READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]
READ_ONLY_DISALLOWED = {"Write", "Edit", "NotebookEdit", "Bash"}

# Agents that implement or fix. They must declare an explicit tool list that can read, edit and run
# tests, and nothing broader (no Task, so they cannot spawn agents; no web or MCP tools).
WRITE_AGENTS = ("implement-feature", "fix-failure")
WRITE_TOOLS_REQUIRED = {"Read", "Edit", "Write", "Bash"}
WRITE_TOOLS_ALLOWED = {"Read", "Grep", "Glob", "Edit", "Write", "Bash"}

# Frontmatter keys the kit may contain. Anything else (hooks, mcpServers, context, agent,
# permissionMode, allowed-tools, model, ...) aborts the install.
ALLOWED_AGENT_KEYS = {"name", "description", "tools", "disallowedTools"}
ALLOWED_SKILL_KEYS = {"name", "description"}

# Project-local, personal settings file (not the shared .claude/settings.json). Claude Code reads
# permissions.allow rules from it. Syntax: https://code.claude.com/docs/en/permissions
# "Bash(pytest *)" matches `pytest` and `pytest -q tests/`. A rule matches the command text as
# written, so each way of launching pytest needs its own rule, and `./venv/...` and `venv/...`
# are different. Only pytest is allowed: no bare python, no curl, no uvicorn, no file readers.
# The pattern below is also what a manifest must match, so an edited manifest cannot widen the list.
SETTINGS_REL = ".claude/settings.local.json"
KIT_PERMISSIONS = [
    "Bash(pytest *)",
    "Bash(python -m pytest *)",
    "Bash(python3 -m pytest *)",
    "Bash(venv/bin/python -m pytest *)",
    "Bash(./venv/bin/python -m pytest *)",
    "Bash(.venv/bin/python -m pytest *)",
    "Bash(./.venv/bin/python -m pytest *)",
]
PERMISSION_RULE = re.compile(r"^Bash\((?:pytest|python3? -m pytest|(?:\./)?\.?venv/bin/python -m pytest) \*\)$")
SETTINGS_KEYS = {"permissions", "allow"}

RULES_TARGETS = {"local": "CLAUDE.local.md", "rules": ".claude/rules/sam-rules.md"}
RULES_HEADER = (
    "<!-- sam-claude-kit: installed by bootstrap.py. "
    "Remove with: python3 bootstrap.py --uninstall -->\n\n"
)

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"/Users/[^/\s]+/|/home/[^/\s]+/|[A-Za-z]:\\Users\\"),
]

# The only paths this installer may ever create, modify, or delete (relative to the repo root).
ALLOWED_FILE_PATTERNS = [
    re.compile(r"^\.claude/agents/sam-[a-z-]+\.md$"),
    re.compile(r"^\.claude/skills/sam-[a-z-]+/SKILL\.md$"),
    re.compile(r"^\.claude/skills/sam-[a-z-]+/references/[a-z-]+\.md$"),
    re.compile(r"^CLAUDE\.local\.md$"),
    re.compile(r"^\.claude/rules/sam-rules\.md$"),
]
ALLOWED_DIR_PATTERN = re.compile(
    r"^\.claude(/agents|/rules|/skills|/skills/sam-[a-z-]+|/skills/sam-[a-z-]+/references)?$"
)

SNAPSHOT_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache"}
SNAPSHOT_LIMIT = 20000


class Abort(Exception):
    """Fatal error. `code` is the process exit status."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def out(line: str = "") -> None:
    print(line)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def human(n: int) -> str:
    return "%d B" % n if n < 1024 else "%.1f KB" % (n / 1024.0)


# ---------------------------------------------------------------------------------------------
# Kit validation
# ---------------------------------------------------------------------------------------------

def split_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Return (frontmatter dict, body). Raises ValueError when malformed."""
    if not text.startswith("---\n"):
        raise ValueError("file does not start with '---' frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("frontmatter is not closed with '---'")
    fm: Dict[str, str] = {}
    for line in text[4:end].split("\n"):
        if not line.strip():
            continue
        if line[0] in " \t" or ":" not in line:
            raise ValueError("unsupported frontmatter line: %r" % line[:60])
        key, value = line.split(":", 1)
        key = key.strip()
        if key in fm:
            raise ValueError("duplicate frontmatter key: %s" % key)
        fm[key] = value.strip().strip('"').strip("'")
    return fm, text[end + 5:]


def csv(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def validate_component(kind: str, name: str, text: str, label: str) -> None:
    """Check one agent or skill file (already prefixed or not) for structure and restrictions."""
    try:
        fm, _ = split_frontmatter(text)
    except ValueError as exc:
        raise Abort("%s: %s" % (label, exc))
    allowed = ALLOWED_AGENT_KEYS if kind == "agent" else ALLOWED_SKILL_KEYS
    unexpected = sorted(set(fm) - allowed)
    if unexpected:
        raise Abort("%s: unexpected frontmatter key(s): %s" % (label, ", ".join(unexpected)))
    if fm.get("name") != name:
        raise Abort("%s: frontmatter name is %r, expected %r" % (label, fm.get("name"), name))
    if not fm.get("description"):
        raise Abort("%s: missing description" % label)
    base = name[len(PREFIX):] if name.startswith(PREFIX) else name
    if kind == "agent" and base in READ_ONLY_AGENTS:
        if csv(fm.get("tools", "")) != READ_ONLY_TOOLS:
            raise Abort("%s: read-only agent must have tools: %s" % (label, ", ".join(READ_ONLY_TOOLS)))
        missing = READ_ONLY_DISALLOWED - set(csv(fm.get("disallowedTools", "")))
        if missing:
            raise Abort("%s: read-only agent must disallow: %s" % (label, ", ".join(sorted(missing))))
    if kind == "agent" and base in WRITE_AGENTS:
        tools = set(csv(fm.get("tools", "")))
        if not WRITE_TOOLS_REQUIRED <= tools:
            raise Abort("%s: implementation agent must declare tools including: %s"
                        % (label, ", ".join(sorted(WRITE_TOOLS_REQUIRED))))
        if not tools <= WRITE_TOOLS_ALLOWED:
            raise Abort("%s: implementation agent may only use: %s (found extra: %s)"
                        % (label, ", ".join(sorted(WRITE_TOOLS_ALLOWED)), ", ".join(sorted(tools - WRITE_TOOLS_ALLOWED))))


def check_clean_text(label: str, text: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise Abort("%s: contains a credential-like or machine-specific string (%s)" % (label, pattern.pattern[:30]))
    if "\x00" in text:
        raise Abort("%s: contains NUL bytes" % label)


def source_files() -> List[Tuple[str, str, str]]:
    """(kind, name, path relative to the kit) for every file the installer reads."""
    files = [("rules", "CLAUDE", ".claude/CLAUDE.md")]
    files += [("agent", n, ".claude/agents/%s.md" % n) for n in AGENTS]
    for n in SKILLS:
        files.append(("skill", n, ".claude/skills/%s/SKILL.md" % n))
        for ref in SKILL_REFERENCES.get(n, ()):
            files.append(("skill-reference", n, ".claude/skills/%s/%s" % (n, ref)))
    return files


def read_kit(kit: Path) -> Dict[str, str]:
    """Read and validate every source file. Nothing is written. Returns {kit-relative path: text}."""
    if not (kit / ".claude").is_dir():
        raise Abort("kit not found: %s has no .claude/ folder (use --kit PATH)" % kit)
    texts: Dict[str, str] = {}
    for kind, name, rel in source_files():
        path = kit / rel
        if path.is_symlink() or not path.is_file():
            raise Abort("kit file missing or not a regular file: %s" % rel)
        if path.stat().st_size > 200000:
            raise Abort("kit file unexpectedly large: %s" % rel)
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            raise Abort("kit file is not valid UTF-8: %s" % rel)
        text = text.replace("\r\n", "\n")
        check_clean_text(rel, text)
        if kind in ("agent", "skill"):
            validate_component(kind, name, text, rel)
        texts[rel] = text
    return texts


# ---------------------------------------------------------------------------------------------
# Text transformation (kit text -> prefixed project text)
# ---------------------------------------------------------------------------------------------

def transform(text: str, rules_ref: Optional[str]) -> str:
    """Prefix agent and skill names and point rule references at the installed rules file."""
    names = "|".join(re.escape(n) for n in NAMES)
    text = re.sub(r"\A(---\nname: )(%s)(\n)" % names, lambda m: m.group(1) + PREFIX + m.group(2) + m.group(3), text)
    text = re.sub(r"`(%s)`" % names, lambda m: "`%s%s`" % (PREFIX, m.group(1)), text)
    text = re.sub(r"(?<![\w/.-])/(%s)(?![\w-])" % names, lambda m: "/%s%s" % (PREFIX, m.group(1)), text)
    text = re.sub(r"(\.claude/skills/)(%s)(?=/)" % names, lambda m: m.group(1) + PREFIX + m.group(2), text)
    replacement = "`%s`" % rules_ref if rules_ref else "sam engineering rules"
    return text.replace("`CLAUDE.md`", replacement)


def check_transformed(label: str, text: str) -> None:
    names = "|".join(re.escape(n) for n in NAMES)
    leftover = re.findall(r"`(%s)`" % names, text)
    if leftover:
        raise Abort("%s: unprefixed reference(s) remain: %s" % (label, ", ".join(sorted(set(leftover)))))
    stale_paths = re.findall(r"\.claude/skills/(%s)/" % names, text)
    if stale_paths:
        raise Abort("%s: unprefixed skill path(s) remain: %s" % (label, ", ".join(sorted(set(stale_paths)))))
    if "CLAUDE.md" in text:
        raise Abort("%s: stale reference to CLAUDE.md remains" % label)
    installed = {PREFIX + n for n in NAMES}
    unknown = [r for r in re.findall(r"`(sam-[a-z-]+)`", text) if r not in installed]
    if unknown:
        raise Abort("%s: reference(s) to items that are not installed: %s" % (label, ", ".join(sorted(set(unknown)))))


# ---------------------------------------------------------------------------------------------
# Repository inspection
# ---------------------------------------------------------------------------------------------

def find_repo_root_problem(cwd: Path, here: bool) -> Optional[str]:
    if (cwd / ".git").exists() or here:
        return None
    for parent in cwd.parents:
        if (parent / ".git").exists():
            return ("this folder is inside a git repository whose root is %s. Run the installer from the repo root, "
                    "or pass --here to install in this folder anyway" % parent)
    return None


def list_dir(path: Path, only_dirs: bool = False, suffix: str = "") -> List[str]:
    if not path.is_dir():
        return []
    items = []
    for entry in sorted(path.iterdir()):
        if only_dirs and entry.is_dir():
            items.append(entry.name)
        elif not only_dirs and entry.is_file() and entry.name.endswith(suffix):
            items.append(entry.name[: -len(suffix)] if suffix else entry.name)
    return items


def detect(root: Path) -> List[Tuple[str, str]]:
    claude = root / ".claude"
    rows = [
        ("CLAUDE.md (repo root)", "present" if (root / "CLAUDE.md").is_file() else "absent"),
        (".claude/CLAUDE.md", "present" if (claude / "CLAUDE.md").is_file() else "absent"),
        ("CLAUDE.local.md", "present" if (root / "CLAUDE.local.md").is_file() else "absent"),
        (".claude/rules/", ", ".join(list_dir(claude / "rules", suffix=".md")) or "none"),
        (".claude/agents/", ", ".join(list_dir(claude / "agents", suffix=".md")) or "none"),
        (".claude/skills/", ", ".join(list_dir(claude / "skills", only_dirs=True)) or "none"),
    ]
    settings = [p.name for p in sorted(claude.glob("settings*.json"))] if claude.is_dir() else []
    if (root / ".mcp.json").is_file():
        settings.append(".mcp.json")
    rows.append(("settings / MCP files", ", ".join(settings) + " (existing settings are preserved)" if settings else "none"))
    rows.append(("git repository", "yes" if (root / ".git").exists() else "no"))
    return rows


def snapshot(root: Path) -> Tuple[Dict[str, Tuple[int, int, str]], bool]:
    """(size, mtime_ns, content hash for config files) for every file, excluding heavy dirs."""
    snap: Dict[str, Tuple[int, int, str]] = {}
    truncated = False
    for dirpath, dirnames, filenames in os.walk(str(root), followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SNAPSHOT_SKIP_DIRS]
        for filename in filenames:
            full = Path(dirpath) / filename
            rel = full.relative_to(root).as_posix()
            if len(snap) >= SNAPSHOT_LIMIT:
                truncated = True
                return snap, truncated
            try:
                st = full.lstat()
            except OSError:
                continue
            digest = ""
            if rel.startswith(".claude/") or rel in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".mcp.json", ".gitignore"):
                try:
                    digest = sha256(full.read_bytes()) if full.is_file() else ""
                except OSError:
                    digest = ""
            snap[rel] = (st.st_size, st.st_mtime_ns, digest)
    return snap, truncated


def compare_snapshots(before: Dict[str, Tuple[int, int, str]], after: Dict[str, Tuple[int, int, str]],
                      ours: set) -> Tuple[int, List[str]]:
    """Every pre-existing file that is not ours must be identical. Returns (checked, problems)."""
    problems: List[str] = []
    checked = 0
    for rel, sig in before.items():
        if rel in ours:
            continue
        checked += 1
        if rel not in after:
            problems.append("missing after run: %s" % rel)
        elif after[rel] != sig:
            problems.append("changed during run: %s" % rel)
    return checked, problems


def path_is_safe(root: Path, rel: str) -> bool:
    """True when no component of root/rel is a symlink and the real path stays inside root."""
    current = root
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            return False
    real_root = os.path.realpath(str(root))
    real = os.path.realpath(str(root / rel))
    return real == real_root or real.startswith(real_root + os.sep)


def allowed_file(rel: str) -> bool:
    return ".." not in Path(rel).parts and any(p.match(rel) for p in ALLOWED_FILE_PATTERNS)


# ---------------------------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------------------------

def load_manifest(root: Path) -> Optional[dict]:
    path = root / MANIFEST_REL
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or data.get("tool") != "sam-claude-kit-bootstrap":
            raise ValueError("unrecognised manifest schema")
        for entry in data["files"]:
            if not allowed_file(entry["path"]) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
                raise ValueError("manifest lists a path or hash this installer would never create: %r" % entry.get("path"))
        for d in data["dirs"]:
            if not ALLOWED_DIR_PATTERN.match(d):
                raise ValueError("manifest lists a directory this installer would never create: %r" % d)
        for m in data.get("modified", []):
            if m.get("path") == GIT_EXCLUDE_REL:
                continue
            if m.get("path") != SETTINGS_REL or m.get("type") != "permissions":
                raise ValueError("manifest lists a modified file this installer would never edit: %r" % m.get("path"))
            if not isinstance(m["added"], list) or not all(isinstance(r, str) and PERMISSION_RULE.match(r) for r in m["added"]):
                raise ValueError("manifest lists a permission rule this installer would never add")
            if not isinstance(m["created_file"], bool) or not set(m["created_keys"]) <= SETTINGS_KEYS:
                raise ValueError("manifest has an invalid settings entry")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise Abort("manifest %s is unreadable or not trusted (%s). Nothing was changed." % (MANIFEST_REL, exc))
    return data


def write_manifest(root: Path, files: List[dict], dirs: List[str], modified: List[dict], rules: Optional[dict],
                   installed_at: Optional[str] = None) -> None:
    data = {
        "tool": "sam-claude-kit-bootstrap",
        "schema": 1,
        "version": VERSION,
        "installed_at": installed_at or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rules": rules,
        "files": sorted(files, key=lambda e: e["path"]),
        "dirs": dirs,
        "modified": modified,
    }
    path = root / MANIFEST_REL
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


# ---------------------------------------------------------------------------------------------
# Permissions (merged into .claude/settings.local.json)
# ---------------------------------------------------------------------------------------------

def canon_rule(rule: object) -> object:
    """`Bash(ls:*)` and `Bash(ls *)` are the same rule in Claude Code; compare them as one."""
    return re.sub(r":\*\)$", " *)", rule) if isinstance(rule, str) else rule


def read_settings(path: Path) -> Tuple[Optional[dict], str, str]:
    """(parsed settings, raw text, problem). Parsed is None when the file cannot be merged safely."""
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, "", "cannot be read (%s)" % exc
    try:
        obj = json.loads(text)
    except ValueError as exc:
        return None, text, "is not valid JSON (%s)" % exc
    if not isinstance(obj, dict):
        return None, text, "is not a JSON object"
    perms = obj.get("permissions", {})
    if not isinstance(perms, dict):
        return None, text, "has a 'permissions' value that is not an object"
    for key in ("allow", "deny", "ask"):
        if not isinstance(perms.get(key, []), list):
            return None, text, "has permissions.%s that is not a list" % key
    return obj, text, ""


def merge_permissions(obj: dict, add: List[str]) -> Tuple[dict, List[str]]:
    """Copy of obj with `add` appended to permissions.allow. Also returns the keys that did not exist."""
    new = copy.deepcopy(obj)
    created: List[str] = []
    if "permissions" not in new:
        new["permissions"] = {}
        created.append("permissions")
    if "allow" not in new["permissions"]:
        new["permissions"]["allow"] = []
        created.append("allow")
    new["permissions"]["allow"].extend(add)
    return new, created


def strip_permissions(obj: dict, owned: List[str], created_keys: List[str], created_file: bool) -> Optional[dict]:
    """Copy of obj without the rules this installer added. None means the file itself should go."""
    new = copy.deepcopy(obj)
    perms = new.get("permissions")
    if isinstance(perms, dict) and isinstance(perms.get("allow"), list):
        for rule in owned:
            if rule in perms["allow"]:
                perms["allow"].remove(rule)  # one occurrence: a duplicate you added yourself stays
        if not perms["allow"] and "allow" in created_keys:
            del perms["allow"]
        if not perms and "permissions" in created_keys:
            del new["permissions"]
    return None if created_file and not new else new


def dump_settings(obj: dict, original_text: str) -> str:
    """Serialise with the indent and trailing newline the file already used (2 spaces for a new file)."""
    match = re.search(r"^([ \t]+)\S", original_text, re.M)
    indent = ("\t" if match.group(1).startswith("\t") else len(match.group(1))) if match else 2
    newline = "\n" if not original_text or original_text.endswith("\n") else ""
    return json.dumps(obj, indent=indent, ensure_ascii=False) + newline


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    if path.exists():
        os.chmod(str(tmp), path.stat().st_mode & 0o7777)
    os.replace(str(tmp), str(path))


def plan_permissions(root: Path, manifest: Optional[dict], enabled: bool) -> dict:
    """Decide what to do with the settings file. Nothing is written here.

    status: create | restore | merge | unchanged | skip | off
    """
    prev = next((m for m in (manifest or {}).get("modified", []) if m["path"] == SETTINGS_REL), None)
    plan: dict = {"status": "", "note": "", "add": [], "leftout": [], "original": {}, "text": "", "merged": {},
                  "new_file": False, "new_keys": [],
                  "owned": list(prev["added"]) if prev else [],
                  "created_file": bool(prev and prev["created_file"]),
                  "created_keys": list(prev["created_keys"]) if prev else []}
    if not enabled:
        plan.update(status="off", note="--no-permissions given; the settings file is not touched")
        return plan
    path = root / SETTINGS_REL
    if not path_is_safe(root, SETTINGS_REL):
        plan.update(status="skip", note="a symlink is in the path")
        return plan
    if path.is_symlink() or (path.exists() and not path.is_file()):
        plan.update(status="skip", note="exists and is not a regular file")
        return plan
    if path.exists():
        obj, text, problem = read_settings(path)
        if obj is None:
            plan.update(status="skip", note="left untouched: the file %s" % problem)
            return plan
        plan.update(original=obj, text=text)
    else:
        obj = {}
        plan.update(new_file=True, created_file=True)
    perms = obj.get("permissions", {})
    present = {canon_rule(r) for r in perms.get("allow", [])}
    refused = {canon_rule(r) for key in ("deny", "ask") for r in perms.get(key, [])}
    for rule in KIT_PERMISSIONS:
        if canon_rule(rule) in present:
            continue
        (plan["leftout"] if canon_rule(rule) in refused else plan["add"]).append(rule)
    plan["merged"], plan["new_keys"] = merge_permissions(obj, plan["add"]) if plan["add"] else (obj, [])
    plan["created_keys"] = sorted(set(plan["created_keys"]) | set(plan["new_keys"]))
    plan["owned"] = plan["owned"] + [r for r in plan["add"] if r not in plan["owned"]]
    if plan["new_file"]:
        plan["status"] = "restore" if prev else "create"
    else:
        plan["status"] = "merge" if plan["add"] else "unchanged"
    return plan


def verify_permissions(root: Path, manifest: Optional[dict]) -> Tuple[List[str], int, int]:
    """Check that every rule the manifest says was added is still in the settings file."""
    entry = next((m for m in (manifest or {}).get("modified", []) if m["path"] == SETTINGS_REL), None)
    if entry is None or not entry["added"]:
        return [], 0, 0
    path = root / SETTINGS_REL
    if not path_is_safe(root, SETTINGS_REL) or not path.is_file():
        return ["missing or unsafe: %s" % SETTINGS_REL], 0, len(entry["added"])
    obj, _, problem = read_settings(path)
    if obj is None:
        return ["%s %s" % (SETTINGS_REL, problem)], 0, len(entry["added"])
    allow = obj.get("permissions", {}).get("allow", [])
    missing = [r for r in entry["added"] if r not in allow]
    problems = ["permission rule no longer in %s (edited since install?): %s" % (SETTINGS_REL, r) for r in missing]
    return problems, len(entry["added"]) - len(missing), len(entry["added"])


# ---------------------------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------------------------

def choose_rules_target(root: Path, mode: str, manifest: Optional[dict]) -> Tuple[Optional[str], str]:
    """Pick where the rules file goes. Returns (relative path or None, explanation)."""
    if manifest and manifest.get("rules"):
        return manifest["rules"]["path"], "reusing the location recorded in the manifest"
    candidates = ["local", "rules"] if mode == "auto" else [mode]
    notes = []
    for key in candidates:
        rel = RULES_TARGETS[key]
        if (root / rel).exists() or (root / rel).is_symlink():
            notes.append("%s already exists" % rel)
            continue
        return rel, "; ".join(notes + ["using %s" % rel]) if notes else "using %s" % rel
    return None, "; ".join(notes) + "; rules NOT installed"


def build_plan(texts: Dict[str, str], rules_rel: Optional[str]) -> List[dict]:
    """Transform every source file into the content that will be written (nothing is written here)."""
    plan: List[dict] = []
    for kind, name, rel in source_files():
        text = transform(texts[rel], rules_rel)
        if kind == "rules":
            if rules_rel is None:
                continue
            text = RULES_HEADER + text
            target = rules_rel
        elif kind == "agent":
            target = ".claude/agents/%s%s.md" % (PREFIX, name)
            validate_component("agent", PREFIX + name, text, target)
        elif kind == "skill":
            target = ".claude/skills/%s%s/SKILL.md" % (PREFIX, name)
            validate_component("skill", PREFIX + name, text, target)
        else:
            target = ".claude/skills/%s%s/%s" % (PREFIX, name, rel.split("/%s/" % name, 1)[1])
        check_transformed(target, text)
        data = text.encode("utf-8")
        plan.append({"path": target, "kind": kind, "data": data, "sha256": sha256(data)})
    for item in plan:
        if not allowed_file(item["path"]):
            raise Abort("internal error: refusing to plan a path outside the allowlist: %s" % item["path"])
    return plan


def exclude_block(paths: List[str]) -> str:
    lines = [EXCLUDE_BEGIN] + ["/" + p for p in sorted(paths)] + [EXCLUDE_END]
    return "\n".join(lines) + "\n"


def ensure_dirs(root: Path, rel_parent: str, created: List[str]) -> None:
    current = root
    parts = Path(rel_parent).parts
    for index, part in enumerate(parts):
        current = current / part
        rel = "/".join(parts[: index + 1])
        if current.is_symlink():
            raise Abort("refusing to write through a symlinked folder: %s" % rel)
        if current.exists():
            if not current.is_dir():
                raise Abort("expected a folder but found a file: %s" % rel)
        else:
            if not ALLOWED_DIR_PATTERN.match(rel):
                raise Abort("internal error: refusing to create folder %s" % rel)
            current.mkdir()
            created.append(rel)


def print_report_header(mode: str, root: Path, kit: Optional[Path], dry: bool) -> None:
    out("sam-claude-kit bootstrap %s" % VERSION)
    out("Mode        : %s%s" % (mode, " (dry run, nothing will be written)" if dry else ""))
    out("Target repo : %s" % root)
    if kit is not None:
        out("Kit source  : %s" % kit)
    out()


def run_install(args: argparse.Namespace, root: Path) -> int:
    kit = Path(args.kit).expanduser().resolve()
    print_report_header("INSTALL", root, kit, args.dry_run)
    if kit == root:
        raise Abort("the kit folder and the target repository are the same folder. Run this from the repo you want to configure.")

    texts = read_kit(kit)
    out("Kit validation: OK (%d source files read; names, tool restrictions, frontmatter and content checked)" % len(texts))
    out()

    manifest = load_manifest(root)
    out("DETECTED (existing project configuration; none of it is modified)")
    for label, value in detect(root):
        out("  %-24s: %s" % (label, value))
    if manifest:
        out("  %-24s: yes, %d file(s) from an earlier run" % ("existing manifest", len(manifest["files"])))
    out()

    rules_rel, rules_note = choose_rules_target(root, args.rules_mode, manifest)
    out("RULES LOCATION: %s" % rules_note)
    if rules_rel is None:
        out("  Rules will not be installed. Remove or rename the existing file, or paste sam-claude-bootstrap.md instead.")
    out()

    plan = build_plan(texts, rules_rel)
    out("Content checks on planned files: OK (%d files; prefixed names, references and restrictions checked)" % len(plan))
    out()

    previous = {e["path"]: e for e in manifest["files"]} if manifest else {}
    perm = plan_permissions(root, manifest, not args.no_permissions)
    actions = []  # (status, item)
    for item in plan:
        target = root / item["path"]
        if not path_is_safe(root, item["path"]):
            actions.append(("blocked", item, "a symlink is in the path"))
        elif target.is_symlink() or (target.exists() and not target.is_file()):
            actions.append(("skip", item, "exists and is not a regular file"))
        elif not target.exists():
            actions.append(("restore" if item["path"] in previous else "create", item, ""))
        elif item["path"] in previous:
            current = sha256(target.read_bytes())
            if current != previous[item["path"]]["sha256"]:
                actions.append(("keep", item, "modified since it was installed"))
            elif current == item["sha256"]:
                actions.append(("unchanged", item, ""))
            else:
                actions.append(("update", item, "kit content changed"))
        else:
            actions.append(("skip", item, "already exists and was not created by this installer"))

    out("PLAN")
    for status, item, note in actions:
        extra = (" -- " + note) if note else ""
        out("  %-9s %-58s (%s, %s)%s" % (status, item["path"], item["kind"], human(len(item["data"])), extra))
    # Files an earlier run installed that this kit version no longer ships (for example a renamed agent).
    plan_paths = {i["path"] for i in plan}
    retired = []  # (status, manifest entry, note)
    for rel, entry in sorted(previous.items()):
        if rel in plan_paths:
            continue
        path = root / rel
        if not path_is_safe(root, rel):
            retired.append(("keep", entry, "a symlink is in the path"))
        elif not path.exists():
            retired.append(("gone", entry, "already absent"))
        elif not path.is_file():
            retired.append(("keep", entry, "not a regular file"))
        elif sha256(path.read_bytes()) != entry["sha256"]:
            retired.append(("keep", entry, "no longer part of the kit but modified since installed: delete it yourself if unwanted"))
        else:
            retired.append(("retire", entry, "no longer part of the kit; unmodified, so removed"))
    for status, entry, note in retired:
        out("  %-9s %-58s (%s) -- %s" % (status, entry["path"], entry.get("kind", "file"), note))
    exclude_paths = [i["path"] for s, i, _ in actions if s in ("create", "restore", "update", "unchanged", "keep")]
    exclude_paths += [e["path"] for s, e, _ in retired if s == "keep"]
    exclude_paths.append(MANIFEST_REL)
    if perm["created_file"]:
        exclude_paths.append(SETTINGS_REL)
    git_dir = root / ".git"
    block = exclude_block(exclude_paths)
    recorded_block = next((m for m in (manifest or {}).get("modified", []) if m["path"] == GIT_EXCLUDE_REL), None)
    if recorded_block is not None:
        if recorded_block["block"] != block and git_dir.is_dir():
            out("  %-9s %-58s (refresh the block this installer added earlier)" % ("update", GIT_EXCLUDE_REL))
    elif args.git_exclude:
        if git_dir.is_dir():
            out("  %-9s %-58s (hides the installed files from git status)" % ("append", GIT_EXCLUDE_REL))
        else:
            out("  %-9s %-58s (.git is not a folder; skipped)" % ("skip", GIT_EXCLUDE_REL))
    out("  %-9s %-58s (records what this run created)" % ("write", MANIFEST_REL))
    out()
    out("PERMISSIONS (narrow Bash allow rules, merged into %s)" % SETTINGS_REL)
    perm_what = {
        "create": "new file; it holds only these rules",
        "restore": "file was removed since the last run; recreated with these rules",
        "merge": "existing file; every other setting and rule is kept",
        "unchanged": "every rule is already present",
    }
    out("  %-9s %-58s%s" % (perm["status"], SETTINGS_REL, " (%s)" % (perm_what.get(perm["status"]) or perm["note"])))
    for rule in perm["add"]:
        out("            + %s" % rule)
    for rule in perm["leftout"]:
        out("            not added: %s is already in your deny or ask rules" % rule)
    out()

    blocked = [a for a in actions if a[0] == "blocked"]
    if blocked:
        raise Abort("refusing to continue: %s" % "; ".join("%s (%s)" % (a[1]["path"], a[2]) for a in blocked))

    if args.dry_run:
        out("DRY RUN COMPLETE. No files were written. Run again without --dry-run to install.")
        return 0

    before, truncated = snapshot(root)
    created_dirs: List[str] = list(manifest["dirs"]) if manifest else []
    files_out: List[dict] = [dict(e) for e in manifest["files"]] if manifest else []
    by_path = {e["path"]: e for e in files_out}
    done: List[Tuple[str, str]] = []
    new_dirs: List[str] = []
    settings_written = ""
    try:
        for status, item, _ in actions:
            target = root / item["path"]
            if status in ("create", "restore"):
                ensure_dirs(root, str(Path(item["path"]).parent.as_posix()), new_dirs)
                with open(str(target), "xb") as handle:
                    handle.write(item["data"])
                done.append((status, item["path"]))
            elif status == "update":
                tmp = target.with_name(target.name + ".tmp")
                tmp.write_bytes(item["data"])
                os.replace(str(tmp), str(target))
                done.append((status, item["path"]))
            if status in ("create", "restore", "update"):
                entry = {"path": item["path"], "sha256": item["sha256"], "bytes": len(item["data"]), "kind": item["kind"]}
                if item["path"] in by_path:
                    by_path[item["path"]].update(entry)
                else:
                    files_out.append(entry)
                    by_path[item["path"]] = entry
        for status, entry, _ in retired:
            if status == "retire":
                (root / entry["path"]).unlink()
                done.append(("retire", entry["path"]))
            if status in ("retire", "gone"):
                files_out = [e for e in files_out if e["path"] != entry["path"]]
                by_path.pop(entry["path"], None)
        modified = [dict(m) for m in manifest.get("modified", [])] if manifest else []
        for m in modified:
            if m["path"] == GIT_EXCLUDE_REL and m["block"] != block and git_dir.is_dir():
                exclude_path = root / GIT_EXCLUDE_REL
                current = exclude_path.read_bytes().decode("utf-8", "replace") if exclude_path.is_file() else ""
                old_snippet = ("\n" if m.get("added_newline") else "") + m["block"]
                if old_snippet in current:
                    new_snippet = ("\n" if m.get("added_newline") else "") + block
                    exclude_path.write_bytes(current.replace(old_snippet, new_snippet, 1).encode("utf-8"))
                    m["block"] = block
        if args.git_exclude and git_dir.is_dir() and not any(m["path"] == GIT_EXCLUDE_REL for m in modified):
            exclude_path = root / GIT_EXCLUDE_REL
            (git_dir / "info").mkdir(exist_ok=True)
            existing = exclude_path.read_bytes() if exclude_path.exists() else b""
            needs_newline = bool(existing) and not existing.endswith(b"\n")
            with open(str(exclude_path), "ab") as handle:
                handle.write((("\n" if needs_newline else "") + block).encode("utf-8"))
            modified.append({"path": GIT_EXCLUDE_REL, "type": "block", "block": block, "added_newline": needs_newline})
        if perm["status"] in ("create", "restore", "merge"):
            settings_path = root / SETTINGS_REL
            ensure_dirs(root, ".claude", new_dirs)
            if perm["new_file"]:
                with open(str(settings_path), "xb") as handle:
                    handle.write(dump_settings(perm["merged"], "").encode("utf-8"))
            else:
                write_atomic(settings_path, dump_settings(perm["merged"], perm["text"]).encode("utf-8"))
            settings_written = "new" if perm["new_file"] else "merged"
            modified = [m for m in modified if m["path"] != SETTINGS_REL]
            modified.append({"path": SETTINGS_REL, "type": "permissions", "added": perm["owned"],
                             "created_file": perm["created_file"], "created_keys": perm["created_keys"]})
        rules_entry = {"path": rules_rel, "mode": "local" if rules_rel == RULES_TARGETS["local"] else "rules"} if rules_rel else None
        ensure_dirs(root, ".claude", new_dirs)
        write_manifest(root, files_out, created_dirs + new_dirs, modified, rules_entry,
                       manifest["installed_at"] if manifest else None)
    except (OSError, Abort) as exc:
        out("INSTALL FAILED: %s" % exc)
        for status, rel in reversed(done):
            if status in ("create", "restore"):
                try:
                    (root / rel).unlink()
                except OSError:
                    pass
        try:
            if settings_written == "new":
                (root / SETTINGS_REL).unlink()
            elif settings_written == "merged":
                write_atomic(root / SETTINGS_REL, perm["text"].encode("utf-8"))
        except OSError:
            pass
        for rel in reversed(new_dirs):
            try:
                (root / rel).rmdir()
            except OSError:
                pass
        out("Rolled back the files and folders created by this run. Updated or retired files, if any, were not reverted.")
        return 1

    out("ACTIONS TAKEN")
    for status, item, note in actions:
        out("  %-9s %s%s" % (status if status not in ("create", "restore", "update") else status + "d", item["path"],
                            (" -- " + note) if note else ""))
    for status, entry, note in retired:
        out("  %-9s %s -- %s" % ("retired" if status == "retire" else status, entry["path"], note))
    if perm["status"] != "off":
        past = {"create": "created", "restore": "restored", "merge": "merged", "unchanged": "unchanged", "skip": "skipped"}
        out("  %-9s %s%s" % (past[perm["status"]], SETTINGS_REL,
                            (" -- " + perm["note"]) if perm["note"] else " (%d rule(s) added)" % len(perm["add"])))
    out()

    # Verification: nothing is reported as installed until it has been read back.
    kept_paths = {i["path"] for s, i, _ in actions if s == "keep"} | {e["path"] for s, e, _ in retired if s == "keep"}
    problems, verified, unverified = verify_manifest(root, load_manifest(root), skip=kept_paths)
    ours = {e["path"] for e in files_out} | {MANIFEST_REL} | {e["path"] for s, e, _ in retired if s in ("retire", "gone")}
    if perm["status"] in ("create", "restore", "merge"):
        ours.add(SETTINGS_REL)
        read_back, _, problem = read_settings(root / SETTINGS_REL)
        if read_back is None:
            problems.append("%s %s" % (SETTINGS_REL, problem))
        else:
            rest = strip_permissions(read_back, perm["add"], perm["new_keys"], perm["new_file"])
            if (rest if rest is not None else {}) != perm["original"]:
                problems.append("%s: content other than the added rules differs from what was there before" % SETTINGS_REL)
    after, _ = snapshot(root)
    checked, changed = compare_snapshots(before, after, ours)
    problems += changed
    skipped = [a for a in actions if a[0] in ("skip", "keep")] + [r for r in retired if r[0] == "keep"]
    skipped += [perm] if perm["status"] == "skip" else []

    out("VERIFICATION (files read back from disk)")
    out("  installed files verified : %d of %d" % (verified, len([e for e in files_out if e["path"] not in kept_paths])))
    out("  existing files unchanged : %d checked%s" % (checked - len(changed), " (first %d files only)" % SNAPSHOT_LIMIT if truncated else ""))
    if perm["status"] in ("create", "restore", "merge"):
        out("  settings file            : existing content identical, %d rule(s) added" % len(perm["add"]))
    for p in problems:
        out("  PROBLEM: %s" % p)
    out()
    out("COULD NOT BE VERIFIED BY THIS SCRIPT")
    for line in unverified:
        out("  - %s" % line)
    out()
    if not args.git_exclude and (root / ".git").exists():
        out("NOTE: the added files show up in `git status`. Re-run with --git-exclude to hide them locally, or add them to .gitignore yourself.")
        out()

    out("NEXT STEPS")
    out("  Start (or restart) Claude Code in this folder, then check: /memory, /agents, /permissions, and type / for skills.")
    if rules_rel == RULES_TARGETS["rules"]:
        out("  Rules are in .claude/rules/sam-rules.md and load automatically.")
    out("  Remove everything this installer added: python3 %s --uninstall" % sys.argv[0])
    out()
    if problems:
        out("RESULT: INSTALLED BUT NOT VERIFIED. %d problem(s) above. Run --uninstall, then report them." % len(problems))
        return 1
    if skipped:
        out("RESULT: PARTIAL. %d item(s) skipped or kept (see PLAN). Everything else is installed and verified (%d files)." % (len(skipped), verified))
        return 3
    out("RESULT: INSTALLED AND VERIFIED (%d files, manifest %s)" % (verified, MANIFEST_REL))
    return 0


# ---------------------------------------------------------------------------------------------
# Verify an installed copy
# ---------------------------------------------------------------------------------------------

def verify_manifest(root: Path, manifest: Optional[dict], skip: Optional[set] = None,
                    require_complete: bool = False) -> Tuple[List[str], int, List[str]]:
    """Read every manifest file back. Returns (problems, verified count, unverifiable notes)."""
    problems: List[str] = []
    verified = 0
    unverified = [
        "that Claude Code loads these files: start it here and run /memory, /agents, and / (this script cannot start Claude Code)",
        "which Claude Code version you run: CLAUDE.local.md and .claude/rules/ loading was observed on 2.1.329 only",
        "that Claude Code applies the permission rules: run /permissions in Claude Code to see them (syntax follows the current Claude Code documentation)",
    ]
    if manifest is None:
        return ["no manifest at %s: nothing to verify" % MANIFEST_REL], 0, unverified
    installed_names = set()
    for entry in manifest["files"]:
        rel = entry["path"]
        path = root / rel
        label = rel
        if skip and rel in skip:
            continue
        if not path_is_safe(root, rel) or not path.is_file():
            problems.append("missing or unsafe: %s" % rel)
            continue
        data = path.read_bytes()
        if sha256(data) != entry["sha256"]:
            problems.append("content differs from what was installed (edited since install?): %s" % rel)
            continue
        text = data.decode("utf-8", "replace")
        try:
            if entry["kind"] == "agent":
                name = Path(rel).stem
                validate_component("agent", name, text, label)
                installed_names.add(name)
            elif entry["kind"] == "skill":
                name = Path(rel).parent.name
                validate_component("skill", name, text, label)
                installed_names.add(name)
            check_transformed(label, text.replace(RULES_HEADER, ""))
        except Abort as exc:
            problems.append(str(exc))
            continue
        verified += 1
    problems += verify_permissions(root, manifest)[0]
    expected = {PREFIX + n for n in NAMES}
    if require_complete and not problems and installed_names != expected:
        problems.append("installed agent/skill set is incomplete: missing %s" % ", ".join(sorted(expected - installed_names)))
    return problems, verified, unverified


def run_verify(args: argparse.Namespace, root: Path) -> int:
    print_report_header("VERIFY", root, None, False)
    manifest = load_manifest(root)
    problems, verified, unverified = verify_manifest(root, manifest, require_complete=True)
    total = len(manifest["files"]) if manifest else 0
    out("installed files verified : %d of %d" % (verified, total))
    rules_ok, rules_total = verify_permissions(root, manifest)[1:]
    if rules_total:
        out("permission rules present : %d of %d in %s" % (rules_ok, rules_total, SETTINGS_REL))
    for p in problems:
        out("PROBLEM: %s" % p)
    out()
    out("COULD NOT BE VERIFIED BY THIS SCRIPT")
    for line in unverified:
        out("  - %s" % line)
    out()
    if problems:
        out("RESULT: NOT VERIFIED (%d problem(s))" % len(problems))
        return 1
    out("RESULT: VERIFIED (%d files match the manifest and pass structure and restriction checks)" % verified)
    return 0


# ---------------------------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------------------------

def run_uninstall(args: argparse.Namespace, root: Path) -> int:
    print_report_header("UNINSTALL", root, None, args.dry_run)
    manifest = load_manifest(root)
    if manifest is None:
        raise Abort("no manifest at %s: nothing to uninstall. No files were touched." % MANIFEST_REL, 1)
    before, truncated = snapshot(root)
    remove, keep, gone = [], [], []
    for entry in manifest["files"]:
        rel = entry["path"]
        path = root / rel
        if not path_is_safe(root, rel):
            keep.append((rel, "a symlink is in the path"))
        elif not path.exists():
            gone.append(rel)
        elif not path.is_file():
            keep.append((rel, "not a regular file"))
        elif sha256(path.read_bytes()) != entry["sha256"] and not args.force:
            keep.append((rel, "modified since install (use --force to remove anyway)"))
        else:
            remove.append(rel)

    out("PLAN")
    for rel in remove:
        out("  remove    %s" % rel)
    for rel, why in keep:
        out("  keep      %s -- %s" % (rel, why))
    for rel in gone:
        out("  gone      %s -- already absent" % rel)
    for m in manifest.get("modified", []):
        if m.get("type") == "permissions":
            out("  edit      %s -- remove only the %d permission rule(s) this installer added" % (m["path"], len(m["added"])))
        else:
            out("  edit      %s -- remove the block this installer added" % m["path"])
    out("  remove    %s -- once nothing else is left" % MANIFEST_REL)
    out()
    if args.dry_run:
        out("DRY RUN COMPLETE. No files were removed.")
        return 0

    removed: List[str] = []
    for rel in remove:
        (root / rel).unlink()
        removed.append(rel)

    block_notes: List[str] = []
    remaining_modified = []
    for m in manifest.get("modified", []):
        path = root / m["path"]
        done = False
        if m.get("type") == "permissions":
            if not path.exists():
                block_notes.append("%s is already absent; no permission rules to remove" % m["path"])
                continue
            obj, text, problem = read_settings(path) if path_is_safe(root, m["path"]) and path.is_file() else (None, "", "is not a safe regular file")
            if obj is None:
                block_notes.append("could not edit %s (the file %s); left as is" % (m["path"], problem))
                remaining_modified.append(m)
                continue
            rest = strip_permissions(obj, m["added"], m["created_keys"], m["created_file"])
            if rest is None:
                path.unlink()
                block_notes.append("removed %s (this installer created it and nothing else was in it)" % m["path"])
            else:
                write_atomic(path, dump_settings(rest, text).encode("utf-8"))
                block_notes.append("removed %d permission rule(s) from %s; everything else kept" % (len(m["added"]), m["path"]))
            continue
        if path.is_file():
            current = path.read_bytes().decode("utf-8", "replace")
            snippet = ("\n" if m.get("added_newline") else "") + m["block"]
            if snippet in current:
                path.write_bytes(current.replace(snippet, "", 1).encode("utf-8"))
                done = True
        if done:
            block_notes.append("removed block from %s" % m["path"])
        else:
            block_notes.append("could not find the exact block in %s; left as is" % m["path"])
            remaining_modified.append(m)

    kept_paths = {rel for rel, _ in keep}
    leftover_files = [e for e in manifest["files"] if e["path"] in kept_paths]
    if leftover_files or remaining_modified:
        write_manifest(root, leftover_files, manifest["dirs"], remaining_modified, manifest.get("rules"),
                       manifest["installed_at"])
    else:
        (root / MANIFEST_REL).unlink()

    # Folders: only ones recorded as created by this installer, deepest first, only if empty.
    for rel in reversed(manifest["dirs"]):
        path = root / rel
        if path.is_dir() and not path.is_symlink():
            try:
                path.rmdir()
            except OSError:
                pass
    if leftover_files or remaining_modified:
        write_manifest(root, leftover_files, [d for d in manifest["dirs"] if (root / d).is_dir()],
                       remaining_modified, manifest.get("rules"), manifest["installed_at"])

    after, _ = snapshot(root)
    ours = {e["path"] for e in manifest["files"]} | {MANIFEST_REL}
    ours |= {m["path"] for m in manifest.get("modified", []) if m.get("type") == "permissions"}
    checked, changed = compare_snapshots(before, after, ours)
    still_there = [rel for rel in removed if (root / rel).exists()]

    out("ACTIONS TAKEN")
    for rel in removed:
        out("  removed   %s" % rel)
    for note in block_notes:
        out("  edited    %s" % note)
    for rel, why in keep:
        out("  kept      %s -- %s" % (rel, why))
    out()
    out("VERIFICATION")
    out("  files removed and confirmed absent : %d of %d" % (len(removed) - len(still_there), len(removed)))
    out("  other files unchanged              : %d checked" % (checked - len(changed)))
    problems = ["still present: %s" % r for r in still_there] + changed
    for p in problems:
        out("  PROBLEM: %s" % p)
    out()
    if problems:
        out("RESULT: UNINSTALL NOT VERIFIED (%d problem(s))" % len(problems))
        return 1
    if keep or remaining_modified:
        out("RESULT: PARTIAL. %d file(s) kept and the manifest was updated to list them." % (len(keep) + len(remaining_modified)))
        return 3
    out("RESULT: UNINSTALLED AND VERIFIED. Everything the installer created is gone; no other file was touched.")
    return 0


# ---------------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="Install Sam's Claude Code Toolkit into the repository in the current folder.",
    )
    parser.add_argument("--kit", default=str(Path(globals().get("__file__", ".")).resolve().parent),
                        help="path to the extracted sam-claude-kit folder (default: the folder containing this script)")
    parser.add_argument("--dry-run", action="store_true", help="show every proposed change and write nothing")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--uninstall", action="store_true", help="remove the files recorded in the manifest")
    mode.add_argument("--verify", action="store_true", help="re-check an installed copy against the manifest")
    parser.add_argument("--rules-mode", choices=("auto", "local", "rules"), default="auto",
                        help="auto: CLAUDE.local.md, else .claude/rules/sam-rules.md. Never overwrites an existing file")
    parser.add_argument("--git-exclude", action="store_true",
                        help="add the installed paths to .git/info/exclude (local only; recorded and reversed on uninstall)")
    parser.add_argument("--no-permissions", action="store_true",
                        help="do not merge the pytest Bash allow rules into .claude/settings.local.json")
    parser.add_argument("--force", action="store_true", help="with --uninstall, also remove installed files you edited")
    parser.add_argument("--here", action="store_true", help="install in this folder even if it is inside a larger git repository")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if sys.version_info < (3, 8):
            raise Abort("Python 3.8 or newer is required")
        root = Path.cwd().resolve()
        problem = find_repo_root_problem(root, args.here)
        if problem:
            raise Abort(problem)
        if args.uninstall:
            return run_uninstall(args, root)
        if args.verify:
            return run_verify(args, root)
        return run_install(args, root)
    except Abort as exc:
        out("ERROR: %s" % exc)
        out("RESULT: NOT INSTALLED. No files were changed by this run." if not (args.uninstall or args.verify) else "RESULT: FAILED.")
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
