from __future__ import annotations

import datetime as dt
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    import mss
except Exception:  # pragma: no cover
    mss = None

from core.logger import get_logger

logger = get_logger(__name__)


class ScreenCapture:
    def __init__(self, save_by_default: bool = True, keep_last: int = 50) -> None:
        self.save_by_default = save_by_default
        self.keep_last = keep_last
        self.output_dir = Path.home() / "Pictures" / "jarvis_screenshots"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def list_monitors(self) -> list[dict[str, Any]]:
        if mss is None:
            return []
        with mss.mss() as sct:
            monitors = sct.monitors[1:] if len(sct.monitors) > 1 else sct.monitors
            return [
                {
                    "index": idx,
                    "left": m.get("left", 0),
                    "top": m.get("top", 0),
                    "width": m.get("width", 0),
                    "height": m.get("height", 0),
                    "is_primary": idx == 1,
                }
                for idx, m in enumerate(monitors, start=1)
            ]

    async def capture_full(self, save: bool | None = None):
        if mss is None or Image is None:
            raise RuntimeError("Screenshot dependencies unavailable. Install mss and Pillow.")

        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        image = self._post_process(image)
        if save if save is not None else self.save_by_default:
            self._save_image(image)
        return image

    async def capture_monitor(self, index: int, save: bool | None = None):
        if mss is None or Image is None:
            raise RuntimeError("Screenshot dependencies unavailable. Install mss and Pillow.")

        with mss.mss() as sct:
            all_monitors = sct.monitors
            if index < 1 or index >= len(all_monitors):
                raise ValueError(f"Invalid monitor index: {index}")
            shot = sct.grab(all_monitors[index])
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        image = self._post_process(image)
        if save if save is not None else self.save_by_default:
            self._save_image(image)
        return image

    async def capture_region(self, x: int, y: int, w: int, h: int, save: bool | None = None):
        if mss is None or Image is None:
            raise RuntimeError("Screenshot dependencies unavailable. Install mss and Pillow.")

        monitor = {"left": x, "top": y, "width": w, "height": h}
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        image = self._post_process(image)
        if save if save is not None else self.save_by_default:
            self._save_image(image)
        return image

    async def capture_active_window(self, save: bool | None = None):
        region = self._active_window_region()
        if region is None:
            return await self.capture_full(save=save)
        return await self.capture_region(*region, save=save)

    def encode_for_api(self, image, quality: int = 85) -> bytes:
        if Image is None:
            raise RuntimeError("Pillow is required for image encoding")
        processed = self._post_process(image)
        with BytesIO() as buf:
            processed.save(buf, format="JPEG", quality=quality, optimize=True)
            return buf.getvalue()

    def _active_window_region(self) -> tuple[int, int, int, int] | None:
        try:
            cmd = ["bash", "-lc", "xwininfo -id $(xdotool getactivewindow) | awk '/Absolute upper-left X|Absolute upper-left Y|Width|Height/ {print $4}'"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            values = [int(v.strip()) for v in result.stdout.splitlines() if v.strip()]
            if len(values) == 4:
                return values[0], values[1], values[2], values[3]
        except Exception:
            return None
        return None

    def _post_process(self, image):
        if Image is None:
            return image
        max_side = max(image.size)
        if max_side <= 1568:
            return image
        scale = 1568.0 / float(max_side)
        resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
        return resized

    def _save_image(self, image) -> Path:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.output_dir / f"screen_{ts}.jpg"
        image.save(path, format="JPEG", quality=85, optimize=True)
        self._cleanup_old()
        return path

    def _cleanup_old(self) -> None:
        files = sorted(self.output_dir.glob("screen_*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
        for extra in files[self.keep_last :]:
            try:
                extra.unlink(missing_ok=True)
            except Exception:
                logger.warning(f"Unable to delete old screenshot: {extra}")
