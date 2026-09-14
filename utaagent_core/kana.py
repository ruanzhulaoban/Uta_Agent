# -*- coding: utf-8 -*-
"""假名 <-> 罗马音转换工具（基于修订版 Hepburn 罗马字）。

功能：
- 片假名 / 平假名之间的相互转换
- 假名 -> 罗马音（处理促音「っ」、长音「ー」、拨音「ん」、
  拗音「きゃ」、以及片假名外来语音节「ティ / ファ / ヴ」等）
"""

from __future__ import annotations

# 平假名与片假名之间的 Unicode 偏移量（ア - あ = 0x60）
_KANA_OFFSET = 0x60

# 元音的长音标记（长音符「ー」及「おう / えい」等长音对）
VOWEL_MACRON = {"a": "ā", "i": "ī", "u": "ū", "e": "ē", "o": "ō"}

# 平假名 -> 罗马音（Hepburn）
_HIRAGANA_ROMAN = {
    # 元音
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    # 清音
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "o", "ん": "n",
    # 浊音 / 半浊音
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    # 拗音（二合假名）
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo",
    "ぢゃ": "ja", "ぢゅ": "ju", "ぢょ": "jo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
    # 小写假名（用于片假名外来语的对应平假名形式）
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
    "ゃ": "ya", "ゅ": "yu", "ょ": "yo", "ゎ": "wa",
}

# 片假名专属音节（外来语）
_KATAKANA_EXTRA = {
    "ヴ": "vu",
    "ヴァ": "va", "ヴィ": "vi", "ヴェ": "ve", "ヴォ": "vo",
    "ファ": "fa", "フィ": "fi", "フェ": "fe", "フォ": "fo",
    "ティ": "ti", "ディ": "di", "トゥ": "tu", "ドゥ": "du",
    "ウィ": "wi", "ウェ": "we", "ウォ": "wo",
    "ツァ": "tsa", "ツィ": "tsi", "ツェ": "tse", "ツォ": "tso",
    "チェ": "che", "シェ": "she", "ジェ": "je",
    "イェ": "ye",
    "ヮ": "wa",
}

# 常见标点符号 -> 罗马音（用于无读音的「記号」词条）
PUNCT_ROMAN = {
    "。": ".", "、": ",", "，": ",", "．": ".",
    "！": "!", "？": "?", "‼": "!!", "⁇": "??",
    "・": " ", "…": "...", "‥": "..",
    "「": '"', "」": '"', "『": '"', "』": '"',
    "（": "(", "）": ")", "〈": "<", "〉": ">",
    "―": "-", "～": "~", "＝": "=", "♪": "♪",
    "　": " ", " ": " ",
}

# 由平假名表推导出片假名表（同音，仅字形不同）
_KATAKANA_ROMAN = {}
for _k, _v in _HIRAGANA_ROMAN.items():
    _KATAKANA_ROMAN["".join(chr(ord(c) + _KANA_OFFSET) for c in _k)] = _v
_KATAKANA_ROMAN.update(_KATAKANA_EXTRA)

# 完整的假名 -> 罗马音映射表（含平假名与片假名）
ROMAN_MAP = {**_HIRAGANA_ROMAN, **_KATAKANA_ROMAN}

# 常见长音对（在罗马音层面合并为一个长元音）
# 注意：刻意不合并 "ei"（先生 -> sensei）与 "ii"（新しい -> atarashii），
# 以符合日语学习资料的通行惯例。
_LONG_VOWELS = {
    "ou": "ō", "oo": "ō",
    "uu": "ū",
    "aa": "ā",
    "ee": "ē",
}


def katakana_to_hiragana(text: str) -> str:
    """片假名 -> 平假名（长音符「ー」保留原样）。"""
    out = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - _KANA_OFFSET))
        else:
            out.append(ch)
    return "".join(out)


def hiragana_to_katakana(text: str) -> str:
    """平假名 -> 片假名。"""
    out = []
    for ch in text:
        code = ord(ch)
        if 0x3041 <= code <= 0x3096:
            out.append(chr(code + _KANA_OFFSET))
        else:
            out.append(ch)
    return "".join(out)


def _lengthen(rom: str) -> str:
    """把最后一个罗马音节的元音变为长音（用于长音符「ー」）。"""
    for idx in range(len(rom) - 1, -1, -1):
        c = rom[idx]
        if c in VOWEL_MACRON:
            return rom[:idx] + VOWEL_MACRON[c] + rom[idx + 1:]
    return rom


def _geminate(rom: str) -> str:
    """促音（っ / ッ）处理：双写后续辅音。"""
    if not rom:
        return rom
    if rom.startswith("ch"):
        return "t" + rom  # っち -> tchi
    if rom.startswith("sh"):
        return "s" + rom  # っし -> sshi
    if rom.startswith("ts"):
        return "t" + rom  # っつ -> ttsu
    return rom[0] + rom  # 双写首辅音（っか -> kka）


def _peek_romaji(text: str, i: int) -> str:
    """返回从位置 i 开始的下一音节的罗马音（不做促音/长音/拨音处理）。"""
    if i >= len(text):
        return ""
    two = text[i:i + 2]
    rom = ROMAN_MAP.get(two)
    if rom is not None:
        return rom
    return ROMAN_MAP.get(text[i], "")


def _resolve_long_vowels(rom: str) -> str:
    """在罗马音层面合并常见长音对（おう / おお -> ō 等）。"""
    out = []
    i = 0
    while i < len(rom):
        two = rom[i:i + 2]
        if two in _LONG_VOWELS:
            out.append(_LONG_VOWELS[two])
            i += 2
        else:
            out.append(rom[i])
            i += 1
    return "".join(out)


def to_romaji(text: str, long_vowels: bool = True) -> str:
    """把假名字符串转换为罗马音（Hepburn）。

    支持：平假名、片假名、长音符「ー」、促音「っ/ッ」、
    拨音「ん/ン」（元音前加撇号）、拗音、外来语音节。
    非假名字符（如标点）原样保留，常见标点见 ``PUNCT_ROMAN``。
    """
    if not text:
        return ""
    result = []
    i = 0
    n = len(text)
    geminate = False
    while i < n:
        ch = text[i]
        # 长音符：拉长上一个音节的元音
        if ch == "ー":
            if result:
                result[-1] = _lengthen(result[-1])
            i += 1
            continue
        # 促音：标记下一个音节需要双写辅音
        if ch in ("っ", "ッ"):
            geminate = True
            i += 1
            continue
        # 先尝试二合假名（拗音 / 外来语音节），再退化为单字符
        two = text[i:i + 2]
        rom = ROMAN_MAP.get(two)
        if rom is not None:
            i += 2
        else:
            rom = ROMAN_MAP.get(ch, ch)
            i += 1
        if geminate:
            rom = _geminate(rom)
            geminate = False
        # 拨音「ん」在元音 / や行前加撇号（はんい -> han'i）
        if rom == "n":
            nxt = _peek_romaji(text, i)
            if nxt and nxt[0] in "aiueoy":
                rom = "n'"
        result.append(rom)
    romaji = "".join(result)
    if long_vowels:
        romaji = _resolve_long_vowels(romaji)
    return romaji
