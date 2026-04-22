# Graph Report - /home/fujel/Documents/Fujel-Developer/Voice Assistent vs code/jarvis  (2026-04-21)

## Corpus Check
- 160 files · ~221,742 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 976 nodes · 1933 edges · 56 communities detected
- Extraction: 63% EXTRACTED · 37% INFERRED · 0% AMBIGUOUS · INFERRED: 715 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]

## God Nodes (most connected - your core abstractions)
1. `JarvisBackend` - 46 edges
2. `PluginResult` - 30 edges
3. `EventBus` - 29 edges
4. `TTSManager` - 28 edges
5. `VoiceEnrollment` - 24 edges
6. `JarvisConfig` - 24 edges
7. `SpeakerEmbeddingEngine` - 22 edges
8. `Lightweight HTTP server on port 8766 for health checks.` - 22 edges
9. `SystemControlPlugin` - 21 edges
10. `AppLauncherPlugin` - 20 edges

## Surprising Connections (you probably didn't know these)
- `useWebSocket()` --calls--> `MainPage()`  [INFERRED]
  frontend/src/hooks/useWebSocket.js → /home/fujel/Documents/Fujel-Developer/Voice Assistent vs code/jarvis/frontend/src/pages/MainPage.jsx
- `Memory subsystem utilities for short and long context management.` --uses--> `ContextBuilder`  [INFERRED]
  backend/brain/memory/__init__.py → /home/fujel/Documents/Fujel-Developer/Voice Assistent vs code/jarvis/backend/brain/memory/context_builder.py
- `Memory subsystem utilities for short and long context management.` --uses--> `LongTermMemory`  [INFERRED]
  backend/brain/memory/__init__.py → /home/fujel/Documents/Fujel-Developer/Voice Assistent vs code/jarvis/backend/brain/memory/long_term.py
- `JarvisBackend` --uses--> `AccessController`  [INFERRED]
  /home/fujel/Documents/Fujel-Developer/Voice Assistent vs code/jarvis/backend/main.py → backend/auth/access_control.py
