# JARVIS — Agent Rules

## Stack
- FastAPI + WebSocket + Python 3.11+
- Loguru for logging (never use print())
- Pydantic v2 models for all data shapes

## Code Rules
- Type hints on EVERY function — no exceptions
- FastAPI routes MUST have `response_model`
- WebSocket handlers MUST have try/except with close codes
- Never bare `except:` — always specific exception
- Async functions for all I/O operations

## Formatting
- Ruff for lint + format (line-length = 88)
- Run `ruff check --fix .` before commit

## Security
- No hardcoded secrets — use .env + python-dotenv
- Run `bandit -r backend/` for security scan

# JARVIS — Agent Rules

## Project
- FastAPI + WebSocket backend
- Python 3.11+
- Voice pipeline: STT → LLM → TTS

## Python
- `from __future__ import annotations` — every file line 1
- Type hints mandatory on every function
- f-strings only. No .format()
- Match statement over if-elif chains
- No bare `except:` — always specific exception

## FastAPI
- Every route: `response_model` + `status_code` + `summary`
- Never return raw dict — always Pydantic model
- Dependency injection via `Annotated`
- Router prefix: `/api/v1/`
- Use `lifespan` — never deprecated `@app.on_event`
- Background tasks via `BackgroundTasks` only

## WebSocket
- Always try/except/finally with `ws.close()`
- Close codes: 1000=normal, 1011=server error
- All messages validated via Pydantic before processing
- Heartbeat ping/pong — never assume connection alive

## Async
- All I/O = async. Zero blocking calls
- `httpx.AsyncClient` — never requests library
- `asyncio.gather()` for concurrent ops
- `await asyncio.sleep()` — never time.sleep()

## Pydantic v2
- `model_validator` not `validator`
- `ConfigDict` not class Config
- `Field(...)` required, `Field(default=)` optional

## Logging
- loguru only. Zero print()
- `logger.info/debug/warning/error/exception`
- `logger.exception()` inside except blocks always

## Error Handling
- Custom exception classes in `backend/exceptions.py`
- Global handler in main.py
- Log then raise — never silent catch

## Security
- All secrets via `.env` + python-dotenv
- No hardcoded keys anywhere
- Run `bandit -r backend/` before commit

## Testing
- pytest + pytest-asyncio
- `AsyncClient` from httpx for route testing
- Mock external APIs — never call real in tests

## File Structure
- One responsibility per file
- Router files in `backend/routers/`
- Schemas in `backend/schemas/`
- Services in `backend/services/`
- Utils in `backend/utils/`