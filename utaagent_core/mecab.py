# -*- coding: utf-8 -*-
"""MeCab 形态素分析器的轻量封装。

通过子进程调用 mecab 可执行文件。词典与二进制路径会自动探测
（见 :func:`find_mecab`），也可通过环境变量 ``MECAB_PATH`` /
``MECAB_DICDIR`` 或构造参数覆盖。

MeCab 会依据上下文（Viterbi 解码）自动选择正确的汉字读音，
因此「处理上下文相关的汉字读音」这一需求由分析器本身保证。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

# 节点输出格式：原文 + 词性层级 + 活用 + 原形 + 读音 + 发音，用制表符分隔。
# 注意：这里的 \t / \n 是字面转义（meCab 自己解释），因此用原始字符串；
# 末尾的 \n 必不可少，否则同一行的多个词条会被拼接成一行。
_NODE_FORMAT = r"%m\t%f[0]\t%f[1]\t%f[2]\t%f[3]\t%f[4]\t%f[5]\t%f[6]\t%f[7]\t%f[8]\n"
_UNKNOWN_FORMAT = r"%m\t%f[0]\t%f[1]\t%f[2]\t%f[3]\t%f[4]\t%f[5]\t%m\t*\t*\n"

# EOS 哨兵：用不易与歌词冲突的字符串，便于按行切分结果。
_EOS = "__UTAAGENT_EOS__"

_KNOWN_MECAB_PATHS = [
    r"C:/msys64/mingw64/bin/mecab.exe",
    r"C:/msys64/usr/bin/mecab.exe",
    r"C:/Program Files/MeCab/bin/mecab.exe",
    r"C:/Program Files (x86)/MeCab/bin/mecab.exe",
]


@dataclass
class Token:
    """MeCab 解析出的单个词条。"""

    surface: str      # 表層形（原文）
    pos: str          # 品詞（名詞 / 動詞 / 助詞 ...）
    pos1: str         # 品詞細分類1（一般 / 自立 ...）
    pos2: str         # 品詞細分類2
    pos3: str         # 品詞細分類3
    ctype: str        # 活用型
    cform: str        # 活用形
    base: str         # 原形
    reading: str      # 読み（片假名，未知时为 "*"）
    pron: str         # 発音（片假名）

    @property
    def is_symbol(self) -> bool:
        return self.pos == "記号"

    @property
    def is_unknown(self) -> bool:
        return self.reading in ("", "*")


def find_mecab() -> Optional[str]:
    """按 环境变量 -> 已知路径 -> PATH 的顺序查找 mecab 可执行文件。"""
    env = os.environ.get("MECAB_PATH") or os.environ.get("MECAB_BIN")
    if env and os.path.isfile(env):
        return env
    for path in _KNOWN_MECAB_PATHS:
        if os.path.isfile(path):
            return path
    return shutil.which("mecab")


def find_dicdir() -> Optional[str]:
    """查找 MeCab 词典目录（默认 IPADIC）。"""
    env = os.environ.get("MECAB_DICDIR")
    if env and os.path.isdir(env):
        return env
    for path in [
        r"C:/msys64/mingw64/lib/mecab/dic/ipadic",
        r"C:/Program Files/MeCab/dic/ipadic",
    ]:
        if os.path.isdir(path):
            return path
    return None


class MeCab:
    """MeCab 子进程封装。"""

    def __init__(self, path: Optional[str] = None, dicdir: Optional[str] = None):
        self.path = path or find_mecab()
        if not self.path:
            raise FileNotFoundError(
                "未找到 mecab 可执行文件，请设置环境变量 MECAB_PATH 或安装 MeCab。"
            )
        self.dicdir = dicdir or find_dicdir()

    def _command(self) -> List[str]:
        cmd = [self.path]
        if self.dicdir:
            cmd += ["-d", self.dicdir]
        cmd += [
            "--node-format=" + _NODE_FORMAT,
            "--unk-format=" + _UNKNOWN_FORMAT,
            "--eos-format=" + _EOS + r"\n",
        ]
        return cmd

    def parse_line(self, text: str) -> List[Token]:
        """解析单行文本，返回词条列表。"""
        return self.parse_lines([text])[0]

    def parse_lines(self, lines: List[str]) -> List[List[Token]]:
        """解析多行文本，返回与输入行一一对应的词条列表（空行 -> 空列表）。"""
        if not lines:
            return []
        payload = "\n".join(lines) + "\n"
        proc = subprocess.run(
            self._command(),
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"mecab 执行失败（returncode={proc.returncode}）：{proc.stderr.strip()}"
            )
        blocks = proc.stdout.split(_EOS)
        # blocks 数量 = 输入行数 + 1（最后一个 EOS 之后的空块）
        result: List[List[Token]] = []
        for block in blocks[: len(lines)]:
            tokens = []
            for ln in block.splitlines():
                ln = ln.strip("\r\n")
                if not ln:
                    continue
                parts = ln.split("\t")
                if len(parts) < 10:
                    continue
                tokens.append(
                    Token(
                        surface=parts[0],
                        pos=parts[1],
                        pos1=parts[2],
                        pos2=parts[3],
                        pos3=parts[4],
                        ctype=parts[5],
                        cform=parts[6],
                        base=parts[7],
                        reading=parts[8],
                        pron=parts[9],
                    )
                )
            result.append(tokens)
        while len(result) < len(lines):
            result.append([])
        return result
