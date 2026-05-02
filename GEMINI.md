# JARVIS — Gemini Agent Rules

## Project Context
- **Stack**: FastAPI + WebSocket backend, Python 3.11+
- **Pipeline**: Wake Word → STT → LLM → TTS → Audio Output
- **Frontend**: Electron 32 + React 19 + Vite + Tailwind CSS v4
- **Full docs**: See `agent/` directory for architecture, stack, and skills

## Python

- `from __future__ import annotations` — every file, line 1
- Type hints mandatory on every function (params + return)
- f-strings only — no `.format()`, no `%`
- `match` statement over `if-elif` chains
- No bare `except:` — always specific exception type

## FastAPI

- Every route: `response_model` + `status_code` + `summary`
- Never return raw `dict` — always Pydantic model
- Dependency injection via `Annotated[T, Depends(...)]`
- Router prefix: `/api/v1/`
- Use `lifespan` context manager — never deprecated `@app.on_event`
- Background tasks via `BackgroundTasks` only

## WebSocket

- Always `try/except/finally` with `ws.close()`
- Close codes: `1000`=normal, `1011`=server error
- All messages validated via Pydantic before processing
- Heartbeat ping/pong — never assume connection alive

## Async

- All I/O = async — zero blocking calls
- `httpx.AsyncClient` — never `requests` library
- `asyncio.gather()` for concurrent ops
- `await asyncio.sleep()` — never `time.sleep()`

## Pydantic v2

- `model_validator` not `validator`
- `ConfigDict` not `class Config`
- `Field(...)` required, `Field(default=)` optional

## Logging

- `from core.logger import get_logger` → `logger = get_logger(__name__)`
- loguru only — zero `print()` calls
- `logger.exception()` inside `except` blocks always

## Error Handling

- Custom exceptions extend `JarvisError` in `core/error_handler.py`
- Hierarchy: `JarvisError` → `MicrophoneError`, `ModelError`, `APIError`, `ConfigError`
- Global handler in `core/error_handler.py`
- Pattern: log then raise — never silent catch

## Security

- All secrets via `.env` + `python-dotenv`
- No hardcoded keys anywhere
- Run `bandit -r backend/` before commit

## Testing

- `pytest` + `pytest-asyncio`
- `httpx.AsyncClient` for route testing
- Mock external APIs — never call real in tests

## File Structure

- Routers: `backend/api/routers/`
- Schemas: `backend/api/schemas.py`
- Services: `backend/services/`
- Infrastructure: `backend/infrastructure/`
- Core: `backend/core/`
- Plugins: `backend/plugins/`
- Tests: `backend/tests/`

## Quality Gates

```bash
ruff check --fix .
mypy --strict backend/
bandit -r backend/ -ll
pytest backend/tests/ -v
```

## Critical Context

- `core/orchestrator.py` is the singleton coordinator (~460 lines, decomposition planned)
- `services/voice/pipeline.py` owns the voice loop — state machine transitions are load-bearing
- `core/config.py` uses `@lru_cache` — call `load_config.cache_clear()` after any mutation
- Brain module exists in both `brain/` and `services/brain/` (migration in progress)
- The `THINKING → SPEAKING` state transition order prevents the "no audio" bug