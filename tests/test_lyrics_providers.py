import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import app_paths
import lyrics_providers
import main
from cache_service import CacheService
from lrc_parser import merge_translations, parse_enhanced_lrc
from lyrics_providers import (
    LocalLrcProvider,
    LrclibProvider,
    NeteaseProvider,
    list_local_lrc,
    normalize_metadata,
    read_local_lrc_file,
    save_local_lrc,
    score_candidate,
    search_all,
)
from lyrics_service import LyricsService


def _candidate(provider="lrclib", identifier="lrclib:1", **overrides):
    values = {
        "provider": provider,
        "id": identifier,
        "title": "Song",
        "artist": "Artist",
        "album": "Album",
        "duration": 201.0,
        "has_synced": True,
        "has_plain": False,
        "score": 0.0,
    }
    values.update(overrides)
    return values


class MetadataNormalizationTestCase(unittest.TestCase):
    def test_known_suffixes_are_stripped(self):
        cases = {
            "Song (Remastered 2024)": "Song",
            "Song - Remastered": "Song",
            "Song (Deluxe Edition)": "Song",
            "Song (feat. Other Artist)": "Song",
            "Song [Official Audio]": "Song",
            "Song [Official Video]": "Song",
            "Song (Live)": "Song",
            'Song (From "The Movie")': "Song",
            "Song - Single": "Song",
            "Song (Radio Edit)": "Song",
            "Song (Bonus Track)": "Song",
            "Song (OST)": "Song",
            'Song (Theme from "The Show")': "Song",
            "Song - Remaster": "Song",
            "Song - Live": "Song",
            "Song - Deluxe": "Song",
            "Song feat. Other Artist": "Song",
            "Song ft. Other Artist": "Song",
            "Song featuring Other Artist": "Song",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(
                    normalize_metadata(title, "Artist", "Album")["title"], expected
                )

    def test_multiple_suffixes_are_stripped(self):
        result = normalize_metadata(
            "Song (feat. Other) [Official Video] - Remastered 2021",
            "Artist",
            "Album",
        )
        self.assertEqual(result["title"], "Song")

    def test_unknown_parentheses_and_raw_fields_are_preserved(self):
        raw_title = "  괴도  (Danger)  "
        raw_artist = "  The   Artist "
        raw_album = "  The   Album "
        result = normalize_metadata(raw_title, raw_artist, raw_album)

        self.assertEqual(result["title"], "괴도 (Danger)")
        self.assertEqual(result["artist"], "The Artist")
        self.assertEqual(result["album"], "The Album")
        self.assertEqual(result["raw_title"], raw_title)
        self.assertEqual(result["raw_artist"], raw_artist)
        self.assertEqual(result["raw_album"], raw_album)
        self.assertEqual(result["title_key"], "괴도 (danger)".casefold())
        self.assertEqual(result["artist_key"], "the artist")

    def test_casefold_and_whitespace_are_normalized(self):
        result = normalize_metadata("  Mixed   CASE  ", "  SOME   Artist ")
        self.assertEqual(result["title_key"], "mixed case")
        self.assertEqual(result["artist_key"], "some artist")


class CandidateScoringTestCase(unittest.TestCase):
    def setUp(self):
        self.query = normalize_metadata("Song", "Artist")
        self.query["duration"] = 200.0

    def test_exact_match_beats_duration_and_artist_mismatches(self):
        exact = score_candidate(self.query, _candidate(duration=201.0))
        duration_bad = score_candidate(self.query, _candidate(duration=260.0))
        artist_bad = score_candidate(
            self.query, _candidate(artist="Different Band", duration=201.0)
        )

        self.assertGreater(exact, duration_bad)
        self.assertGreater(duration_bad, artist_bad)

    def test_synced_bonus(self):
        synced = score_candidate(self.query, _candidate(has_synced=True))
        plain = score_candidate(self.query, _candidate(has_synced=False))
        self.assertGreater(synced, plain)

    def test_provider_preference_and_score_bounds(self):
        local = score_candidate(
            self.query,
            _candidate(
                provider="local",
                identifier="Song - Artist.lrc",
                duration=0.0,
                has_synced=False,
            ),
        )
        lrclib = score_candidate(
            self.query,
            _candidate(provider="lrclib", duration=0.0, has_synced=False),
        )
        netease = score_candidate(
            self.query,
            _candidate(provider="netease", duration=0.0, has_synced=False),
        )

        self.assertGreater(local, lrclib)
        self.assertGreater(lrclib, netease)
        for value in (local, lrclib, netease):
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 100.0)

    def test_scoring_is_deterministic(self):
        candidate = _candidate(duration=205.0)
        self.assertEqual(
            score_candidate(self.query, candidate),
            score_candidate(self.query, candidate),
        )


