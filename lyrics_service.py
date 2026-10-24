import re
import urllib.parse
import urllib.request
import json
import logging
from cache_service import CacheService

logger = logging.getLogger("LyricsService")

class LyricsService:
    def __init__(self):
        self.cache = CacheService()
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
                    if part1: variations.append((en_artist, part1))
                    if part2: variations.append((en_artist, part2))

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
        except Exception:
            return ""

    def fetch_lyrics(self, artist: str, title: str, duration: float = 0):
        # 1. Check local offline SQLite cache first
        cached = self.cache.get_lyrics(artist, title)
        if cached:
            return cached

        variations = self.get_variations(artist, title)

        for a, t in variations:
            lyrics = self._query_lrclib(a, t, duration)
            if lyrics and (lyrics.get("syncedLyrics") or lyrics.get("plainLyrics")):
                result = self._format_lyrics(lyrics, a, t)
                self.cache.save_lyrics(artist, title, result)
                return result

        for a, t in variations:
            lyrics = self._search_lrclib(a, t, duration)
            if lyrics and (lyrics.get("syncedLyrics") or lyrics.get("plainLyrics")):
                result = self._format_lyrics(lyrics, a, t)
                self.cache.save_lyrics(artist, title, result)
                return result

        # Fallback 3: Search by sanitized clean title
        clean_title = re.sub(r"[^\w\s]", " ", title).strip()
        if clean_title and clean_title != title:
            lyrics = self._search_lrclib(artist, clean_title, duration)
            if lyrics and (lyrics.get("syncedLyrics") or lyrics.get("plainLyrics")):
                result = self._format_lyrics(lyrics, artist, title)
                self.cache.save_lyrics(artist, title, result)
                return result

        return None

    def _format_lyrics(self, lyrics: dict, artist: str, title: str) -> dict:
        parsed = self.parse_lrc(lyrics.get("syncedLyrics") or lyrics.get("plainLyrics") or "")
        return {
            "id": lyrics.get("id"),
            "title": lyrics.get("trackName") or title,
            "artist": lyrics.get("artistName") or artist,
            "is_synced": bool(lyrics.get("syncedLyrics")),
            "lines": parsed
        }

    def _query_lrclib(self, artist: str, title: str, duration: float):
        params = {
            "artist_name": artist,
            "track_name": title
        }
        if duration > 0:
            params["duration"] = str(int(duration))
            
        url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SpotifyLyricsDesktop/2.5"})
            with urllib.request.urlopen(req, timeout=3.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if data.get("syncedLyrics") or data.get("plainLyrics"):
                        return data
        except Exception:
            pass
        return None

    def _search_lrclib(self, artist: str, title: str, duration: float = 0):
        query = f"{artist} {title}"
        url = "https://lrclib.net/api/search?" + urllib.parse.urlencode({"q": query})
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SpotifyLyricsDesktop/2.5"})
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    items = json.loads(response.read().decode("utf-8"))
                    if items and isinstance(items, list):
                        synced = [it for it in items if it.get("syncedLyrics")]
                        if synced:
                            if duration > 0:
                                synced.sort(key=lambda x: abs((x.get("duration") or 0) - duration))
                            return synced[0]
                        return items[0]
        except Exception:
            pass
        return None

    def parse_lrc(self, lrc_text: str):
        lines = []
        if not lrc_text:
            return lines

        pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")
        has_synced = False

        for raw_line in lrc_text.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            matches = pattern.findall(raw_line)
            if matches:
                has_synced = True
                for min_str, sec_str, text in matches:
                    sec = int(min_str) * 60 + float(sec_str)
                    text = text.strip()
                    if text:
                        lines.append({
                            "time": round(sec, 2),
                            "text": text
                        })
            elif not has_synced and raw_line:
                if not (raw_line.startswith("[") and ":" in raw_line and raw_line.endswith("]")):
                    lines.append({
                        "time": -1,
                        "text": raw_line
                    })

        if has_synced:
            lines.sort(key=lambda x: x["time"])

        return lines
