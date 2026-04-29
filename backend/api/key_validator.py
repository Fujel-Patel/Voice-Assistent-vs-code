from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx


def _to_model_options(
    items: list[dict[str, Any]], *, id_key: str = "id", label_key: str = "name"
) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for item in items:
        model_id = str(item.get(id_key) or "").strip()
        if not model_id:
            continue
        label = str(item.get(label_key) or model_id).strip() or model_id
        options.append({"value": model_id, "label": label})
    return options


async def validate_anthropic_key(key: str) -> dict[str, Any]:
    if not key or not key.startswith("sk-ant"):
        return {"valid": False, "details": "Invalid Anthropic key format"}

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "ping"}],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=payload
            )
        if response.status_code < 400:
            models: list[dict[str, str]] = []
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    models_res = await client.get(
                        "https://api.anthropic.com/v1/models", headers=headers
                    )
                if models_res.status_code < 400:
                    models_data = models_res.json() if models_res.text else {}
                    models = _to_model_options(
                        models_data.get("data", []),
                        id_key="id",
                        label_key="display_name",
                    )
            except Exception:
                # Model discovery isn't critical for key validation.
                pass

            return {
                "valid": True,
                "details": "Anthropic key verified",
                "models": models[:100],
            }
        return {
            "valid": False,
            "details": f"Anthropic rejected key ({response.status_code})",
        }
    except Exception as exc:
        return {"valid": False, "details": f"Validation error: {exc}"}


async def validate_elevenlabs_key(key: str) -> dict[str, Any]:
    if not key:
        return {"valid": False, "details": "Missing ElevenLabs key"}

    headers = {"xi-api-key": key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/user/subscription", headers=headers
            )
        if response.status_code < 400:
            data = response.json() if response.text else {}
            remaining = data.get("character_limit", 0) - data.get("character_count", 0)
            return {
                "valid": True,
                "details": "ElevenLabs key verified",
                "remaining_quota": max(0, remaining),
            }
        return {
            "valid": False,
            "details": f"ElevenLabs rejected key ({response.status_code})",
        }
    except Exception as exc:
        return {"valid": False, "details": f"Validation error: {exc}"}


async def validate_openwakeword_key(_key: str) -> dict[str, Any]:
    # openWakeWord is fully local and does not require an API key.
    return {
        "valid": True,
        "details": "openWakeWord is local and does not require an API key",
    }


async def validate_brave_key(key: str) -> dict[str, Any]:
    if not key:
        return {"valid": False, "details": "Missing Brave API key"}

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": key,
    }
    params: dict[str, Any] = {"q": "jarvis health check", "count": 1}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
            )
        if response.status_code < 400:
            return {"valid": True, "details": "Brave key verified"}
        return {
            "valid": False,
            "details": f"Brave rejected key ({response.status_code})",
        }
    except Exception as exc:
        return {"valid": False, "details": f"Validation error: {exc}"}


async def validate_gemini_key(key: str) -> dict[str, Any]:
    if not key:
        return {"valid": False, "details": "Missing Gemini API key"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
        if response.status_code < 400:
            data = response.json() if response.text else {}
            models = []
            for entry in data.get("models", []):
                name = str(entry.get("name") or "")
                methods = entry.get("supportedGenerationMethods") or []
                if not name.startswith("models/"):
                    continue
                if methods and "generateContent" not in methods:
                    continue
                model_id = name.split("models/", 1)[1].strip()
                if model_id:
                    models.append({"value": model_id, "label": model_id})

            return {
                "valid": True,
                "details": "Gemini key verified",
                "models": models[:100],
            }
        return {
            "valid": False,
            "details": f"Gemini rejected key ({response.status_code})",
        }
    except Exception as exc:
        return {"valid": False, "details": f"Validation error: {exc}"}


async def validate_groq_key(key: str) -> dict[str, Any]:
    if not key:
        return {"valid": False, "details": "Missing Groq API key"}

    headers = {"Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models", headers=headers
            )
        if response.status_code < 400:
            data = response.json() if response.text else {}
            models = _to_model_options(
                data.get("data", []), id_key="id", label_key="id"
            )
            return {
                "valid": True,
                "details": "Groq key verified",
                "models": models[:100],
            }
        return {
            "valid": False,
            "details": f"Groq rejected key ({response.status_code})",
        }
    except Exception as exc:
        return {"valid": False, "details": f"Validation error: {exc}"}


async def validate_openrouter_key(key: str) -> dict[str, Any]:
    if not key:
        return {"valid": False, "details": "Missing OpenRouter API key"}

    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://jarvis.local",
        "X-Title": "Jarvis Assistant",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models", headers=headers
            )
        if response.status_code < 400:
            data = response.json() if response.text else {}
            models = _to_model_options(
                data.get("data", []), id_key="id", label_key="name"
            )
            return {
                "valid": True,
                "details": "OpenRouter key verified",
                "models": models[:150],
            }
        return {
            "valid": False,
            "details": f"OpenRouter rejected key ({response.status_code})",
        }
    except Exception as exc:
        return {"valid": False, "details": f"Validation error: {exc}"}


async def validate_ollama_key(key: str) -> dict[str, Any]:
    # Ollama local deployments often do not require an API key.
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "http://localhost:11434/api/tags", headers=headers
            )
        if response.status_code < 400:
            data = response.json() if response.text else {}
            models = []
            for model in data.get("models", []):
                model_name = str(model.get("name") or "").strip()
                if not model_name:
                    continue
                models.append({"value": model_name, "label": model_name})
            return {
                "valid": True,
                "details": "Ollama local server reachable",
                "models": models[:100],
            }
        return {
            "valid": False,
            "details": f"Ollama reachable but rejected request ({response.status_code})",
        }
    except Exception as exc:
        return {
            "valid": False,
            "details": f"Could not reach local Ollama server at localhost:11434 ({exc})",
        }


ValidatorFn = Callable[[str], Awaitable[dict[str, Any]]]

_PROVIDER_VALIDATORS: dict[str, ValidatorFn] = {
    "anthropic": validate_anthropic_key,
    "gemini": validate_gemini_key,
    "groq": validate_groq_key,
    "openrouter": validate_openrouter_key,
    "ollama": validate_ollama_key,
    "elevenlabs": validate_elevenlabs_key,
    "openwakeword": validate_openwakeword_key,
    "porcupine": validate_openwakeword_key,
    "picovoice": validate_openwakeword_key,
    "brave": validate_brave_key,
}


async def validate_key(provider: str, key: str) -> dict[str, Any]:
    provider = (provider or "").lower().strip()
    validator = _PROVIDER_VALIDATORS.get(provider)
    if validator:
        return await validator(key)
    return {"valid": False, "details": f"Unknown provider '{provider}'"}
