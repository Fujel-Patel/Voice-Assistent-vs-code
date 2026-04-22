## JARVIS BACKEND — FIX VERIFICATION REPORT

### 1. FILES MODIFIED

1. File path: [backend/voice/stt_moonshine.py](backend/voice/stt_moonshine.py)
Original code:
```python
self.model = moonshine.load_model("moonshine/tiny")
logger.info("Moonshine tiny model loaded.")

...
text = await loop.run_in_executor(None, self.model.transcribe, normalized)
```

New code:
```python
self._model = None

async def _ensure_model(self) -> None:
    if self._model is not None:
        return
    self._model = await asyncio.to_thread(moonshine.load_model, "moonshine/tiny")
    logger.info("Moonshine tiny model loaded.")

...
await self._ensure_model()
tokens = await loop.run_in_executor(None, self._model.transcribe, normalized)
text = " ".join(tokens).strip() if isinstance(tokens, list) else str(tokens or "").strip()

if not text or len(text.strip()) < 2:
    return {
        "text": "",
        "confidence": 0.05,
        "language": "en",
        "duration_seconds": round(duration, 3),
    }
```

Status: ✅ Fixed

---

2. File path: [backend/requirements.txt](backend/requirements.txt)
Original code:
```txt
anthropic>=0.34.0
duckduckgo-search>=6.0.0
httpx>=0.27.0
sounddevice>=0.4.6
tiktoken>=0.7.0
uvicorn[standard]>=0.32.0
tensorflow>=2.16.0,<3.0.0
openwakeword>=0.6.0; python_version < "3.12"
websockets>=13.0
google-generativeai>=0.7.0
```

New code:
```txt
anthropic>=0.49.0
duckduckgo-search>=7.0.0
httpx>=0.28.0
sounddevice>=0.5.0
tiktoken>=0.9.0
uvicorn[standard]>=0.34.0
onnxruntime>=1.19.0
# Optional: tensorflow is only needed for moonshine-onnx variants.
openwakeword>=0.6.0
websockets>=14.0
google-genai>=1.0.0
```

Status: ⚠️ Partially Fixed
Note: All requested text changes were applied, but runtime install still reports Linux/Python 3.12 dependency friction around tflite-runtime in this environment.

---

3. File path: [scripts/dev.sh](scripts/dev.sh)
Original code:
```bash
LOG_RED='\033[0;31m'
LOG_YELLOW='\033[1;33m'
LOG_GREEN='\033[0;32m'
LOG_NC='\033[0m'
```

New code:
```bash
LOG_RED='\033[0;31m'
LOG_YELLOW='\033[1;33m'
LOG_GREEN='\033[0;32m'
LOG_NC='\033[0m'

CYAN='\033[0;36m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'
```

Status: ✅ Fixed

---

4. File path: [backend/voice/tts.py](backend/voice/tts.py)
Original code:
```python
def _decode_audio_bytes(self, encoded_audio: bytes) -> np.ndarray:
    import soundfile as sf
    from io import BytesIO

    audio, sr = sf.read(BytesIO(encoded_audio), dtype="float32")
    if isinstance(audio, np.ndarray) and audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != self.config.tts.sample_rate:
        audio = self._resample(audio, sr, self.config.tts.sample_rate)
    return audio.astype(np.float32)
```

New code:
```python
def _decode_audio_bytes(self, encoded_audio: bytes) -> np.ndarray:
    import io
    # Try soundfile first (works for WAV/FLAC/OGG)
    try:
        import soundfile as sf

        audio, sr = sf.read(io.BytesIO(encoded_audio), dtype="float32")
        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != self.config.tts.sample_rate:
            audio = self._resample(audio, sr, self.config.tts.sample_rate)
        return audio.astype(np.float32)
    except Exception:
        pass
    # Fallback: pydub for MP3 (ElevenLabs output)
    try:
        from pydub import AudioSegment

        segment = AudioSegment.from_file(io.BytesIO(encoded_audio))
        segment = segment.set_frame_rate(self.config.tts.sample_rate).set_channels(1)
        samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
        # Normalize based on sample width
        max_val = float(2 ** (8 * segment.sample_width - 1))
        return (samples / max_val).astype(np.float32)
    except Exception as exc:
        logger.error(f"Audio decode failed with all backends: {exc}")
        return np.zeros(self.config.tts.sample_rate, dtype=np.float32)  # 1 second silence
```

