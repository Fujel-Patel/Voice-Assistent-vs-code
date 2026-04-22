from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from collections import OrderedDict, deque
from io import BytesIO
from typing import Any

import httpx

from config.config_loader import load_config
from core.logger import get_logger

logger = get_logger(__name__)

SCREEN_ANALYSIS_PROMPT = (
    "You are analyzing a screenshot from a desktop computer. "
    "Describe what you see in a concise manner. Focus on active app/window title, "
    "main visible content, errors/warnings, and relevant UI elements."
)


class ScreenAnalyzer:
    def __init__(self, max_per_minute: int = 5, cache_size: int = 5) -> None:
        self.max_per_minute = max_per_minute
        self.cache_size = cache_size
        self._timestamps: deque[float] = deque()
        self._cache: OrderedDict[str, str] = OrderedDict()

        cfg = load_config()
        self.api_key = cfg.provider_keys.anthropic_api_key
        self.model = cfg.brain.models.claude
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def describe_screen(self, image) -> str:
        return await self.answer_about_screen(image, "Describe what is visible on this screen.")

    async def answer_about_screen(self, image, question: str) -> str:
        await self._check_rate_limit()
        image_hash = self._image_hash(image)
        cache_key = f"{image_hash}:{question.strip().lower()}"
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        answer = await self._send_vision_prompt(image, question)
        self._cache[cache_key] = answer
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
        return answer

    async def extract_structured_data(self, image) -> dict[str, Any]:
        prompt = "Extract structured content from this screen as JSON with keys: app, title, errors, lists, forms."
        answer = await self.answer_about_screen(image, prompt)
        return {"raw": answer}

    async def find_element(self, image, description: str) -> dict[str, Any]:
        prompt = (
            "Find this UI element and describe where it is located: "
            f"{description}. Return concise location clues and nearby labels."
        )
        answer = await self.answer_about_screen(image, prompt)
        return {"description": description, "result": answer}

    async def _check_rate_limit(self) -> None:
        now = time.time()
        while self._timestamps and now - self._timestamps[0] > 60.0:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_per_minute:
            raise RuntimeError("Screen analysis rate limit reached (5 per minute)")
        self._timestamps.append(now)

    async def _send_vision_prompt(self, image, question: str) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured for screen analysis")

        logger.warning("Sending screenshot to Claude Vision for analysis")
        encoded = self._encode_image(image)

        payload = {
            "model": self.model,
            "max_tokens": 500,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{SCREEN_ANALYSIS_PROMPT}\n\nQuestion: {question}"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": encoded,
                            },
                        },
                    ],
                }
            ],
        }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            if response.status_code >= 400:
                raise RuntimeError(f"Claude Vision API error: {response.status_code} {response.text}")
            data = response.json()

        chunks: list[str] = []
        for block in data.get("content", []):
            text = block.get("text", "")
            if text:
                chunks.append(text)

        return "\n".join(chunks).strip()

    def _encode_image(self, image) -> str:
        with BytesIO() as buf:
            image.save(buf, format="JPEG", quality=85, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _image_hash(self, image) -> str:
        return hashlib.sha256(image.tobytes()).hexdigest()
