# -*- coding: utf-8 -*-
"""标注编排层：把原始歌词文本转换为结构化的行/词标注数据。

输出结构（当前第一阶段，对应需求 1、2、3 点）：

    {
      "analyzer": {...},
      "lines": [
        {
          "text": "原歌词行",
          "reading": "整行平假名读音",
          "romaji": "整行罗马音",
          "words": [
            {"surface": "...", "reading": "...", "romaji": "...",
             "pos": "...", "pos1": "...", "base": "...",
             "conjugation_type": "...", "conjugation_form": "...",
             "jlpt": "N5"}
          ]
        }
      ]
    }

Glossifier 在词层补充 gloss/source，在行层补充 grammar 与处理状态。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .jlpt import JlptTagger
from .kana import PUNCT_ROMAN, katakana_to_hiragana, to_romaji
from .mecab import MeCab, Token

# 标注数据格式版本
SCHEMA_VERSION = "0.1.0"

# 虚词 / 符号不参与 JLPT 等级标注（词表中不含这些功能词）
_FUNCTION_POS = {"助詞", "助動詞", "記号", "フィラー", "その他"}


class Annotator:
    """歌词标注器。

    ``jlpt`` 参数：
      - ``None``（默认）：使用内置 JLPT 词表；
      - ``False``：禁用 JLPT 等级标注；
      - 传入 ``JlptTagger`` 实例：使用自定义词表。
    """

    def __init__(self, mecab: Optional[MeCab] = None, jlpt: Optional[JlptTagger] = None):
        self.mecab = mecab or MeCab()
        if jlpt is None:
            self.jlpt = JlptTagger()
        elif jlpt is False:
            self.jlpt = None
        else:
            self.jlpt = jlpt

    def annotate(self, text: str) -> Dict:
        """标注整段歌词文本。"""
        lines = text.splitlines()
        tokens_per_line = self.mecab.parse_lines(lines)
        annotated_lines = []
        for raw, tokens in zip(lines, tokens_per_line):
            annotated_lines.append(self._annotate_line(raw, tokens))
        return {
            "schema_version": SCHEMA_VERSION,
            "analyzer": {
                "name": "mecab",
                "path": self.mecab.path,
                "dicdir": self.mecab.dicdir,
                "dictionary": "ipadic",
            },
            "lines": annotated_lines,
        }

    def _annotate_line(self, raw: str, tokens: List[Token]) -> Dict:
        words = [self._annotate_token(t) for t in tokens]
        line_reading = "".join(w["reading"] for w in words)
        line_romaji = " ".join(w["romaji"] for w in words if w["romaji"]).strip()
        return {
            "text": raw,
            "reading": line_reading,
            "romaji": line_romaji,
            "words": words,
        }

    def _annotate_token(self, t: Token) -> Dict:
        # 读音未知（如标点、未知词）：读音取表層形，罗马音查标点表
        if t.is_unknown:
            reading = t.surface
            romaji = PUNCT_ROMAN.get(t.surface, "")
            reading_hira = None
        else:
            reading_hira = katakana_to_hiragana(t.reading)
            reading = reading_hira
            # 罗马音用「発音」字段生成，能正确反映实际读音
            # （如助词 は -> wa、长音 ガッコウ -> ガッコー -> gakkō）
            pron = t.pron if t.pron not in ("", "*") else t.reading
            romaji = to_romaji(pron)

        return {
            "surface": t.surface,
            "reading": reading,
            "romaji": romaji,
            "pos": t.pos or None,
            "pos1": t.pos1 or None,
            "base": t.base or None,
            "conjugation_type": t.ctype or None,
            "conjugation_form": t.cform or None,
            "jlpt": self._jlpt_level(t, reading_hira),
        }

    def _jlpt_level(self, t: Token, reading_hira: Optional[str]) -> Optional[str]:
        """按 原形 -> 表層形 -> 读音 的顺序查 JLPT 等级。"""
        if self.jlpt is None:
            return None
        if t.pos in _FUNCTION_POS:
            return None
        base = t.base if t.base not in ("", "*") else None
        if base:
            level = self.jlpt.lookup(form=base, reading=reading_hira)
            if level:
                return level
        level = self.jlpt.lookup(form=t.surface, reading=reading_hira)
        if level:
            return level
        return self.jlpt.lookup(reading=reading_hira)
