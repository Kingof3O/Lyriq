"""Multi-provider lyrics engine.

Providers are searched in priority order: local ``.lrc`` files, LRCLIB and
NetEase Cloud Music.  Everything returned by this module is JSON-friendly and
provider failures are contained so one unavailable service never breaks a
search.
"""

from __future__ import annotations

import difflib
import json
import logging
import math
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import app_paths
from lrc_parser import format_timestamp, merge_translations, parse_enhanced_lrc

logger = logging.getLogger("LyricsProviders")

LRCLIB_BASE = "https://lrclib.net"
NETEASE_BASE = "https://music.163.com"
USER_AGENT = "SpotifyLyricsDesktop/3.0"
PROVIDER_ORDER = ("local", "lrclib", "netease")
PROVIDER_NAMES = {
    "local": "Local .lrc",
    "lrclib": "LRCLIB",
    "netease": "NetEase Cloud Music",
}
PROVIDER_PRIORITY = {"local": 0, "lrclib": 1, "netease": 2}
PROVIDER_SCORE_BONUS = {"local": 14.0, "lrclib": 4.0, "netease": 2.0}


# ---------------------------------------------------------------------------
# Metadata normalisation
# ---------------------------------------------------------------------------
_SUFFIX_CONTENT = r"""
    remaster(?:ed)?(?:\s+[0-9Xx]{4})?(?:\s+version)?
  | [0-9Xx]{4}\s+remaster(?:ed)?(?:\s+version)?
  | deluxe(?:\s+(?:edition|version))?
  | live(?:\s+(?:at|from)\s+[^)\]]+)?(?:\s+version)?
  | from\s+[^)\]]+
  | theme\s+from\s+[^)\]]+
  | feat\.?[^)\]]*
  | ft\.?[^)\]]*
  | featuring[^)\]]*
  | official\s+(?:audio|video|music\s+video|lyric\s+video)
  | (?:official\s+)?(?:audio|video|music\s+video|lyric\s+video)
  | radio\s+edit
  | bonus\s+track
  | ost
  | original\s+soundtrack
  | single(?:\s+version)?
  | explicit(?:\s+version)?
  | clean(?:\s+version)?
  | album\s+version
"""
_PAREN_SUFFIX_RE = re.compile(
    r"\s*[\(\[]\s*(?:" + _SUFFIX_CONTENT + r")\s*[\)\]]",
    re.IGNORECASE | re.VERBOSE,
)
_DASH_SUFFIX_RE = re.compile(
    r"\s+[-\u2013\u2014]\s*(?:" + _SUFFIX_CONTENT + r")\s*$",
    re.IGNORECASE | re.VERBOSE,
)
_FEAT_SUFFIX_RE = re.compile(
    r"\s+(?:feat\.?|ft\.?|featuring)\s+[^\(\[\]]+$", re.IGNORECASE
)
_TRAILING_DASH_RE = re.compile(r"\s*[-\u2013\u2014]\s*$")
_BRACKETED_RE = re.compile(r"[\(\[]\s*[^\)\]]*[\)\]]")
_WHITESPACE_RE = re.compile(r"\s+")


def _collapse(value) -> str:
    return _WHITESPACE_RE.sub(" ", str(value or "")).strip()


def _strip_title_suffixes(value) -> str:
    text = _collapse(value)
    for _ in range(10):
        previous = text
        text = _PAREN_SUFFIX_RE.sub("", text)
        text = _DASH_SUFFIX_RE.sub("", text)
        text = _FEAT_SUFFIX_RE.sub("", text)
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        text = _TRAILING_DASH_RE.sub("", text)
        text = _collapse(text)
        if text == previous:
            break
    return text


def _key(value) -> str:
    return _collapse(value).casefold()


def _loose_key(value) -> str:
    """Casefold and punctuation-insensitive key used for fuzzy matching."""
    text = _strip_title_suffixes(value).casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return _collapse(text)


def _base_title_key(value) -> str:
    """Title key with every bracketed segment removed (bilingual titles)."""
    text = _BRACKETED_RE.sub(" ", str(value or ""))
    return _loose_key(text)


