# Jarvis Development Context & Guidelines

Welcome to the Jarvis project! This file provides the full context, tech stack, and conventions required to write high-quality, fully integrated code for Jarvis. Please keep these guidelines active in your context for every interaction.

---

## 1. Project Overview & Tech Stack
Jarvis is a robust, desktop-based AI Voice Assistant structured as an inter-communicating frontend and backend application.

- **Frontend**: Electron, Vite, React. UI relies on complex animations (Iron Man HUD aesthetic) powered by **Three.js**, **Canvas API**, and **Framer Motion**. Standard layout uses Tailwind.
- **Backend**: Python 3.10+, fully asynchronous, reliant on FastAPI / WebSockets for duplex communication, `structlog` for logging, `pydantic-settings` for config, `aiosqlite` for DB, and `APScheduler`. 
- **Communication Bridge**: Strict bidirectional WebSocket communication defined by `shared/ipc_protocol.json`.
- **Data Layer**: SQLite initialized locally, managed securely.

---

## 2. Global Conventions 
- **Architectural Rules**: AI Logic, plugin execution, voice detection, and TTS/STT are handled in the Python backend. The Electron React app operates strictly as a dumb terminal / HUD.
- **Naming Conventions**: Python = `snake_case`, TypeScript/React = `camelCase` & `PascalCase`.
- **Security**: Never raw-expose API keys. Use OS Keychain or structured secrets managers.

---

## 3. Expected Copilot / AI Skills

When operating in this repository, strictly adhere to the following workflow patterns ("Skills"):

### 🔌 Plugin Template Skill
- **Rule**: All backend plugins must inherit from the `JarvisPlugin` base class.
- **Action**: When generating a new plugin (e.g., "Create a clipboard plugin"), unconditionally subclass `JarvisPlugin`. Include properly defined `name`, `intents`, and an `async def execute(self, ...)` method.

### 🧪 Backend Test Generation Skill
- **Rule**: Backend testing uses `pytest` and `pytest-asyncio`.
- **Action**: Ensure tests are strictly async. Always mock the Claude/Gemini API calls and TTS providers via `conftest.py` fixtures.

### 🚨 Error Handling Skill
- **Rule**: Zero unhandled external API failures allowed.
- **Action**: Obey patterns found in `core/retry.py` and `core/error_handler.py`. Wrap API calls in automatic retry logic with exponential backoff.

### 📡 IPC Protocol Skill
- **Rule**: Any data flowing between backend and frontend must adhere strictly to `shared/ipc_protocol.json`.
- **Action**: Whenever creating full-stack features, immediately output matched Python event enums and TypeScript event types based off the JSON schema. Ensure frontend WebSocket hooks and backend emitters align completely. 

### 🎨 HUD Animation Skill
- **Rule**: The UI relies on highly complex visual aesthetics (Arc Reactor, wave visualizers, etc.).
- **Action**: *Do not attempt to build complex HUD animations using Tailwind utilities.* Fall back strictly to **Three.js** or the **Canvas API** for these renderings. Ensure rendering loops are heavily performance optimized.

### 🔗 WebSocket Hook Skill
- **Rule**: The React frontend must connect to the backend utilizing our standard `useWebSocket.js` interface.
- **Action**: Include standardized reconnect logic, respect the internal message queue, parse using defined IPC types, and expose connection-state reliably to the view.

### 🗣️ VoiceState Machine Skill
- **Rule**: Jarvis operates on exactly 6 strict states.
- **Action**: Validate interactions against these 6 states: `IDLE`, `WAKE_DETECTED`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`. Ensure handling like interruption logic gracefully shifts from `SPEAKING` to `LISTENING`.

### 🖥️ Electron IPC Skill
- **Rule**: Follow proper IPC bridging for native desktop features.
- **Action**: Respect the separation between the `main` process and `renderer` process. Always implement the `contextBridge` pattern. 

### 🧪 Component Testing Skill
- **Rule**: Frontend tests demand isolated DOM environments and robust mocking.
- **Action**: Output `Vitest` + `React Testing Library` tests. Ensure tests stub out WebSockets natively and mock `Canvas/Three.js` where hardware acceleration would otherwise fail in CI.

### ✅ IPC Validator Skill
- **Rule**: Both sides must trust the message schema inherently.
- **Action**: When altering endpoints, automatically update runtime checks using typed solutions like `zod` for TS (`validate_message.ts`) or `Pydantic` for Python.

---

## 4. MCP Ecosystem (Awareness Context)

Be aware that the following Model Context Protocol (MCP) servers are active or suggested to be active in the developer's environment. Take advantage of them when requested:

**Local Operations & Search:**
1. **GitHub MCP**: Use to create issues for features (e.g. state machine overhauls), review PRs, and manage branches natively.
2. **Filesystem MCP**: Directly access Jarvis folders (`backend/core/`, `shared/` etc.) for deep context.
3. **SQLite MCP**: Run queries on the local Jarvis memory/conversation DB to fetch schemas and debug errors.
4. **Brave Search MCP**: Reach out to real-time resources for SDKs (Porcupine, Whisper, etc.).

**Package Management & Dev Tooling:**
5. **Python Packages MCP**: Pull latest PyPi standards constraint validation (e.g., `pydantic-settings`).
6. **Node/NPM MCP**: Ensure dependency compliance tracking for packages like `Three.js` (r165+) and `electron`.
7. **Terminal/Shell MCP**: Directly run scripts to fast-track verification (e.g., `npm run dev`, `pytest`).
8. **Playwright MCP**: Use to drive end-to-end Electron UI headless tests. Verify HUD element rendering directly.
9. **Storybook MCP**: Read component stories (`StatusRing`, `Waveform`) isolated development prior to React bindings.
10. **Browser DevTools MCP**: Diagnose tricky Three.js rendering memory leaks directly.

**Design & Org (Optional):**
- **Figma MCP** (Extract HUD design tokens)
- **Notion/Obsidian MCP** (Access Architecture docs)
- **Keychain/Secrets MCP** (Test Secure Credential Storage)

## graphify

Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` if it exists.
If `graphify-out/wiki/index.md` exists, navigate it for deep questions.
Type `/graphify` in Copilot Chat to build or update the knowledge graph.
