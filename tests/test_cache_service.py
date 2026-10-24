import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import app_paths
import cache_service
from cache_service import CacheService


class CacheServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / "test_cache.db"
        self.cache = CacheService(self.db_path)
        self.cache2 = CacheService(self.db_path)
        self.addCleanup(self._close_caches)

    def _close_caches(self):
        for cache in (self.cache, self.cache2):
            try:
                cache.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    def test_two_instances_share_settings_offsets_and_lyrics(self):
        self.assertTrue(self.cache.set_setting("theme", "dark"))
        self.assertEqual(self.cache2.get_setting("theme"), "dark")

        self.cache.set_song_offset("Daft Punk", "Get Lucky", 1.25)
        self.assertAlmostEqual(
            self.cache2.get_song_offset("daft  punk", "get   lucky"), 1.25
        )

        lyrics = {"title": "Get Lucky", "lines": [{"time": 0.0, "text": "Like the legend"}]}
        self.cache.save_lyrics("Daft Punk", "Get Lucky", lyrics)
        self.assertEqual(self.cache2.get_lyrics("daft punk", "get lucky"), lyrics)

    def test_connections_are_reused_per_thread(self):
        self.assertIs(self.cache._get_connection(), self.cache._get_connection())
        self.assertIsNot(self.cache._get_connection(), self.cache2._get_connection())

    def test_settings_round_trip_preserves_types(self):
        values = {
            "enabled": True,
            "disabled": False,
            "count": 42,
            "ratio": 0.75,
            "name": "한국어 ✓",
            "nested": {"a": [1, 2, None], "b": {"c": "d"}},
            "nothing": None,
        }
        self.assertTrue(self.cache.set_settings(values))
        self.assertEqual(self.cache.get_settings(), values)
        for key, expected in values.items():
            self.assertEqual(self.cache.get_setting(key), expected)

        self.assertIsNone(self.cache.get_setting("missing"))
        self.assertEqual(self.cache.get_setting("missing", "fallback"), "fallback")

    def test_settings_decode_non_json_values_defensively(self):
        conn = self.cache._get_connection()
        with conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('legacy', 'not-json')"
            )
        self.assertEqual(self.cache.get_setting("legacy"), "not-json")

    def test_offset_normalization_and_round_trip(self):
        self.assertEqual(
            CacheService.normalize_track_key("  Daft   Punk ", " Get\tLucky\n"),
            "daft punk::get lucky",
        )
        self.assertEqual(self.cache.get_song_offset("Nobody", "Nothing"), 0.0)
        self.assertEqual(self.cache.set_song_offset("  IU ", "  Palette ", 0.0), 0.0)
        self.assertAlmostEqual(self.cache.get_song_offset("iu", "palette"), 0.0)

        self.cache.set_song_offset("IU", "Palette", 2.5)
        self.assertAlmostEqual(self.cache.get_song_offset(" iu ", "PALETTE"), 2.5)
        # Updating an existing offset must not create a second row.
        self.cache.set_song_offset("IU", "Palette", -1.5)
        self.assertAlmostEqual(self.cache.get_song_offset("IU", "Palette"), -1.5)

    def test_clear_cache_preserves_user_data(self):
        self.cache.record_song_play("IU", "Palette", "Palette", "thumb-data")
        self.assertTrue(self.cache.toggle_favorite("IU", "Palette"))
        self.assertTrue(
            self.cache.save_vocab_word("팔레트", "palette", "palette", "ko", "Palette")
        )
        self.cache.set_setting("lang", "ko")
        self.cache.set_song_offset("IU", "Palette", 1.5)
        self.cache.save_lyrics("IU", "Palette", {"lines": []})
        self.cache.save_translations_batch(
            {"팔레트": {"translation": "palette", "romaji": "palette"}}, "en"
        )
        self.cache.save_thumbnail("iu::palette", "data:image/png;base64,AAAA")

        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["lyrics_cache"], 1)
        self.assertEqual(stats["translation_cache"], 1)
        self.assertEqual(stats["thumbnails"], 1)
        self.assertEqual(stats["settings"], 1)

        deleted = self.cache.clear_cache()
        self.assertEqual(
            deleted,
            {"lyrics_cache": 1, "translation_cache": 1, "thumbnails": 1},
        )

        self.assertIsNone(self.cache.get_lyrics("IU", "Palette"))
        self.assertEqual(
            self.cache.get_translations_batch(["팔레트"], "en"), {}
        )
        self.assertIsNone(self.cache.get_thumbnail("iu::palette"))

        self.assertTrue(self.cache.is_favorite("IU", "Palette"))
        self.assertEqual(len(self.cache.get_song_history()), 1)
        self.assertEqual(len(self.cache.get_vocab_words()), 1)
        self.assertEqual(self.cache.get_setting("lang"), "ko")
        self.assertAlmostEqual(self.cache.get_song_offset("IU", "Palette"), 1.5)

        cleared = self.cache.get_cache_stats()
        self.assertEqual(cleared["lyrics_cache"], 0)
        self.assertEqual(cleared["translation_cache"], 0)
        self.assertEqual(cleared["thumbnails"], 0)
        self.assertEqual(cleared["settings"], 1)

    def test_clear_cache_discards_counts_when_a_delete_fails(self):
        lyrics = {"lines": [{"time": 0.0, "text": "rolled back"}]}
        self.cache.save_lyrics("Artist", "Song", lyrics)
        self.cache.save_translations_batch(
            {"text": {"translation": "texto", "romaji": ""}}, "en"
        )

        broken_tables = ("lyrics_cache", "missing_table", "translation_cache")
        with mock.patch.object(cache_service, "CACHE_TABLES", broken_tables):
            with self.assertLogs("CacheService", level="ERROR"):
                deleted = self.cache.clear_cache()

        # A failed DELETE rolls the transaction back, so no counts are reported
        # and the cache rows must still be present.
        self.assertEqual(deleted, {})
        self.assertEqual(self.cache.get_lyrics("Artist", "Song"), lyrics)
        self.assertEqual(
            self.cache.get_translations_batch(["text"], "en"),
            {"text": {"translation": "texto", "romaji": ""}},
        )
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["lyrics_cache"], 1)
        self.assertEqual(stats["translation_cache"], 1)

    def test_in_memory_database_is_rejected(self):
        with self.assertRaises(ValueError):
            CacheService(":memory:")

    def test_thumbnail_cache_evicts_oldest_rows(self):
        payload = "x" * 10
        self.assertTrue(self.cache.save_thumbnail("track-1", payload, max_bytes=25))
        self.assertTrue(self.cache.save_thumbnail("track-2", payload, max_bytes=25))
        self.assertTrue(self.cache.save_thumbnail("track-3", payload, max_bytes=25))

        self.assertIsNone(self.cache.get_thumbnail("track-1"))
        self.assertEqual(self.cache.get_thumbnail("track-2"), payload)
        self.assertEqual(self.cache.get_thumbnail("track-3"), payload)
        self.assertEqual(self.cache.get_cache_stats()["thumbnails"], 2)

    def test_oversized_thumbnail_evicts_itself(self):
        self.assertTrue(self.cache.save_thumbnail("huge", "x" * 100, max_bytes=10))
        self.assertIsNone(self.cache.get_thumbnail("huge"))
        self.assertEqual(self.cache.get_cache_stats()["thumbnails"], 0)

    def test_translation_batch_round_trip_and_pruning(self):
        mapping = {
            "line one": {"translation": "línea uno", "romaji": ""},
            "line two": {"translation": "línea dos", "romaji": "line two"},
        }
        self.cache.save_translations_batch(mapping, "es")
        self.assertEqual(
            self.cache.get_translations_batch(["line one", "line two"], "es"), mapping
        )
        self.assertEqual(self.cache.get_translations_batch(["line one"], "en"), {})

        for index in range(5):
            self.cache.save_translations_batch(
                {f"prune {index}": {"translation": f"value {index}", "romaji": ""}},
                "en",
            )
        deleted = self.cache.prune_translations(max_rows=2)
        self.assertEqual(deleted, 5)
        remaining = self.cache.get_translations_batch(
            [f"prune {index}" for index in range(5)], "en"
        )
        self.assertEqual(set(remaining), {"prune 3", "prune 4"})
        self.assertEqual(self.cache.get_cache_stats()["translation_cache"], 2)

    def test_cache_stats_shape(self):
        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["db_path"], str(self.db_path.resolve()))
        self.assertEqual(stats["data_dir"], str(self.db_path.resolve().parent))
        self.assertGreater(stats["db_size"], 0)
        for key in ("lyrics_cache", "translation_cache", "thumbnails", "settings"):
            self.assertIn(key, stats)
        self.assertEqual(
            stats["row_counts"],
            {
                "lyrics_cache": 0,
                "translation_cache": 0,
                "thumbnails": 0,
            },
        )

    def test_concurrent_writes_from_multiple_threads(self):
        errors = []

        def worker(index):
            try:
                for step in range(5):
                    self.cache.set_setting(f"thread_{index}", step)
                    self.cache.set_song_offset("Artist", f"Track {index}", step)
                    self.cache.save_lyrics("Artist", f"Track {index}", {"step": step})
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)
            finally:
                # Thread-local connections are only reachable from their owner.
                self.cache.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(len(self.cache.get_settings()), 4)
        self.assertEqual(
            self.cache.get_lyrics("Artist", "Track 3"), {"step": 4}
        )