class EnhancedLrcParserTestCase(unittest.TestCase):
    def test_multiple_timestamps_and_ordering(self):
        lines = parse_enhanced_lrc(
            "[ti:Song]\n[00:10.00][00:20.00]Chorus\n[00:05.00]Verse"
        )

        self.assertEqual([line["text"] for line in lines], ["Verse", "Chorus", "Chorus"])
        self.assertEqual([line["time"] for line in lines], [5.0, 10.0, 20.0])
        self.assertNotIn("[ti:", " ".join(line["text"] for line in lines))

    def test_translation_lines_merge_into_preceding_original(self):
        lines = parse_enhanced_lrc(
            "[ti:Song]\n[00:01.00]Hello\n[00:01.00](Hola)\n[00:02.50]World"
        )

        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["text"], "Hello")
        self.assertEqual(lines[0]["translation"], "Hola")
        self.assertNotIn("translation", lines[1])

    def test_reordered_translation_still_matches_by_timestamp(self):
        lines = parse_enhanced_lrc("[00:05.00]Hello\n[00:05.03](Hola)")
        self.assertEqual(lines[0]["translation"], "Hola")

    def test_plain_text_uses_minus_one_and_ignores_metadata(self):
        lines = parse_enhanced_lrc("[ti:Title]\n[ar:Artist]\nfirst\nsecond")

        self.assertEqual([line["text"] for line in lines], ["first", "second"])
        self.assertTrue(all(line["time"] == -1 for line in lines))

    def test_plain_translation_merges(self):
        lines = parse_enhanced_lrc("first\n(primero)\nsecond")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["translation"], "primero")

    def test_malformed_lines_do_not_break_parsing(self):
        lines = parse_enhanced_lrc(
            "[00:aa]Broken\n[00:05.00]Good\nstray text\n[00:07.50]Fine"
        )

        self.assertEqual([line["text"] for line in lines], ["Good", "Fine"])
        self.assertEqual([line["time"] for line in lines], [5.0, 7.5])

    def test_empty_and_metadata_only(self):
        self.assertEqual(parse_enhanced_lrc(""), [])
        self.assertEqual(parse_enhanced_lrc("[ti:Song]\n[by:SpotifyLyrics]"), [])

    def test_merge_translations_nearest_timestamp_and_existing_value(self):
        lines = [
            {"time": 1.0, "text": "Hello"},
            {"time": 2.0, "text": "World", "translation": "Keep"},
        ]
        merge_translations(
            lines,
            [
                {"time": 1.05, "text": "Hola"},
                {"time": 2.0, "text": "Mundo"},
            ],
        )
        self.assertEqual(lines[0]["translation"], "Hola")
        self.assertEqual(lines[1]["translation"], "Keep")


class LocalLrcTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._env = mock.patch.dict(
            os.environ, {app_paths.DATA_DIR_ENV: self._tmp.name}
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        self.lrc_dir = Path(self._tmp.name) / "lrc"

    def _save_synced(self):
        result = save_local_lrc(
            "The Artist",
            "The Song",
            [
                {"time": 1.0, "text": "Hello", "translation": "Hola"},
                {"time": 2.5, "text": "World"},
            ],
        )
        self.assertTrue(result["ok"])
        return result

    def test_save_read_list_search_and_fetch_round_trip(self):
        result = self._save_synced()
        path = Path(result["path"])

        self.assertTrue(path.is_file())
        self.assertEqual(path.parent, self.lrc_dir)
        text = path.read_text(encoding="utf-8")
        self.assertIn("[ti:The Song]", text)
        self.assertIn("[ar:The Artist]", text)
        self.assertIn("[by:SpotifyLyrics]", text)
        self.assertIn("[00:01.00]Hello", text)
        self.assertIn("[00:01.00](Hola)", text)
        self.assertEqual(list(path.parent.glob("*.tmp")), [])

        data = read_local_lrc_file(path)
        self.assertEqual(data["provider"], "local")
        self.assertEqual(data["title"], "The Song")
        self.assertEqual(data["artist"], "The Artist")
        self.assertTrue(data["is_synced"])
        self.assertEqual(data["lines"][0]["translation"], "Hola")

        listing = list_local_lrc()
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["provider"], "local")
        self.assertTrue(listing[0]["has_synced"])

        provider = LocalLrcProvider()
        query = normalize_metadata("The Song", "The Artist")
        query["duration"] = 200.0
        candidates = provider.search(query, limit=5)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"], "local")
        self.assertEqual(candidates[0]["score"], 100.0)
        self.assertTrue(candidates[0]["has_synced"])

        fetched = provider.fetch(candidates[0], query)
        self.assertEqual(fetched["provider"], "local")
        self.assertTrue(fetched["is_synced"])
        self.assertEqual(fetched["lines"][0]["text"], "Hello")
        self.assertEqual(fetched["lines"][0]["translation"], "Hola")

    def test_plain_round_trip_uses_minus_one(self):
        result = save_local_lrc(
            "The Artist",
            "Plain Song",
            [
                {"time": -1, "text": "First"},
                {"time": -1, "text": "Second", "translation": "Segundo"},
            ],
        )
        data = read_local_lrc_file(result["path"])

        self.assertFalse(data["is_synced"])
        self.assertEqual([line["text"] for line in data["lines"]], ["First", "Second"])
        self.assertTrue(all(line["time"] == -1 for line in data["lines"]))
        self.assertEqual(data["lines"][1]["translation"], "Segundo")

    def test_read_external_lrc_path_outside_lrc_folder(self):
        path = Path(self._tmp.name) / "external.lrc"
        path.write_text("[ti:External]\n[ar:Someone]\n[00:01.00]Hello", encoding="utf-8")

        data = read_local_lrc_file(path)

        self.assertEqual(data["title"], "External")
        self.assertEqual(data["artist"], "Someone")
        self.assertTrue(data["is_synced"])

    def test_filename_is_sanitized_and_save_overwrites(self):
        first = save_local_lrc(
            "AC/DC", "Back: In Black", [{"time": 1.0, "text": "One"}]
        )
        self.assertTrue(first["ok"])
        name = Path(first["path"]).name
        self.assertNotIn("/", name)
        self.assertNotIn(":", name)
        self.assertEqual(name, "AC_DC - Back_ In Black.lrc")

        second = save_local_lrc(
            "AC/DC", "Back: In Black", [{"time": 2.0, "text": "Two"}]
        )
        self.assertEqual(second["path"], first["path"])
        self.assertEqual(
            [line["text"] for line in read_local_lrc_file(second["path"])["lines"]],
            ["Two"],
        )


class ProviderSearchTestCase(unittest.TestCase):
    def setUp(self):
        self.query = normalize_metadata("Song", "Artist")
        self.query["duration"] = 200.0

    def test_search_all_survives_one_provider_failure(self):
        candidate = _candidate()
        with mock.patch.object(
            lyrics_providers.LOCAL_PROVIDER,
            "search",
            side_effect=RuntimeError("local unavailable"),
        ), mock.patch.object(
            lyrics_providers.LRCLIB_PROVIDER, "search", return_value=[candidate]
        ), mock.patch.object(
            lyrics_providers.NETEASE_PROVIDER, "search", return_value=[]
        ):
            results = search_all(self.query)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provider"], "lrclib")
        self.assertGreater(results[0]["score"], 0)
        self.assertEqual(
            set(results[0]),
            {
                "provider",
                "id",
                "title",
                "artist",
                "album",
                "duration",
                "has_synced",
                "has_plain",
                "score",
            },
        )

    def test_search_all_returns_empty_when_every_provider_fails(self):
        with mock.patch.object(
            lyrics_providers.LOCAL_PROVIDER,
            "search",
            side_effect=RuntimeError("local"),
        ), mock.patch.object(
            lyrics_providers.LRCLIB_PROVIDER,
            "search",
            side_effect=RuntimeError("lrclib"),
        ), mock.patch.object(
            lyrics_providers.NETEASE_PROVIDER,
            "search",
            side_effect=RuntimeError("netease"),
        ):
            self.assertEqual(search_all(self.query), [])

    def test_search_all_dedupes_identical_provider_entries(self):
        duplicate = _candidate()
        renamed = dict(duplicate, title="Song (Remastered)")
        with mock.patch.object(
            lyrics_providers.LOCAL_PROVIDER, "search", return_value=[]
        ), mock.patch.object(
            lyrics_providers.LRCLIB_PROVIDER, "search", return_value=[duplicate, renamed]
        ), mock.patch.object(
            lyrics_providers.NETEASE_PROVIDER, "search", return_value=[]
        ):
            results = search_all(self.query)

        self.assertEqual(len(results), 1)

    def test_local_candidate_shadows_network_duplicate(self):
        local = _candidate(
            provider="local", identifier="Song - Artist.lrc", duration=0.0
        )
        remote = _candidate(provider="lrclib", identifier="lrclib:9")
        with mock.patch.object(
            lyrics_providers.LOCAL_PROVIDER, "search", return_value=[local]
        ), mock.patch.object(
            lyrics_providers.LRCLIB_PROVIDER, "search", return_value=[remote]
        ), mock.patch.object(
            lyrics_providers.NETEASE_PROVIDER, "search", return_value=[]
        ):
            results = search_all(self.query)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["provider"], "local")


