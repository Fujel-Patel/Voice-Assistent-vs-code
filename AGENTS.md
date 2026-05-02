# JARVIS — Agent Configuration

> This file is the universal entry point for all AI agents working on this project.

## Project

- **Name**: JARVIS (Just A Rather Very Intelligent System)
- **Type**: Desktop voice assistant
- **Stack**: Python 3.11+ / FastAPI / Electron / React 19
- **Backend Entry**: `backend/main.py` → uvicorn on port 8765
- **Frontend Entry**: `frontend/src/main.jsx` → Vite dev server on port 5173

## Key Paths

| Path | Purpose |
|------|---------|
| `backend/core/orchestrator.py` | Central coordinator (singleton, ~18K lines) |
| `backend/services/voice/pipeline.py` | Voice pipeline (wake→STT→LLM→TTS, ~35K lines) |
| `backend/services/brain/agent.py` | Multi-provider LLM client |
| `backend/core/config.py` | Pydantic config model + YAML/env loader |
| `backend/core/event_bus.py` | Async pub/sub event system |
| `backend/api/fastapi_app.py` | FastAPI app factory |
| `backend/plugins/base.py` | Plugin ABC + result model |

## Agent Knowledge Base

Detailed documentation lives in `/agent/`:

| File | Contents |
|------|----------|
| [agent/project.md](agent/project.md) | What the project does, who uses it, features |
| [agent/architecture.md](agent/architecture.md) | Folder structure, data flow, key modules |
| [agent/stack.md](agent/stack.md) | Languages, frameworks, tools, versions |
| [agent/rules.md](agent/rules.md) | Coding conventions, what AI must never do |
| [agent/tasks.md](agent/tasks.md) | Active TODO list with pending/completed items |
| [agent/skills/](agent/skills/_index.md) | Specialized procedures (refactor, debug, review) |

## Universal Rules

1. `from __future__ import annotations` — line 1 of every Python file
2. Type hints on every function — no exceptions
3. `loguru` only — zero `print()` calls
4. No bare `except:` — always specific exceptions
5. No hardcoded secrets — `.env` + `python-dotenv`
6. All I/O is async — no blocking calls
7. Run quality gates before committing: `ruff check --fix . && mypy --strict backend/ && pytest backend/tests/ -v`

## Pipeline Warning

The voice pipeline state machine (`IDLE → WAKE_DETECTED → LISTENING → TRANSCRIBING → THINKING → SPEAKING → IDLE`) is **load-bearing**. The `THINKING → SPEAKING` transition must only happen after LLM chunks are collected. Breaking this order causes the "text appears but no audio" bug. See `agent/skills/debug.md` for troubleshooting.

## Development Commands

| Command | Purpose |
|---------|---------|
| `./scripts/dev.sh` | Start dev environment (backend on :8765, frontend on :5173) |
| `ruff check --fix .` | Lint + auto-fix |
| `mypy --strict backend/` | Type checking |
| `pytest backend/tests/ -v` | Run tests |
| `bandit -r backend/` | Security scan |

## Critical Architecture

The voice pipeline is the core processing loop that handles real-time voice processing. Changes to the core orchestrator should be made carefully to avoid breaking the pipeline flow.
