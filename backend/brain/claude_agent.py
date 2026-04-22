from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from brain.intent import IntentClassifier
from brain.prompt_templates import JARVIS_SYSTEM_PROMPT
from core.error_handler import APIError, ConfigError
from core.logger import get_logger
from core.retry import retry

logger = get_logger(__name__)


@dataclass
class BrainResult:
    intent: str
    response_text: str
    action: dict[str, Any] | None
    tokens_used: dict[str, int]
    model: str
    raw_text: str


class ClaudeAgent:
    """Phase-2 brain agent supporting multiple providers behind one interface."""

    def __init__(self, config, context_builder, system_prompt: str | None = None) -> None:
        self.config = config
        self.context_builder = context_builder
        self.intent_classifier = IntentClassifier()
        self.system_prompt = system_prompt or JARVIS_SYSTEM_PROMPT

    async def process_input(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        provider_order = self._provider_order(context.get("preferred_provider"))
        errors: list[str] = []

        for provider_name in provider_order:
            try:
                result = await self._call_provider(provider_name, text)
                parsed = self.intent_classifier.parse(result.raw_text)
                payload = {
                    "intent": parsed["intent"],
                    "response_text": parsed["response"],
                    "action": parsed["action"],
                    "tokens_used": result.tokens_used,
                    "model": result.model,
                    "provider": provider_name,
                }
                logger.info(
                    f"Brain response provider={provider_name} model={result.model} "
                    f"input_tokens={result.tokens_used.get('input', 0)} "
                    f"output_tokens={result.tokens_used.get('output', 0)}"
                )
                return payload
            except Exception as exc:
                errors.append(f"{provider_name}: {exc}")
                logger.warning(f"Provider failed ({provider_name}): {exc}")

        return {
            "intent": "unknown",
            "response_text": "I'm having trouble connecting to my brain providers right now.",
            "action": None,
            "tokens_used": {"input": 0, "output": 0},
            "model": "fallback",
            "provider": "fallback",
            "errors": errors,
        }

    async def process_with_context(
        self,
        query: str,
        search_results: list[dict[str, Any]],
        pages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        context_lines = [f'Web search results for "{query}":']

        for index, item in enumerate(search_results[:8], start=1):
            context_lines.append(
                f"{index}. {item.get('title', 'Untitled')} ({item.get('url', '')})\n"
                f"   {item.get('description', '')}"
            )

        if pages:
            context_lines.append("\nFetched page excerpts:")
            budget_chars = 8000
            used = 0
            for page in pages[:3]:
                title = page.get("title", "Untitled")
                url = page.get("url", "")
                content = " ".join((page.get("content", "") or "").split())
                if not content:
                    continue
                excerpt = content[:1600]
                block = f"- {title} ({url}): {excerpt}"
                if used + len(block) > budget_chars:
                    break
                context_lines.append(block)
                used += len(block)

        context_blob = "\n".join(context_lines)
        synthesis_prompt = (
            f"{context_blob}\n\n"
            f"Based on these web results, answer the user's question below and cite source URLs inline.\n"
            f"Question: {query}"
        )
        return await self.process_input(synthesis_prompt, {"preferred_provider": "claude"})

    async def stream_response(
        self,
        text: str,
        context: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        provider_order = self._provider_order(context.get("preferred_provider"))
        last_error: Exception | None = None
        errors: list[str] = []

        for provider_name in provider_order:
            try:
                full_text = ""
                async for chunk in self._stream_provider(provider_name, text):
                    full_text += chunk
                    yield {
                        "type": "assistant_response_chunk",
                        "payload": {"text_chunk": chunk, "is_final": False},
                    }

                parsed = self.intent_classifier.parse(full_text)
                yield {
                    "type": "assistant_response_chunk",
                    "payload": {
                        "text_chunk": "",
                        "is_final": True,
                        "intent": parsed["intent"],
                        "response": parsed["response"],
                        "action": parsed["action"],
                        "provider": provider_name,
                    },
                }
                return
            except Exception as exc:
                last_error = exc
                errors.append(f"{provider_name}: {exc}")
                logger.warning(f"Streaming provider failed ({provider_name}): {exc}")

        logger.error(f"All streaming providers failed. last_error={last_error}")
        fallback_text = "I'm having trouble connecting to my AI providers right now. Please check API keys or local model setup."
        yield {
            "type": "assistant_response_chunk",
            "payload": {
                "text_chunk": fallback_text,
                "is_final": True,
                "intent": "unknown",
                "response": fallback_text,
                "action": None,
                "provider": "fallback",
                "errors": errors,
            },
        }

    def _provider_order(self, preferred: str | None = None) -> list[str]:
        order = list(self.config.brain.providers.fallback_order)
        default_provider = self.config.brain.providers.default_provider
        if default_provider in order:
            order.remove(default_provider)
            order.insert(0, default_provider)
        if preferred and preferred in order:
            order.remove(preferred)
            order.insert(0, preferred)
        return order

    def _gemini_candidate_models(self) -> list[str]:
        configured = (self.config.brain.models.gemini or "").strip()
        ordered = [
            configured,
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]

        deduped: list[str] = []
        for model in ordered:
            if not model or model in deduped:
                continue
            deduped.append(model)
        return deduped

    async def _call_provider(self, provider_name: str, text: str) -> BrainResult:
        if provider_name == "claude":
            return await self._call_claude(text)
        if provider_name == "gemini":
            return await self._call_gemini(text)
        if provider_name in {"groq", "openrouter", "ollama"}:
            return await self._call_openai_compatible(provider_name, text)
        raise ConfigError(f"Unsupported provider: {provider_name}")

    async def _stream_provider(self, provider_name: str, text: str) -> AsyncIterator[str]:
        if provider_name in {"groq", "openrouter", "ollama"}:
            async for chunk in self._stream_openai_compatible(provider_name, text):
                yield chunk
            return

        # Fallback for providers without direct streaming integration in this phase.
        result = await self._call_provider(provider_name, text)
        parsed = self.intent_classifier.parse(result.raw_text)
        stream_text = (parsed.get("response") or result.response_text or "").strip()
        
        # Yield in logical chunks (delimiters) to avoid stuttering TTS
        import re
        chunks = re.split(r"(?<=[.!?\n,])\s+", stream_text)
        for chunk in chunks:
            if chunk.strip():
                yield chunk + " "
                await asyncio.sleep(0.01)

    async def _build_messages(self, text: str) -> list[dict[str, str]]:
        return await self.context_builder.build_context(current_input=text)

    @retry(max_retries=3, base_delay=1.0, exceptions_to_retry=(APIError,))
    async def _call_claude(self, text: str) -> BrainResult:
        key = self.config.provider_keys.anthropic_api_key
        if not key:
            raise ConfigError("ANTHROPIC_API_KEY is missing")

        try:
            from anthropic import AsyncAnthropic
        except Exception as exc:
            raise APIError(f"anthropic package unavailable: {exc}") from exc

        model = self.config.brain.models.claude
        client = AsyncAnthropic(api_key=key)
        messages = await self._build_messages(text)

        response = await client.messages.create(
            model=model,
            max_tokens=800,
            temperature=0.2,
            system=self.system_prompt,
            messages=messages,
        )

        text_chunks = []
        for block in response.content:
            block_text = getattr(block, "text", "")
            if block_text:
                text_chunks.append(block_text)

        usage = getattr(response, "usage", None)
        return BrainResult(
            intent="unknown",
            response_text="".join(text_chunks),
            action=None,
            tokens_used={
                "input": int(getattr(usage, "input_tokens", 0) or 0),
                "output": int(getattr(usage, "output_tokens", 0) or 0),
            },
            model=model,
            raw_text="".join(text_chunks),
        )

    @retry(max_retries=3, base_delay=1.0, exceptions_to_retry=(APIError,))
    async def _call_gemini(self, text: str) -> BrainResult:
        key = self.config.provider_keys.gemini_api_key
        if not key:
            raise ConfigError("GEMINI_API_KEY is missing")

        base_url = self.config.provider_keys.gemini_base_url.rstrip("/")
        messages = await self._build_messages(text)
        prompt_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0.2},
        }

        attempted_models: list[str] = []
        data: dict[str, Any] | None = None
        selected_model: str | None = None

        async with httpx.AsyncClient(timeout=45.0) as client:
            for model in self._gemini_candidate_models():
                attempted_models.append(model)
                url = f"{base_url}/models/{model}:generateContent?key={key}"
                r = await client.post(url, json=payload)

                if r.status_code == 404:
                    # Try the next known model alias before failing.
                    continue

                if r.status_code >= 400:
                    raise APIError(f"Gemini API error: {r.status_code} {r.text}")

                data = r.json()
                selected_model = model
                break

        if data is None or selected_model is None:
            raise ConfigError(
                "Gemini model not found for this API key/version. "
                f"Tried: {', '.join(attempted_models)}"
            )

        candidates = data.get("candidates", [])
        text_out = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text_out = "".join(part.get("text", "") for part in parts)

        usage = data.get("usageMetadata", {})
        return BrainResult(
            intent="unknown",
            response_text=text_out,
            action=None,
            tokens_used={
                "input": int(usage.get("promptTokenCount", 0) or 0),
                "output": int(usage.get("candidatesTokenCount", 0) or 0),
            },
            model=selected_model,
            raw_text=text_out,
        )

    @retry(max_retries=3, base_delay=1.0, exceptions_to_retry=(APIError,))
    async def _call_openai_compatible(self, provider_name: str, text: str) -> BrainResult:
        endpoint, key, model, extra_headers = self._openai_compatible_config(provider_name)
        messages = await self._build_messages(text)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }
        headers = {"Content-Type": "application/json", **extra_headers}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(f"{endpoint}/chat/completions", headers=headers, json=payload)
            if r.status_code >= 400:
                raise APIError(f"{provider_name} API error: {r.status_code} {r.text}")
            data = r.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return BrainResult(
            intent="unknown",
            response_text=content,
            action=None,
            tokens_used={
                "input": int(usage.get("prompt_tokens", 0) or 0),
                "output": int(usage.get("completion_tokens", 0) or 0),
            },
            model=model,
            raw_text=content,
        )

    async def _stream_openai_compatible(self, provider_name: str, text: str) -> AsyncIterator[str]:
        endpoint, key, model, extra_headers = self._openai_compatible_config(provider_name)
        messages = await self._build_messages(text)

        headers = {"Content-Type": "application/json", **extra_headers}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{endpoint}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise APIError(f"{provider_name} stream error: {response.status_code} {body.decode('utf-8', 'ignore')}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_line = line.removeprefix("data:").strip()
                    if data_line == "[DONE]":
                        break
                    try:
                        event = json.loads(data_line)
                    except json.JSONDecodeError:
                        continue
                    delta = event.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta

    def _openai_compatible_config(self, provider_name: str) -> tuple[str, str | None, str, dict[str, str]]:
        if provider_name == "groq":
            key = self.config.provider_keys.groq_api_key
            if not key:
                raise ConfigError("GROQ_API_KEY is missing")
            return (
                self.config.provider_keys.groq_base_url.rstrip("/"),
                key,
                self.config.brain.models.groq,
                {},
            )

        if provider_name == "openrouter":
            key = self.config.provider_keys.openrouter_api_key
            if not key:
                raise ConfigError("OPENROUTER_API_KEY is missing")
            return (
                self.config.provider_keys.openrouter_base_url.rstrip("/"),
                key,
                self.config.brain.models.openrouter,
                {
                    "HTTP-Referer": "https://jarvis.local",
                    "X-Title": "Jarvis Assistant",
                },
            )

        if provider_name == "ollama":
            return (
                f"{self.config.provider_keys.ollama_base_url.rstrip('/')}/v1",
                self.config.provider_keys.ollama_api_key,
                self.config.brain.models.ollama,
                {},
            )

        raise ConfigError(f"Unsupported OpenAI-compatible provider: {provider_name}")
