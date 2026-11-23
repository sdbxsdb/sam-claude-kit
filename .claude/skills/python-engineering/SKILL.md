---
name: python-engineering
description: "Python engineering depth for any repo: orienting in an unfamiliar codebase, typing, simple design, validation and edge cases, concurrency and async correctness, error boundaries, and pytest. Use when writing, reviewing, or debugging Python beyond style. The repo's tooling and framework win."
---

# Python engineering

The repo's existing style, formatter, linter, and test runner win. Match the nearest file's imports, quotes, async style, and where types live. Do not reformat existing code, and do not add a second tool. Framework detail is in `fastapi-engineering`. Pytest and asyncio detail is in [references/pytest-and-async.md](references/pytest-and-async.md); read it when writing async code or tests.

## Orient (then stop)

- Python version: `requires-python` in `pyproject.toml`, `.python-version`, CI matrix, Docker base image. Do not use syntax newer than the oldest supported version.
- Dependencies and manager: `pyproject.toml`, lock file, or `requirements*.txt`. The framework follows from the dependencies.
- Conventions: formatter, linter, type-checker config, and how strict the checker is.
- Test command: CI workflow, `Makefile`, `tox.ini`, or `[tool.pytest]` config. Note markers and the async plugin.
- Trace one path from the entry point to the boundary, the service, data access, and its test.

Use the existing environment. Do not create a virtualenv or install packages without asking.

## Style (for new code only)

- `snake_case` functions and variables, `PascalCase` classes, `UPPER_SNAKE` constants. Boolean-returning functions are predicates (`is_`, `has_`, `can_`). Do not return a bare `bool` as a success flag; raise or return the affected value.
- Annotate parameters and returns. Use `str | None`, `list[str]`, `dict[str, int]`; avoid `Optional`, `List`, `Dict` in new code unless the repo's Python is older. Avoid `Any`; narrow unknown values.
- Imports at the top, ordered stdlib, third-party, local. No wildcard imports. Prefer `pathlib.Path`.
- No mutable default arguments and no bare `except:`. Keep the repo's logger style. Never log secrets or PII.
- When surrounding code is async, new I/O is `async def` and awaited. Do not put a sync client on an async path.

## Design

- Keep the core as simple functions with one responsibility and I/O at the edges. A function callable with plain arguments is testable.
- Pass dependencies as parameters or constructor arguments from one composition point. Add a `Protocol` only for two implementations or a test boundary. No DI container, abstract base class, or module-level client unless the repo has them. Do not build a client in a default argument or at import time.
- Know the cost of the loop. Membership tests in a loop want a `set` or `dict`. Sort once. Use a generator for large data. Use `Counter`, `defaultdict`, `deque`, `heapq`, `bisect` where they fit. Measure before optimising.
- Use a dataclass, `NamedTuple`, or the repo's model for records, not loose dicts passed around.

## Validation and edge cases

- Validate at the boundary with the model the repo already uses and reject malformed input with a specific error.
- Check empty, `None`, duplicates, very large input, bad encoding, naive versus timezone-aware datetimes, and `Decimal` for money.
- Bound every read and every list the caller controls.
- Never `eval`, `exec`, or unpickle untrusted data. Avoid `subprocess(..., shell=True)` and unsafe `yaml.load`.

## Concurrency

- Identify the model first: asyncio, threads, processes, or a worker framework. Do not mix models without a reason.
- Shared mutable state needs a lock or confinement to one task. The GIL does not make compound operations atomic.
- Do not share a client, session, or cursor across threads or tasks unless its documentation says it is safe. Use `contextvars` for per-request state.
- On the event loop, blocking I/O goes through an async client or `asyncio.to_thread`. CPU-bound work goes to processes.
- Cancellation: re-raise `asyncio.CancelledError`, clean up in `finally` or an async context manager, put a timeout on every external call, and keep a reference to every task you create.

## Errors

- Raise specific exceptions and chain with `raise ... from`. Do not catch and return `None`.
- Handle an error at the layer that can act, and map domain errors to responses once at the boundary.
- Release resources with context managers. Never swallow with a broad `except`.

## Preserve behaviour

Keep public signatures, return shapes, exception types, and serialized formats. Add new parameters as optional keyword-only. Search for callers, including string and dynamic references, before changing or removing anything.

## Verification

Run the narrowest test first (one test, then the file).

- A green test with mocks proves the logic against the mocked contract, not the real integration.
- A passing type check does not prove runtime validation exists.
- Check skipped and xfail counts. An async test that never awaits the code under test proves nothing.
- A race or cancellation fix needs a test that forces the interleaving, not a sleep.
