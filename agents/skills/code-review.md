# Skill: Code Review

## When to Use
- Reviewing new modules before merge
- Auditing existing code for standards compliance
- Pre-commit quality check

## Review Checklist

### 1. File Structure
- [ ] `from __future__ import annotations` is line 1
- [ ] File has a single responsibility
- [ ] File is in the correct directory per `agent/architecture.md`
- [ ] No circular imports (use `TYPE_CHECKING` guards if needed)

### 2. Type Safety
- [ ] All functions have complete type annotations (params + return)
- [ ] No `Any` types unless explicitly justified
- [ ] Pydantic models used for all structured data
- [ ] `mypy --strict` passes with 0 errors

### 3. Async Correctness
- [ ] All I/O operations are `async`
- [ ] No `time.sleep()` — only `await asyncio.sleep()`
- [ ] No `requests` library — only `httpx.AsyncClient`
- [ ] `asyncio.gather()` used for concurrent operations
- [ ] No blocking calls in async functions

### 4. Error Handling
- [ ] No bare `except:` clauses
- [ ] `logger.exception()` used inside `except` blocks
- [ ] Custom exceptions extend `JarvisError`
- [ ] Errors are logged *then* raised (never silently swallowed)
- [ ] WebSocket handlers have `try/except/finally` with `ws.close()`

### 5. Logging
- [ ] No `print()` calls anywhere
- [ ] Logger initialized as `logger = get_logger(__name__)`
- [ ] Appropriate log levels used (debug/info/warning/error)
- [ ] Sensitive data (API keys, tokens) never logged

### 6. FastAPI Routes
- [ ] `response_model` specified on every route
- [ ] `status_code` specified on every route
- [ ] `summary` specified on every route
- [ ] Route prefix is `/api/v1/`
- [ ] Dependencies injected via `Annotated[T, Depends(...)]`

### 7. Security
- [ ] No hardcoded API keys or secrets
- [ ] All secrets loaded from `.env` via `python-dotenv`
- [ ] No `os.system()` or unvalidated `subprocess` calls
- [ ] Input validated via Pydantic before processing

### 8. Testing
- [ ] New code has corresponding test file in `backend/tests/`
- [ ] External APIs are mocked — no real network calls
- [ ] `pytest-asyncio` used for async test functions
- [ ] Test assertions are specific (not just `assert result`)

## Automated Checks

Run all of these — every one must pass:

```bash
# Lint (auto-fix safe issues)
ruff check --fix .

# Type check (strict)
mypy --strict backend/

# Security scan
bandit -r backend/ -ll

# Tests
pytest backend/tests/ -v --tb=short
```

## Red Flags (Reject Immediately)

- `print()` calls in production code
- Bare `except:` without specific exception type
- `time.sleep()` in async code
- Raw `dict` return from FastAPI route (must be Pydantic model)
- Missing `from __future__ import annotations`
- Hardcoded API keys or secret values
- Imports from `frontend/` in `backend/` code
- New module-level mutable globals
