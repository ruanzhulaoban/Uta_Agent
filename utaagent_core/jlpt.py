# -*- coding: utf-8 -*-
"""JLPT 词汇等级查询。

数据来源：Bluskyo/JLPT_Vocabulary（原始数据为 tanos.co.uk 的 Jonathan Waller 整理），
许可：CC BY（署名），详见 ``data/jlpt/LICENSE.txt``。

词表把「词形」（汉字或假名）映射到若干 ``{reading, level}`` 条目，其中
level 取值 5..1，对应 N5..N1（数值越大越初级）。

同一个词形可能有多条读音、且不同读音等级不同（如「人」：
じん=N1、ひと=N5），因此匹配时优先用「词形 + 读音」精确匹配，
再退化为「词形」或「读音」，取该词形下最容易的等级（N5 优先）。
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple

from .kana import katakana_to_hiragana

_LEVEL_TO_STR = {5: "N5", 4: "N4", 3: "N3", 2: "N2", 1: "N1"}

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "jlpt", "JLPT_vocab_ALL.json",
)


class JlptTagger:
    """把词形 / 读音映射到 JLPT 等级。"""

    def __init__(self, path: Optional[str] = None):
        path = path or os.environ.get("UTAAGENT_JLPT_PATH") or _DEFAULT_PATH
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        # (词形, 读音) -> level（精确匹配）
        self._form_reading: Dict[Tuple[str, str], int] = {}
        # 词形 -> level（取该词形下最容易的等级）
        self._form: Dict[str, int] = {}
        # 读音 -> level（取最容易的等级）
        self._reading: Dict[str, int] = {}

        for form, entries in raw.items():
            form = form.strip()
            if not form:
                continue
            easiest = max(e["level"] for e in entries)
            self._form[form] = max(self._form.get(form, 0), easiest)
            for e in entries:
                reading = katakana_to_hiragana(e.get("reading", "").strip())
                if not reading:
                    continue
                self._form_reading[(form, reading)] = e["level"]
                self._reading[reading] = max(
                    self._reading.get(reading, 0), e["level"]
                )

    def lookup(self, form: Optional[str] = None, reading: Optional[str] = None) -> Optional[str]:
        """按 词形+读音 -> 词形 -> 读音 的顺序查等级，返回 "N5".."N1" 或 None。

        ``form`` 可为表層形或原形；``reading`` 可为平假名或片假名。
        """
        form = (form or "").strip()
        reading = katakana_to_hiragana((reading or "").strip())

        if form and reading:
            lv = self._form_reading.get((form, reading))
            if lv is not None:
                return _LEVEL_TO_STR[lv]
        if form:
            lv = self._form.get(form)
            if lv is not None:
                return _LEVEL_TO_STR[lv]
        if reading:
            lv = self._reading.get(reading)
            if lv is not None:
                return _LEVEL_TO_STR[lv]
        return None

    def __len__(self) -> int:
        return len(self._form)