class NetworkProviderTestCase(unittest.TestCase):
    def setUp(self):
        self.query = normalize_metadata("Song", "Artist")
        self.query["duration"] = 200.0

    def test_lrclib_fetch_synced(self):
        raw = {
            "id": 42,
            "trackName": "Song",
            "artistName": "Artist",
            "albumName": "Album",
            "duration": 201,
            "syncedLyrics": "[00:01.00]Hello\n[00:02.00]World",
            "plainLyrics": "Hello\nWorld",
        }
        with mock.patch("lyrics_providers._http_json", return_value=raw):
            data = LrclibProvider().fetch(
                {"provider": "lrclib", "id": "lrclib:42", "title": "Song"},
                self.query,
            )

        self.assertEqual(data["provider"], "lrclib")
        self.assertEqual(data["id"], "lrclib:42")
        self.assertTrue(data["is_synced"])
        self.assertEqual([line["text"] for line in data["lines"]], ["Hello", "World"])

    def test_lrclib_fetch_plain_lyrics(self):
        raw = {
            "id": 43,
            "trackName": "Song",
            "artistName": "Artist",
            "syncedLyrics": None,
            "plainLyrics": "Hello\nWorld",
        }
        with mock.patch("lyrics_providers._http_json", return_value=raw):
            data = LrclibProvider().fetch(
                {"provider": "lrclib", "id": "lrclib:43"}, self.query
            )

        self.assertFalse(data["is_synced"])
        self.assertTrue(all(line["time"] == -1 for line in data["lines"]))

    def test_lrclib_candidate_without_id_uses_artist_title_key(self):
        raw = {
            "trackName": "Song",
            "artistName": "Artist",
            "syncedLyrics": "[00:01.00]Hello",
            "plainLyrics": None,
        }
        with mock.patch("lyrics_providers._http_json", return_value=raw):
            results = LrclibProvider().search(self.query)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "lrclib:Artist::Song")

    def test_lrclib_search_falls_back_to_search_endpoint(self):
        raw = {
            "id": 7,
            "trackName": "Song",
            "artistName": "Artist",
            "syncedLyrics": "[00:01.00]Hello",
            "plainLyrics": None,
        }
        with mock.patch(
            "lyrics_providers._http_json", side_effect=[None, [raw]]
        ) as request:
            results = LrclibProvider().search(self.query)

        self.assertEqual(len(results), 1)
        self.assertEqual(request.call_count, 2)
        self.assertIn("/api/search", request.call_args_list[1].args[0])

    def test_netease_search_maps_song(self):
        payload = {
            "result": {
                "songs": [
                    {
                        "id": 123,
                        "name": "Song",
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                        "duration": 201000,
                    }
                ]
            }
        }
        with mock.patch(
            "lyrics_providers._http_json", return_value=payload
        ) as request:
            results = NeteaseProvider().search(self.query)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "netease:123")
        self.assertEqual(results[0]["duration"], 201.0)
        self.assertIn("type=1", request.call_args.args[0])
        self.assertEqual(
            request.call_args.kwargs["headers"]["Referer"],
            "https://music.163.com/",
        )

    def test_netease_fetch_merges_translations(self):
        payload = {
            "code": 200,
            "lrc": {"lyric": "[00:01.00]Hello\n[00:02.00]World"},
            "tlyric": {"lyric": "[00:01.00]Hola\n[00:02.00]Mundo"},
        }
        candidate = {
            "provider": "netease",
            "id": "netease:123",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
        }
        with mock.patch("lyrics_providers._http_json", return_value=payload):
            data = NeteaseProvider().fetch(candidate, self.query)

        self.assertEqual(data["provider"], "netease")
        self.assertTrue(data["is_synced"])
        self.assertEqual(
            [line.get("translation") for line in data["lines"]], ["Hola", "Mundo"]
        )

    def test_netease_empty_and_error_responses_are_contained(self):
        candidate = {"provider": "netease", "id": "netease:123"}

        with mock.patch(
            "lyrics_providers._http_json", return_value={"code": 404}
        ):
            self.assertIsNone(NeteaseProvider().fetch(candidate, self.query))

        with mock.patch(
            "lyrics_providers._http_json",
            return_value={"code": 200, "lrc": {"lyric": ""}},
        ):
            self.assertIsNone(NeteaseProvider().fetch(candidate, self.query))

        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
            self.assertEqual(NeteaseProvider().search(self.query), [])


class LyricsServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = CacheService(Path(self._tmp.name) / "lyrics.db")
        self.addCleanup(self.cache.close)
        self.service = LyricsService(cache=self.cache)

    def test_search_lyrics_builds_normalized_query(self):
        with mock.patch(
            "lyrics_providers.search_all", return_value=[_candidate()]
        ) as search:
            result = self.service.search_lyrics("Artist", "Song (Remastered)", 201.5)

        self.assertEqual(len(result), 1)
        query = search.call_args.args[0]
        self.assertEqual(query["title"], "Song")
        self.assertEqual(query["title_key"], "song")
        self.assertEqual(query["duration"], 201.5)

    def test_cached_result_is_used_without_network_calls(self):
        cached = {
            "provider": "netease",
            "id": "netease:1",
            "title": "Song",
            "artist": "Artist",
            "is_synced": True,
            "lines": [{"time": 0.0, "text": "Cached"}],
        }
        self.cache.save_lyrics("Artist", "Song", cached)

        with mock.patch("lyrics_providers.search_all") as search, mock.patch(
            "lyrics_providers.fetch_candidate"
        ) as fetch:
            result = self.service.fetch_lyrics("Artist", "Song", 200)

        self.assertEqual(result["provider"], "netease")
        self.assertEqual(result["lines"][0]["text"], "Cached")
        search.assert_not_called()
        fetch.assert_not_called()

    def test_old_cached_row_defaults_to_lrclib_provider(self):
        self.cache.save_lyrics(
            "Artist",
            "Song",
            {
                "title": "Song",
                "artist": "Artist",
                "is_synced": True,
                "lines": [{"time": 0.0, "text": "Legacy"}],
            },
        )

        result = self.service.fetch_lyrics("Artist", "Song", 200)
        self.assertEqual(result["provider"], "lrclib")

    def test_candidate_selection_skips_search_and_caches(self):
        candidate = _candidate(identifier="lrclib:42")
        fetched = {
            "provider": "lrclib",
            "id": "lrclib:42",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "is_synced": True,
            "lines": [{"time": 1.0, "text": "Selected"}],
        }

        with mock.patch("lyrics_providers.search_all") as search, mock.patch(
            "lyrics_providers.fetch_candidate", return_value=fetched
        ) as fetch:
            result = self.service.fetch_lyrics(
                "Artist", "Song", 200, candidate=candidate
            )

        self.assertEqual(result["lines"][0]["text"], "Selected")
        fetch.assert_called_once()
        search.assert_not_called()
        cached = self.cache.get_lyrics("Artist", "Song")
        self.assertEqual(cached["provider"], "lrclib")
        self.assertEqual(cached["lines"][0]["text"], "Selected")

    def test_failed_candidate_falls_back_to_normal_pipeline(self):
        candidate = _candidate(identifier="lrclib:bad")
        fallback = _candidate(identifier="lrclib:good", score=90.0)
        fetched = {
            "provider": "lrclib",
            "id": "lrclib:good",
            "title": "Song",
            "artist": "Artist",
            "is_synced": True,
            "lines": [{"time": 2.0, "text": "Fallback"}],
        }

        with mock.patch(
            "lyrics_providers.search_all", return_value=[fallback]
        ) as search, mock.patch(
            "lyrics_providers.fetch_candidate", side_effect=[None, fetched]
        ) as fetch:
            result = self.service.fetch_lyrics(
                "Artist", "Song", 200, candidate=candidate
            )

        self.assertEqual(result["lines"][0]["text"], "Fallback")
        search.assert_called_once()
        self.assertEqual(fetch.call_count, 2)

    def test_pipeline_fetches_highest_scored_candidate(self):
        low = _candidate(identifier="lrclib:low", score=30.0)
        high = _candidate(identifier="lrclib:high", score=95.0)

        def fake_fetch(candidate, query):
            return {
                "provider": "lrclib",
                "id": candidate["id"],
                "title": "Song",
                "artist": "Artist",
                "is_synced": True,
                "lines": [{"time": 0.0, "text": candidate["id"]}],
            }

        with mock.patch(
            "lyrics_providers.search_all", return_value=[low, high]
        ), mock.patch(
            "lyrics_providers.fetch_candidate", side_effect=fake_fetch
        ) as fetch:
            result = self.service.fetch_lyrics("Artist", "Song", 200)

        self.assertEqual(result["lines"][0]["text"], "lrclib:high")
        self.assertEqual(fetch.call_args.args[0]["id"], "lrclib:high")

    def test_provider_filter_is_forwarded(self):
        with mock.patch(
            "lyrics_providers.search_all", return_value=[]
        ) as search:
            self.assertIsNone(
                self.service.fetch_lyrics("Artist", "Song", 200, provider="netease")
            )

        self.assertEqual(search.call_args.kwargs["providers"], ["netease"])

    def test_aborted_candidate_selection_never_fetches_or_caches(self):
        with mock.patch("lyrics_providers.fetch_candidate") as fetch:
            result = self.service.fetch_lyrics(
                "Artist",
                "Song",
                200,
                should_abort=lambda: True,
                candidate=_candidate(),
            )

        self.assertIsNone(result)
        fetch.assert_not_called()
        self.assertEqual(self.cache.get_cache_stats()["lyrics_cache"], 0)

    def test_abort_after_search_prevents_fetch_and_cache_write(self):
        state = {"abort": False}

        def fake_search(*args, **kwargs):
            state["abort"] = True
            return [_candidate(score=100.0)]

        with mock.patch(
            "lyrics_providers.search_all", side_effect=fake_search
        ), mock.patch("lyrics_providers.fetch_candidate") as fetch:
            result = self.service.fetch_lyrics(
                "Artist", "Song", 200, should_abort=lambda: state["abort"]
            )

        self.assertIsNone(result)
        fetch.assert_not_called()
        self.assertEqual(self.cache.get_cache_stats()["lyrics_cache"], 0)

    def test_abort_after_fetch_prevents_cache_write(self):
        state = {"abort": False}

        def fake_fetch(candidate, query):
            state["abort"] = True
            return {
                "provider": "lrclib",
                "id": "lrclib:1",
                "title": "Song",
                "artist": "Artist",
                "is_synced": True,
                "lines": [{"time": 0.0, "text": "Never cached"}],
            }

        with mock.patch(
            "lyrics_providers.search_all", return_value=[_candidate(score=100.0)]
        ), mock.patch("lyrics_providers.fetch_candidate", side_effect=fake_fetch):
            result = self.service.fetch_lyrics(
                "Artist", "Song", 200, should_abort=lambda: state["abort"]
            )

        self.assertIsNone(result)
        self.assertEqual(self.cache.get_cache_stats()["lyrics_cache"], 0)


