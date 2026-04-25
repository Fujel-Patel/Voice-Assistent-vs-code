# 🔍 Jarvis Voice Assistant — Architecture Review

## Overall Verdict

Your plan is **well-structured and ambitious**. The phased approach is smart, and the tech choices are mostly solid. However, there are **critical gaps** in security, error handling, testing, and some architectural decisions that could cause pain later. Below is a detailed breakdown.

---

## ✅ What's Already Strong

| Area | Why It Works |
|------|-------------|
| **Phased development** | 10 clear phases with focused scope — great for incremental delivery |
| **IPC via WebSocket** | Clean separation between Python backend and Electron frontend |
| **Wake word → STT pipeline** | Porcupine + Whisper is a proven combo |
| **Intent classification via Claude** | Flexible and avoids brittle regex-based routing |
| **Shared IPC protocol file** | Good practice for contract-driven development |

---

## 🔴 Critical Issues to Fix

### 1. Security — API Keys Are Exposed

> [!CAUTION]
> Your plan stores API keys as plain constants. If the Electron app ships with keys baked in, **anyone can extract them** from the app binary.

**Fix:**
- Store keys in an OS-level credential manager (e.g., `keytar` for Electron, `keyring` for Python)
- Add an `env/` or `.env` file with `python-dotenv`, and **never commit it**
- Add a `secrets_manager.py` module under `backend/`

### 2. Security — Lock Screen Voice Unlock Is Dangerous

> [!CAUTION]
> Voice-based unlock using speaker embeddings alone is **not secure enough** for OS-level authentication. Voice can be replayed from recordings or deepfaked.

**Fix:**
- **Remove lock-screen unlock from MVP** — treat it as an experimental Phase 11+
- If you keep it, add **liveness detection** (random challenge phrase) + **confidence threshold tuning**
- Consider making it a "convenience unlock" with a secondary PIN fallback, not a true security gate

### 3. No Error Handling / Resilience Strategy

Your plan has **zero mention** of what happens when:
- Claude API is down or rate-limited
- Microphone is disconnected mid-recording
- WebSocket connection drops between frontend ↔ backend
- TTS API fails (and Coqui fallback also fails)
- Whisper produces garbage transcriptions

**Fix:** Add a `backend/core/` layer:
```
backend/core/
├── error_handler.py    # Central error handling + user-friendly error messages
├── retry.py            # Exponential backoff for API calls
├── health_check.py     # Periodic checks on mic, APIs, WebSocket
└── fallback_chain.py   # Graceful degradation strategy
```

### 4. No Testing Strategy Anywhere

> [!WARNING]
> A project this complex with **zero test infrastructure** will become unmaintainable fast.

**Fix:** Add from Phase 1:
```
backend/tests/
├── test_stt.py
├── test_intent.py
├── test_tts.py
├── test_os_bridge.py
└── conftest.py          # Shared fixtures (mock audio, mock Claude responses)

frontend/src/__tests__/
├── HUD.test.jsx
├── WebSocket.test.js
└── StatusRing.test.jsx
```
- Use `pytest` + `pytest-asyncio` for backend
- Use `vitest` or `jest` for frontend
- **Mock all external APIs** in tests (Claude, ElevenLabs, Brave)

---

## 🟡 Architectural Improvements Needed

### 5. Missing Plugin / Extension System

Your `control/` module hard-codes every capability (apps, files, web, screen). This will become a monolith quickly.

**Improve:** Design a plugin architecture:
```python
# backend/plugins/base.py
class JarvisPlugin:
    name: str
    intents: list[str]  # What intents this plugin handles
    
    async def execute(self, intent: dict, context: dict) -> dict:
        raise NotImplementedError

# backend/plugins/app_launcher.py
class AppLauncherPlugin(JarvisPlugin):
    name = "app_launcher"
    intents = ["open-app", "close-app"]
    
    async def execute(self, intent, context):
        ...
```
This lets you **add new capabilities without touching core code**.

### 6. Memory / Context Management Is Too Simple

Your plan mentions "rolling conversation history in SQLite" — this will hit limits fast:
- Claude has a context window limit
- Raw conversation dumps are token-expensive
- No distinction between short-term and long-term memory

**Improve:**
```
backend/brain/memory/
├── short_term.py       # Last N turns (in-memory, fast)
├── long_term.py        # Summarized past sessions (SQLite + embeddings)
├── context_builder.py  # Assembles optimal context for each Claude call
└── summarizer.py       # Periodically summarizes old conversations
```
- Use **embedding-based retrieval** (e.g., `sentence-transformers`) to pull relevant past context
- Summarize old conversations periodically to save tokens
- Set a **token budget** per Claude call and trim context accordingly

### 7. IPC Protocol Needs More Structure

A single `ipc_protocol.json` file isn't enough. You need:

```
shared/
├── ipc_protocol.json       # Message schema
├── events.py               # Python enum of all event types
├── events.ts               # TypeScript enum (mirrored)
└── validators/
    ├── validate_message.py
    └── validate_message.ts
```

