"""CLI: raw lyrics or annotated JSON -> validated enrichment JSON."""
import argparse
import json
import sys
from pathlib import Path
from jsonschema import ValidationError
from utaagent_core.gloss_dict import GlossDict
from utaagent_core.glossifier import Glossifier
from utaagent_core.llm import CompatibleClient, DEFAULT_BASE_URL, DEFAULT_MODEL
from utaagent_core.schemas import FINAL_SCHEMA, validate

def _build_parser():
    p = argparse.ArgumentParser(description="日语歌词标注：词典与通用 OpenAI 兼容模型")
    p.add_argument("input", nargs="?", help="文本或标注 JSON 文件；- 或省略为 stdin")
    p.add_argument("--text")
    p.add_argument("--input-format", choices=["text", "json"], default="text")
    p.add_argument("--mecab")
    p.add_argument("--no-romaji", action="store_true")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--config", help="JSON 配置文件；命令行覆盖配置")
    p.add_argument("--model", help="任意兼容模型名")
    p.add_argument("--base-url")
    p.add_argument("--api-key-env", help="保存密钥的环境变量名称")
    p.add_argument("--output-mode", choices=["auto", "json_schema", "json_object", "text"])
    p.add_argument("--timeout", type=float)
    p.add_argument("--retries", type=int)
    p.add_argument("--extra-body", help="模型专用参数 JSON，例如 thinking/max_tokens")
    p.add_argument("--cache")
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--dict", dest="dict_path")
    p.add_argument("--quiet", action="store_true", help="关闭 stderr 进度提示")
    return p

def main(argv=None):
    args = _build_parser().parse_args(argv)
    status = (lambda message: None) if args.quiet else (lambda message: print("[utaagent] " + message, file=sys.stderr))
    try:
        config = {"model": DEFAULT_MODEL, "base_url": DEFAULT_BASE_URL,
                  "api_key_env": "DASHSCOPE_API_KEY", "output_mode": "auto",
                  "timeout": 60, "retries": 1, "cache_path": None, "extra_body": {}}
        if args.config:
            saved = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
            if not isinstance(saved, dict) or set(saved) - set(config):
                raise ValueError("配置必须为 JSON 对象且只能包含文档列出的配置项")
            config.update(saved)
        for key in config:
            arg = getattr(args, "cache" if key == "cache_path" else key, None)
            if arg is not None:
                config[key] = json.loads(arg) if key == "extra_body" else arg
        if args.no_cache:
            config["cache_path"] = ""
        text = args.text if args.text is not None else (
            sys.stdin.read() if args.input in (None, "-") else Path(args.input).read_text(encoding="utf-8-sig"))
        llm = None if args.no_llm else CompatibleClient(**config, status=status)
        status("仅词典模式" if llm is None else "模型 " + llm.model + "；模式 " + llm.requested_mode + "；本地校验已启用")
        annotator = None
        if args.input_format == "text":
            from utaagent_core.annotator import Annotator
            from utaagent_core.mecab import MeCab
            annotator = Annotator(mecab=MeCab(path=args.mecab))
        processor = Glossifier(annotator=annotator, dictionary=GlossDict(args.dict_path), llm=llm, status=status)
        doc = processor.enrich(json.loads(text)) if args.input_format == "json" else processor.annotate(text)
        if args.no_romaji:
            for line in doc["lines"]:
                line.pop("romaji", None)
                for word in line["words"]:
                    word.pop("romaji", None)
        validate(doc, FINAL_SCHEMA)
        status("完成：HTTP 请求 " + str(doc["llm"]["calls"]) + "，缓存命中 " +
               str(doc["llm"]["cache_hits"]) + "，失败块 " + str(doc["llm"]["failures"]) +
               "，待补充词 " + str(sum(w["source"] == "pending" for line in doc["lines"] for w in line["words"])) + "；最终校验通过")
        print(json.dumps(doc, ensure_ascii=False, indent=None if args.compact else 2, allow_nan=False))
        return 0
    except ValidationError as exc:
        print("输入或输出 Schema 校验失败，位置：" + "/".join(map(str, exc.absolute_path)), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError) as exc:
        print("输入或配置无效（" + type(exc).__name__ + "），请检查文件和参数。", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
