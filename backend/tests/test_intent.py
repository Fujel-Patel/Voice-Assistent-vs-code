from __future__ import annotations

import pytest

from brain.intent import IntentClassifier, IntentRouter


def test_conversation_intent() -> None:
    classifier = IntentClassifier()
    payload = classifier.parse(
        '{"intent":"conversation","response":"Weather is clear.","action":null}'
    )
    assert payload["intent"] == "conversation"


def test_open_app_intent() -> None:
    classifier = IntentClassifier()
    payload = classifier.parse(
        '{"intent":"open-app","response":"Opening VS Code.","action":{"type":"open-app","params":{"app_name":"Visual Studio Code"}}}'
    )
    assert payload["intent"] == "open-app"


def test_unknown_intent() -> None:
    classifier = IntentClassifier()
    payload = classifier.parse("not-json-gibberish")
    assert payload["intent"] == "unknown"


def test_conversation_spacing_normalization() -> None:
    classifier = IntentClassifier()
    payload = classifier.parse('{"intent":"conversation","response":"Hello,sir.IamJARVIS.HowmayIassistyou?","action":null}')
    assert payload["intent"] == "conversation"
    assert payload["response"] == "Hello, sir. I am JARVIS. How may I assist you?"


@pytest.mark.asyncio
async def test_intent_router() -> None:
    called = {"value": False}

    async def mock_handler(action):
        called["value"] = True
        return {"status": "ok", "action": action}

    router = IntentRouter()
    router.register("open-app", mock_handler)

    result = await router.route(
        {
            "intent": "open-app",
            "response": "Opening VS Code.",
            "action": {"type": "open-app", "params": {"app_name": "Visual Studio Code"}},
        }
    )

    assert called["value"] is True
    assert result["status"] == "ok"
