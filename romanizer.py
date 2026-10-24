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

class Romanizer:
    @staticmethod
    def romanize(text: str, lang: str = "auto") -> str:
        if not text:
            return ""

        # Check for Korean Hangul
        if re.search(r"[\uac00-\ud7a3]", text):
            return Romanizer.hangul_to_romaja(text)

        # Check for Japanese Kana
        if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
            return Romanizer.kana_to_romaji(text)

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
        while i < len(converted):
            if i + 1 < len(converted) and converted[i:i+2] in KANA_MAP:
                res.append(KANA_MAP[converted[i:i+2]])
                i += 2
            elif converted[i] in KANA_MAP:
                res.append(KANA_MAP[converted[i]])
                i += 1
            else:
                res.append(converted[i])
                i += 1
        return "".join(res)