def _artist_match_key(value) -> str:
    text = _collapse(value)
    text = re.split(
        r"\s+(?:feat\.?|ft\.?|featuring|with)\s+", text, maxsplit=1, flags=re.I
    )[0]
    text = re.split(r"\s*[,&;]\s*", text, maxsplit=1)[0]
    return _loose_key(text)


def normalize_metadata(title: str, artist: str = "", album: str = "") -> dict:
    """Normalise track metadata for matching while retaining raw display data."""
    raw_title = "" if title is None else str(title)
    raw_artist = "" if artist is None else str(artist)
    raw_album = "" if album is None else str(album)

    clean_title = _strip_title_suffixes(raw_title) or _collapse(raw_title)
    clean_artist = _collapse(raw_artist)
    clean_album = _collapse(raw_album)

    return {
        "title": clean_title,
        "artist": clean_artist,
        "album": clean_album,
        "raw_title": raw_title,
        "raw_artist": raw_artist,
        "raw_album": raw_album,
        "title_key": _key(clean_title),
        "artist_key": _key(clean_artist),
    }


def _prepare_query(query) -> dict:
    if not isinstance(query, dict):
        query = {}
    if "raw_title" in query:
        prepared = dict(query)
        prepared["title"] = _collapse(prepared.get("title") or prepared.get("raw_title"))
        prepared["artist"] = _collapse(
            prepared.get("artist") or prepared.get("raw_artist")
        )
        prepared["album"] = _collapse(prepared.get("album") or prepared.get("raw_album"))
        prepared["raw_title"] = prepared.get("raw_title") or ""
        prepared["raw_artist"] = prepared.get("raw_artist") or ""
        prepared["raw_album"] = prepared.get("raw_album") or ""
        prepared["title_key"] = prepared.get("title_key") or _key(prepared["title"])
        prepared["artist_key"] = prepared.get("artist_key") or _key(prepared["artist"])
    else:
        prepared = normalize_metadata(
            query.get("title", ""), query.get("artist", ""), query.get("album", "")
        )
    prepared["duration"] = max(0.0, _safe_float(prepared.get("duration")))
    return prepared


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _safe_float(value, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _title_points(query_title, candidate_title) -> float:
    exact_query = _key(query_title)
    exact_candidate = _key(candidate_title)
    if exact_query and exact_candidate and exact_query == exact_candidate:
        return 60.0

    query_key = _loose_key(query_title)
    candidate_key = _loose_key(candidate_title)
    if not query_key or not candidate_key:
        return 0.0
    if query_key == candidate_key:
        return 52.0

    query_base = _base_title_key(query_title)
    candidate_base = _base_title_key(candidate_title)
    if query_base and query_base == candidate_base:
        return 48.0

    if query_base and candidate_base and (
        query_base in candidate_base or candidate_base in query_base
    ):
        ratio = min(len(query_base), len(candidate_base)) / max(
            len(query_base), len(candidate_base)
        )
        if ratio >= 0.5:
            return 44.0

    if query_key in candidate_key or candidate_key in query_key:
        ratio = min(len(query_key), len(candidate_key)) / max(
            len(query_key), len(candidate_key)
        )
        if ratio >= 0.5:
            return 40.0

    ratio = difflib.SequenceMatcher(None, query_key, candidate_key).ratio()
    if ratio >= 0.72:
        return round(35.0 * ratio, 2)
    return 0.0


def _artist_points(query_artist, candidate_artist) -> float:
    query_key = _artist_match_key(query_artist)
    candidate_key = _artist_match_key(candidate_artist)
    if not query_key or not candidate_key:
        return 0.0
    if query_key == candidate_key:
        return 22.0

    if query_key in candidate_key or candidate_key in query_key:
        ratio = min(len(query_key), len(candidate_key)) / max(
            len(query_key), len(candidate_key)
        )
        if ratio >= 0.75:
            return 18.0

    query_tokens = set(query_key.split())
    candidate_tokens = set(candidate_key.split())
    if query_tokens and candidate_tokens:
        overlap = query_tokens & candidate_tokens
        ratio = len(overlap) / max(len(query_tokens), len(candidate_tokens))
        if ratio >= 0.75:
            return round(18.0 * ratio, 2)

    ratio = difflib.SequenceMatcher(None, query_key, candidate_key).ratio()
    if ratio >= 0.86:
        return round(18.0 * ratio, 2)
    return 0.0


def _duration_points(query_duration, candidate_duration) -> float:
    query_value = max(0.0, _safe_float(query_duration))
    candidate_value = max(0.0, _safe_float(candidate_duration))
    if query_value <= 0 or candidate_value <= 0:
        return 0.0
    delta = abs(query_value - candidate_value)
    if delta <= 1.5:
        return 8.0
    if delta <= 3.0:
        return 6.0
    if delta <= 6.0:
        return 4.0
    if delta <= 10.0:
        return 1.5
    if delta <= 20.0:
        return 0.5
    return 0.0


def score_candidate(query: dict, candidate: dict) -> float:
    """Return a deterministic 0-100 score for a provider candidate."""
    if not isinstance(query, dict):
        query = {}
    if not isinstance(candidate, dict):
        return 0.0

    prepared = _prepare_query(query)
    title_points = _title_points(
        prepared.get("title") or prepared.get("raw_title"),
        candidate.get("title"),
    )
    artist_points = _artist_points(
        prepared.get("artist") or prepared.get("raw_artist"),
        candidate.get("artist"),
    )
    duration_points = _duration_points(
        prepared.get("duration"), candidate.get("duration")
    )
    synced_points = 4.0 if candidate.get("has_synced") else 0.0
    provider = str(candidate.get("provider") or "").lower()
    provider_points = PROVIDER_SCORE_BONUS.get(provider, 0.0)

    total = (
        title_points + artist_points + duration_points + synced_points + provider_points
    )
    return round(max(0.0, min(100.0, total)), 2)


def _normalise_candidate(candidate: dict, provider: str) -> dict | None:
    if not isinstance(candidate, dict):
        return None
    title = _collapse(candidate.get("title"))
    if not title:
        return None
    identifier = candidate.get("id")
    if identifier is None or str(identifier).strip() == "":
        return None
    return {
        "provider": provider,
        "id": str(identifier),
        "title": title,
        "artist": _collapse(candidate.get("artist")),
        "album": _collapse(candidate.get("album")),
        "duration": round(max(0.0, _safe_float(candidate.get("duration"))), 2),
        "has_synced": bool(candidate.get("has_synced")),
        "has_plain": bool(candidate.get("has_plain")),
        "score": 0.0,
    }


def _rank_key(candidate: dict):
    return (
        -_safe_float(candidate.get("score")),
        0 if candidate.get("has_synced") else 1,
        PROVIDER_PRIORITY.get(str(candidate.get("provider")), 99),
        str(candidate.get("title") or "").casefold(),
    )


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _http_json(url: str, timeout: float = 4.0, headers: dict | None = None):
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if headers:
        request_headers.update(headers)

    try:
        request = urllib.request.Request(url, headers=request_headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            body = response.read()
        if status != 200:
            logger.debug("Unexpected HTTP %s from %s", status, url)
            return None
        return json.loads(body.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        logger.debug("HTTP %s from %s: %s", exc.code, url, exc)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        logger.debug("Request failed for %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001 - providers must never crash the app
        logger.warning("Unexpected request error for %s: %s", url, exc)
    return None


# ---------------------------------------------------------------------------
# Local .lrc provider
# ---------------------------------------------------------------------------
_INVALID_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_METADATA_LINE_RE = re.compile(r"^\[([A-Za-z][A-Za-z0-9_#-]*):\s*(.*?)\]\s*$")
_LENGTH_RE = re.compile(r"^(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?$")


def _sanitize_filename_part(value, fallback: str) -> str:
    text = _collapse(value)
    text = _INVALID_FILENAME_RE.sub("_", text)
    text = _collapse(text).strip(" .")
    return (text[:90].strip(" .") or fallback)


def _lrc_value(value) -> str:
    return _collapse(str(value or "").replace("[", "(").replace("]", ")"))


def _format_lrc_lines(lines) -> list[str]:
    output: list[str] = []
    for line in lines or []:
        if isinstance(line, dict):
            text = _collapse(line.get("text"))
            translation = _collapse(line.get("translation"))
            timestamp = _safe_float(line.get("time"), -1.0)
        else:
            text = _collapse(line)
            translation = ""
            timestamp = -1.0
        if not text:
            continue

        if timestamp >= 0:
            prefix = format_timestamp(timestamp)
            output.append(f"{prefix}{text}")
            if translation:
                output.append(f"{prefix}({translation})")
        else:
            output.append(text)
            if translation:
                output.append(f"({translation})")
    return output


def _build_lrc_text(artist: str, title: str, lines) -> str:
    header = [
        f"[ti:{_lrc_value(title)}]",
        f"[ar:{_lrc_value(artist)}]",
        "[by:SpotifyLyrics]",
    ]
    body = _format_lrc_lines(lines)
    return "\n".join(header + [""] + body).rstrip() + "\n"


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    temp_path = None
    try:
        handle_number, temp_path = tempfile.mkstemp(
            prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent)
        )
        handle = os.fdopen(handle_number, "w", encoding="utf-8", newline="\n")
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        handle = None
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def save_local_lrc(artist: str, title: str, lines) -> dict:
    """Write an atomic ``<artist> - <title>.lrc`` under the app lrc folder."""
    safe_artist = _sanitize_filename_part(artist, "Unknown Artist")
    safe_title = _sanitize_filename_part(title, "Unknown Title")
    filename = f"{safe_artist} - {safe_title}.lrc"
    path = app_paths.get_lrc_dir() / filename
    try:
        _atomic_write_text(path, _build_lrc_text(artist, title, lines))
        return {"ok": True, "path": str(path)}
    except OSError as exc:
        logger.error("Could not save local lyrics to %s: %s", path, exc)
        return {"ok": False, "path": "", "error": str(exc)}


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1")


def _read_metadata(text: str) -> dict:
    metadata = {}
    for raw_line in text.splitlines():
        match = _METADATA_LINE_RE.match(raw_line.strip())
        if not match:
            continue
        key = match.group(1).lower()
        value = match.group(2).strip()
        if value and key not in metadata:
            metadata[key] = value
    return metadata


def _metadata_duration(value) -> float:
    match = _LENGTH_RE.match(str(value or "").strip())
    if not match:
        return 0.0
    seconds = int(match.group(1)) * 60 + int(match.group(2))
    fraction = match.group(3)
    if fraction:
        seconds += int(fraction) / (10 ** len(fraction))
    return round(float(seconds), 2)


def _resolve_local_lrc_path(value) -> Path | None:
    lrc_dir = app_paths.get_lrc_dir().resolve()
    raw = Path(str(value or ""))
    candidate = raw if raw.is_absolute() else lrc_dir / raw
    try:
        resolved = candidate.resolve()
        resolved.relative_to(lrc_dir)
    except (OSError, ValueError):
        return None
    return resolved


def _resolve_read_path(value) -> Path | None:
    raw = Path(str(value or ""))
    candidate = raw if raw.is_absolute() else app_paths.get_lrc_dir() / raw
    try:
        return candidate.resolve()
    except OSError:
        return None


def read_local_lrc_file(path) -> dict:
    """Read one local ``.lrc`` and return parsed lyrics with metadata."""
    resolved = _resolve_read_path(path)
    if resolved is None or not resolved.is_file():
        logger.debug("Local lyrics file not found: %s", path)
        return {}

    try:
        text = _read_text(resolved)
    except OSError as exc:
        logger.warning("Could not read local lyrics %s: %s", resolved, exc)
        return {}

    metadata = _read_metadata(text)
    stem = resolved.stem
    filename_artist = ""
    filename_title = stem
    if " - " in stem:
        filename_artist, filename_title = stem.split(" - ", 1)

    title = metadata.get("ti") or filename_title
    artist = metadata.get("ar") or filename_artist
    album = metadata.get("al") or ""
    lines = parse_enhanced_lrc(text)
    synced = bool(lines) and all(line.get("time", -1) >= 0 for line in lines)

    return {
        "provider": "local",
        "id": resolved.name,
        "path": str(resolved),
        "title": _collapse(title),
        "artist": _collapse(artist),
        "album": _collapse(album),
        "duration": _metadata_duration(metadata.get("length")),
        "is_synced": synced,
        "has_synced": synced,
        "has_plain": any(line.get("time", -1) < 0 for line in lines),
        "lines": lines,
    }


def list_local_lrc() -> list[dict]:
    """List every readable local LRC file as a provider candidate."""
    try:
        paths = sorted(app_paths.get_lrc_dir().glob("*.lrc"), key=lambda p: p.name.casefold())
    except OSError as exc:
        logger.warning("Could not list local lyrics folder: %s", exc)
        return []

    results = []
    for path in paths:
        data = read_local_lrc_file(path)
        if not data.get("lines"):
            continue
        results.append(
            {
                "provider": "local",
                "id": data.get("id") or path.name,
                "title": data.get("title") or path.stem,
                "artist": data.get("artist") or "",
                "album": data.get("album") or "",
                "duration": data.get("duration") or 0.0,
                "has_synced": bool(data.get("has_synced")),
                "has_plain": bool(data.get("has_plain")),
                "score": 0.0,
            }
        )
    return results


def _local_title_matches(query_title, candidate_title) -> bool:
    query_key = _loose_key(query_title)
    candidate_key = _loose_key(candidate_title)
    if not query_key or not candidate_key:
        return False
    if query_key == candidate_key:
        return True
    if _base_title_key(query_title) == _base_title_key(candidate_title):
        return True
    query_tokens = [w for w in query_key.split() if w]
    candidate_tokens = [w for w in candidate_key.split() if w]
    if query_tokens and candidate_tokens:
        overlap = set(query_tokens) & set(candidate_tokens)
        token_ratio = len(overlap) / max(len(query_tokens), len(candidate_tokens))
        if token_ratio >= 0.75:
            return True
    return difflib.SequenceMatcher(None, query_key, candidate_key).ratio() >= 0.88


def _local_artist_matches(query_artist, candidate_artist) -> bool:
    query_key = _artist_match_key(query_artist)
    candidate_key = _artist_match_key(candidate_artist)
    if not query_key or not candidate_key:
        return True
    if query_key == candidate_key:
        return True
    query_tokens = [w for w in query_key.split() if w]
    candidate_tokens = [w for w in candidate_key.split() if w]
    if query_tokens and candidate_tokens:
        overlap = set(query_tokens) & set(candidate_tokens)
        token_ratio = len(overlap) / max(len(query_tokens), len(candidate_tokens))
        if token_ratio >= 0.75:
            return True
    return difflib.SequenceMatcher(None, query_key, candidate_key).ratio() >= 0.9


class LocalLrcProvider:
    id = "local"
    name = "Local .lrc"

    def search(self, query: dict, limit: int = 12) -> list[dict]:
        prepared = _prepare_query(query)
        if not prepared.get("title") and not prepared.get("artist"):
            return []

        results = []
        for candidate in list_local_lrc():
            if prepared.get("title") and not _local_title_matches(
                prepared.get("title"), candidate.get("title")
            ):
                continue
            if prepared.get("artist") and not _local_artist_matches(
                prepared.get("artist"), candidate.get("artist")
            ):
                continue
            candidate["score"] = score_candidate(prepared, candidate)
            if candidate["score"] > 0:
                results.append(candidate)

        results.sort(key=_rank_key)
        return results[:max(1, int(limit))]

    def fetch(self, candidate: dict, query: dict | None = None) -> dict | None:
        raw_path = candidate.get("path") or candidate.get("id")
        resolved = _resolve_local_lrc_path(raw_path)
        if resolved is None or not resolved.is_file():
            return None
        data = read_local_lrc_file(resolved)
        if not data.get("lines"):
            return None
        data["id"] = resolved.name
        return data


# ---------------------------------------------------------------------------
# LRCLIB provider
# ---------------------------------------------------------------------------
class LrclibProvider:
    id = "lrclib"
    name = "LRCLIB"

    @staticmethod
    def _candidate(item: dict, query: dict) -> dict | None:
        if not isinstance(item, dict):
            return None
        title = item.get("trackName") or item.get("name") or ""
        artist = item.get("artistName") or ""
        if not title and not artist:
            return None
        if not (item.get("syncedLyrics") or item.get("plainLyrics")):
            return None

        identifier = item.get("id")
        if identifier is not None and str(identifier).strip() != "":
            candidate_id = f"lrclib:{identifier}"
        else:
            fallback_artist = artist or query.get("artist") or ""
            fallback_title = title or query.get("title") or ""
            candidate_id = f"lrclib:{fallback_artist}::{fallback_title}"

        return {
            "provider": "lrclib",
            "id": candidate_id,
            "title": title,
            "artist": artist,
            "album": item.get("albumName") or "",
            "duration": item.get("duration") or 0.0,
            "has_synced": bool(item.get("syncedLyrics")),
            "has_plain": bool(item.get("plainLyrics")),
            "score": 0.0,
        }

    @staticmethod
    def _lookup_by_query(artist: str, title: str, duration: float) -> dict | None:
        if not artist or not title:
            return None
        params = {"artist_name": artist, "track_name": title}
        if duration > 0:
            params["duration"] = str(int(round(duration)))
        url = f"{LRCLIB_BASE}/api/get?" + urllib.parse.urlencode(params)
        data = _http_json(url, timeout=3.5)
        if isinstance(data, dict) and (
            data.get("syncedLyrics") or data.get("plainLyrics")
        ):
            return data

        search_text = f"{artist} {title}".strip()
        search_url = f"{LRCLIB_BASE}/api/search?" + urllib.parse.urlencode(
            {"q": search_text}
        )
        results = _http_json(search_url, timeout=4.0)
        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                if item.get("syncedLyrics") or item.get("plainLyrics"):
                    return item
        return None

    def search(self, query: dict, limit: int = 12) -> list[dict]:
        prepared = _prepare_query(query)
        data = self._lookup_by_query(
            prepared.get("artist") or "",
            prepared.get("title") or "",
            _safe_float(prepared.get("duration")),
        )
        if not data:
            return []
        candidate = self._candidate(data, prepared)
        return [candidate] if candidate else []

    def fetch(self, candidate: dict, query: dict | None = None) -> dict | None:
        prepared = _prepare_query(query or candidate)
        raw_id = str(candidate.get("id") or "")
        if raw_id.startswith("lrclib:"):
            raw_id = raw_id[len("lrclib:") :]

        data = None
        if raw_id.isdigit():
            data = _http_json(f"{LRCLIB_BASE}/api/get/{raw_id}", timeout=3.5)

        if not isinstance(data, dict) or not (
            data.get("syncedLyrics") or data.get("plainLyrics")
        ):
            artist = candidate.get("artist") or prepared.get("artist") or ""
            title = candidate.get("title") or prepared.get("title") or ""
            data = self._lookup_by_query(
                artist, title, _safe_float(prepared.get("duration"))
            )

        if not isinstance(data, dict):
            return None

        synced_text = data.get("syncedLyrics") or ""
        plain_text = data.get("plainLyrics") or ""
        lines = parse_enhanced_lrc(synced_text) if synced_text else []
        if not lines and plain_text:
            lines = parse_enhanced_lrc(plain_text)
        if not lines:
            return None

        identifier = candidate.get("id")
        if data.get("id") is not None:
            identifier = f"lrclib:{data['id']}"
        if not identifier:
            artist = data.get("artistName") or prepared.get("artist") or ""
            title = data.get("trackName") or prepared.get("title") or ""
            identifier = f"lrclib:{artist}::{title}"

        return {
            "provider": "lrclib",
            "id": str(identifier),
            "title": data.get("trackName") or data.get("name") or candidate.get("title") or "",
            "artist": data.get("artistName") or candidate.get("artist") or "",
            "album": data.get("albumName") or candidate.get("album") or "",
            "is_synced": bool(lines) and all(line.get("time", -1) >= 0 for line in lines),
            "lines": lines,
        }


# ---------------------------------------------------------------------------
# NetEase provider
# ---------------------------------------------------------------------------
class NeteaseProvider:
    id = "netease"
    name = "NetEase Cloud Music"

    @staticmethod
    def _netease_id(value) -> str:
        text = str(value or "").strip()
        if text.startswith("netease:"):
            text = text[len("netease:") :]
        return text.strip()

    def search(self, query: dict, limit: int = 12) -> list[dict]:
        prepared = _prepare_query(query)
        term = " ".join(
            part for part in (prepared.get("artist"), prepared.get("title")) if part
        ).strip()
        if not term:
            return []

        request_limit = max(1, min(int(limit or 10), 10))
        url = f"{NETEASE_BASE}/api/search/get?" + urllib.parse.urlencode(
            {"s": term, "type": 1, "limit": request_limit}
        )
        data = _http_json(
            url, timeout=4.5, headers={"Referer": f"{NETEASE_BASE}/"}
        )
        result = data.get("result") if isinstance(data, dict) else None
        songs = result.get("songs") if isinstance(result, dict) else None
        if not isinstance(songs, list):
            return []

        results = []
        for song in songs:
            if not isinstance(song, dict):
                continue
            song_id = song.get("id")
            title = song.get("name") or song.get("title") or ""
            if song_id is None or not title:
                continue
            artists = song.get("artists") or song.get("ar") or []
            names = [
                artist.get("name")
                for artist in artists
                if isinstance(artist, dict) and artist.get("name")
            ]
            album = song.get("album") or song.get("al") or {}
            album_name = album.get("name") if isinstance(album, dict) else ""
            duration_ms = _safe_float(song.get("duration") or song.get("dt"))
            results.append(
                {
                    "provider": "netease",
                    "id": f"netease:{song_id}",
                    "title": title,
                    "artist": ", ".join(names),
                    "album": album_name or "",
                    "duration": round(duration_ms / 1000.0, 2) if duration_ms else 0.0,
                    "has_synced": True,
                    "has_plain": False,
                    "score": 0.0,
                }
            )
            if len(results) >= request_limit:
                break
        return results

    def fetch(self, candidate: dict, query: dict | None = None) -> dict | None:
        prepared = _prepare_query(query or candidate)
        song_id = self._netease_id(candidate.get("id"))
        if not song_id:
            return None

        url = f"{NETEASE_BASE}/api/song/lyric?" + urllib.parse.urlencode(
            {"id": song_id, "lv": 1, "kv": 1, "tv": -1}
        )
        data = _http_json(
            url, timeout=4.5, headers={"Referer": f"{NETEASE_BASE}/"}
        )
        if not isinstance(data, dict):
            return None
        code = data.get("code")
        if code not in (None, 200):
            logger.debug("NetEase lyric request for %s returned code %s", song_id, code)
            return None

        lrc_block = data.get("lrc")
        lrc_text = lrc_block.get("lyric") if isinstance(lrc_block, dict) else ""
        if not lrc_text:
            return None
        lines = parse_enhanced_lrc(lrc_text)
        if not lines:
            return None

        translation_block = data.get("tlyric")
        translation_text = (
            translation_block.get("lyric")
            if isinstance(translation_block, dict)
            else ""
        )
        if translation_text:
            merge_translations(lines, parse_enhanced_lrc(translation_text))

        return {
            "provider": "netease",
            "id": f"netease:{song_id}",
            "title": candidate.get("title") or prepared.get("title") or "",
            "artist": candidate.get("artist") or prepared.get("artist") or "",
            "album": candidate.get("album") or prepared.get("album") or "",
            "is_synced": all(line.get("time", -1) >= 0 for line in lines),
            "lines": lines,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
LOCAL_PROVIDER = LocalLrcProvider()
LRCLIB_PROVIDER = LrclibProvider()
NETEASE_PROVIDER = NeteaseProvider()
_PROVIDERS = {
    "local": LOCAL_PROVIDER,
    "lrclib": LRCLIB_PROVIDER,
    "netease": NETEASE_PROVIDER,
}


def get_lyrics_providers() -> list[dict]:
    """Return provider metadata for the settings/search UI."""
    return [
        {"id": provider_id, "name": PROVIDER_NAMES[provider_id], "available": True}
        for provider_id in PROVIDER_ORDER
    ]


def search_all(query: dict, limit: int = 12, providers=None) -> list[dict]:
    """Search every enabled provider and return scored, de-duplicated candidates."""
    prepared = _prepare_query(query)
    try:
        limit = max(1, int(limit))
    except (TypeError, ValueError):
        limit = 12

    if providers:
        requested = {str(item).lower() for item in providers}
        provider_ids = [item for item in PROVIDER_ORDER if item in requested]
    else:
        provider_ids = list(PROVIDER_ORDER)

    results: list[dict] = []
    seen_ids = set()
    seen_titles = set()

    for provider_id in provider_ids:
        provider = _PROVIDERS.get(provider_id)
        if provider is None:
            continue
        try:
            candidates = provider.search(prepared, limit=limit) or []
        except Exception as exc:  # noqa: BLE001 - a provider must not break search
            logger.warning("%s lyrics search failed: %s", provider_id, exc)
            continue

        for raw_candidate in candidates:
            candidate = _normalise_candidate(raw_candidate, provider_id)
            if candidate is None:
                continue

            identifier = (provider_id, candidate["id"])
            title_key = (
                _loose_key(candidate["title"]),
                _loose_key(candidate["artist"]),
            )
            if identifier in seen_ids or title_key in seen_titles:
                continue
            seen_ids.add(identifier)
            seen_titles.add(title_key)

            provided_score = _safe_float(raw_candidate.get("score"))
            candidate["score"] = round(
                min(100.0, max(score_candidate(prepared, candidate), provided_score)),
                2,
            )
            results.append(candidate)

    results.sort(key=_rank_key)
    return results[:limit]


def _coerce_lines(raw_lines) -> list[dict]:
    lines = []
    for raw_line in raw_lines or []:
        if not isinstance(raw_line, dict):
            continue
        text = _collapse(raw_line.get("text"))
        if not text:
            continue
        line = {"time": _safe_float(raw_line.get("time"), -1.0), "text": text}
        translation = _collapse(raw_line.get("translation"))
        if translation:
            line["translation"] = translation
        lines.append(line)
    return lines


def fetch_candidate(candidate: dict, query: dict) -> dict | None:
    """Fetch one candidate through its provider, returning formatted lyrics."""
    if not isinstance(candidate, dict):
        return None
    provider_id = str(candidate.get("provider") or "").lower()
    provider = _PROVIDERS.get(provider_id)
    if provider is None:
        logger.debug("Unknown lyrics provider %r", candidate.get("provider"))
        return None

    prepared = _prepare_query(query or candidate)
    try:
        data = provider.fetch(candidate, prepared)
    except Exception as exc:  # noqa: BLE001 - fetch failures are non-fatal
        logger.warning("%s lyrics fetch failed: %s", provider_id, exc)
        return None
    if not isinstance(data, dict):
        return None

    lines = _coerce_lines(data.get("lines"))
    if not lines:
        return None

    return {
        "provider": provider_id,
        "id": data.get("id") or candidate.get("id"),
        "title": _collapse(data.get("title")) or _collapse(candidate.get("title")) or prepared.get("title", ""),
        "artist": _collapse(data.get("artist")) or _collapse(candidate.get("artist")) or prepared.get("artist", ""),
        "album": _collapse(data.get("album")) or _collapse(candidate.get("album")) or prepared.get("album", ""),
        "is_synced": all(line.get("time", -1) >= 0 for line in lines),
        "lines": lines,
    }