Status: ✅ Fixed

---

5. File path: [backend/voice/tts_piper.py](backend/voice/tts_piper.py)
Original code:
```python
model_name = str(getattr(self.config.tts, "piper_model", "") or "en_US-lessac-medium.onnx").strip()
if not model_name:
    model_name = "en_US-lessac-medium.onnx"

if self._voice is not None and self._voice_model_name == model_name:
    return self._voice

from piper import PiperVoice
logger.info(f"Loading Piper voice model: {model_name}")
self._voice = PiperVoice.load(model_name, use_cuda=False)
self._voice_model_name = model_name
```

New code:
```python
import os
from pathlib import Path

model_name_cfg = str(getattr(self.config.tts, "piper_model", "") or "en_US-lessac-medium.onnx").strip()

if self._voice is not None and self._voice_model_name == model_name_cfg:
    return self._voice

# Search locations in order
search_paths = [
    Path(model_name_cfg),
    Path.home() / ".jarvis" / "models" / "tts" / model_name_cfg,
    Path.home() / ".local" / "share" / "piper" / model_name_cfg,
    Path("/usr/share/piper/voices") / model_name_cfg,
]

resolved_path = None
for candidate in search_paths:
    if candidate.exists():
        resolved_path = os.fspath(candidate)
        break

if resolved_path is None:
    raise RuntimeError(
        f"Piper model '{model_name_cfg}' not found. "
        f"Run: python scripts/download_models.py\n"
        f"Searched: {[str(p) for p in search_paths]}"
    )

from piper import PiperVoice
logger.info(f"Loading Piper voice model from: {resolved_path}")
self._voice = PiperVoice.load(resolved_path, use_cuda=False)
self._voice_model_name = model_name_cfg
```

Status: ✅ Fixed

---

6. File path: [backend/voice/tts_kokoro.py](backend/voice/tts_kokoro.py)
Original code:
```python
async def synthesize(self, text: str) -> bytes:
    self._cancelled = False
    ...

async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
    self._cancelled = False
    ...
```

New code:
```python
async def synthesize(self, text: str) -> bytes:
    if self.pipeline is None:
        raise RuntimeError("KokoroTTS is not available (kokoro package not installed)")
    self._cancelled = False
    ...

async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
    if self.pipeline is None:
        raise RuntimeError("KokoroTTS is not available (kokoro package not installed)")
    self._cancelled = False
    ...
```

Status: ✅ Fixed

---

7. File path: [backend/voice/recorder.py](backend/voice/recorder.py)
Original code:
```python
audio_chunk, _overflowed = stream.read(frame_samples)
...
await asyncio.sleep(0)
```

New code:
```python
audio_chunk, _overflowed = await asyncio.to_thread(stream.read, frame_samples)
...
# sleep removed
```

Status: ✅ Fixed

---

8. File path: [backend/main.py](backend/main.py)
Original code (key snippets):
```python
await self.health_checker.start_periodic()
asyncio.create_task(self._warm_startup_models(), name="startup-model-warmup")

...
tasks = [client.send(body) for client in self.clients]

...
if self.config.brain.stream_chunks:
    ...
    await tts_text_queue.put(None)

if final_chunk_payload is None:
    brain_result = await self.brain_agent.process_input(...)

...
if self.config.brain.stream_chunks:
    ...
if final_chunk_payload is not None:
    response_text = final_chunk_payload.get("response", "")
else:
    response_text = _stitch_text_chunks(collected_chunks)
```

New code (key snippets):
```python
await self.health_checker.start_periodic()
asyncio.create_task(self._ws_keepalive_loop(), name="ws-keepalive")
asyncio.create_task(self._warm_startup_models(), name="startup-model-warmup")

...
tasks = [client.send(body) for client in list(self.clients)]

...
streaming_was_attempted = False
if self.config.brain.stream_chunks:
    streaming_was_attempted = True
    ...
    await tts_text_queue.put(None)

if not streaming_was_attempted or final_chunk_payload is None:
    if streaming_was_attempted:
        logger.warning("Streaming produced no final payload, falling back to non-streaming")
        tts_playback_task = None
    brain_result = await self.brain_agent.process_input(...)

...
async def _ws_keepalive_loop(self) -> None:
    while not self.stop_event.is_set():
        await asyncio.sleep(30)
        if self.clients:
            await self.broadcast(self._message(msg_type="ping", payload={"ts": datetime.now(timezone.utc).isoformat()}))

...
streaming_was_attempted = False
if self.config.brain.stream_chunks:
    streaming_was_attempted = True
    ...
if not streaming_was_attempted or final_chunk_payload is None:
    ...
else:
    ...
    if not response_text:
        response_text = _stitch_text_chunks(collected_chunks)
```

