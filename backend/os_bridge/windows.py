from __future__ import annotations

import shutil


def has_tool(tool_name: str) -> bool:
    return shutil.which(tool_name) is not None
