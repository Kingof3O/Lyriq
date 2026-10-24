"""Enhanced LRC parsing helpers shared by every lyrics provider.

The parser is intentionally dependency-free.  It understands standard
``[mm:ss.xx]`` timestamps (including several timestamps on one line), LRC
metadata tags, and the local translation extension where a translation is
written as ``[mm:ss.xx](translation)`` immediately after its original line.
"""

from __future__ import annotations

import math
import re

_TIMESTAMP_RE = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")
_METADATA_RE = re.compile(r"^\[([A-Za-z][A-Za-z0-9_#-]*):\s*(.*?)\]\s*$")
_TRANSLATION_RE = re.compile(r"^\((.*)\)$", re.DOTALL)
_TRANSLATION_TOLERANCE = 0.15


def _safe_float(value, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _frame_to_seconds(minutes: str, seconds: str, fraction: str | None) -> float:
    value = int(minutes) * 60 + int(seconds)
    if fraction:
        value += int(fraction) / (10 ** len(fraction))
    return round(value, 2)


def format_timestamp(seconds) -> str:
    """Format seconds as a standard centisecond LRC timestamp."""
    total = int(round(max(0.0, _safe_float(seconds)) * 100))
    minutes, remainder = divmod(total, 6000)
    secs, centis = divmod(remainder, 100)
    return f"[{minutes:02d}:{secs:02d}.{centis:02d}]"


def _split_timestamps(raw_line: str) -> tuple[list[float], str]:
    timestamps = [
        _frame_to_seconds(match.group(1), match.group(2), match.group(3))
        for match in _TIMESTAMP_RE.finditer(raw_line)
    ]
    content = _TIMESTAMP_RE.sub("", raw_line).strip()
    return timestamps, content


def _times_match(times, group, tolerance: float = _TRANSLATION_TOLERANCE) -> bool:
    return any(
        abs(timestamp - line.get("time", -1)) <= tolerance
        for timestamp in times
        for line in group
    )


def _merge_plain_translation(previous_line: dict, content: str) -> bool:
    match = _TRANSLATION_RE.match(content)
    if not match:
        return False
    translation = match.group(1).strip()
    if translation and not previous_line.get("translation"):
        previous_line["translation"] = translation
    return True


def parse_enhanced_lrc(text) -> list[dict]:
    """Parse LRC or plain lyrics into ``{time, text, translation?}`` dicts.

    Synced input returns only timestamped lines (sorted by time), with time
    ``-1`` reserved for plain lyrics.  Metadata tags such as ``[ti:]`` are
    ignored.  Malformed timestamp-like lines never raise.
    """
    if not isinstance(text, str) or not text:
        return []

    raw_lines = text.lstrip("\ufeff").splitlines()
    has_timestamps = any(_TIMESTAMP_RE.search(line) for line in raw_lines)

    parsed: list[dict] = []
    previous_group: list[dict] = []
    previous_plain: dict | None = None

    for raw_line in raw_lines:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        timestamps, content = _split_timestamps(raw_line)
        if timestamps:
            if content and _TRANSLATION_RE.match(content) and previous_group:
                translation = _TRANSLATION_RE.match(content).group(1).strip()
                if not translation:
                    previous_group = []
                    previous_plain = None
                    continue
                if _times_match(timestamps, previous_group):
                    for line in previous_group:
                        if not line.get("translation"):
                            line["translation"] = translation
                    previous_group = []
                    previous_plain = None
                    continue

            group: list[dict] = []
            for timestamp in timestamps:
                if not content:
                    continue
                line = {"time": timestamp, "text": content}
                parsed.append(line)
                group.append(line)
            previous_group = group
            previous_plain = None
            continue

        # A plain line inside an otherwise synced document is almost always a
        # tag, a comment, or stray text.  Keep synced output clean.
        if has_timestamps:
            continue

        if _METADATA_RE.match(raw_line):
            continue

        if previous_plain is not None and _merge_plain_translation(
            previous_plain, raw_line
        ):
            previous_plain = None
            continue

        line = {"time": -1, "text": raw_line}
        parsed.append(line)
        previous_plain = line

    if has_timestamps:
        parsed.sort(key=lambda item: (item["time"], item["text"].casefold()))
    return parsed


def merge_translations(lines: list[dict], translations: list[dict]) -> list[dict]:
    """Merge timestamp-keyed translation lines into ``lines`` in place.

    Exact timestamps are preferred; a translation within 0.15 s of an
    original line is accepted so providers with slightly different
    centisecond rounding still align.  Existing translations are preserved.
    """
    if not lines or not translations:
        return lines

    by_time: dict[float, list[dict]] = {}
    for line in lines:
        timestamp = round(_safe_float(line.get("time"), -1.0), 2)
        by_time.setdefault(timestamp, []).append(line)

    for translated in translations:
        text = str(translated.get("text") or "").strip()
        if not text:
            continue
        timestamp = round(_safe_float(translated.get("time"), -1.0), 2)
        if timestamp < 0:
            continue

        target = None
        matches = by_time.get(timestamp)
        if matches:
            target = matches[-1]
        else:
            best_delta = _TRANSLATION_TOLERANCE + 0.001
            for candidate_time, candidate_lines in by_time.items():
                delta = abs(candidate_time - timestamp)
                if delta < best_delta:
                    best_delta = delta
                    target = candidate_lines[-1]

        if target is not None and not target.get("translation"):
            target["translation"] = text

    return lines
