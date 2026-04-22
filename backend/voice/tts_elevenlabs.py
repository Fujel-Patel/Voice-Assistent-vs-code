from __future__ import annotations

import time
from collections.abc import AsyncIterator

import httpx

from core.error_handler import APIError, ConfigError
from core.logger import get_logger
from core.retry import retry

logger = get_logger(__name__)


class ElevenLabsTTS:
    def __init__(self, config) -> None:
        self.config = config
        self._cancelled = False
        self._resolved_voice_id: str | None = None

    def cancel(self) -> None:
        self._cancelled = True

    @retry(max_retries=1, base_delay=0.5, exceptions_to_retry=(APIError,))
    async def synthesize(self, text: str) -> bytes:
        self._cancelled = False
        key = self.config.elevenlabs_api_key
        if not key:
            raise ConfigError("ELEVENLABS_API_KEY is missing")

        headers = {
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        voice_id = await self._resolve_voice_id(key)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload = {
            "text": text,
            "model_id": self.config.tts.model_id,
            "voice_settings": {
                "stability": self.config.tts.stability,
                "similarity_boost": self.config.tts.similarity_boost,
            },
        }

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 401:
            raise ConfigError("Invalid ElevenLabs API key")
        if response.status_code == 404:
            # Voice may have been removed remotely; clear cache and force re-resolve once.
            self._resolved_voice_id = None
            raise ConfigError("Invalid ElevenLabs voice_id. Check configured voice.")
        if response.status_code == 429:
            raise APIError("ElevenLabs rate limited")
        if response.status_code >= 400:
            raise APIError(f"ElevenLabs request failed: {response.status_code} {response.text}")

        elapsed_ms = (time.perf_counter() - start) * 1000
        chars = len(text)
        est_cost = (chars / 1000.0) * 0.30
        logger.info(
            f"ElevenLabs synthesis chars={chars} latency_ms={elapsed_ms:.1f} "
            f"estimated_cost_usd={est_cost:.4f}"
        )
        return response.content

    async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
        self._cancelled = False
        key = self.config.elevenlabs_api_key
        if not key:
            raise ConfigError("ELEVENLABS_API_KEY is missing")

        headers = {
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        voice_id = await self._resolve_voice_id(key)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        payload = {
            "text": text,
            "model_id": self.config.tts.model_id,
            "voice_settings": {
                "stability": self.config.tts.stability,
                "similarity_boost": self.config.tts.similarity_boost,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code == 429:
                    raise APIError("ElevenLabs rate limited")
                if response.status_code == 404:
                    self._resolved_voice_id = None
                    body = await response.aread()
                    raise ConfigError(
                        f"Invalid ElevenLabs voice_id. Configure a valid voice. details={body.decode('utf-8', 'ignore')}"
                    )
                if response.status_code >= 400:
                    body = await response.aread()
                    raise APIError(
                        f"ElevenLabs stream failed: {response.status_code} {body.decode('utf-8', 'ignore')}"
                    )
                async for chunk in response.aiter_bytes():
                    if self._cancelled:
                        break
                    if chunk:
                        yield chunk

    async def _resolve_voice_id(self, api_key: str) -> str:
        if self._resolved_voice_id:
            return self._resolved_voice_id

        configured = (self.config.tts.voice_id or "").strip()

        headers = {"xi-api-key": api_key, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get("https://api.elevenlabs.io/v1/voices", headers=headers)

        if response.status_code == 401:
            raise ConfigError("Invalid ElevenLabs API key")
        if response.status_code >= 400:
            raise APIError(f"ElevenLabs voices fetch failed: {response.status_code} {response.text}")

        data = response.json() or {}
        voices = data.get("voices") or []
        if not voices:
            raise ConfigError("No ElevenLabs voices available for this account")

        available_ids = {str(v.get("voice_id") or "").strip() for v in voices}
        available_ids.discard("")

        if configured and configured in available_ids:
            self._resolved_voice_id = configured
            return configured

        picked = str(voices[0].get("voice_id") or "").strip()
        if not picked:
            raise ConfigError("Unable to resolve a valid ElevenLabs voice_id")

        if configured and configured != picked:
            logger.warning(
                f"Configured ElevenLabs voice_id '{configured}' unavailable. Using account voice '{picked}'"
            )

        self._resolved_voice_id = picked
        return picked
