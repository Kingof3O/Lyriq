import json
import logging
import math
import re
import urllib.parse
import urllib.request

import lyrics_providers
from cache_service import get_cache
from lrc_parser import parse_enhanced_lrc

logger = logging.getLogger("LyricsService")

_PROVIDER_DEFAULT = "lrclib"


def _safe_duration(value) -> float:
    try:
        duration = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return duration if math.isfinite(duration) and duration > 0 else 0.0


class LyricsService:
    def __init__(self, cache=None):
        self.cache = cache if cache is not None else get_cache()
        self.artist_trans_cache = {}

    def get_variations(self, artist: str, title: str) -> list:
        variations = []

        # 1. Base clean
        clean = re.sub(r"[\(\[][^\)\]]*(?:feat|with|remaster|version|official|bonus|prod|clean|ver)[^\)\]]*[\)\]]", "", title, flags=re.IGNORECASE).strip()
        clean = re.sub(r" - .*(?:remaster|version|live|deluxe).*", "", clean, flags=re.IGNORECASE).strip()

        variations.append((artist, title))
        if clean and clean != title:
            variations.append((artist, clean))

        # 2. Extract bilingual parts: "괴도 (Danger)" or "Danger (괴도)"
        paren_match = re.search(r"^(.*?)\s*[\(\[](.*?)[\)\]]\s*$", clean or title)
        if paren_match:
            part1 = paren_match.group(1).strip()
            part2 = paren_match.group(2).strip()
            if part1 and part1 != clean:
                variations.append((artist, part1))
            if part2 and part2 != clean:
                variations.append((artist, part2))

        # 3. If artist has Korean Hangul, translate artist name (e.g. 방탄소년단 -> BTS, 아이유 -> IU)
        if re.search(r"[\uac00-\ud7a3]", artist):
            en_artist = self._translate_artist(artist)
            if en_artist and en_artist.lower() != artist.lower():
                variations.append((en_artist, title))
                if clean:
                    variations.append((en_artist, clean))
                if paren_match:
                    if part1:
                        variations.append((en_artist, part1))
                    if part2:
                        variations.append((en_artist, part2))

        seen = set()
        deduped = []
        for a, t in variations:
            key = f"{a}:::{t}".lower()
            if key not in seen and a and t:
                seen.add(key)
                deduped.append((a, t))

        return deduped

    def _translate_artist(self, artist: str) -> str:
        if artist in self.artist_trans_cache:
            return self.artist_trans_cache[artist]
        try:
            params = {"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": artist}
            url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read().decode('utf-8'))
                res = "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
                self.artist_trans_cache[artist] = res
                return res
        except Exception as exc:
            logger.debug("Artist name translation failed for %s: %s", artist, exc)
            return ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def search_lyrics(self, artist: str, title: str, duration: float = 0) -> list:
        """Return scored lyric candidates from local, LRCLIB and NetEase."""
        query = self._build_query(artist, title, duration)
        try:
            return lyrics_providers.search_all(query, limit=12)
        except Exception as exc:  # noqa: BLE001 - search must never break the UI
            logger.warning("Lyrics search failed: %s", exc)
            return []

    def fetch_candidate(self, candidate: dict, artist: str, title: str,
                        duration: float = 0, should_abort=None) -> dict | None:
        """Fetch and format one explicit candidate (manual selection)."""
        def aborted() -> bool:
            return bool(should_abort and should_abort())

        if aborted() or not isinstance(candidate, dict):
            return None
        query = self._build_query(artist, title, duration)
        data = lyrics_providers.fetch_candidate(candidate, query)
        if aborted() or not data:
            return None
        return self._format_provider_result(data, artist, title)

    def fetch_lyrics(self, artist: str, title: str, duration: float = 0,
                     should_abort=None, candidate: dict | None = None,
                     provider: str | None = None):
        def aborted() -> bool:
            return bool(should_abort and should_abort())

        if aborted():
            return None

        query = self._build_query(artist, title, duration)

        # Manual selection always wins over an older cached result.
        if candidate:
            if aborted():
                return None
            selected = self.fetch_candidate(
                candidate, artist, title, duration, should_abort=should_abort
            )
            if aborted():
                return None
            if selected and selected.get("lines"):
                self._save_result(artist, title, selected, aborted)
                return selected

        cached = self.cache.get_lyrics(artist, title)
        if aborted():
            return None
        if isinstance(cached, dict):
            normalized = self._normalize_cached(cached)
            if normalized.get("lines"):
                return normalized

        provider_filter = [provider] if provider else None
        attempts = 0
        max_attempts = 6
        queries = [query]
        variations_queued = False

        for current_query in queries:
            if aborted():
                return None
            try:
                candidates = lyrics_providers.search_all(
                    current_query, limit=12, providers=provider_filter
                )
            except Exception as exc:  # noqa: BLE001 - search_all normally contains errors
                logger.warning("Lyrics search failed for %s / %s: %s", artist, title, exc)
                candidates = []

            for selected_candidate in self._rank_candidates(candidates):
                if attempts >= max_attempts:
                    break
                if aborted():
                    return None
                attempts += 1
                fetched = lyrics_providers.fetch_candidate(selected_candidate, current_query)
                if aborted():
                    return None
                if not fetched or not fetched.get("lines"):
                    continue
                result = self._format_provider_result(fetched, artist, title)
                if not result:
                    continue
                self._save_result(artist, title, result, aborted)
                return result

            if attempts >= max_attempts:
                break

            # LRCLIB/NetEase may need a cleaned or translated artist/title.
            if provider is None and not variations_queued:
                if aborted():
                    return None
                variations_queued = True
                queries.extend(
                    self._variation_queries(artist, title, duration, query)
                )

        return None

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_query(artist: str, title: str, duration: float = 0) -> dict:
        query = lyrics_providers.normalize_metadata(title or "", artist or "")
        query["duration"] = _safe_duration(duration)
        return query

    def _variation_queries(self, artist: str, title: str, duration: float,
                           original_query: dict) -> list:
        try:
            variations = self.get_variations(artist, title)
        except Exception as exc:  # noqa: BLE001 - fallback search is optional
            logger.debug("Could not build lyric variations: %s", exc)
            return []

        seen = {
            (
                original_query.get("artist_key"),
                original_query.get("title_key"),
            )
        }
        queries = []
        for alt_artist, alt_title in variations:
            query = self._build_query(alt_artist, alt_title, duration)
            key = (query.get("artist_key"), query.get("title_key"))
            if key in seen:
                continue
            seen.add(key)
            queries.append(query)
            if len(queries) >= 4:
                break
        return queries

    @staticmethod
    def _rank_candidates(candidates: list) -> list:
        def score_value(item):
            try:
                return float(item.get("score") or 0)
            except (TypeError, ValueError):
                return 0.0

        clean = [item for item in candidates if isinstance(item, dict)]
        preferred = [
            item
            for item in clean
            if score_value(item) >= 10 or item.get("provider") == "local"
        ]
        pool = preferred or clean
        return sorted(
            pool,
            key=lambda item: (
                -score_value(item),
                0 if item.get("has_synced") else 1,
                0 if item.get("provider") == "local" else 1,
                str(item.get("title") or "").casefold(),
            ),
        )

    # ------------------------------------------------------------------
    # Result formatting / cache
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_line(line: dict) -> dict | None:
        if not isinstance(line, dict):
            return None
        text = str(line.get("text") or "").strip()
        if not text:
            return None
        try:
            timestamp = float(line.get("time", -1))
        except (TypeError, ValueError):
            timestamp = -1.0
        if not math.isfinite(timestamp):
            timestamp = -1.0
        result = {"time": timestamp, "text": text}
        translation = str(line.get("translation") or "").strip()
        if translation:
            result["translation"] = translation
        return result

    @staticmethod
    def _drop_untimed_if_synced(lines: list) -> list:
        """Drop stray untimed lines when the result contains real timestamps."""
        timed = [line for line in lines if line.get("time", -1) >= 0]
        return timed if timed else list(lines)

    def _format_provider_result(self, data: dict, artist: str, title: str) -> dict | None:
        lines = [
            line
            for line in (self._coerce_line(item) for item in data.get("lines") or [])
            if line is not None
        ]
        if not lines:
            return None
        lines = self._drop_untimed_if_synced(lines)

        return {
            "id": data.get("id"),
            "provider": data.get("provider") or _PROVIDER_DEFAULT,
            "title": data.get("title") or title,
            "artist": data.get("artist") or artist,
            "album": data.get("album") or "",
            "is_synced": bool(lines) and all(line.get("time", -1) >= 0 for line in lines),
            "lines": lines,
        }

    def _normalize_cached(self, cached: dict) -> dict:
        result = dict(cached)
        result["provider"] = result.get("provider") or _PROVIDER_DEFAULT
        lines = [
            line
            for line in (self._coerce_line(item) for item in result.get("lines") or [])
            if line is not None
        ]
        lines = self._drop_untimed_if_synced(lines)
        result["lines"] = lines
        result["is_synced"] = bool(lines) and all(
            line.get("time", -1) >= 0 for line in lines
        )
        result.setdefault("id", None)
        result.setdefault("title", "")
        result.setdefault("artist", "")
        result.setdefault("album", "")
        return result

    def _save_result(self, artist: str, title: str, result: dict, aborted) -> bool:
        if aborted():
            return False
        try:
            self.cache.save_lyrics(artist, title, result)
            return True
        except Exception as exc:  # noqa: BLE001 - a cache failure must not hide lyrics
            logger.error("Could not cache lyrics for %s / %s: %s", artist, title, exc)
            return False

    # ------------------------------------------------------------------
    # Legacy helpers (kept for compatibility)
    # ------------------------------------------------------------------
    def _format_lyrics(self, lyrics: dict, artist: str, title: str) -> dict:
        synced_text = lyrics.get("syncedLyrics") or ""
        plain_text = lyrics.get("plainLyrics") or ""
        parsed = self._drop_untimed_if_synced(
            self.parse_lrc(synced_text or plain_text)
        )

        # Only a parsed timestamped LRC counts as synced.  Plain provider
        # lyrics are returned with time=-1 and must render statically.
        is_synced = bool(synced_text) and bool(parsed) and all(
            line.get("time", -1) >= 0 for line in parsed
        )

        return {
            "id": lyrics.get("id"),
            "provider": "lrclib",
            "title": lyrics.get("trackName") or title,
            "artist": lyrics.get("artistName") or artist,
            "album": lyrics.get("albumName") or "",
            "is_synced": is_synced,
            "lines": parsed,
        }

    def _query_lrclib(self, artist: str, title: str, duration: float):
        params = {
            "artist_name": artist,
            "track_name": title,
        }
        if duration > 0:
            params["duration"] = str(int(duration))

        url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "SpotifyLyricsDesktop/3.0"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if data.get("syncedLyrics") or data.get("plainLyrics"):
                        return data
        except Exception as exc:  # noqa: BLE001 - legacy fallback is best-effort
            logger.debug("LRCLIB lookup failed for %s / %s: %s", artist, title, exc)
        return None

    def _search_lrclib(self, artist: str, title: str, duration: float = 0):
        query = f"{artist} {title}"
        url = "https://lrclib.net/api/search?" + urllib.parse.urlencode({"q": query})
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "SpotifyLyricsDesktop/3.0"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    items = json.loads(response.read().decode("utf-8"))
                    if items and isinstance(items, list):
                        synced = [it for it in items if it.get("syncedLyrics")]
                        if synced:
                            if duration > 0:
                                synced.sort(
                                    key=lambda x: abs(
                                        (x.get("duration") or 0) - duration
                                    )
                                )
                            return synced[0]
                        return items[0]
        except Exception as exc:  # noqa: BLE001 - legacy fallback is best-effort
            logger.debug("LRCLIB search failed for %s / %s: %s", artist, title, exc)
        return None

    def parse_lrc(self, lrc_text: str):
        return parse_enhanced_lrc(lrc_text)
