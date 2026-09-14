# -*- coding: utf-8 -*-
"""utaagent —— 日语歌词学习 agent。

第一阶段（当前）：接入 MeCab 形态素分析器，实现分词、词性标注、
假名注音（ふりがな）与罗马音生成。

后续阶段：JLPT 等级标注、语境化释义与语法点提取、LyricDoc JSON 输出。
"""

from .kana import to_romaji, katakana_to_hiragana, hiragana_to_katakana
from .mecab import MeCab, Token, find_mecab
from .annotator import Annotator

__version__ = "0.1.0"

__all__ = [
    "Annotator",
    "MeCab",
    "Token",
    "find_mecab",
    "to_romaji",
    "katakana_to_hiragana",
    "hiragana_to_katakana",
    "__version__",
]