Define clear message types:
```json
{
  "type": "voice_state_change",
  "payload": { "state": "listening" | "thinking" | "speaking" | "idle" },
  "timestamp": "ISO8601",
  "request_id": "uuid"
}
```

### 8. Missing Logging & Observability

No logs = blind debugging. Add:
```
backend/core/
├── logger.py           # Structured logging (JSON format)
└── metrics.py          # Response times, error rates, API usage tracking
```
- Use Python's `structlog` or `loguru`
- Log every Claude API call with token counts (for cost tracking!)
- Frontend should log WebSocket events to a debug console

### 9. Configuration Management Is Scattered

Your plan mentions a settings page but no config architecture.

**Improve:**
```
backend/config/
├── default.yaml        # Default settings
├── user_config.yaml    # User overrides (generated at runtime)
└── config_loader.py    # Merges defaults + user overrides + env vars
```
- Use `pydantic-settings` for type-safe configuration
- Single source of truth for all settings, not scattered across modules

### 10. Audio Pipeline Needs a Queue / State Machine

Your audio flow (wake word → record → transcribe → respond → speak) has race conditions:
- What if user speaks while TTS is playing?
- What if two wake words are detected in quick succession?
- What if transcription takes 5 seconds and user interrupts?

**Improve:** Add an explicit state machine:
```python
# backend/voice/state_machine.py
class VoiceState(Enum):
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"

class VoicePipeline:
    state: VoiceState
    
    async def handle_interrupt(self):
        """User spoke while Jarvis was speaking — stop TTS, start listening"""
        ...
    
    async def transition(self, new_state: VoiceState):
        """Validated state transitions with event emission"""
        ...
```

---

## 🟡 Tech Stack Suggestions

### 11. Reconsider Some Tech Choices

| Current Choice | Issue | Suggested Alternative |
|---|---|---|
| **Electron 28** | Heavy (~200MB RAM idle). For an always-on assistant, this matters | Consider **Tauri 2.0** (Rust-based, ~10MB RAM) with React frontend. If you stay with Electron, use `v8-compile-cache` and lazy loading |
| **Tailwind CSS** | Fine, but HUD animations need custom CSS/Canvas anyway | Keep Tailwind for layout, but use **Three.js or Canvas API** for the arc reactor HUD — Tailwind alone won't give you that Iron Man feel |
| **SQLite via SQLAlchemy** | SQLAlchemy is overkill for simple key-value + conversation storage | Use **`aiosqlite`** directly for async compatibility, or consider **LevelDB** for faster key-value operations |
| **pyautogui** | Fragile, no Wayland support on Linux, requires active display | Add **`xdotool`** fallback for Linux, or use **`pynput`** for cross-platform input |
| **Brave Search API** | Paid API, limited free tier | Add **DuckDuckGo Instant Answers** (free, no API key) as fallback |

### 12. Whisper Model Selection Strategy

Your plan says "OpenAI Whisper (local)" but doesn't specify which model size. This matters enormously:

| Model | RAM | Speed | Accuracy |
|-------|-----|-------|----------|
| `tiny` | ~1GB | ~32x realtime | Low |
| `base` | ~1GB | ~16x realtime | Okay |
| `small` | ~2GB | ~6x realtime | Good |
| `medium` | ~5GB | ~2x realtime | Great |
| `large-v3` | ~10GB | ~1x realtime | Best |

**Recommendation:** 
- Use **`faster-whisper`** (CTranslate2-based) instead of vanilla Whisper — it's **4x faster** with the same accuracy
- Default to `small` model, let users choose in settings
- Add a `backend/voice/model_manager.py` to handle model downloads and switching

---

## 🟡 Missing Features to Consider

### 13. Features Your Plan Doesn't Address

| Feature | Why It Matters |
|---------|---------------|
| **Hotkey activation** | Not everyone wants to say a wake word. Add `Ctrl+Space` or customizable hotkey |
| **Multi-monitor support** | Screen vision module assumes single screen |
| **Clipboard integration** | "Read what I copied" / "Summarize my clipboard" is a killer feature |
| **Task queue / scheduling** | "Remind me in 30 minutes" needs a scheduler (use `APScheduler`) |
| **Notification system** | Jarvis should proactively notify (e.g., "Your download finished") |
| **Streaming responses** | Claude supports streaming — don't wait for full response before TTS starts |
| **Offline mode** | What works without internet? Document this clearly |
| **Update mechanism** | How does the user update Jarvis? Add `electron-updater` for frontend |

### 14. Streaming Pipeline (Big Performance Win)

Currently your flow is sequential:
```
Record → Full Transcription → Full Claude Response → Full TTS → Play
```

This means **long pauses**. Instead, implement streaming:
```
Record → Stream to Whisper → Stream text to Claude → Stream Claude output → 
Stream to TTS → Play audio chunks as they arrive
```

This reduces perceived latency from ~5-8 seconds to ~1-2 seconds.

