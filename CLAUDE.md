## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

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