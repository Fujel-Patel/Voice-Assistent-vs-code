import os
from typing import Dict, Any

from google import genai

class GeminiAgent:
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        # TODO: integrate context
        if self.client is None:
            raise RuntimeError("GEMINI_API_KEY is missing")

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        text = getattr(response, "text", None)
        return text or ""
