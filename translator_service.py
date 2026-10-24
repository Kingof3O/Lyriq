import urllib.request
import urllib.parse
import json
import logging
from cache_service import CacheService
from romanizer import Romanizer

logger = logging.getLogger("TranslatorService")

class TranslatorService:
    def __init__(self, target_lang="en"):
        self.target_lang = target_lang
        self.cache = CacheService()

    def set_target_lang(self, lang: str):
        self.target_lang = lang or "en"

    def translate_lines(self, lines: list) -> tuple:
        """
        Takes: [{'time': float, 'text': str}, ...]
        Returns: ([{'time': float, 'original': str, 'translation': str, 'romaji': str}, ...], dominant_lang)
        """
        if not lines:
            return [], "unknown"

        texts = [item.get("text", "").strip() for item in lines]
        unique_texts = list(set([t for t in texts if t]))

        # 1. Query local SQLite cache
        cached_data = self.cache.get_translations_batch(unique_texts, self.target_lang)

        # 2. Find missing texts that need online translation
        missing_texts = [t for t in unique_texts if t not in cached_data]
        
        new_cached_entries = {}
        dominant_lang = "unknown"

        if missing_texts:
            chunk_size = 35
            for i in range(0, len(missing_texts), chunk_size):
                chunk = missing_texts[i:i + chunk_size]
                tr_chunk, romaji_chunk, lang = self._translate_batch(chunk)
                if lang != "unknown" and dominant_lang == "unknown":
                    dominant_lang = lang
                for src, trans, rom in zip(chunk, tr_chunk, romaji_chunk):
                    # If romanization from translate API is empty, use local Romanizer
                    if not rom:
                        rom = Romanizer.romanize(src)
                    new_cached_entries[src] = {
                        "translation": trans,
                        "romaji": rom
                    }

            # Save newly fetched translations & romanizations to SQLite
            if new_cached_entries:
                self.cache.save_translations_batch(new_cached_entries, self.target_lang)

        # Merge cached and new
        all_data = {**cached_data, **new_cached_entries}

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

    def _translate_batch(self, texts: list) -> tuple:
        """
        Translates a batch and extracts both translated text and phonetic romanization (dt=['t', 'rm']).
        Returns: (translations: list, romanizations: list, lang: str)
        """
        if not texts:
            return [], [], "unknown"

        delimiter = "\n---@---\n"
        full_text = delimiter.join(texts)

        try:
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": self.target_lang,
                "dt": ["t", "rm"],
                "q": full_text
            }
            url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params, doseq=True)
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    
                    trans_parts = []
                    romaji_parts = []
                    
                    if data and len(data) > 0 and isinstance(data[0], list):
                        for seg in data[0]:
                            if seg and seg[0] and isinstance(seg[0], str):
                                trans_parts.append(seg[0])
                            elif seg and seg[0] is None and len(seg) > 3 and isinstance(seg[3], str):
                                romaji_parts = [r.strip() for r in seg[3].split("---@---")]

                    translated_str = "".join(trans_parts)
                    lang = data[2] if len(data) > 2 and isinstance(data[2], str) else "unknown"
                    
                    parts = translated_str.split("---@---")
                    cleaned_trans = [p.strip() for p in parts]
                    
                    # Pad or slice translations
                    if len(cleaned_trans) < len(texts):
                        cleaned_trans += ["" for _ in range(len(texts) - len(cleaned_trans))]
                    elif len(cleaned_trans) > len(texts):
                        cleaned_trans = cleaned_trans[:len(texts)]

                    # Pad or slice romanizations
                    if len(romaji_parts) < len(texts):
                        romaji_parts += ["" for _ in range(len(texts) - len(romaji_parts))]
                    elif len(romaji_parts) > len(texts):
                        romaji_parts = romaji_parts[:len(texts)]

                    return cleaned_trans, romaji_parts, lang

        except Exception as e:
            logger.debug(f"Batch translation error: {e}")

        return ["" for _ in texts], ["" for _ in texts], "unknown"
