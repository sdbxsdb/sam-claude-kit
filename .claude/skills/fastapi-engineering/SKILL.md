---
name: fastapi-engineering
description: "FastAPI patterns for adding or changing endpoints: routers, dependencies and auth, Pydantic request and response models, validation, sync versus async, HTTP status and error handling, SQLAlchemy sessions and transactions, lifespan, and TestClient testing. Use only when the repo depends on FastAPI; never introduce FastAPI into another project."
---

# FastAPI engineering

The repo's existing conventions win. Copy the nearest router, schema, and test. Use this when writing or reviewing FastAPI code. Orientation steps are in `python-engineering`.

## Orient

Find the app factory, how routers are included, shared dependencies, the Pydantic major version (v1 and v2 differ: `model_validator` and `ConfigDict` versus `validator` and `class Config`), how settings load, and how the DB session is created.

## Endpoints

- `async def` runs on the event loop. Blocking code inside it (sync DB driver, `requests`, file reads, `time.sleep`) stalls every request. A plain `def` runs in a threadpool. Use `async def` only when the body awaits async I/O, and match what the neighbouring routes do with the DB.
- Follow the neighbouring routes for `response_model` and `status_code`; explicitly declare them when adding a contract and consistent with the codebase. Typical defaults when the existing API has no established convention: use `201` for create, `204` for delete with no body, `404` for missing, `409` for conflict or uniqueness violation, `422` for validation (automatic), `401` unauthenticated, `403` authenticated but not permitted.
- Keep request, response, and DB models separate so a column change cannot leak into the contract or expose internal fields. In a response model, whitelist fields.
- Put bounds in the request model: list `limit` with `ge=1, le=<max>`, `offset` or cursor, string `max_length`, numeric ranges. Never return an unbounded list.
- Use `APIRouter` with the same prefix and tags convention as the neighbours. Register the router where the others are registered.
- Choose the verb and URL shape the repo already uses. `POST` create, `GET` read, `PATCH` partial update (explicit about `null` versus absent via `model_dump(exclude_unset=True)`), `PUT` replace, `DELETE` idempotent.

## Pydantic validation

- Validate at the boundary and use typed fields: `EmailStr`, `UUID`, `Literal`/`Enum`, `datetime` (timezone-aware), `Decimal` for money, `Field(min_length=..., max_length=..., ge=..., pattern=...)`.
- Cross-field rules go in a model validator, not in the handler.
- Mutable defaults use `Field(default_factory=...)`.
- Forbid unexpected fields when the repo does (`extra="forbid"`).
- Do not build responses from raw ORM objects unless `from_attributes=True` (v2) or `orm_mode` (v1) is the repo's pattern.

## Dependencies and auth

- Use `Depends` for per-request resources: DB session (with `yield`), current user, settings, clients. Do not construct them in the handler.
- Reuse the repo's current-user and permission dependencies. Apply authorization to the route or router, and check on every read or write of private data, including object-level checks (the caller owns or may access this record) and tenant scoping in the query itself. Hiding something in the response is not authorization.
- Do not change auth, CORS, or security headers unless the feature requires it. Propose the change, then wait.
- Create long-lived clients once in `lifespan`, not per request or at import time.
- Background tasks only for work that may be lost on a crash. Durable work goes to the repo's queue.

## Errors

- Raise `HTTPException` or the repo's domain exception, and map domain errors to responses in one place (an exception handler). Use the repo's error body shape. Never leak stack traces, SQL, or internal ids in messages.
- Bad input is a `4xx`, never a `500`. A missing record is `404`, and do not reveal whether an inaccessible record exists when the repo hides that (return `404`).
- A client disconnect can cancel the handler. Keep cleanup in `finally` or a context manager.

## Database and transactions (SQLAlchemy if the repo uses it)

- One session per request, from a dependency. Commit or roll back at one known place (the service or the dependency), following the repo. Do not share a session across tasks.
- Match the repo's SQLAlchemy style (1.x `session.query` or 2.0 `select()`), and its sync or async session. An `AsyncSession` needs `await` on `execute`, `commit`, `refresh`, and `selectinload` for relationships (lazy loading fails in async).
- Keep transactions short and make no network call inside one.
- Enforce uniqueness and integrity with constraints. Catch `IntegrityError`, roll back, and return `409`. Do not check-then-insert.
- Read-modify-write that can race: `with_for_update()` or a version column. Idempotent create: a unique key plus `ON CONFLICT`, or catch the conflict.
- Avoid N+1: `selectinload` or `joinedload`, or one query with `IN`. Paginate with a stable sort that has a unique tiebreaker.
- Never build SQL by string formatting. Use bound parameters or the ORM.
- Propose a material product-schema change or migration before executing it; safe initialization of a verified disposable development DB may proceed under the main safety rules.

## Testing

- `TestClient(app)` for sync, `httpx.AsyncClient(transport=ASGITransport(app=app))` for async paths. Copy the repo's client fixture.
- Replace dependencies with `app.dependency_overrides[dep] = fake` and clear it after each test (fixture teardown).
- For each new route test: success, validation failure (`422`), unauthenticated or forbidden, not found, and a conflict or integrity case if it writes.
- Assert status code, response body shape, and the persisted effect. Check that a failed write leaves no partial data.
- Use the repo's database strategy (transaction rollback per test, test database, or in-memory fake). Do not swap databases for convenience.
- Check the OpenAPI output (`app.openapi()`) only when request or response shapes changed.

```python
def test_create_item_rejects_negative_quantity(client):
    resp = client.post("/items", json={"name": "x", "quantity": -1})
    assert resp.status_code == 422
```
