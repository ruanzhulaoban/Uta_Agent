# -*- coding: utf-8 -*-
"""命令行入口：输入歌词文本 -> 输出标注 JSON。

用法示例：
    python main.py lyrics.txt
    python main.py --text "桜の花が咲く"
    echo "心に咲いた花よ" | python main.py -
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from utaagent_core.annotator import Annotator
from utaagent_core.mecab import MeCab


def _read_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.input is None or args.input == "-":
        return sys.stdin.read()
    path = Path(args.input)
    if not path.is_file():
        raise SystemExit(f"文件不存在：{path}")
    return path.read_text(encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="utaagent",
        description="日语歌词标注工具：分词、词性标注、假名注音、罗马音生成。",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="歌词文本文件路径；省略或用 '-' 时从标准输入读取",
    )
    parser.add_argument(
        "--text",
        metavar="TEXT",
        help="直接在命令行传入歌词文本（优先级高于 input）",
    )
    parser.add_argument(
        "--mecab",
        metavar="PATH",
        help="mecab 可执行文件路径（默认自动探测）",
    )
    parser.add_argument(
        "--no-romaji",
        action="store_true",
        help="省略罗马音字段",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="输出紧凑 JSON（不缩进）",
    )
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    text = _read_text(args)

    mecab = MeCab(path=args.mecab) if args.mecab else MeCab()
    annotator = Annotator(mecab=mecab)
    doc = annotator.annotate(text)

    if args.no_romaji:
        for line in doc["lines"]:
            line.pop("romaji", None)
            for w in line["words"]:
                w.pop("romaji", None)

    indent = None if args.compact else 2
    print(json.dumps(doc, ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
