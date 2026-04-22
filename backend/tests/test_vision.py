from __future__ import annotations

import pytest
Image = pytest.importorskip("PIL.Image", reason="Pillow is required for vision tests")
ImageDraw = pytest.importorskip("PIL.ImageDraw", reason="Pillow is required for vision tests")

from plugins.screen_reader import ScreenReaderPlugin
from vision.analyzer import ScreenAnalyzer
from vision.capture import ScreenCapture
from vision.ocr import OCREngine


@pytest.fixture
def sample_image() -> Image.Image:
    image = Image.new("RGB", (300, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 40), "Error: File not found", fill="black")
    return image


@pytest.mark.asyncio
async def test_screenshot_capture(mocker, sample_image) -> None:
    capture = ScreenCapture(save_by_default=False)
    mocker.patch.object(capture, "capture_full", return_value=sample_image)

    image = await capture.capture_full()
    assert image.size == sample_image.size


def test_multi_monitor_list(mocker) -> None:
    class FakeMSS:
        monitors = [
            {},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},
        ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    mocker.patch("vision.capture.mss.mss", return_value=FakeMSS())

    capture = ScreenCapture(save_by_default=False)
    monitors = capture.list_monitors()
    assert len(monitors) == 2
    assert monitors[0]["is_primary"] is True


@pytest.mark.asyncio
async def test_ocr_text_extraction(mocker, sample_image) -> None:
    engine = OCREngine()
    mocker.patch.object(engine, "_extract_text_sync", return_value="Error: File not found")

    text = await engine.extract_text(sample_image)
    assert "Error" in text


@pytest.mark.asyncio
async def test_ocr_empty_image(mocker, sample_image) -> None:
    engine = OCREngine()
    mocker.patch.object(engine, "_extract_text_sync", return_value="")
    text = await engine.extract_text(sample_image)
    assert text == ""


@pytest.mark.asyncio
async def test_claude_vision_analysis(mocker, sample_image) -> None:
    analyzer = ScreenAnalyzer()
    mocker.patch.object(analyzer, "_send_vision_prompt", return_value="VS Code showing a Python error")

    text = await analyzer.describe_screen(sample_image)
    assert "error" in text.lower()


@pytest.mark.asyncio
async def test_screen_reader_plugin(mocker, sample_image) -> None:
    plugin = ScreenReaderPlugin()
    mocker.patch.object(plugin.capture, "capture_active_window", return_value=sample_image)
    mocker.patch.object(plugin.analyzer, "describe_screen", return_value="Browser with docs page")

    result = await plugin.execute({"type": "screen-read", "params": {"action": "describe"}}, context={})
    assert result.success is True
    assert "Browser" in result.output


@pytest.mark.asyncio
async def test_rate_limiting(sample_image) -> None:
    analyzer = ScreenAnalyzer(max_per_minute=1)
    analyzer._timestamps.append(__import__("time").time())

    with pytest.raises(RuntimeError, match="rate limit"):
        await analyzer.answer_about_screen(sample_image, "what is on screen?")