class _FakeApp:
    def __init__(self):
        self.state_lock = threading.Lock()
        self.current_generation_id = 0
        self.current_artist = "Artist"
        self.current_title = "Song"
        self.current_duration = 200.0
        self.current_lyrics_key = "Artist - Song"
        self.current_lyrics = None
        self.lyrics_service = mock.Mock()
        self.fetch_calls = []

    def _fetch_and_translate_lyrics(self, *args, **kwargs):
        self.fetch_calls.append((args, kwargs))


class MainApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = _FakeApp()
        self.api = main.AppAPI(self.app)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._env = mock.patch.dict(
            os.environ, {app_paths.DATA_DIR_ENV: self._tmp.name}
        )
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_search_lyrics_delegates_to_service(self):
        candidates = [_candidate()]
        self.app.lyrics_service.search_lyrics.return_value = candidates

        result = self.api.search_lyrics("Artist", "Song", 201)

        self.assertEqual(result, candidates)
        self.app.lyrics_service.search_lyrics.assert_called_once_with(
            "Artist", "Song", 201
        )

    def test_search_lyrics_returns_empty_on_service_error(self):
        self.app.lyrics_service.search_lyrics.side_effect = RuntimeError("offline")
        self.assertEqual(self.api.search_lyrics("Artist", "Song", 201), [])

    def test_select_lyrics_increments_generation_and_starts_thread(self):
        candidate = _candidate(identifier="lrclib:42")

        with mock.patch("main.threading.Thread") as thread:
            result = self.api.select_lyrics("Artist", "Song", 200, candidate)

        self.assertTrue(result)
        self.assertEqual(self.app.current_generation_id, 1)
        self.assertEqual(self.app.current_lyrics_key, "Artist - Song")
        thread.return_value.start.assert_called_once()
        args = thread.call_args.kwargs["args"]
        self.assertEqual(args[:4], ("Artist", "Song", 200.0, 1))
        self.assertEqual(args[4], candidate)

    def test_select_lyrics_rejects_invalid_candidate(self):
        self.assertFalse(self.api.select_lyrics("Artist", "Song", 200, None))
        self.assertFalse(self.api.select_lyrics("Artist", "Song", 200, {}))
        self.assertEqual(self.app.current_generation_id, 0)

    def test_select_preview_does_not_change_live_track_identity(self):
        with mock.patch("main.threading.Thread"):
            result = self.api.select_lyrics(
                "Other Artist", "Other Song", 0, _candidate()
            )

        self.assertTrue(result)
        self.assertEqual(self.app.current_artist, "Artist")
        self.assertEqual(self.app.current_title, "Song")
        self.assertEqual(self.app.current_lyrics_key, "Other Artist - Other Song")

    def test_save_local_lyrics_reloads_matching_current_track(self):
        saved = {"ok": True, "path": r"C:\data\lrc\Artist - Song.lrc"}
        with mock.patch(
            "main.lyrics_providers.save_local_lrc", return_value=saved
        ) as save, mock.patch("main.threading.Thread") as thread:
            result = self.api.save_local_lyrics(
                "Artist", "Song", [{"time": 1.0, "text": "Hello"}]
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["reloaded"])
        save.assert_called_once()
        self.assertEqual(self.app.current_generation_id, 1)
        thread.return_value.start.assert_called_once()
        args = thread.call_args.kwargs["args"]
        self.assertEqual(args[:3], ("Artist", "Song", 200.0))
        self.assertEqual(args[4]["provider"], "local")
        self.assertEqual(args[4]["id"], "Artist - Song.lrc")

    def test_save_local_lyrics_for_other_track_does_not_reload(self):
        saved = {"ok": True, "path": r"C:\data\lrc\Other - Song.lrc"}
        with mock.patch(
            "main.lyrics_providers.save_local_lrc", return_value=saved
        ), mock.patch("main.threading.Thread") as thread:
            result = self.api.save_local_lyrics(
                "Other Artist", "Other Song", [{"time": 1.0, "text": "Hello"}]
            )

        self.assertFalse(result["reloaded"])
        self.assertEqual(self.app.current_generation_id, 0)
        thread.assert_not_called()

    def test_lrc_folder_and_provider_list(self):
        folder = self.api.get_lrc_folder()
        self.assertEqual(Path(folder), Path(self._tmp.name) / "lrc")

        with mock.patch("main.os.startfile") as startfile:
            self.assertTrue(self.api.open_lrc_folder())
        startfile.assert_called_once_with(folder)

        providers = self.api.get_lyrics_providers()
        self.assertEqual(
            [provider["id"] for provider in providers],
            ["local", "lrclib", "netease"],
        )
        for provider in providers:
            self.assertEqual(
                set(provider), {"id", "name", "available"}
            )


if __name__ == "__main__":
    unittest.main()