- `JarvisBackend` --uses--> `VoiceEnrollment`  [INFERRED]
  /home/fujel/Documents/Fujel-Developer/Voice Assistent vs code/jarvis/backend/main.py → backend/auth/enrollment.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (37): AudioPlayer, AudioQueue, event_bus(), mock_config(), MicrophoneError, setup_global_error_handler(), EventBus, JarvisEvents (+29 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (17): AISettings(), modelKeyForProvider(), AppShell(), ErrorBoundary, Framer Motion, MainPage(), React + Vite, SettingsPage() (+9 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (25): ClipboardService, Jarvis Services — Clipboard Integration Stub ===================================, Read and write the system clipboard., Get the current clipboard content., Set the clipboard content., _config(), test_backend_mapping_supports_new_backends(), test_elevenlabs_synthesis() (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (25): AppLauncherPlugin, JarvisPlugin, PluginResult, Standardized return from plugin.execute()., Base class for all Jarvis plugins., FileManagerPlugin, Jarvis Plugins — File Manager Stub (Phase 5) ===================================, TODO Phase 5: File open, search, and management. (+17 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (19): AccessController, Create and compare speaker embeddings.      Uses resemblyzer when available. Fal, SpeakerEmbeddingEngine, EnrollmentSession, VoiceEnrollment, LivenessDetector, SpeakerVerifier, VerificationCache (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (33): AccessLevel, Enum, BackendEvent, CommandSource, FrontendEvent, HealthStatus, Jarvis Shared — Event Type Enums ================================== Python enum, System health statuses. (+25 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (38): BaseModel, AudioConfig, AuthConfig, BrainConfig, BrainModelConfig, BrainProviderConfig, _coerce_value(), _deep_merge() (+30 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (13): BraveSearch, _search_endpoint(), DuckDuckGoSearch, test_brave_search(), test_duckduckgo_search(), test_fallback_to_duckduckgo(), test_search_caching(), test_ssrf_protection() (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (23): BrainResult, _call_claude(), _call_gemini(), _call_openai_compatible(), ClaudeAgent, Phase-2 brain agent supporting multiple providers behind one interface., Phase-2 brain agent supporting multiple providers behind one interface., APIError (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (11): ScreenAnalyzer, ScreenCapture, OCREngine, ScreenReaderPlugin, test_claude_vision_analysis(), test_multi_monitor_list(), test_ocr_empty_image(), test_ocr_text_extraction() (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (16): JarvisConfig, model(), ModelManager, Handles local faster-whisper model loading and switching., faster-whisper transcription service., SpeechToText, Vosk speech-to-text service with partial transcript callbacks., SpeechToTextVosk (+8 more)

### Community 11 - "Community 11"
Cohesion: 0.1
Nodes (17): Electron, Electron Main Process, createMainWindow(), registerShortcuts(), setupIpc(), setupTray(), Preload Script (contextBridge), Orchestrates backend startup and shutdown with health/degraded reporting. (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (15): FastAPIWebSocketAdapter, health(), lifespan(), Adapter to reuse existing websocket business logic with FastAPI transport., _serve_websocket(), websocket_endpoint(), websocket_root_endpoint(), get_backend() (+7 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (31): AI Brain (Claude), Aiosqlite, Anthropic Claude API, APScheduler, StatusRing (Arc Reactor), Backend (FastAPI + Python), Dashboard (Main HUD), ElevenLabs TTS (+23 more)

### Community 14 - "Community 14"
Cohesion: 0.16
Nodes (8): Database, get_db(), LongTermMemory, test_long_term_store_and_search(), test_app_launcher_close(), test_app_launcher_open(), test_brightness_control(), test_volume_control()

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (9): IntentRouter, IntentValidationError, validate_intent_payload(), PluginManager, Discovers, loads, and manages plugins., handler(), build_system_prompt(), test_intent_router() (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.24
Nodes (6): ContextBuilder, ShortTermMemory, test_context_builder(), test_short_term_add_turn(), test_short_term_max_turns(), test_short_term_token_budget()

### Community 17 - "Community 17"
Cohesion: 0.24
Nodes (7): isIsoDate(), validateIpcEnvelope(), _configure_logger(), get_logger(), Drop common handshake noise that isn't actionable for developers., _WebSocketNoiseFilter, tokenizePhrase()

### Community 18 - "Community 18"
Cohesion: 0.73
Nodes (5): ensure_dirs(), main(), prepare_moonshine(), prepare_piper(), print_step()

### Community 19 - "Community 19"
Cohesion: 0.6
Nodes (5): _install_fake_backend(), test_fastapi_health_cors_for_vite_origin(), test_fastapi_health_endpoint(), test_websocket_transport_root_alias(), test_websocket_transport_ws_path()

### Community 20 - "Community 20"
Cohesion: 0.4
Nodes (2): GeminiAgent, # TODO: integrate context

### Community 21 - "Community 21"
Cohesion: 0.5
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.83
Nodes (3): disable(), enable(), isEnabled()

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (2): isIsoDate(), validateMessageEnvelope()

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (1): ScreenRegion

### Community 25 - "Community 25"
Cohesion: 0.67
Nodes (2): Retry async call with exponential backoff., retry()

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Handles WebSocket CRUD operations for runtime settings and API keys.

## Knowledge Gaps
- **46 isolated node(s):** `Jarvis Shared — Event Type Enums ================================== Python enum`, `Events sent FROM the Python backend TO the Electron frontend.`, `Events sent FROM the Electron frontend TO the Python backend.`, `All valid voice pipeline states (used in voice_state_change payload).`, `TTS playback states (used in tts_state payload).` (+41 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 26`** (2 nodes): `App()`, `App.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `GeneralSettings.jsx`, `GeneralSettings()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `AppearanceSettings()`, `AppearanceSettings.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (2 nodes): `AboutSettings()`, `AboutSettings.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `StatusRing.jsx`, `StatusRing()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `SettingsDropdown.jsx`, `SettingsDropdown()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `SettingsSlider.jsx`, `SettingsSlider()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (2 nodes): `SettingsSidebar.jsx`, `SettingsSidebar()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (2 nodes): `SettingsSection.jsx`, `SettingsSection()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (2 nodes): `SettingsToggle.jsx`, `SettingsToggle()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (2 nodes): `resolveBackendHealthUrl()`, `constants.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (2 nodes): `windows.py`, `has_tool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (2 nodes): `macos.py`, `has_tool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (2 nodes): `linux.py`, `has_tool()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `appStore.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `HUD.test.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `StatusRing.test.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `settingsDefaults.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `events.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Handles WebSocket CRUD operations for runtime settings and API keys.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JarvisBackend` connect `Community 0` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 10`, `Community 12`, `Community 14`, `Community 15`, `Community 16`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `TTSManager` connect `Community 2` to `Community 0`, `Community 8`, `Community 15`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `str` (e.g. with `validate_message_envelope()` and `_stitch_text_chunks()`) actually correct?**
  _`str` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `JarvisBackend` (e.g. with `SettingsHandler` and `AccessController`) actually correct?**
  _`JarvisBackend` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `PluginResult` (e.g. with `.execute()` and `._open_app()`) actually correct?**
  _`PluginResult` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `EventBus` (e.g. with `JarvisBackend` and `TTSManager`) actually correct?**
  _`EventBus` has 21 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Jarvis Shared — Event Type Enums ================================== Python enum`, `Events sent FROM the Python backend TO the Electron frontend.`, `Events sent FROM the Electron frontend TO the Python backend.` to the rest of the system?**
  _46 weakly-connected nodes found - possible documentation gaps or missing edges._