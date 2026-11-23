---
name: test-strategy
description: "Decide what to test, at which layer, with which test doubles, then write focused pytest tests for a change. Use when planning tests for a feature, judging coverage, or reviewing test quality in a Python/FastAPI service."
---

# Test strategy

Copy the nearest existing test: runner, fixtures, client, naming, and location. Keep existing assertions intact. A failing assertion is evidence: change production code, not the expectation, unless the contract is meant to change.

## Choose the layer

- Pure logic: unit test.
- A FastAPI route: test through the client (`TestClient` or `httpx.AsyncClient`), because that exercises routing, validation, dependencies, and serialization together.
- Database writes, constraints, and transactions: against the repo's real test database strategy when it is cheap, not a different engine.
- Spend tests where failure costs most. Skip cases the change cannot affect.

## Choose the cases (aim for 5-8, not more)

For a new endpoint:

1. Happy path: status, body shape, persisted effect.
2. Validation failure: missing, wrong type, out of bounds (`422`).
3. Unauthenticated or forbidden, plus object or tenant isolation, when the repo has auth.
4. Not found or conflict.
5. A data-integrity edge case: duplicate, concurrent or repeated request, failed write leaves no partial data.
6. Boundaries of any list or limit: empty, one, max, over max.

A bug fix starts with a test that reproduces it.

## Test doubles

- Double only process boundaries: network, clock, randomness, slow I/O. Never double the unit under test.
- Use `app.dependency_overrides` for the auth user, settings, or external clients, and clear it afterwards.
- Prefer a fake over a mock. Assert the outcome a caller observes, not the sequence of internal calls.
- If a mocked boundary can drift from the real one, say how it is kept honest.

## Smells

Asserting implementation details, snapshots of large payloads, shared mutable fixtures, order dependence, fixed sleeps, real time, and retries that hide failures.

## Running

Run one new test, then its file, then the neighbouring test directory. Run the full suite only when it is fast. Report what each run proves, and check skip and xfail counts.

## Output

Before writing tests, give a short plan: layer, the cases above that apply, which doubles, and what is deliberately not tested. Then write the tests and run them.
