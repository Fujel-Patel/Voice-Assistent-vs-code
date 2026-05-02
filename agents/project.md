# JARVIS — Project Overview

> **JARVIS** (Just A Rather Very Intelligent System) — A desktop voice assistant inspired by the AI from Iron Man.

## What It Does

JARVIS is a fully local-first voice assistant with a streaming AI pipeline. Users speak a wake word, JARVIS transcribes the speech, routes it through an LLM, and responds with synthesized voice — all while displaying a real-time HUD in an Electron desktop app.

### Core Pipeline

```
Wake Word → STT → LLM (Claude/Gemini/Groq) → TTS → Audio Output
```

The pipeline runs as a state machine (`IDLE → WAKE_DETECTED → LISTENING → TRANSCRIBING → THINKING → SPEAKING → IDLE`) to prevent race conditions and ensure clean audio handoff.

## Who Uses It

- **Primary user**: Fujel (solo developer, Linux desktop)
- **Target audience**: Power users who want a privacy-respecting, local-first voice assistant with LLM-powered natural language understanding
- **Use cases**: Hands-free app launching, web search, system control, conversational Q&A, file management, scheduling

## Core Features

| Feature | Status | Description |
|---------|--------|-------------|
| Wake Word Detection | ✅ | OpenWakeWord with configurable sensitivity |
| Speech-to-Text | ✅ | Moonshine (primary), Vosk (fallback), real-time streaming |
| Multi-Provider LLM | ✅ | Claude, Gemini, Groq, OpenRouter, Ollama with automatic fallback chain |
| Text-to-Speech | ✅ | Edge TTS (primary), ElevenLabs, Piper, Kokoro, Kitten with streaming |
| Plugin System | ✅ | App launcher, web search, file manager, system control, scheduler, screen reader |
| Memory System | ✅ | Short-term (deque) + Long-term (SQLite + embeddings) conversation memory |
| Voice Auth | ⚠️ | Experimental speaker verification + liveness detection |
| Electron HUD | ✅ | React 19 + Three.js waveform visualization, settings UI, dark mode |
| Always-On Mode | ✅ | Continuous listening with auto-restart after each response |
| Access Control | ✅ | Intent-based permissions with challenge/PIN fallback |

## Entry Points

| Entry | Path | Purpose |
|-------|------|---------|
| Backend | `backend/main.py` | Starts uvicorn on `0.0.0.0:8765` |
| FastAPI App | `backend/api/fastapi_app.py` | Mounts routers, CORS, lifespan |
| Frontend | `frontend/src/main.jsx` | React app root |
| Electron | `frontend/electron/main.js` | Desktop window shell |
| Dev Script | `scripts/dev.sh` | Starts both backend + frontend |

## Configuration

- **Backend config**: `backend/core/default.yaml` → `backend/core/user_config.yaml` → `.env` overrides
- **Config model**: `backend/core/config.py` → `JarvisConfig` (Pydantic v2)
- **API keys**: All via `.env` + `python-dotenv` (never hardcoded)
- **Frontend settings**: Zustand stores persisted via `electron-store`
