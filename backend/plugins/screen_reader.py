from __future__ import annotations

from typing import Any

from vision.analyzer import ScreenAnalyzer
from vision.capture import ScreenCapture
from vision.ocr import OCREngine

from plugins.base import JarvisPlugin, PluginResult


class ScreenReaderPlugin(JarvisPlugin):
    name = "screen_reader"
    description = "Read and analyze screen content"
    intents = ["screen-read", "read-screen", "analyze-screen", "find-on-screen"]

    ACTIONS = {
        "describe": "Describe what's on screen",
        "read_text": "Read visible text using OCR",
        "read_error": "Find and explain error messages",
        "summarize": "Summarize visible content",
        "find_element": "Find a specific UI element",
    }

    def __init__(self) -> None:
        self.capture = ScreenCapture(save_by_default=True)
        self.ocr = OCREngine()
        self.analyzer = ScreenAnalyzer()

    async def execute(
        self, intent: dict[str, Any], context: dict[str, Any]
    ) -> PluginResult:
        params = (
            intent.get("params", {}) if isinstance(intent.get("params"), dict) else {}
        )
        action = str(params.get("action") or "describe").strip().lower()

        try:
            if action == "describe":
                image = await self.capture.capture_active_window()
                description = await self.analyzer.describe_screen(image)
                return PluginResult(success=True, output=description)

            if action == "read_text":
                image = await self.capture.capture_active_window()
                text = await self.ocr.extract_text(image)
                message = (
                    text if text else "I could not detect readable text on screen."
                )
                return PluginResult(success=True, output=message, data={"text": text})

            if action == "read_error":
                image = await self.capture.capture_full()
                answer = await self.analyzer.answer_about_screen(
                    image,
                    "Find any error messages or warnings and explain them.",
                )
                return PluginResult(success=True, output=answer)

            if action == "summarize":
                image = await self.capture.capture_active_window()
                text = await self.ocr.extract_text(image)
                summary = self._summarize_text(text)
                return PluginResult(success=True, output=summary, data={"text": text})

            if action == "find_element":
                target = str(
                    params.get("target") or params.get("description") or ""
                ).strip()
                if not target:
                    return PluginResult(
                        success=False,
                        output="Please specify which UI element to find.",
                        error="missing_target",
                    )
                image = await self.capture.capture_active_window()
                found = await self.analyzer.find_element(image, target)
                return PluginResult(
                    success=True, output=found.get("result", ""), data=found
                )

            return PluginResult(
                success=False,
                output=f"Unsupported screen action: {action}",
                error="unsupported_action",
            )
        except Exception as exc:
            return PluginResult(
                success=False, output="Screen analysis failed.", error=str(exc)
            )

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [
            {"intent": "screen-read", "description": f"{k}: {v}"}
            for k, v in self.ACTIONS.items()
        ]

    def _summarize_text(self, text: str) -> str:
        clean = " ".join(text.split())
        if not clean:
            return "I could not extract enough text to summarize."
        if len(clean) <= 260:
            return clean
        return f"{clean[:260].rstrip()}..."
