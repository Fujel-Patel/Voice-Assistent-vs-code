# JARVIS — Technology Stack

## Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ (target in pyproject.toml) |
| Framework | FastAPI | latest (via pip) |
| Server | uvicorn | latest |
| WebSocket | FastAPI WebSocket | built-in |
| Config | Pydantic v2 + PyYAML | `BaseModel`, `Field`, `ConfigDict` |
| Logging | Loguru | latest (via `get_logger()` wrapper) |
| HTTP Client | httpx | `AsyncClient` only |
| Database | aiosqlite | async SQLite |
| Environment | python-dotenv | `.env` file loading |

### AI / ML Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| LLM (primary) | Claude (Anthropic) | `claude-sonnet-4-20250514` |
| LLM (fallback 1) | Gemini (Google) | `gemini-2.5-flash` |
| LLM (fallback 2) | Groq | `llama-3.3-70b-versatile` |
| LLM (fallback 3) | OpenRouter | `openai/gpt-4o-mini` |
| LLM (fallback 4) | Ollama (local) | `llama3.2` |
| STT (primary) | Moonshine | Local, offline |
| STT (fallback) | Vosk | Local, offline |
| TTS (primary) | Edge TTS | Free, cloud |
| TTS (options) | ElevenLabs, Piper, Kokoro, Kitten | Cloud / local options |
| Wake Word | OpenWakeWord | Local, configurable sensitivity |
| Embeddings | SpeechBrain (optional) | Speaker verification |

### Quality Tools

| Tool | Purpose | Config Location |
|------|---------|-----------------|
| Ruff | Lint + format (line-length=88) | `pyproject.toml [tool.ruff]` |
| mypy | Static type checking (strict mode) | `pyproject.toml [tool.mypy]` |
| Bandit | Security scanning | `pyproject.toml [tool.bandit]` |
| pytest | Test runner | `backend/tests/` |
| pytest-asyncio | Async test support | via pytest |
| pre-commit | Git hooks | `.pre-commit-config.yaml` |

### Ruff Rule Selection

```toml
select = ["E", "F", "I", "N", "UP", "S", "B", "A", "C4", "PT"]
ignore = ["E501", "E402", "S110", "S603", "N802", "S112", "S311", "S607", "B023", "B904", "F821", "N801", "S104"]
```

## Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | ^19.2.4 |
| Bundler | Vite | ^8.0.4 |
| Desktop Shell | Electron | ^32.0.0 |
| Styling | Tailwind CSS v4 | ^4.2.2 |
| State Management | Zustand | ^4.5.7 |
| Routing | react-router-dom | ^7.6.1 |
| 3D Visualization | Three.js + @react-three/fiber | ^0.179.1 / ^9.6.0 |
| Animations | Framer Motion | ^12.38.0 |
| Icons | Lucide React | ^0.465.0 |
| CSS Utilities | clsx + tailwind-merge | ^2.1.1 / ^2.5.0 |
| Testing | Vitest + Testing Library | ^2.0.0 |
| Linting | ESLint + TypeScript ESLint | ^9.39.4 |

## Package Managers

| Layer | Manager | Lock File |
|-------|---------|-----------|
| Backend | pip | `requirements.txt` |
| Frontend | npm | `package-lock.json` |

## Runtime Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8765 | `http://localhost:8765` |
| WebSocket | 8765 | `ws://localhost:8765/ws` |
| Health Check | 8765 | `http://localhost:8765/api/v1/health` |
| Frontend Dev | 5173 | `http://localhost:5173` |
