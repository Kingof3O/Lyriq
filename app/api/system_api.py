"""System startup, close-to-tray, and Discord RPC APIs."""

import logging
import startup

logger = logging.getLogger("SystemAPI")


class SystemAPIMixin:
    def set_close_to_tray(self, enabled):
        """Enables or disables hiding the window instead of closing it."""
        return self._app.set_close_to_tray(bool(enabled))

    def set_start_with_windows(self, enabled):
        """Adds or removes the per-user Run registry entry."""
        return self._app.set_start_with_windows(bool(enabled))

    def get_startup_state(self):
        """Returns the live registry state for the startup toggle."""
        try:
            enabled = startup.is_start_with_windows()
        except Exception as exc:
            logger.warning("Could not read startup state: %s", exc)
            enabled = False
        return {"enabled": enabled, "supported": True}

    def toggle_discord_rpc(self, enabled):
        self._app.discord_rpc.enabled = bool(enabled)
        if not enabled:
            self._app.discord_rpc.clear()
