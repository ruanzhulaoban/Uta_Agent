# -*- coding: utf-8 -*-
"""标注编排层：把原始歌词文本转换为结构化的行/词标注数据。

输出结构（当前第一阶段，对应需求 1、2 点）：

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
             "conjugation_type": "...", "conjugation_form": "..."}
          ]
        }
      ]
    }

后续阶段会在 word 层继续补充 ``jlpt``、``gloss``、``grammar`` 字段。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .kana import PUNCT_ROMAN, katakana_to_hiragana, to_romaji
from .mecab import MeCab, Token

# 标注数据格式版本
SCHEMA_VERSION = "0.1.0"


class Annotator:
    """歌词标注器。"""

    def __init__(self, mecab: Optional[MeCab] = None):
        self.mecab = mecab or MeCab()

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
        else:
            reading = katakana_to_hiragana(t.reading)
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
        }