Status: ✅ Fixed

---

9. File path: [backend/services/web_fetcher.py](backend/services/web_fetcher.py)
Original code:
```python
async def fetch_page(self, url: str) -> dict[str, Any]:
    self._validate_url(url)

...
def _validate_url(self, url: str) -> None:
    ...
    self._assert_public_host(host)

def _assert_public_host(self, host: str) -> None:
    addresses = socket.getaddrinfo(host, None)
```

New code:
```python
async def fetch_page(self, url: str) -> dict[str, Any]:
    await self._validate_url(url)

...
async def _validate_url(self, url: str) -> None:
    ...
    await asyncio.to_thread(self._assert_public_host, host)

def _assert_public_host(self, host: str) -> None:
    # This is now async-safe via asyncio.to_thread at the call site.
    addresses = socket.getaddrinfo(host, None)
```

Status: ✅ Fixed

---

10. File path: [backend/api/fastapi_app.py](backend/api/fastapi_app.py)
Original code:
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from main import get_backend

...
async def __anext__(self) -> str:
    try:
        return await self._ws.receive_text()
    except WebSocketDisconnect:
        raise StopAsyncIteration
```

New code:
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from core.logger import get_logger
from main import get_backend

logger = get_logger(__name__)

...
async def __anext__(self) -> str:
    try:
        return await self._ws.receive_text()
    except WebSocketDisconnect:
        raise StopAsyncIteration
    except RuntimeError as exc:
        # "WebSocket is not connected" or similar
        raise StopAsyncIteration from exc
    except Exception as exc:
        logger.warning(f"WebSocket receive error: {exc}")
        raise StopAsyncIteration from exc
```

Status: ✅ Fixed

---

11. File path: [backend/config/user_config.yaml](backend/config/user_config.yaml)
Original code:
```yaml
auth:
  mode: 'off'
  liveness: always
tts:
  primary: local
  voice_profile: custom
audio:
  silence_stop_seconds: 1.5
  speaker_device: communications
brain:
  stream_chunks: true
  models:
    gemini: gemma-4-31b-it
stt:
  model: large-v3
```

New code:
```yaml
auth:
  mode: 'off'
  liveness: always
tts:
  primary: piper
  piper_model: en_US-lessac-medium.onnx
audio:
  silence_stop_seconds: 1.5
  speaker_device: communications
brain:
  stream_chunks: true
  models:
    gemini: gemini-2.0-flash
```

Status: ✅ Fixed

---

12. File path: [backend/tests/test_web.py](backend/tests/test_web.py)
Original code:
```python
def test_ssrf_protection() -> None:
    fetcher = WebFetcher()
    with pytest.raises(ValueError):
        fetcher._validate_url("http://127.0.0.1/admin")
```

New code:
```python
@pytest.mark.asyncio
async def test_ssrf_protection() -> None:
    fetcher = WebFetcher()
    with pytest.raises(ValueError):
        await fetcher._validate_url("http://127.0.0.1/admin")
```

Status: ✅ Fixed
Note: This was a required verification compatibility update after making URL validation async.

---

### 2. FILES CREATED

1. File path: [backend/storage/migrations/002_usage_log_index.sql](backend/storage/migrations/002_usage_log_index.sql)
Full file contents:
```sql
-- Migration 002: Add index for api_usage_log and fix gap in sequence
CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage_log(provider, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_request_id ON api_usage_log(request_id);
```

Reason it was created: Required migration placeholder/index file to close the sequence gap and add usage-log indexes (Fix 16).

---

### 3. FIX STATUS TABLE

