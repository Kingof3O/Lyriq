import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cache_service import CacheService
from lyrics_service import LyricsService
from romanizer import Romanizer
from translator_service import TranslatorService


class LyricsFormattingTestCase(unittest.TestCase):
    def setUp(self):
        # _format_lyrics / parse_lrc are pure; avoid touching the real cache.
        self.service = LyricsService.__new__(LyricsService)

    def test_parse_lrc_synced_is_ordered(self):
        lrc = "\n".join([
            "[00:30.00]third",
            "[00:02.50]first",
            "[00:10.25]second",
        ])
        lines = self.service.parse_lrc(lrc)

        self.assertEqual(
            [line["text"] for line in lines],
            ["first", "second", "third"],
        )
        self.assertEqual([line["time"] for line in lines], [2.5, 10.25, 30.0])
        self.assertTrue(all(line["time"] >= 0 for line in lines))

    def test_parse_lrc_plain_lines_use_minus_one(self):
        lines = self.service.parse_lrc("hello\nworld")

        self.assertEqual([line["text"] for line in lines], ["hello", "world"])
        self.assertTrue(all(line["time"] == -1 for line in lines))

    def test_format_lyrics_marks_plain_text_as_unsynced(self):
        provider = {
            "id": 1,
            "trackName": "Plain Song",
            "artistName": "Plain Artist",
            "syncedLyrics": None,
            "plainLyrics": "First line\nSecond line",
        }
        result = self.service._format_lyrics(provider, "Plain Artist", "Plain Song")

        self.assertFalse(result["is_synced"])
        self.assertEqual(len(result["lines"]), 2)
        self.assertTrue(all(line["time"] == -1 for line in result["lines"]))

    def test_format_lyrics_marks_parsed_lrc_as_synced(self):
        provider = {
            "id": 2,
            "trackName": "Synced Song",
            "artistName": "Synced Artist",
            "syncedLyrics": "[00:05.00]First\n[00:09.00]Second",
            "plainLyrics": "First\nSecond",
        }
        result = self.service._format_lyrics(provider, "Synced Artist", "Synced Song")

        self.assertTrue(result["is_synced"])
        self.assertEqual([line["time"] for line in result["lines"]], [5.0, 9.0])

    def test_format_lyrics_synced_field_without_timestamps_is_unsynced(self):
        provider = {
            "id": 3,
            "trackName": "Mislabelled Song",
            "artistName": "Mislabelled Artist",
            "syncedLyrics": "First line\nSecond line",
            "plainLyrics": None,
        }
        result = self.service._format_lyrics(
            provider, "Mislabelled Artist", "Mislabelled Song"
        )

        self.assertFalse(result["is_synced"])
        self.assertTrue(all(line["time"] == -1 for line in result["lines"]))


class MarkedTranslationParserTestCase(unittest.TestCase):
    def test_exact_markers(self):
        parsed = TranslatorService._parse_marked_translations(
            "[[0]] hola\n[[1]] mundo", 2
        )
        self.assertEqual(parsed, ["hola", "mundo"])

    def test_reordered_markers_are_remapped(self):
        parsed = TranslatorService._parse_marked_translations(
            "[[1]] mundo\n[[0]] hola", 2
        )
        self.assertEqual(parsed, ["hola", "mundo"])

    def test_missing_index_is_rejected(self):
        self.assertIsNone(
            TranslatorService._parse_marked_translations("[[0]] hola", 2)
        )

    def test_duplicate_index_is_rejected(self):
        self.assertIsNone(
            TranslatorService._parse_marked_translations(
                "[[0]] hola\n[[0]] mundo", 2
            )
        )

    def test_extra_index_is_rejected(self):
        self.assertIsNone(
            TranslatorService._parse_marked_translations(
                "[[0]] a\n[[1]] b\n[[2]] c", 2
            )
        )

    def test_whitespace_around_markers_and_text(self):
        parsed = TranslatorService._parse_marked_translations(
            "[[ 0 ]]   hola  \n\t[[ 1 ]]  mundo  ", 2
        )
        self.assertEqual(parsed, ["hola", "mundo"])

    def test_empty_translation_is_rejected(self):
        self.assertIsNone(
            TranslatorService._parse_marked_translations("[[0]]   \n[[1]] mundo", 2)
        )

    def test_text_before_first_marker_is_rejected(self):
        self.assertIsNone(
            TranslatorService._parse_marked_translations(
                "prefix\n[[0]] hola\n[[1]] mundo", 2
            )
        )


class TranslationFallbackTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = CacheService(Path(self._tmp.name) / "translator.db")
        self.addCleanup(self.cache.close)

        self.service = TranslatorService.__new__(TranslatorService)
        self.service.target_lang = "en"
        self.service.cache = self.cache

    def test_wrong_batch_count_falls_back_per_line_without_shifting(self):
        lines = [
            {"time": 0.0, "text": "alpha"},
            {"time": 1.0, "text": "beta"},
            {"time": 2.0, "text": "gamma"},
        ]

        def fake_single(text):
            return f"tr:{text}", f"ro:{text}", "en"

        with mock.patch.object(
            self.service,
            "_translate_batch",
            return_value=(["shifted"], ["romaji-shifted"], "en"),
        ), mock.patch.object(
            self.service, "_translate_single", side_effect=fake_single
        ):
            enriched, lang = self.service.translate_lines(lines)

        self.assertEqual(lang, "en")
        self.assertEqual(len(enriched), 3)
        self.assertEqual(
            [item["translation"] for item in enriched],
            ["tr:alpha", "tr:beta", "tr:gamma"],
        )
        self.assertEqual(
            [item["romaji"] for item in enriched],
            ["ro:alpha", "ro:beta", "ro:gamma"],
        )

        cached = self.cache.get_translations_batch(["alpha", "beta", "gamma"], "en")
        self.assertEqual(cached["alpha"]["translation"], "tr:alpha")
        self.assertEqual(cached["beta"]["translation"], "tr:beta")
        self.assertEqual(cached["gamma"]["translation"], "tr:gamma")

    def test_should_abort_returns_early_without_cache_write(self):
        lines = [{"time": 0.0, "text": "never translated"}]

        with mock.patch.object(self.service, "_translate_batch") as batch:
            enriched, lang = self.service.translate_lines(
                lines, should_abort=lambda: True
            )

        self.assertEqual(enriched, [])
        self.assertEqual(lang, "unknown")
        batch.assert_not_called()
        self.assertEqual(
            self.cache.get_translations_batch(["never translated"], "en"), {}
        )


class LyricsFetchCancellationTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = CacheService(Path(self._tmp.name) / "lyrics.db")
        self.addCleanup(self.cache.close)

        self.service = LyricsService.__new__(LyricsService)
        self.service.cache = self.cache
        self.service.artist_trans_cache = {}

    def test_aborted_fetch_does_not_hit_providers_or_cache(self):
        with mock.patch.object(self.service, "_query_lrclib") as query:
            result = self.service.fetch_lyrics(
                "Artist", "Title", 210, should_abort=lambda: True
            )

        self.assertIsNone(result)
        query.assert_not_called()
        self.assertEqual(self.cache.get_cache_stats()["lyrics_cache"], 0)


class RomanizerScriptDetectionTestCase(unittest.TestCase):
    def test_detect_script(self):
        self.assertEqual(Romanizer.detect_script("안녕하세요"), "ko")
        self.assertEqual(Romanizer.detect_script("こんにちは"), "ja")
        self.assertEqual(Romanizer.detect_script("你好世界"), "zh")
        self.assertEqual(Romanizer.detect_script("hello world"), "")
        self.assertEqual(Romanizer.detect_script(""), "")

    def test_chinese_romanization_never_raises(self):
        # pypinyin is optional; either pinyin or an empty string is valid.
        self.assertIsInstance(Romanizer.romanize("你好"), str)


if __name__ == "__main__":
    unittest.main()
