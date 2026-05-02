# JARVIS — Agent Rules

## Absolute Rules (Never Break)

1. **`from __future__ import annotations`** — first line of every Python file, no exceptions
2. **Type hints on every function** — parameters + return type, always
3. **No `print()` calls** — use `loguru` via `from core.logger import get_logger`
4. **No bare `except:`** — always catch specific exceptions
5. **No hardcoded secrets** — all API keys via `.env` + `python-dotenv`
6. **No blocking I/O** — all I/O must be async (`await`), use `httpx.AsyncClient` never `requests`
7. **No `time.sleep()`** — use `await asyncio.sleep()`

## Python Conventions

- f-strings only, never `.format()` or `%`
- `match` statement over long `if-elif` chains
- Use `asyncio.gather()` for concurrent operations
- Dataclasses or Pydantic models for all structured data — no raw dicts as function signatures

## FastAPI

- Every route must have: `response_model` + `status_code` + `summary`
- Never return a raw `dict` — always a Pydantic model
- Dependency injection via `Annotated[T, Depends(...)]`
- All routers use prefix `/api/v1/`
- Use `lifespan` context manager — never deprecated `@app.on_event`
- Background work via `BackgroundTasks` only

## WebSocket

- Always wrap handlers in `try/except/finally` with `ws.close()`
- Close codes: `1000` = normal, `1011` = server error
- Validate all incoming messages via Pydantic `WebSocketMessage` schema
- Implement heartbeat ping/pong — never assume connection is alive

## Pydantic v2

- Use `model_validator` (not deprecated `validator`)
- Use `ConfigDict` (not `class Config`)
- `Field(...)` for required fields, `Field(default=...)` for optional

## Logging

- Import pattern: `from core.logger import get_logger; logger = get_logger(__name__)`
- Use `logger.info()`, `logger.debug()`, `logger.warning()`, `logger.error()`
- Use `logger.exception()` inside `except` blocks (auto-captures traceback)
- Console output: human-readable with colors
- File output: JSON-serialized to `logs/jarvis.log` (10MB rotation, 14-day retention)

## Error Handling

- Custom exceptions extend `JarvisError` in `core/error_handler.py`
- Hierarchy: `JarvisError` → `MicrophoneError`, `ModelError`, `APIError`, `ConfigError`
- Pattern: **log then raise** — never silently swallow exceptions
- User-facing errors go through `to_user_error()` → `ErrorPayload`

## Testing

- Framework: `pytest` + `pytest-asyncio`
- Route testing: `httpx.AsyncClient`
- Always mock external APIs — never call real services in tests
- Test files in `backend/tests/test_*.py`
- Per-file ignores: `S101` (assert), `S110`, `S112`, `PT` rules disabled in tests

## File Organization

- One responsibility per file
- Routers in `backend/api/routers/`
- Schemas in `backend/api/schemas.py`
- Services in `backend/services/`
- Infrastructure adapters in `backend/infrastructure/`
- Core utilities in `backend/core/`
- Plugins in `backend/plugins/`

## Quality Gates (Run Before Commit)

```bash
# Lint + auto-fix
ruff check --fix .

# Type checking (strict)
mypy --strict backend/

# Security scan
bandit -r backend/

# Tests
pytest backend/tests/ -v
```

## What AI Must Never Do

- Never modify `.env` or `user_config.yaml` directly — use `save_setting()` / `save_all()`
- Never add a new dependency without documenting it
- Never create files outside the established directory structure
- Never skip `from __future__ import annotations`
- Never use `os.system()` or `subprocess.run()` without proper error handling
- Never store state in module-level mutable globals (use the singleton orchestrator)
- Never import from `frontend/` in `backend/` code or vice versa
