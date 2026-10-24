"""Lyrics fetching, manual selection, and local file storage APIs."""

import logging
import os
import threading
import app_paths
import lyrics_providers

logger = logging.getLogger("LyricsAPI")


def _make_track_key(artist, title):
    return f"{artist or ''} - {title or ''}"


class LyricsAPIMixin:
    def retry_lyrics(self):
        self._app.reload_current_lyrics()

    def search_lyrics(self, artist, title, duration=0):
        """Returns scored lyric candidates for the current track."""
        try:
            return self._app.lyrics_service.search_lyrics(
                artist or "", title or "", duration or 0
            )
        except Exception as exc:
            logger.warning("Lyrics search failed: %s", exc)
            return []

    def select_lyrics(self, artist, title, duration, candidate):
        """Fetches an explicitly chosen candidate for the lyrics pane."""
        if not isinstance(candidate, dict) or not candidate.get("provider"):
            return False

        artist = str(artist or "")
        title = str(title or "")
        if not title:
            return False
        try:
            duration = float(duration or 0)
        except (TypeError, ValueError):
            duration = 0.0

        app = self._app
        with app.state_lock:
            app.current_generation_id += 1
            generation_id = app.current_generation_id
            app.current_lyrics_key = _make_track_key(artist, title)
            app._pending_lyrics = None
            app._pending_translations = None

        threading.Thread(
            target=app._fetch_and_translate_lyrics,
            args=(artist, title, duration, generation_id, candidate),
            daemon=True,
        ).start()
        return True

    def save_local_lyrics(self, artist, title, lines):
        """Saves lyrics as a local .lrc and reloads if it is the current song."""
        result = lyrics_providers.save_local_lrc(artist, title, lines)
        if not result.get("ok"):
            return result

        app = self._app
        with app.state_lock:
            live_artist = app.current_artist
            live_title = app.current_title
            live_duration = app.current_duration
            matches_live = bool(title) and (
                _make_track_key(artist, title)
                == _make_track_key(live_artist, live_title)
            )
            generation_id = None
            if matches_live:
                app.current_generation_id += 1
                generation_id = app.current_generation_id
                app.current_lyrics_key = _make_track_key(artist, title)
                app._pending_lyrics = None
                app._pending_translations = None

        result["reloaded"] = matches_live
        if matches_live:
            local_candidate = {
                "provider": "local",
                "id": os.path.basename(result.get("path") or ""),
                "title": title,
                "artist": artist,
            }
            threading.Thread(
                target=app._fetch_and_translate_lyrics,
                args=(
                    live_artist,
                    live_title,
                    live_duration,
                    generation_id,
                    local_candidate,
                ),
                daemon=True,
            ).start()
        return result

    def get_lrc_folder(self):
        """Returns the folder where local .lrc files are stored."""
        return str(app_paths.get_lrc_dir())

    def open_lrc_folder(self):
        """Opens the local lyrics folder in the system file browser."""
        try:
            folder = str(app_paths.get_lrc_dir())
            if hasattr(os, "startfile"):
                os.startfile(folder)
            else:
                logger.warning("Opening folders is not supported on this platform")
                return False
            return True
        except OSError as exc:
            logger.warning("Could not open lrc folder: %s", exc)
            return False

    def get_lyrics_providers(self):
        """Returns provider metadata for the lyrics search UI."""
        return lyrics_providers.get_lyrics_providers()