| Fix # | Description | Status | Notes |
|-------|-------------|--------|-------|
| 1 | Moonshine STT returns List[str] — join fix + lazy load | ✅ | Joined token lists, added async lazy load, switched to self._model, added short-text guard. |
| 2 | openWakeWord python_version condition removed | ⚠️ | Condition removed as requested; however, full dependency install on this Linux/Python 3.12 host still reports tflite-runtime resolution issues. |
| 3 | dev.sh color variables defined | ✅ | Added CYAN/RED/GREEN/YELLOW/BOLD/NC constants. |
| 4 | ElevenLabs MP3 decode pydub fallback | ✅ | Added soundfile-first then pydub fallback with silence fallback on full decode failure. |
| 5 | Piper model path resolved from disk | ✅ | Added multi-path search and resolved-path loading with clear error if missing. |
| 6 | KokoroTTS None pipeline guard | ✅ | Added RuntimeError guards in both synthesize paths. |
| 7 | AudioRecorder asyncio.to_thread fix | ✅ | stream.read moved to thread, sleep(0) removed. |
| 8 | Streaming + non-streaming race condition fix | ✅ | Applied in both voice loop and text-command path; fallback now re-synthesizes with audio playback. |
| 9 | Web fetcher DNS lookup async fix | ✅ | _validate_url became async and DNS check moved to asyncio.to_thread. |
| 10 | broadcast() iterates list(self.clients) | ✅ | Updated to list(self.clients). |
| 11 | user_config.yaml invalid Gemini model fixed | ✅ | Changed to gemini-2.0-flash. |
| 12 | WebSocket disconnect catches all errors | ✅ | Adapter now catches WebSocketDisconnect, RuntimeError, and generic exceptions. |
| 13 | WebSocket server-side keepalive ping added | ✅ | Added _ws_keepalive_loop and startup task creation. |
| 14 | user_config.yaml TTS primary changed to piper | ✅ | Set primary piper and piper_model. |
| 15 | requirements.txt package versions updated | ✅ | All requested version and package changes applied exactly. |
| 16 | Migration 002 SQL file created | ✅ | File created with both required indexes. |
| 17 | STT minimum confidence/empty text check | ✅ | Added text length guard with low-confidence return payload. |
| 18 | user_config.yaml cleaned up (removed large-v3) | ✅ | stt.model entry removed from final config. |

---

### 4. TESTS RUN

1. Command executed:
```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```
Output / result:
```txt
ImportError while loading conftest: ModuleNotFoundError: No module named config
```
Pass or Fail:
❌ Fail

2. Command executed:
```bash
cd backend && source .venv/bin/activate && pip install openwakeword && python -c "import openwakeword; print('OK')"
```
Output / result:
```txt
Pip completed; import printed OK.
Resolver changed installed openwakeword to 0.4.0 in this environment.
```
Pass or Fail:
✅ Pass (with dependency/version caveat)

3. Command executed:
```bash
python moonshine smoke script validating result["text"] is str
```
Output / result:
```txt
STT OK: {'text': '', 'confidence': 0.05, 'language': 'en', 'duration_seconds': 0.0}
```
Pass or Fail:
✅ Pass

4. Command executed:
```bash
python piper availability script
```
Output / result:
```txt
Piper available: True
```
Pass or Fail:
✅ Pass

5. Command executed:
```bash
bash scripts/dev.sh plus health and websocket probe sequence
```
Output / result:
```txt
HEALTH_READY=true
WS_CONNECT_OK=true
Backend and frontend started; websocket connected; shutdown clean.
```
Pass or Fail:
✅ Pass

6. Command executed:
```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/ -v
```
Output / result:
```txt
67 passed, 1 failed
Failing test: test_ssrf_protection (sync call to async _validate_url)
```
Pass or Fail:
❌ Fail

7. Command executed:
```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_web.py::test_ssrf_protection -v
```
Output / result:
```txt
1 passed
```
Pass or Fail:
✅ Pass

8. Command executed:
```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/ -v
```
Output / result:
```txt
68 passed, 0 failed, 12 warnings
```
Pass or Fail:
✅ Pass

9. Command executed:
```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/ -v > /tmp/pytest_backend_tests.log 2>&1; echo EXIT_CODE=$?; tail -n 40 /tmp/pytest_backend_tests.log
```
Output / result:
```txt
Terminated
EXIT_CODE=143
```
Pass or Fail:
❌ Fail (terminated externally)

---

### 5. REMAINING ISSUES

