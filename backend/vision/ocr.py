from __future__ import annotations

import asyncio
import hashlib
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

if TYPE_CHECKING:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
else:
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except ImportError:
        Image = Any
        ImageEnhance = Any
        ImageFilter = Any
        ImageOps = Any

if TYPE_CHECKING:
    import pytesseract
else:
    try:
        import pytesseract
    except ImportError:
        pytesseract = Any

from core.logger import get_logger

logger = get_logger(__name__)


class OCREngine:
    def __init__(self, languages: str = "eng", cache_size: int = 5) -> None:
        self.languages = languages
        self.cache_size = cache_size
        self._cache: OrderedDict[str, str] = OrderedDict()

    async def extract_text(self, image: PILImage) -> str:
        key = self._image_hash(image)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        text = await asyncio.to_thread(self._extract_text_sync, image)
        self._cache[key] = text
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
        return text

    async def extract_regions(self, image: PILImage) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._extract_regions_sync, image)

    async def extract_from_region(
        self, image: PILImage, x: int, y: int, w: int, h: int
    ) -> str:
        region = image.crop((x, y, x + w, y + h))
        return await self.extract_text(region)

    def _extract_text_sync(self, image: PILImage) -> str:
        if pytesseract is None or Image is None:
            raise RuntimeError(
                "OCR dependencies unavailable. Install pytesseract and Pillow."
            )

        if image is None or image.size[0] == 0 or image.size[1] == 0:
            return ""

        prepared = self._prepare(image)
        try:
            text = str(pytesseract.image_to_string(prepared, lang=self.languages))
            return text.strip()
        except pytesseract.pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract not installed. Install with: sudo apt install tesseract-ocr"
            ) from exc

    def _extract_regions_sync(self, image: PILImage) -> list[dict[str, Any]]:
        if pytesseract is None or Image is None:
            raise RuntimeError(
                "OCR dependencies unavailable. Install pytesseract and Pillow."
            )

        if image is None or image.size[0] == 0 or image.size[1] == 0:
            return []

        prepared = self._prepare(image)
        data = pytesseract.image_to_data(
            prepared, output_type=pytesseract.Output.DICT, lang=self.languages
        )
        result: list[dict[str, Any]] = []

        count = len(data.get("text", []))
        for i in range(count):
            text = (data.get("text", [""])[i] or "").strip()
            conf_raw = data.get("conf", ["-1"])[i]
            try:
                conf_val = float(conf_raw)
            except Exception:
                conf_val = -1.0
            if not text:
                continue
            result.append(
                {
                    "text": text,
                    "bbox": [
                        int(data.get("left", [0])[i]),
                        int(data.get("top", [0])[i]),
                        int(data.get("width", [0])[i]),
                        int(data.get("height", [0])[i]),
                    ],
                    "confidence": max(0.0, min(1.0, conf_val / 100.0)),
                }
            )

        if result and all(item["confidence"] < 0.35 for item in result):
            logger.warning("OCR confidence is low for the current screenshot")

        return result

    def _prepare(self, image: PILImage) -> PILImage:
        if Image is None:
            return image

        gray = ImageOps.grayscale(image)
        contrast = ImageEnhance.Contrast(gray).enhance(1.7)
        if contrast.width < 1200:
            contrast = contrast.resize(
                (contrast.width * 2, contrast.height * 2), Image.Resampling.LANCZOS
            )
        denoised = contrast.filter(ImageFilter.MedianFilter(size=3))
        return denoised

    def _image_hash(self, image: PILImage) -> str:
        if Image is None:
            return ""
        raw = image.tobytes()
        return hashlib.sha256(raw).hexdigest()
