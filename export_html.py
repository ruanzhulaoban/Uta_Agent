"""Export validated annotation JSON as an offline HTML book."""
import argparse
from pathlib import Path
import sys
from jsonschema import ValidationError
from utaagent_core.html_export import THEMES, load_songs, load_manifest, render_book

def main(argv=None):
    parser = argparse.ArgumentParser(description="标注 JSON → 单文件 HTML 歌词书（无需模型调用）")
    parser.add_argument("inputs", nargs="*", help="一个或多个 0.5.0 标注 JSON")
    parser.add_argument("--manifest", help="多曲目出版配置 JSON")
    parser.add_argument("--output", "-o", required=True, help="输出 .html 路径")
    parser.add_argument("--theme", choices=THEMES, default="bunko")
    parser.add_argument("--title", help="封面书名")
    parser.add_argument("--subtitle", help="封面副标题")
    args = parser.parse_args(argv)
    if bool(args.inputs) == bool(args.manifest):
        parser.error("请提供输入 JSON 文件，或 --manifest，二者选一")
    try:
        metadata = {}
        if args.manifest:
            metadata, songs, sources = load_manifest(args.manifest)
            sources.append(Path(args.manifest).resolve())
        else:
            sources = [Path(p).resolve() for p in args.inputs]
            songs = load_songs(sources)
        output = Path(args.output)
        if output.suffix.lower() != ".html" or output.resolve() in sources:
            raise ValueError("输出应为独立的 .html 文件")
        html = render_book(songs, title=args.title if args.title is not None else metadata.get("title", "言葉の余白"),
                           subtitle=args.subtitle if args.subtitle is not None else metadata.get("subtitle", "日语歌词学习手帖"),
                           theme=args.theme)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print("已导出 " + str(len(songs)) + " 首歌：" + str(output.resolve()), file=sys.stderr)
        return 0
    except (OSError, ValueError, TypeError, KeyError, ValidationError) as exc:
        print("HTML 导出失败：" + (str(exc) if not isinstance(exc, ValidationError) else "标注 JSON 不符合 0.5.0 Schema"),
              file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