1. openWakeWord dependency install remains environment-sensitive on Linux/Python 3.12.
Evidence: pip resolver errors for tflite-runtime and runtime warning behavior while dev script continues.
Relevant file: [backend/requirements.txt](backend/requirements.txt#L46)

2. In this environment, openwakeword resolved to 0.4.0 during direct pip install command. That version emits runtime warning related to download_models helper usage.
Observed warning source: [backend/voice/listener.py](backend/voice/listener.py#L92)

3. Manual action required for full Piper functionality if model file is absent:
- Run model download script as indicated by the new runtime error message path guidance.
Relevant file: [backend/voice/tts_piper.py](backend/voice/tts_piper.py#L59)

4. External provider features still need valid keys/config in environment for complete runtime behavior (Gemini/Anthropic/etc.), independent of these code fixes.

---

### 6. CURRENT REQUIREMENTS.TXT DIFF

```diff
diff --git a/backend/requirements.txt b/backend/requirements.txt
index a966f34..2627d6d 100644
--- a/backend/requirements.txt
+++ b/backend/requirements.txt
@@ -12,13 +12,13 @@
 # Required: Core Runtime + Voice Pipeline
 # ------------------------------------------------------------
 aiosqlite>=0.20.0
-anthropic>=0.34.0
+anthropic>=0.49.0
 beautifulsoup4>=4.12.0
 cryptography>=42.0.0
-duckduckgo-search>=6.0.0
+duckduckgo-search>=7.0.0
 elevenlabs>=1.9.0
 fastapi>=0.115.0
-httpx>=0.27.0
+httpx>=0.28.0
 loguru>=0.7.2
 lxml>=5.0.0
 mss>=9.0.0
@@ -36,18 +36,17 @@ readability-lxml>=0.8.1
 resemblyzer>=0.1.3
 scipy>=1.12.0
 screen-brightness-control>=0.24.2
-sounddevice>=0.4.6
+sounddevice>=0.5.0
 soundfile>=0.12.1
-tiktoken>=0.7.0
-uvicorn[standard]>=0.32.0
+tiktoken>=0.9.0
+uvicorn[standard]>=0.34.0
 useful-moonshine>=0.1.0
-tensorflow>=2.16.0,<3.0.0
-# Python 3.12 on Linux currently lacks compatible tflite-runtime wheels.
-# scripts/dev.sh installs openwakeword with --no-deps and uses ONNX fallback.
-openwakeword>=0.6.0; python_version < "3.12"
+onnxruntime>=1.19.0
+# Optional: tensorflow is only needed for moonshine-onnx variants.
+openwakeword>=0.6.0
 piper-tts>=1.3.0
 webrtcvad-wheels>=2.0.14
-websockets>=13.0
+websockets>=14.0
 
 # ------------------------------------------------------------
 # Optional: Additional TTS/STT Backends
@@ -73,7 +72,7 @@ sentence-transformers>=3.0.0
 # Optional: Legacy/Experimental Provider Module
 # ------------------------------------------------------------
 # Used by backend/brain/gemini_agent.py
-google-generativeai>=0.7.0
+google-genai>=1.0.0
 
 # ------------------------------------------------------------
 # Testing
```

---

### 7. CURRENT user_config.yaml — FINAL STATE

File: [backend/config/user_config.yaml](backend/config/user_config.yaml)

```yaml
auth:
  mode: 'off'
  liveness: always
tts:
  primary: piper
  piper_model: en_US-lessac-medium.onnx
audio:
  silence_stop_seconds: 1.5
  speaker_device: communications
brain:
  stream_chunks: true
  models:
    gemini: gemini-2.0-flash
```

---

### 8. ANY NEW BUGS INTRODUCED

1. Potential compatibility break for any direct synchronous callers of URL validation after Fix 9
Details: _validate_url is now async and must be awaited.
Primary change: [backend/services/web_fetcher.py](backend/services/web_fetcher.py#L122)
Observed impact: test had to be updated at [backend/tests/test_web.py](backend/tests/test_web.py#L118)

2. openWakeWord runtime/install stability risk increased in this environment due unconditional requirement and resolver behavior
Details: tflite-runtime dependency resolution issues on Linux/Python 3.12 and version drift to openwakeword 0.4.0 in direct install flow.
Reference requirement line: [backend/requirements.txt](backend/requirements.txt#L46)
Runtime warning location observed: [backend/voice/listener.py](backend/voice/listener.py#L92)
