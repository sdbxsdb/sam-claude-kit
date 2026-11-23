# Pytest and asyncio detail

Use the repo's plugins, fixtures, and layout first. Copy the nearest test.

## Fixtures

- Fixtures go in the nearest `conftest.py`, not a global one.
- Keep scope as narrow as it can be. Widen it only for something expensive and immutable.
- Prefer a factory fixture over a fixture that returns a fully built object.
- Use `autouse` rarely. A hidden fixture hides what the test depends on.
- Use `tmp_path` and `monkeypatch` instead of touching real paths or the real environment.

## Parametrize

- Use `@pytest.mark.parametrize` with `ids=` for readable failures.
- One behaviour per parametrized test. Do not branch on the parameter inside the test.
- Parametrize the boundary cases: empty, one, many, maximum, invalid.

## Mocks

- Replace only process boundaries: network, clock, randomness, slow I/O. Patch where the name is used, not where it is defined.
- Use `autospec=True` or `create_autospec` so a signature change fails the test.
- Prefer a fake over a mock. Assert the outcome a caller observes, not the exact sequence of internal calls.
- Inject a clock instead of patching time.
- Use `pytest.raises(Type, match=...)` for errors.

## Async tests

- Use the async plugin the repo already uses (`pytest-asyncio` or `anyio`) and its configured mode.
- Use `AsyncMock` for awaited collaborators. Await the code under test.
- Wait on an `asyncio.Event`, a queue, or a barrier to control interleaving. Never `sleep` to wait for another task.
- Cancellation test: start the task, let it reach the await point, `task.cancel()`, await it expecting `CancelledError`, then assert cleanup ran.
- Race test: make two tasks meet at a barrier before the contested step, then assert the invariant, not the order.
- Put a timeout on async tests so a deadlock fails fast.

## Asyncio patterns

```python
async with asyncio.timeout(5):            # 3.11+
    result = await client.fetch(url)

async with asyncio.TaskGroup() as tg:     # 3.11+; all or nothing, children cancelled on error
    a = tg.create_task(load_a())
    b = tg.create_task(load_b())

sem = asyncio.Semaphore(10)               # bound concurrency
async def bounded(item):
    async with sem:
        return await process(item)

data = await asyncio.to_thread(blocking_read, path)   # keep the loop free
```

- Before 3.11 use `asyncio.wait_for` and `gather`, and handle partial failure explicitly.
- `gather(..., return_exceptions=True)` hides failures unless every result is checked.
- A queue between producer and consumer needs a `maxsize` so memory stays bounded.
- Shield only a short, must-finish cleanup. Do not shield long work.
