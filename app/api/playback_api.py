"""Playback transport and audio volume APIs."""

import ctypes
import logging
import threading

logger = logging.getLogger("PlaybackAPI")


class PlaybackAPIMixin:
    def seek(self, seconds):
        if self._app.media_listener:
            self._app.media_listener.seek(float(seconds))

    def play_pause(self):
        if self._app.media_listener:
            self._app.media_listener.toggle_play_pause()

    def next_track(self):
        if self._app.media_listener:
            self._app.media_listener.next_track()

    def prev_track(self):
        if self._app.media_listener:
            self._app.media_listener.prev_track()

    def adjust_volume(self, delta):
        """Adjusts Windows master volume via native keybd_event."""
        try:
            user32 = ctypes.windll.user32
            VK_VOLUME_UP = 0xAF
            VK_VOLUME_DOWN = 0xAE
            vk = VK_VOLUME_UP if delta > 0 else VK_VOLUME_DOWN
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
        except Exception as e:
            logger.warning("Volume adjust error: %s", e)

    def set_sleep_timer(self, minutes):
        """Auto-pause Spotify after specified minutes."""
        if hasattr(self, "_sleep_timer") and self._sleep_timer:
            self._sleep_timer.cancel()
            self._sleep_timer = None

        minutes = float(minutes)
        if minutes > 0:
            def trigger_pause():
                if self._app.media_listener:
                    self._app.media_listener.toggle_play_pause()
                self._app.evaluate_js("window.onSleepTimerTriggered()")

            self._sleep_timer = threading.Timer(minutes * 60, trigger_pause)
            self._sleep_timer.daemon = True
            self._sleep_timer.start()
