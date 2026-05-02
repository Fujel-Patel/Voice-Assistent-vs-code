# JARVIS — Active Tasks

## Pending

### Phase 2: Orchestrator Decomposition
- [ ] Extract `VoicePipeline` fully out of `core/orchestrator.py` (partially done — `services/voice/pipeline.py` exists but orchestrator still has ~460 lines)
- [ ] Extract `WSManager` initialization and lifecycle into a standalone service
- [ ] Reduce `JarvisBackend.__init__()` to dependency wiring only — no business logic

### Phase 4: Logic Deduplication
- [ ] Unify `_voice_loop()` and `_run_turn()` — both contain duplicated LLM→TTS→broadcast logic
- [ ] Create a single `_process_response()` method shared by voice and text command paths
- [ ] Remove the streaming/non-streaming code duplication (currently ~200 lines duplicated)

### Final Restructuring
- [ ] Move `brain/intent.py` and `brain/memory/` under `services/brain/` to match the `services/` convention
- [ ] Consolidate `services/brain/agent.py` with the existing `brain/` module
- [ ] Ensure all imports use the `services/` prefix consistently
- [ ] Update README.md project structure to match actual layout

### Documentation
- [ ] Update README.md tech stack table (currently lists Porcupine but project uses OpenWakeWord)
- [ ] Update README.md structure diagram (outdated — doesn't show `services/`, `infrastructure/`)
- [ ] Add API documentation for WebSocket message protocol

### Testing
- [ ] Increase test coverage for `services/voice/pipeline.py` (the most critical module, 834 lines)
- [ ] Add integration test for full voice pipeline flow (mocked audio)
- [ ] Add test for LLM provider fallback chain

### Technical Debt
- [ ] Clean stale `brain/72d677ec-23d0-4802-8089-7e7b59e111d5/` directory from brain module
- [ ] Piper TTS is brittle — consider subprocess-based approach if issues recur
- [ ] `pipeline.py` has duplicate `from typing import TYPE_CHECKING, Any, cast, Protocol` import on line 36

## Completed

### Previous Session (Phase 1)
- [x] Fix AudioPlayer `play()`/`play_stream()` exception handling
- [x] Fix TTSManager silence fallback in `_stream_sentence()`
- [x] Fix Orchestrator state transitions (THINKING → SPEAKING race condition)
- [x] Fix `load_config.cache_clear()` in `SettingsHandler._store_api_key()`
- [x] Standardize `/api/v1/` prefix on all system routes
- [x] Remove dead code (`brain/gemini_agent.py`, root temp scripts)
- [x] Achieve 100% `mypy --strict` compliance (62 errors fixed)
- [x] Clean 23+ stale files from project root
- [x] Update `.gitignore` for temp artifacts
- [x] Create agent infrastructure (`/agent/` directory)
