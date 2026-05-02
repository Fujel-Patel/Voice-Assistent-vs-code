# Skill: Debug

## When to Use
- Runtime exceptions in the voice pipeline
- "No voice output" — text appears in UI but no audio plays
- WebSocket connection drops or message validation failures
- LLM provider errors or timeout issues
- Audio device (microphone/speaker) failures

## Diagnostic Procedure

### Step 1: Check Logs
```bash
# Real-time log tail (structured JSON)
tail -f backend/logs/jarvis.log | python -m json.tool

# Filter for errors only
grep -i "error\|exception\|traceback" backend/logs/jarvis.log | tail -50
```

### Step 2: Identify the Pipeline Stage

The voice pipeline has distinct stages. Identify which one fails:

| Stage | State | Key Module | Common Failures |
|-------|-------|------------|----------------|
| Wake Word | `WAKE_DETECTED` | `infrastructure/audio/listener.py` | Model not loaded, mic permissions |
| Recording | `LISTENING` | `infrastructure/audio/recorder.py` | No audio device, VAD timeout |
| Transcription | `TRANSCRIBING` | `services/voice/stt_manager.py` | Model download failed, empty audio |
| Auth | `VERIFYING` | `auth/speaker_verify.py` | Embedding mismatch |
| AI Response | `THINKING` | `services/brain/agent.py` | API key invalid, rate limit, timeout |
| Speech | `SPEAKING` | `services/voice/tts.py` | Engine crash, no fallback, empty text |
| Playback | `SPEAKING` | `infrastructure/audio/audio_player.py` | PyAudio device error, sample rate mismatch |

### Step 3: Reproduce with Minimal Config
```python
# Test TTS in isolation
from services.voice.tts import TTSManager
from core.config import load_config
cfg = load_config()
mgr = TTSManager(cfg)
audio = await mgr.synthesize("Hello world")
print(f"Audio bytes: {len(audio)}")

# Test STT in isolation
from services.voice.stt_manager import STTManager
stt = STTManager(cfg)
result = await stt.transcribe(audio_array)
print(f"Transcript: {result}")
```

### Step 4: Check State Machine

The state machine prevents invalid transitions. If the pipeline hangs:
```python
from services.voice.state_machine import VoicePipeline, VoiceState
# Check current state
print(f"Current: {state_machine.state}")
# Force reset (emergency)
await state_machine.reset()
```

## Common Issues & Fixes

### "Text appears but no audio"
1. Check `config.tts.primary` — is it set to a valid engine?
2. Check `TTSManager.synthesize()` — is it returning `bytes(0)`?
3. Check `AudioPlayer.play()` — is PyAudio initialized with the correct sample rate?
4. Check `config.tts.sample_rate` — default is `22050`, some engines output `24000`

### "WebSocket disconnects"
1. Check `WSManager.broadcast()` — is it catching per-connection errors?
2. Check CORS origins in `fastapi_app.py` — only `localhost:5173` and `127.0.0.1:5173` allowed
3. Check heartbeat — is the frontend sending ping/pong?

### "LLM returns empty response"
1. Check API key in `.env` — is the correct key set for the configured provider?
2. Check `config.brain.providers.default_provider` — does it match an available key?
3. Check `config.brain.providers.fallback_order` — are fallback providers configured?
4. Check `load_config.cache_clear()` — was config updated without clearing cache?

### "Config changes don't take effect"
1. Call `load_config.cache_clear()` after any config mutation
2. Check that `save_setting()` or `save_all()` was used (not direct file write)

## Debugging Tools

```bash
# Check if backend is running
curl http://localhost:8765/api/v1/health

# Check WebSocket
websocat ws://localhost:8765/ws

# Check mypy for type issues
mypy --strict backend/ 2>&1 | head -30

# Check for security issues
bandit -r backend/ -ll
```
