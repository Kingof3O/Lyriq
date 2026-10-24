import re

# Korean Hangul Jamo tables
CHOSEONG = ['g', 'kk', 'n', 'd', 'tt', 'r', 'm', 'b', 'pp', 's', 'ss', '', 'j', 'jj', 'ch', 'k', 't', 'p', 'h']
JUNGSEONG = ['a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 'wae', 'oe', 'yo', 'u', 'wo', 'we', 'wi', 'yu', 'eu', 'ui', 'i']
JONGSEONG = ['', 'k', 'kk', 'ks', 'n', 'nj', 'nh', 't', 'l', 'lg', 'lm', 'lb', 'ls', 'lt', 'lp', 'lh', 'm', 'p', 'ps', 's', 'ss', 'ng', 'j', 'ch', 'k', 't', 'p', 'h']

# Japanese Kana mapping
KANA_MAP = {
    'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
    'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
    'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
    'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
    'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
    'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
    'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
    'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
    'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
    'わ': 'wa', 'を': 'wo', 'ん': 'n',
    'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go',
    'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
    'だ': 'da', 'ぢ': 'ji', 'づ': 'zu', 'で': 'de', 'ど': 'do',
    'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo',
    'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po',
    'ゔ': 'vu',
    'ぁ': 'a', 'ぃ': 'i', 'ぅ': 'u', 'ぇ': 'e', 'ぉ': 'o',
    'ゃ': 'ya', 'ゅ': 'yu', 'ょ': 'yo', 'ゎ': 'wa',
    'きゃ': 'kya', 'きゅ': 'kyu', 'きょ': 'kyo',
    'しゃ': 'sha', 'しゅ': 'shu', 'しょ': 'sho',
    'ちゃ': 'cha', 'ちゅ': 'chu', 'ちょ': 'cho',
    'にゃ': 'nya', 'にゅ': 'nyu', 'にょ': 'nyo',
    'ひゃ': 'hya', 'ひゅ': 'hyu', 'ひょ': 'hyo',
    'みゃ': 'mya', 'みゅ': 'myu', 'みょ': 'myo',
    'りゃ': 'rya', 'りゅ': 'ryu', 'りょ': 'ryo',
    'ぎゃ': 'gya', 'ぎゅ': 'gyu', 'ぎょ': 'gyo',
    'じゃ': 'ja', 'じゅ': 'ju', 'じょ': 'jo',
    'びゃ': 'bya', 'びゅ': 'byu', 'びょ': 'byo',
    'ぴゃ': 'pya', 'ぴゅ': 'pyu', 'ぴょ': 'pyo',
}

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
KANA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
VOWELS = "aeiou"

# pypinyin is optional: import it lazily so builds remain dependency-free.
_pypinyin_module = None
_pypinyin_checked = False


def _get_pypinyin():
    global _pypinyin_module, _pypinyin_checked
    if not _pypinyin_checked:
        try:
            import pypinyin as module
        except Exception:
            module = None
        _pypinyin_module = module
        _pypinyin_checked = True
    return _pypinyin_module


class Romanizer:
    @staticmethod
    def detect_script(text: str) -> str:
        """Return the dominant script: ``ko``, ``ja``, ``zh`` or ``""``."""
        if not text:
            return ""
        if HANGUL_RE.search(text):
            return "ko"
        if KANA_RE.search(text):
            return "ja"
        if HAN_RE.search(text):
            return "zh"
        return ""

    @staticmethod
    def romanize(text: str, lang: str = "auto") -> str:
        if not text:
            return ""

        # Check for Korean Hangul
        if HANGUL_RE.search(text):
            return Romanizer.hangul_to_romaja(text)

        # Check for Japanese Kana
        if KANA_RE.search(text):
            return Romanizer.kana_to_romaji(text)

        # Chinese Han characters use optional pypinyin (tone-less by default).
        if HAN_RE.search(text):
            pypinyin = _get_pypinyin()
            if pypinyin is None:
                return ""
            try:
                syllables = pypinyin.lazy_pinyin(text)
                return " ".join(str(syllable).lower() for syllable in syllables).strip()
            except Exception:
                return ""

        return ""

    @staticmethod
    def hangul_to_romaja(text: str) -> str:
        result = []
        for char in text:
            code = ord(char)
            if 0xAC00 <= code <= 0xD7A3:
                syllable_index = code - 0xAC00
                cho = syllable_index // 588
                jung = (syllable_index % 588) // 28
                jong = syllable_index % 28

                rom = CHOSEONG[cho] + JUNGSEONG[jung] + JONGSEONG[jong]
                result.append(rom)
            else:
                result.append(char)
        return "".join(result)

    @staticmethod
    def kana_to_romaji(text: str) -> str:
        # Convert Katakana to Hiragana for uniform lookup
        converted = ""
        for char in text:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                converted += chr(code - 0x60)
            else:
                converted += char

        res = []
        i = 0
        geminate = False
        while i < len(converted):
            char = converted[i]

            # Small tsu doubles the next consonant.
            if char == 'っ':
                geminate = True
                i += 1
                continue

            # Long vowel mark repeats the previous vowel.
            if char == 'ー':
                if res:
                    previous = res[-1]
                    for candidate in reversed(previous):
                        if candidate in VOWELS:
                            res.append(candidate)
                            break
                i += 1
                continue

            if i + 1 < len(converted) and converted[i:i+2] in KANA_MAP:
                rom = KANA_MAP[converted[i:i+2]]
                i += 2
            elif char in KANA_MAP:
                rom = KANA_MAP[char]
                i += 1
            else:
                res.append(char)
                geminate = False
                i += 1
                continue

            if geminate:
                if rom and rom[0].isalpha() and rom[0] not in VOWELS:
                    rom = rom[0] + rom
                geminate = False
            res.append(rom)
        return "".join(res)
