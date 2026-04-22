import os
import google.generativeai as genai
from typing import Dict, Any

class GeminiAgent:
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(self.model_name)

    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        # TODO: integrate context
        response = await self.model.generate_content_async(prompt)
        return response.text
