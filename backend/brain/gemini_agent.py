from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from google import genai
else:
    try:
        from google import genai
    except ImportError:
        genai = Any


class GeminiAgent:
    def __init__(
        self, api_key: str | None = None, model_name: str = "gemini-2.0-flash"
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = (
            genai.Client(api_key=self.api_key) if (genai and self.api_key) else None
        )

    async def generate_response(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> str:
        # TODO: integrate context
        if self.client is None:
            raise RuntimeError("GEMINI_API_KEY is missing or genai not installed")

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        text = getattr(response, "text", None)
        return text or ""
