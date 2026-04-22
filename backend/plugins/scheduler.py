"""
Jarvis Plugins — Scheduler Stub (Phase 8)
==========================================
Phase 8 will implement task scheduling using APScheduler.
Architecture review: "Remind me in 30 minutes" needs a scheduler.
"""

from plugins.base import JarvisPlugin, PluginResult
from core.logger import get_logger

logger = get_logger(__name__)


class SchedulerPlugin(JarvisPlugin):
    """TODO Phase 8: Reminders, timers, and scheduled tasks using APScheduler."""

    name = "scheduler"
    intents = ["set-reminder", "set-timer", "cancel-reminder", "list-reminders"]

    async def execute(self, intent: dict, context: dict) -> PluginResult:
        action = intent.get("intent")
        logger.warning(f"[TODO Phase 8] Scheduler: {action}")
        return PluginResult(
            success=False,
            output="Scheduling is not yet implemented (coming in Phase 8).",
            error="not_implemented",
        )
