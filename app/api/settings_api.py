"""Settings, per-song offsets, target language, and cache management APIs."""

import logging
from cache_service import get_cache

logger = logging.getLogger("SettingsAPI")


class SettingsAPIMixin:
    def get_settings(self):
        """Returns every persisted setting (JSON-decoded by the cache)."""
        return get_cache().get_settings()

    def save_settings(self, values):
        """Persists a mapping of settings."""
        if not isinstance(values, dict):
            return False
        return get_cache().set_settings(values)

    def get_song_offset(self, artist, title):
        """Returns the saved lyric offset in seconds for a track."""
        return get_cache().get_song_offset(artist, title)

    def set_song_offset(self, artist, title, offset):
        """Saves the lyric offset in seconds for a track and returns it."""
        return get_cache().set_song_offset(artist, title, offset)

    def clear_cache(self):
        """Clears lyrics/translation/thumbnail caches, keeping user data."""
        return get_cache().clear_cache()

    def get_cache_stats(self):
        """Returns data directory, database size and cache row counts."""
        return get_cache().get_cache_stats()

    def set_target_language(self, lang):
        """Switches the target translation language dynamically."""
        self._app.translator_service.set_target_lang(lang)
        self._app.reload_current_lyrics()
