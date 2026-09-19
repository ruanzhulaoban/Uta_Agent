"""Local book storage; names never become filesystem paths."""
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, book_id, trash=False):
        if not re.fullmatch(r"[a-f0-9]{32}", book_id):
            raise ValueError("无效的书籍编号")
        return self.root / (".trash" if trash else "books") / book_id

    def items(self, trash=False):
        parent = self.root / (".trash" if trash else "books")
        result = []
        for path in parent.glob("*/metadata.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if self.path(path.parent.name, trash) != path.parent or not isinstance(value["title"], str):
                    continue
                value["id"] = path.parent.name
                if (path.parent / "book.html").is_file():
                    result.append(value)
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(result, key=lambda x: x.get("created", ""), reverse=True)

    def add(self, title, html, document=None):
        book_id = uuid.uuid4().hex
        path = self.path(book_id)
        path.mkdir(parents=True)
        try:
            (path / "book.html").write_text(html, encoding="utf-8")
            if document is not None:
                (path / "annotation.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
            self._metadata(path, {"title": title, "created": datetime.now().isoformat(timespec="seconds")})
        except Exception:
            # An incomplete entry has no metadata and is not published in the shelf.
            raise
        return book_id

    def _metadata(self, path, value):
        temp = path / "metadata.tmp"
        temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temp.replace(path / "metadata.json")

    def rename(self, book_id, title):
        if not title.strip():
            raise ValueError("名称不能为空")
        path = self.path(book_id)
        data = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        data["title"] = title.strip()
        self._metadata(path, data)

    def move(self, book_id, restore=False):
        source = self.path(book_id, trash=restore)
        target = self.path(book_id, trash=not restore)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)

    def merge(self, first, second, title, theme="bunko"):
        from .book_merge import merge_books
        if first == second:
            raise ValueError("请选择两本不同的歌词本。")
        sources = [(self.path(book_id) / "book.html").read_text(encoding="utf-8-sig")
                   for book_id in (first, second)]
        html = merge_books(sources, title, theme)
        return self.add(title.strip(), html)

    def update_reader(self, book_id, trash=False):
        from .book_merge import refresh_reader
        path = self.path(book_id, trash) / "book.html"
        original = path.read_text(encoding="utf-8-sig")
        try:
            updated = refresh_reader(original)
        except ValueError:
            return path  # Ordinary imported HTML remains readable without conversion.
        if updated != original:
            temp = path.with_suffix(".tmp")
            temp.write_text(updated, encoding="utf-8")
            temp.replace(path)
        return path

def generate(library, text, title, settings, api_key, status):
    from .annotator import Annotator
    from .mecab import MeCab
    from .glossifier import Glossifier
    from .llm import CompatibleClient
    from .html_export import render_book
    from .schemas import FINAL_SCHEMA, validate
    client = None
    if not settings["no_llm"]:
        client = CompatibleClient(
            api_key=api_key or None, api_key_env=settings["api_key_env"],
            base_url=settings["base_url"], model=settings["model"],
            output_mode=settings["output_mode"], timeout=float(settings["timeout"]),
            cache_path=library.root / "cache.json", status=status)
        if not client.api_key:
            raise ValueError("请填写 API Key，或设置指定的环境变量")
    status("正在分词与注音…")
    annotator = Annotator(mecab=MeCab(path=settings["mecab"] or None))
    doc = Glossifier(annotator=annotator, llm=client, status=status).annotate(text)
    validate(doc, FINAL_SCHEMA)
    status("正在排版并保存 HTML…")
    html = render_book([{"title": title, "document": doc}], title=title, theme=settings["theme"])
    book_id = library.add(title, html, doc)
    pending = sum(w["source"] == "pending" for line in doc["lines"] for w in line["words"])
    return book_id, pending, doc["llm"]["failures"]