---

## 🟡 Phase Order Adjustments

### 15. Reorder Some Phases

Your current order has Phase 7 (Voice Auth + Lock Screen) before Phase 8 (Frontend). This means:

- You're building a dangerous security feature before you have a UI to configure it
- You can't visually test the auth flow

**Suggested reorder:**
1. ✅ Phase 1 — Backend + Voice I/O
2. ✅ Phase 2 — Claude brain + intent
3. ✅ Phase 3 — TTS output
4. **⬆️ Phase 8 → Move to Phase 4** — Build frontend early so you can visually debug everything
5. ✅ Phase 4 → becomes Phase 5 — OS control
6. ✅ Phase 5 → becomes Phase 6 — Screen vision
7. ✅ Phase 6 → becomes Phase 7 — Web fetch
8. ✅ Phase 9 → becomes Phase 8 — Startup + tray
9. ✅ Phase 10 → becomes Phase 9 — Settings UI
10. ✅ Phase 7 → becomes Phase 10 — Voice auth (last, experimental)

---

## 📋 Revised Codebase Structure (Recommended)

```
jarvis/
├── frontend/                    # Electron/Tauri + React
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── HUD.jsx
│   │   │   ├── Waveform.jsx
│   │   │   ├── ChatHistory.jsx
│   │   │   ├── StatusRing.jsx
│   │   │   └── SettingsPanel.jsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js    # ← NEW: Reusable WS hook
│   │   │   └── useVoiceState.js   # ← NEW: Voice state management
│   │   ├── pages/
│   │   ├── store/
│   │   ├── utils/
│   │   │   └── ipc_validator.ts   # ← NEW: Message validation
│   │   └── App.jsx
│   ├── electron/
│   └── package.json
│
├── backend/
│   ├── main.py
│   ├── core/                      # ← NEW: Cross-cutting concerns
│   │   ├── error_handler.py
│   │   ├── logger.py
│   │   ├── retry.py
│   │   ├── health_check.py
│   │   └── event_bus.py           # ← NEW: Internal pub/sub
│   ├── config/                    # ← NEW: Centralized config
│   │   ├── default.yaml
│   │   └── config_loader.py
│   ├── voice/
│   │   ├── listener.py
│   │   ├── stt.py
│   │   ├── tts.py
│   │   ├── state_machine.py       # ← NEW: Voice pipeline states
│   │   ├── model_manager.py       # ← NEW: Whisper model management
│   │   └── audio_queue.py         # ← NEW: Audio playback queue
│   ├── brain/
│   │   ├── claude_agent.py
│   │   ├── intent.py
│   │   └── memory/                # ← EXPANDED
│   │       ├── short_term.py
│   │       ├── long_term.py
│   │       └── context_builder.py
│   ├── plugins/                   # ← NEW: Plugin system
│   │   ├── base.py
│   │   ├── app_launcher.py
│   │   ├── screen_reader.py
│   │   ├── web_search.py
│   │   ├── file_manager.py
│   │   └── scheduler.py           # ← NEW: Reminders/timers
│   ├── storage/
│   │   ├── db.py
│   │   └── migrations/            # ← NEW: Schema versioning
│   ├── services/
│   │   ├── startup.py
│   │   └── clipboard.py           # ← NEW
│   ├── tests/                     # ← NEW: Test suite
│   │   ├── conftest.py
│   │   ├── test_stt.py
│   │   ├── test_intent.py
│   │   └── test_plugins.py
│   └── requirements.txt
│
├── shared/
│   ├── ipc_protocol.json
│   └── events.py
│
├── scripts/                       # ← NEW: Dev tooling
│   ├── setup.sh                   # One-command setup
│   ├── download_models.py         # Download Whisper models
│   └── dev.sh                     # Start both frontend + backend
│
├── .env.example                   # ← NEW: Template for API keys
├── .gitignore
└── README.md
```

---

## Summary of Recommendations

| Priority | Issue | Action |
|----------|-------|--------|
| 🔴 Critical | API key security | Add credential manager + `.env` |
| 🔴 Critical | Lock screen unlock | Move to last phase, add liveness detection |
| 🔴 Critical | No error handling | Add `core/` module with retry + fallbacks |
| 🔴 Critical | No tests | Add test infrastructure from Phase 1 |
| 🟡 Important | No plugin system | Refactor `control/` into plugin architecture |
| 🟡 Important | Simple memory | Add short-term / long-term memory split |
| 🟡 Important | Sequential pipeline | Implement streaming for low latency |
| 🟡 Important | Phase ordering | Move frontend earlier, voice auth later |
| 🟡 Important | No logging | Add structured logging + cost tracking |
| 🟢 Nice-to-have | Electron overhead | Consider Tauri for lower resource usage |
| 🟢 Nice-to-have | Vanilla Whisper | Switch to `faster-whisper` |
| 🟢 Nice-to-have | Missing features | Hotkeys, clipboard, scheduler, notifications |
