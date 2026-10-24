"""Unified AppAPI composite bridge."""

from .playback_api import PlaybackAPIMixin
from .lyrics_api import LyricsAPIMixin
from .settings_api import SettingsAPIMixin
from .window_api import WindowAPIMixin
from .vocab_api import VocabAPIMixin
from .history_api import HistoryAPIMixin
from .system_api import SystemAPIMixin


class AppAPI(
    PlaybackAPIMixin,
    LyricsAPIMixin,
    SettingsAPIMixin,
    WindowAPIMixin,
    VocabAPIMixin,
    HistoryAPIMixin,
    SystemAPIMixin,
):
    """Bridges frontend pywebview calls to the backend components."""

    def __init__(self, app):
        self._app = app
        self._sleep_timer = None
