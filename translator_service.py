import urllib.request
import urllib.parse
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from cache_service import get_cache
from romanizer import Romanizer

logger = logging.getLogger("TranslatorService")

TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
BATCH_SIZE = 35
BATCH_TIMEOUT = 5
SINGLE_TIMEOUT = 4.5
MAX_FALLBACK_WORKERS = 4

_MARKER_RE = re.compile(r"\[\[\s*(\d+)\s*\]\]")
_WORD_RE = re.compile(r"[^\W_]", re.UNICODE)


class TranslatorService:
    def __init__(self, target_lang="en"):
        self.target_lang = target_lang
        self.cache = get_cache()

    def set_target_lang(self, lang: str):
        self.target_lang = lang or "en"

    def translate_lines(self, lines: list, should_abort=None) -> tuple:
        """
        Takes: [{'time': float, 'text': str}, ...]
        Returns: ([{'time': float, 'original': str, 'translation': str, 'romaji': str}, ...], dominant_lang)

        ``should_abort`` is checked between batches and before the cache is
        written.  When it returns True the call returns ``([], "unknown")`` so
        a stale track can never leak partially translated lyrics into the UI.
        """
        if not lines:
            return [], "unknown"

        def aborted() -> bool:
            return bool(should_abort and should_abort())

        if aborted():
            return [], "unknown"

        texts = [item.get("text", "").strip() for item in lines]
        # Order-preserving dedupe: translation indices stay stable.
        unique_texts = list(dict.fromkeys([t for t in texts if t]))

        # 1. Query local SQLite cache.  Empty translations are not trusted for
        # real lines: a previous failed fallback must not poison future plays.
        raw_cached = self.cache.get_translations_batch(unique_texts, self.target_lang)
        cached_data = {}
        for source in unique_texts:
            row = raw_cached.get(source)
            if not row:
                continue
            translation = (row.get("translation") or "").strip()
            if translation or not self._is_translatable_line(source):
                cached_data[source] = row

        # 2. Find missing texts that need online translation
        missing_texts = [t for t in unique_texts if t not in cached_data]

        new_cached_entries = {}
        dominant_lang = "unknown"

        if missing_texts:
            for i in range(0, len(missing_texts), BATCH_SIZE):
                if aborted():
                    return [], "unknown"

                chunk = missing_texts[i:i + BATCH_SIZE]
                tr_chunk, romaji_chunk, lang = self._translate_chunk(
                    chunk, should_abort=should_abort
                )

                if lang != "unknown" and dominant_lang == "unknown":
                    dominant_lang = lang

                for index, src in enumerate(chunk):
                    trans = self._clean_cell(tr_chunk, index)
                    rom = self._clean_cell(romaji_chunk, index)
                    # If romanization from translate API is empty, use local Romanizer
                    if not rom:
                        rom = Romanizer.romanize(src)
                    # Never cache a completely empty result: it would look like
                    # a successful translation forever and suppress retries.
                    if trans or rom:
                        new_cached_entries[src] = {
                            "translation": trans,
                            "romaji": rom
                        }

            if aborted():
                return [], "unknown"

            # Save newly fetched translations & romanizations to SQLite only
            # once the whole operation completed successfully.
            if new_cached_entries:
                self.cache.save_translations_batch(new_cached_entries, self.target_lang)

        # Merge cached and new
        all_data = {**cached_data, **new_cached_entries}

        # A fully cached song never touches the network, so no API language is
        # available.  Derive it from the lyrics themselves for badge/label
        # updates on cached replays.
        if dominant_lang == "unknown":
            dominant_lang = self._detect_dominant_language(texts)

        enriched = []
        for item in lines:
            original = item.get("text", "").strip()
            data = all_data.get(original, {})
            tr = data.get("translation", "")
            romaji = data.get("romaji", "")

            # If translation is identical to original, treat as no translation needed
            if tr.strip().lower() == original.strip().lower() or len(original) <= 1:
                final_tr = ""
            else:
                final_tr = tr

            if not romaji:
                romaji = Romanizer.romanize(original)

            enriched.append({
                "time": item.get("time", -1),
                "original": original,
                "translation": final_tr,
                "romaji": romaji
            })

        return enriched, dominant_lang

    # ------------------------------------------------------------------
    # Chunk translation / fallback handling
    # ------------------------------------------------------------------
    def _translate_chunk(self, chunk: list, should_abort=None) -> tuple:
        """Translate one chunk, falling back per line if the batch is invalid."""
        try:
            tr_chunk, romaji_chunk, lang = self._translate_batch(chunk)
        except Exception as exc:
            logger.debug(f"Batch translation error: {exc}")
            tr_chunk, romaji_chunk, lang = [], [], "unknown"

        if self._is_aligned(tr_chunk, romaji_chunk, len(chunk)):
            return list(tr_chunk), list(romaji_chunk), lang

        logger.debug("Translation batch misaligned; retrying line by line.")
        return self._translate_lines_individually(chunk, should_abort=should_abort)

    @staticmethod
    def _is_translatable_line(text: str) -> bool:
        """True for real lyric text (not symbols/instrumental markers)."""
        stripped = (text or "").strip()
        return bool(stripped) and bool(_WORD_RE.search(stripped))

    @staticmethod
    def _detect_dominant_language(texts: list) -> str:
        """Count script characters and return ko/ja/zh only when dominant."""
        counts = {"ko": 0, "ja": 0, "zh": 0}
        for text in texts:
            for char in text or "":
                script = Romanizer.detect_script(char)
                if script in counts:
                    counts[script] += 1

        total = sum(counts.values())
        if total == 0:
            return "unknown"
        if counts["ko"] * 2 > total:
            return "ko"
        # Japanese mixes kana with Han characters, so kana presence marks the
        # whole Han+kana block as Japanese rather than Chinese.
        if counts["ja"] and (counts["ja"] + counts["zh"]) * 2 > total:
            return "ja"
        if counts["zh"] * 2 > total:
            return "zh"
        return "unknown"

    @staticmethod
    def _is_aligned(translations, romanizations, expected_count: int) -> bool:
        return (
            isinstance(translations, (list, tuple))
            and isinstance(romanizations, (list, tuple))
            and len(translations) == expected_count
            and len(romanizations) == expected_count
        )

    @staticmethod
    def _clean_cell(cells, index: int) -> str:
        if not cells or index >= len(cells):
            return ""
        value = cells[index]
        return value.strip() if isinstance(value, str) else ""

    def _translate_lines_individually(self, texts: list, should_abort=None) -> tuple:
        """Translate each line separately, preserving index alignment."""
        if not texts:
            return [], [], "unknown"

        def aborted() -> bool:
            return bool(should_abort and should_abort())

        if aborted():
            return ["" for _ in texts], ["" for _ in texts], "unknown"

        def translate_one(text):
            # Checked per task so queued lines stop quickly after a track change.
            if aborted():
                return "", "", "unknown"
            try:
                return self._translate_single(text)
            except Exception as exc:
                logger.debug(f"Single translation error: {exc}")
                return "", "", "unknown"

        results = [("", "", "unknown") for _ in texts]
        workers = min(MAX_FALLBACK_WORKERS, len(texts))
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(translate_one, text): index
                    for index, text in enumerate(texts)
                }
                for future, index in futures.items():
                    try:
                        results[index] = future.result()
                    except Exception as exc:
                        logger.debug(f"Single translation error: {exc}")
        except Exception as exc:
            logger.debug(f"Translation pool error: {exc}")
            for index, text in enumerate(texts):
                if aborted():
                    break
                try:
                    results[index] = self._translate_single(text)
                except Exception:
                    results[index] = ("", "", "unknown")

        translations = []
        romanizations = []
        lang = "unknown"
        for index, (translation, romaji, line_lang) in enumerate(results):
            translations.append(translation or "")
            romanizations.append(romaji or Romanizer.romanize(texts[index]))
            if lang == "unknown" and line_lang != "unknown":
                lang = line_lang
        return translations, romanizations, lang

    def _translate_single(self, text: str) -> tuple:
        """Translate one line. Returns (translation, romaji, lang)."""
        if not text:
            return "", "", "unknown"
        try:
            translated, romaji, lang = self._request_translation(text, SINGLE_TIMEOUT)
        except Exception as exc:
            logger.debug(f"Single translation request error: {exc}")
            return "", "", "unknown"

        romanization = romaji.strip() or Romanizer.romanize(text)
        return translated, romanization, lang

    def _translate_batch(self, texts: list) -> tuple:
        """
        Translates a batch and extracts both translated text and phonetic romanization.
        Returns aligned lists on success; empty lists on failure so the caller
        can fall back per line while honouring cancellation.
        """
        if not texts:
            return [], [], "unknown"

        marked_text = "\n".join(f"[[{index}]] {text}" for index, text in enumerate(texts))

        try:
            translated_str, romaji_str, lang = self._request_translation(
                marked_text, BATCH_TIMEOUT
            )
        except Exception as exc:
            logger.debug(f"Batch translation error: {exc}")
            return [], [], "unknown"

        translations = self._parse_marked_translations(translated_str, len(texts))
        if translations is None:
            logger.debug("Translated batch lost its index markers; using per-line fallback.")
            return [], [], "unknown"

        romanizations = self._align_romanizations(romaji_str, texts)
        return translations, romanizations, lang

    def _align_romanizations(self, romaji_text: str, texts: list) -> list:
        """Align API romanization to input lines or romanize locally."""
        expected = len(texts)
        if romaji_text:
            marked = self._parse_marked_translations(romaji_text, expected)
            if marked is not None:
                return marked

            raw_lines = romaji_text.splitlines()
            if len(raw_lines) == expected:
                aligned = [line.strip() for line in raw_lines]
                return [
                    aligned[index] or Romanizer.romanize(text)
                    for index, text in enumerate(texts)
                ]

        # Wrong shape (or no API romanization): never shift; romanize each line.
        return [Romanizer.romanize(text) for text in texts]

    def _request_translation(self, text: str, timeout: float) -> tuple:
        """Return (translated_text, romaji_text, detected_lang) for one request."""
        # 1. Primary: clients5.google.com (dict-chrome-ex) - fast, resilient, not rate-limited
        try:
            url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={self.target_lang}&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data and isinstance(data, list) and len(data) > 0:
                        if isinstance(data[0], list) and len(data[0]) > 0:
                            trans = data[0][0] if isinstance(data[0][0], str) else ""
                            lang = data[0][1] if len(data[0]) > 1 and isinstance(data[0][1], str) else "unknown"
                            if trans:
                                return trans.strip(), "", lang
        except Exception as exc:
            logger.debug(f"clients5 translation request error: {exc}")

        # 2. Secondary: translate.googleapis.com (gtx)
        try:
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": self.target_lang,
                "dt": ["t", "rm"],
                "q": text
            }
            url = TRANSLATE_ENDPOINT + "?" + urllib.parse.urlencode(params, doseq=True)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    trans_parts = []
                    romaji_parts = []
                    if data and len(data) > 0 and isinstance(data[0], list):
                        for seg in data[0]:
                            if seg and len(seg) > 0 and isinstance(seg[0], str):
                                trans_parts.append(seg[0])
                            elif seg and len(seg) > 3 and seg[0] is None and isinstance(seg[3], str):
                                romaji_parts.append(seg[3])
                    translated_str = "".join(trans_parts).strip()
                    romaji_str = "\n".join(part.strip() for part in romaji_parts if part.strip())
                    lang = data[2] if len(data) > 2 and isinstance(data[2], str) else "unknown"
                    if translated_str:
                        return translated_str, romaji_str, lang
        except Exception as exc:
            logger.debug(f"gtx translation request error: {exc}")

        # 3. Tertiary fallback: MyMemory Translation API
        try:
            url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=autodetect|{self.target_lang}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    res_data = data.get("responseData") or {}
                    trans = res_data.get("translatedText") or ""
                    if trans and not trans.startswith("MYMEMORY WARNING"):
                        return trans.strip(), "", "unknown"
        except Exception as exc:
            logger.debug(f"MyMemory translation request error: {exc}")

        return "", "", "unknown"

    # ------------------------------------------------------------------
    # Pure marker parser (unit-testable, no network)
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_marked_translations(text: str, expected_count: int):
        """Map ``[[n]] text`` markers back to their original indices.

        Returns a list of ``expected_count`` translations ordered by index, or
        ``None`` when the response is missing, duplicated, empty, unknown or
        otherwise unsafe to align.
        """
        if expected_count <= 0:
            return []

        if not isinstance(text, str) or not text.strip():
            return None

        matches = list(_MARKER_RE.finditer(text))
        if not matches:
            return None

        # Anything before the first marker is unexplained output: reject it so
        # a leading line cannot silently shift every translation.
        if text[:matches[0].start()].strip():
            return None

        found = {}
        for position, match in enumerate(matches):
            index = int(match.group(1))
            if index < 0 or index >= expected_count or index in found:
                return None

            end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
            content = text[match.end():end].strip()
            if not content:
                return None
            found[index] = content

        if len(found) != expected_count:
            return None

        return [found[index] for index in range(expected_count)]
