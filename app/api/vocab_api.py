"""Vocabulary notebook, word definitions, and CSV export APIs."""

import json
import logging
import os
import urllib.parse
import urllib.request
from romanizer import Romanizer

logger = logging.getLogger("VocabAPI")


class VocabAPIMixin:
    def save_vocab_word(self, word, romaji, meaning, lang, song_title):
        return self._app.lyrics_service.cache.save_vocab_word(
            word, romaji, meaning, lang, song_title
        )

    def get_vocab_words(self):
        return self._app.lyrics_service.cache.get_vocab_words()

    def delete_vocab_word(self, word_id):
        self._app.lyrics_service.cache.delete_vocab_word(int(word_id))

    def export_vocab_csv(self):
        try:
            words = self._app.lyrics_service.cache.get_vocab_words()
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            out_path = os.path.join(desktop, "Spotify_Vocabulary_Deck.csv")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("Word\tPhonetics\tMeaning\tLanguage\tSong\n")
                for w in words:
                    f.write(
                        f"{w['word']}\t{w['romaji']}\t{w['meaning']}\t{w['lang']}\t{w['song_title']}\n"
                    )
            return f"Exported {len(words)} words to Desktop (Spotify_Vocabulary_Deck.csv)"
        except Exception as e:
            return f"Export error: {e}"

    def lookup_word(self, word):
        """Instant translation & dictionary lookup for a single word/phrase."""
        try:
            word = word.strip()
            if not word:
                return {"word": "", "trans": "", "romaji": "", "lang": "unknown"}

            romaji = Romanizer.romanize(word)
            target = self._app.translator_service.target_lang or "en"

            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target,
                "dt": ["t", "rm"],
                "q": word,
            }
            url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(
                params, doseq=True
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                trans_parts = []
                api_romaji = ""
                if data and len(data) > 0 and isinstance(data[0], list):
                    for seg in data[0]:
                        if seg and seg[0] and isinstance(seg[0], str):
                            trans_parts.append(seg[0])
                        elif (
                            seg
                            and seg[0] is None
                            and len(seg) > 3
                            and isinstance(seg[3], str)
                        ):
                            api_romaji = seg[3]

                trans = "".join(trans_parts).strip()
                lang = (
                    data[2]
                    if len(data) > 2 and isinstance(data[2], str)
                    else "unknown"
                )

                return {
                    "word": word,
                    "trans": trans,
                    "romaji": api_romaji or romaji,
                    "lang": lang,
                }
        except Exception as e:
            return {
                "word": word,
                "trans": f"Lookup error: {e}",
                "romaji": "",
                "lang": "unknown",
            }
