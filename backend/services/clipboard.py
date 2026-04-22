"""
Jarvis Services — Clipboard Integration Stub
=============================================
Architecture review recommendation: "Read what I copied" is a killer feature.
Phase 8+ will complete this, but the interface is defined here.
"""

import pyperclip
from core.logger import get_logger

logger = get_logger(__name__)


class ClipboardService:
    """Read and write the system clipboard."""

    def read(self) -> str:
        """Get the current clipboard content."""
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Clipboard read error: {e}")
            return ""

    def write(self, text: str) -> bool:
        """Set the clipboard content."""
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            logger.error(f"Clipboard write error: {e}")
            return False


# Module-level singleton
clipboard = ClipboardService()
