import sys
import threading
import unittest
from unittest import mock


@unittest.skipUnless(sys.platform == "win32", "SpotifyLyricsApp is Windows-only")
class WindowReadyReplayTestCase(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        self.scripts = []
        self.app = main.SpotifyLyricsApp.__new__(main.SpotifyLyricsApp)
        self.app.state_lock = threading.Lock()
        self.app._ui_lock = threading.Lock()
        self.app.current_generation_id = 1
        self.app._window_ready = False
        self.app._pending_track = None
        self.app._pending_playback = None
        self.app._pending_lyrics = None
        self.app._pending_translations = None
        self.app._inflight_fetches = set()
        self.app.current_track = "Artist - Song"
        self.app.current_artist = "Artist"
        self.app.current_title = "Song"
        self.app.current_duration = 100.0
        self.app.current_lyrics_key = "Artist - Song"
        self.app.window = None
        self.app.evaluate_js = self.scripts.append

    def _full_payloads(self, generation_id=1):
        self.app._pending_track = (
            generation_id,
            {
                "title": "Song",
                "artist": "Artist",
                "status": 4,
                "position": 1.0,
                "duration": 100.0,
            },
        )
        self.app._pending_playback = (
            generation_id,
            {
                "position_ms": 1000,
                "is_playing": True,
                "playback_rate": 1.0,
                "duration_ms": 100000,
            },
        )
        self.app._pending_lyrics = (
            generation_id,
            {"is_synced": True, "lines": [{"time": 0.0, "text": "line"}]},
        )
        self.app._pending_translations = (
            generation_id,
            {"lang": "ko", "lines": [{"translation": "translation"}]},
        )

    def test_loaded_replays_current_payloads_once_in_order(self):
        self._full_payloads()

        self.app._on_window_loaded()
        self.app._on_window_loaded()  # idempotent

        self.assertEqual(len(self.scripts), 4, self.scripts)
        prefixes = [
            "window.updateTrack(",
            "window.updatePlaybackState(",
            "window.updateLyrics(",
            "window.updateTranslations(",
        ]
        for script, prefix in zip(self.scripts, prefixes):
            self.assertTrue(script.startswith(prefix), (script, prefix))
        self.assertTrue(self.app._window_ready)

    def test_loaded_does_not_replay_stale_generation(self):
        self._full_payloads(generation_id=1)
        self.app.current_generation_id = 2
        self.app._inflight_fetches.add(2)

        self.app._on_window_loaded()

        self.assertEqual(self.scripts, [])
        self.assertTrue(self.app._window_ready)

    def test_loaded_starts_fetch_when_track_has_no_lyrics(self):
        self.app._pending_track = (1, {"title": "Song", "artist": "Artist"})
        self.app._fetch_and_translate_lyrics = mock.Mock()

        class ImmediateThread:
            def __init__(self, target=None, args=(), daemon=None, **kwargs):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        with mock.patch.object(
            self.main.threading, "Thread", ImmediateThread
        ):
            self.app._on_window_loaded()

        self.app._fetch_and_translate_lyrics.assert_called_once_with(
            "Artist", "Song", 100.0, 1
        )

    def test_loaded_does_not_duplicate_an_inflight_fetch(self):
        self.app._pending_track = (1, {"title": "Song", "artist": "Artist"})
        self.app._inflight_fetches.add(1)
        self.app._fetch_and_translate_lyrics = mock.Mock()

        self.app._on_window_loaded()

        self.app._fetch_and_translate_lyrics.assert_not_called()


if __name__ == "__main__":
    unittest.main()
