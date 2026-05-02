# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context
- **Name**: JARVIS (Just A Rather Very Intelligent System)
- **Type**: Desktop voice assistant
- **Stack**: Python 3.11+ / FastAPI / Electron / React 19
- **Backend Entry**: `backend/main.py` → uvicorn on port 8765
- **Frontend Entry**: `frontend/src/main.jsx` → Vite dev server on port 5173
- **Voice Pipeline**: Wake Word → STT → LLM → TTS → Audio Output
- **Frontend HUD**: Three.js visualization

## Development Commands
| Command | Purpose |
|---------|---------|
| `./scripts/dev.sh` | Start dev environment (backend on :8765, frontend on :5173) |
| `ruff check --fix .` | Lint and auto-fix Python code |
| `mypy --strict backend/` | Run type checking |
| `bandit -r backend/` | Security scan for vulnerabilities |
| `pytest backend/tests/ -v` | Run all tests with verbose output |

## Code Style

### Python
- `from __future__ import annotations` — line 1 of every file
- Type hints mandatory on all functions (parameters + return)
- f-strings only — no `.format()` or `%`
- `match` statements over `if-elif` chains
- No bare `except:` — always specify exception type

### FastAPI
- Every route: `response_model`, `status_code`, and `summary`
- Never return raw `dict` — use Pydantic models
- Dependency injection: `Annotated[T, Depends(...)]`
- Router prefix: `/api/v1/`
- Use `lifespan` context manager — avoid `@app.on_event`

### WebSocket
- Always `try/except/finally` with `ws.close()`
- Close codes: `1000`=normal, `1011`=server error
- Validate all messages via Pydantic before processing

### Async
- All I/O must be async — no blocking calls
- Use `httpx.AsyncClient` — never `requests`
- Use `asyncio.gather()` for concurrent operations
- Use `await asyncio.sleep()` — never `time.sleep()`

### Pydantic v2
- Use `model_validator` instead of `validator`
- Use `ConfigDict` instead of `class Config`
- Use `Field(...)` for required fields, `Field(default=...)` for optional

### Logging
- Import logger via `from core.logger import get_logger`
- Zero `print()` calls — use loguru exclusively
- Use `logger.exception()` inside `except` blocks

### Error Handling
- Custom exceptions extend `JarvisError` from `core/error_handler.py`
- Log then raise — no silent catches

### Security
- All secrets via `.env` + `python-dotenv`
- No hardcoded keys anywhere
- Run `bandit -r backend/` before committing

### Testing
- Use `pytest` + `pytest-asyncio`
- Test routes with `httpx.AsyncClient`
- Mock external APIs — never call real services in tests

## File Structure
- `backend/api/routers/`: API route handlers
- `backend/api/schemas.py`: Pydantic models for request/response
- `backend/services/`: Core service logic (voice, brain, etc.)
- `backend/infrastructure/`: External dependencies (audio, storage)
- `backend/core/`: Shared core utilities (config, event bus)
- `backend/plugins/`: Plugin interfaces and implementations
- `backend/tests/`: Unit and integration tests

## Critical Context
- `core/orchestrator.py`: Singleton coordinator for all subsystems
- `services/voice/pipeline.py`: Voice processing state machine (IDLE → WAKE_DETECTED → LISTENING → TRANSCRIBING → THINKING → SPEAKING → IDLE); `THINKING → SPEAKING` transition must occur only after LLM chunks are collected to prevent "text appears but no audio" bug
- `core/config.py`: Uses `@lru_cache`; call `load_config.cache_clear()` after config mutations
- Brain module: Partially migrated from `brain/` to `services/brain/`; both directories exist for backward compatibility

## Agent Knowledge Base
Full documentation lives in `/agent/`:
- `project.md`: Project overview, features, users
- `architecture.md`: Folder structure, data flow, key modules
- `stack.md`: Languages, frameworks, tools, versions
- `rules.md`: Coding conventions, AI must never do
- `tasks.md`: Active TODO list
- `skills/`: Specialized procedures (refactor, debug, review)