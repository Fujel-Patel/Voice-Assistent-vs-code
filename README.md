# Jarvis Voice Assistant

> JARVIS (Just A Rather Very Intelligent System) — A desktop voice assistant built with Electron + React + Python, inspired by the AI from Iron Man.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Electron 32 + React 19 + Vite + Tailwind CSS |
| **Backend** | Python 3.12 + FastAPI + uvicorn (WebSocket IPC) |
| **Wake Word** | Porcupine (Picovoice) |
| **STT** | faster-whisper (local, offline) |
| **AI Brain** | Claude claude-sonnet-4-5 (Anthropic) |
| **TTS** | ElevenLabs (primary) + Piper (offline fallback) |
| **Storage** | aiosqlite (async SQLite) |
| **Testing** | pytest + vitest |

---

## Project Structure

```
jarvis/
├── frontend/          # Electron + React HUD
│   ├── electron/      # Main process + preload
│   │   ├── main.js
│   │   └── preload.js
│   └── src/
│       ├── components/ # HUD, Waveform, StatusRing, etc.
│       ├── hooks/      # useWebSocket, useVoiceState
│       ├── pages/      # HomePage, SettingsPage, etc.
│       ├── store/      # voiceStore, settingsStore
│       └── __tests__/ # vitest test suites
│
├── backend/           # Python FastAPI backend
│   ├── main.py        # Entry point (uvicorn)
│   ├── core/          # Logging, error handling, event bus, retry
│   ├── config/        # Config loader + default.yaml
│   ├── voice/         # Wake word, STT, TTS, state machine
│   ├── brain/         # Claude agent, intent, memory
│   ├── plugins/       # App launcher, web search, OS control, etc.
│   ├── storage/       # SQLite database
│   ├── services/      # Startup, clipboard
│   └── tests/         # pytest test suites
│
├── shared/            # IPC protocol shared between frontend & backend
│   ├── ipc_protocol.json   # Message schema
│   └── events.py           # Python event type enums
│
├── scripts/           # Dev tooling
│   ├── setup.sh       # One-command setup
│   ├── dev.sh         # Start dev environment
│   └── download_models.py  # Download Whisper models
│
├── .env.example       # API key template
└── README.md
```

---

## Quick Start

### 1. Install Prerequisites

- Python 3.12+
- Node.js 22+ (via NVM: `nvm use 22`)

### 2. Run Setup

```bash
cd jarvis
bash scripts/setup.sh
```

### 3. Add API Keys

```bash
cp .env.example .env
nano .env  # Add your API keys
```

Required keys:
- `CLAUDE_API_KEY` — [Anthropic Console](https://console.anthropic.com/)
- `ELEVENLABS_API_KEY` — [ElevenLabs](https://elevenlabs.io/)
- `PORCUPINE_API_KEY` — [Picovoice Console](https://console.picovoice.ai/) (free tier)

### 4. Download Whisper Model

```bash
cd backend
source .venv/bin/activate
cd ..
python3 scripts/download_models.py  # Downloads 'small' model by default
```

### 5. Start Development Environment

```bash
bash scripts/dev.sh
```

This starts:
- **Backend**: `http://localhost:8765` (Health: `http://localhost:8765/health`, WebSocket: `ws://localhost:8765/ws`)
- **Frontend**: `http://localhost:5173`

---

## Development Phases

| Phase | Description | Est. Time |
|-------|-------------|-----------|
| ✅ Phase 0 | Environment setup | Done |
| Phase 1 | Backend Foundation + Voice I/O (Wake word → STT) | ~18hrs |
| Phase 2 | Claude Brain + Intent Classification | ~21hrs |
| Phase 3 | Text-to-Speech Output | ~19hrs |
| Phase 4 | Frontend (Electron + React HUD) | ~30hrs |
| Phase 5 | OS Control + App Management | ~17.5hrs |
| Phase 6 | Screen Vision + OCR | ~15hrs |
| Phase 7 | Web Search + Fetch | ~17.5hrs |
| Phase 8 | Startup Service + System Tray | ~17hrs |
| Phase 9 | Settings UI + Configuration | ~24.5hrs |
| Phase 10 | Voice Authentication (Experimental) | ~23hrs |

See [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) and [architecture_review.md](../architecture_review.md) for full details.

---

## Running Tests

**Backend (pytest):**
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

**Frontend (vitest):**
```bash
cd frontend
npm test
```

---

## Architecture Decisions

Based on [architecture_review.md](../architecture_review.md):

- **Plugin system**: All capabilities (apps, web, OS) are plugins, not hardcoded modules
- **Streaming pipeline**: Claude → TTS streaming reduces latency from ~8s to ~1-2s
- **State machine**: Explicit `VoiceState` enum prevents race conditions in the audio pipeline
- **Security**: API keys stored in OS keyring (`keyring`), never in source code
- **Memory**: Short-term (deque) + long-term (SQLite + embeddings) conversation memory
- **Voice Auth**: Phase 10, experimental only — not used for security-critical authentication
