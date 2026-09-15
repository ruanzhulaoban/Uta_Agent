# -*- coding: utf-8 -*-
"""预构建释义词典：为高频词提供稳定的、语境无关的中文释义。

词典为 JSON 文件，结构：

    {
      "name": "utaagent-core-gloss",
      "version": "1.0.0",
      "entries": [
        {"surface": "桜", "reading": "さくら", "pos": "名詞",
         "meaning": "樱花", "jlpt_level": "N3"},
        ...
      ]
    }

查询以 ``surface + pos`` 为核心（``reading`` / ``base`` 辅助回退），
命中则返回条目（含 ``meaning``），未命中返回 ``None``。
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from .kana import katakana_to_hiragana

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "gloss", "gloss_dict.json",
)


class GlossDict:
    """把 (surface, pos) 映射到释义条目。"""

    def __init__(self, path: Optional[str] = None):
        path = path or os.environ.get("UTAAGENT_GLOSS_PATH") or _DEFAULT_PATH
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, dict):
            self.name = raw.get("name", "gloss-dict")
            self.version = raw.get("version", "")
            entries = raw.get("entries", [])
        else:  # 直接给条目数组也算合法
            self.name = "gloss-dict"
            self.version = ""
            entries = raw

        self._index: Dict[Tuple, Dict] = {}
        self._count = 0
        for e in entries:
            if not isinstance(e, dict):
                continue
            surface = (e.get("surface") or "").strip()
            if not surface:
                continue
            reading = katakana_to_hiragana((e.get("reading") or "").strip())
            pos = (e.get("pos") or "").strip()
            entry = {
                "surface": surface,
                "reading": reading,
                "pos": pos,
                "meaning": (e.get("meaning") or "").strip(),
                "jlpt_level": (e.get("jlpt_level") or "").strip(),
            }
            for key in self._keys(surface, reading, pos):
                self._index.setdefault(key, entry)
            self._count += 1

    @staticmethod
    def _keys(surface: str, reading: str, pos: str) -> List[Tuple]:
        """按 精确 -> 宽松 的顺序生成候选索引键。"""
        keys = []
        if pos:
            if reading:
                keys.append(("srp", surface, reading, pos))
            keys.append(("sp", surface, pos))
        if reading:
            keys.append(("sr", surface, reading))
        keys.append(("s", surface))
        return keys

    def lookup(
        self,
        surface: Optional[str] = None,
        reading: Optional[str] = None,
        pos: Optional[str] = None,
        base: Optional[str] = None,
    ) -> Optional[Dict]:
        """按 surface -> base 的顺序查释义，返回条目字典或 None。"""
        surface = (surface or "").strip()
        reading = katakana_to_hiragana((reading or "").strip())
        pos = (pos or "").strip()
        base = (base or "").strip()

        candidates: List[Tuple] = []
        if surface:
            candidates.extend(self._keys(surface, reading, pos))
        if base and base != surface:
            candidates.extend(self._keys(base, reading, pos))
        for key in candidates:
            entry = self._index.get(key)
            if entry is not None:
                return entry
        return None

    def __len__(self) -> int:
        return self._count