class AppPathsTestCase(unittest.TestCase):
    def test_env_override_wins_and_never_resolves_under_meipass(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            fake_meipass = Path(tmp) / "_MEI12345"
            fake_meipass.mkdir()
            with mock.patch.dict(
                os.environ, {"SPOTIFYLYRICS_DATA_DIR": str(data_dir)}, clear=False
            ):
                with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
                    sys, "_MEIPASS", str(fake_meipass), create=True
                ):
                    self.assertEqual(app_paths.get_install_dir(), Path(sys.executable).resolve().parent)
                    self.assertEqual(app_paths.get_data_dir(), data_dir.resolve())

                    db_path = app_paths.get_db_path()
                    self.assertTrue(str(db_path).startswith(str(data_dir.resolve())))
                    self.assertNotIn("_MEI", str(db_path))
                    for subdir in ("logs", "lrc", "thumbnails"):
                        self.assertTrue((data_dir / subdir).is_dir())

    def test_localappdata_and_home_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}, clear=True):
                with mock.patch.object(app_paths, "is_portable", return_value=False):
                    self.assertEqual(
                        app_paths.get_data_dir(),
                        (Path(tmp) / "SpotifyLyrics").resolve(),
                    )
            home_env = {
                key: value
                for key, value in os.environ.items()
                if key not in ("LOCALAPPDATA", "SPOTIFYLYRICS_DATA_DIR")
            }
            with mock.patch.dict(os.environ, home_env, clear=True):
                with mock.patch.object(app_paths, "is_portable", return_value=False):
                    self.assertEqual(
                        app_paths.get_data_dir(),
                        (Path.home() / "AppData" / "Local" / "SpotifyLyrics").resolve(),
                    )

    def test_portable_flag_uses_data_beside_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp)
            (install_dir / "portable.flag").write_text("", encoding="utf-8")
            with mock.patch.object(app_paths, "get_install_dir", return_value=install_dir):
                with mock.patch.dict(os.environ, {}, clear=True):
                    self.assertTrue(app_paths.is_portable())
                    self.assertEqual(
                        app_paths.get_data_dir(),
                        (install_dir / "data").resolve(),
                    )

    def test_legacy_database_is_copied_once_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy_db = Path(tmp) / "lyrics_cache.db"
            legacy_db.write_bytes(b"legacy-bytes")
            data_dir = Path(tmp) / "data"
            with mock.patch.dict(
                os.environ, {"SPOTIFYLYRICS_DATA_DIR": str(data_dir)}, clear=False
            ), mock.patch.object(
                app_paths, "_legacy_db_path", return_value=legacy_db
            ):
                db_path = app_paths.get_db_path()
                self.assertEqual(db_path.read_bytes(), b"legacy-bytes")

                # An existing new DB must never be overwritten.
                db_path.write_bytes(b"new-bytes")
                legacy_db.write_bytes(b"changed-bytes")
                app_paths.get_db_path()
                self.assertEqual(db_path.read_bytes(), b"new-bytes")


if __name__ == "__main__":
    unittest.main()
