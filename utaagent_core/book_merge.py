"""Merge exported utaagent HTML without running scripts or requesting a model."""
from html import escape
from html.parser import HTMLParser
import json
import uuid
from .html_export import ASSETS, render_layout

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()

    def text(self):
        return "".join(c.text() if isinstance(c, Node) else c for c in self.children)

    def html(self):
        raw = self.tag in ("script", "style")
        inside = "".join(c.html() if isinstance(c, Node) else (c if raw else escape(c, quote=False)) for c in self.children)
        if not self.tag:
            return inside
        attrs = "".join(" " + k + ("" if v is None else '="' + escape(v, quote=True) + '"') for k, v in self.attrs.items())
        return "<" + self.tag + attrs + ">" + ("" if self.tag in VOID else inside + "</" + self.tag + ">")


class BookParser(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _read(html):
    root = BookParser(html).root
    nodes = list(root.walk())
    body = next((n for n in nodes if n.tag == "body" and n.attrs.get("data-book-id")), None)
    articles = [n for n in nodes if n.tag == "article" and n.has_class("song")]
    state_node = next((n for n in nodes if n.attrs.get("id") == "vocab-state"), None)
    if body is None or not articles or state_node is None:
        raise ValueError("请选择由 utaagent 导出的歌词本 HTML；普通网页暂不支持合并。")
    for article in articles:
        classes = {c for n in article.walk() for c in (n.attrs.get("class") or "").split()}
        if not {"lyric-text", "annotations", "word-notes", "removed-panel", "editor-status"} <= classes:
            raise ValueError("歌词本格式过旧，请先用当前版本重新导出。")
    try:
        state = json.loads(state_node.text())
        if not isinstance(state, dict) or state.get("version") != 1:
            raise ValueError()
        if not isinstance(state.get("custom"), list) or not isinstance(state.get("removed"), list):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("词语手帖的保存数据无效，无法合并。") from None
    return root, articles, state


def refresh_reader(html):
    """Update supported stored books' reader assets, preserving IDs and embedded edits."""
    root, _, _ = _read(html)
    nodes = list(root.walk())
    style = next((n for n in nodes if n.tag == "style"), None)
    scripts = [n for n in nodes if n.tag == "script" and "filterVocabulary" in n.text() and "storageKey" in n.text()]
    if style is None or len(scripts) != 1:
        raise ValueError("无法识别此歌词本的阅读脚本。")
    style.children = [(ASSETS / "book.css").read_text(encoding="utf-8")]
    scripts[0].children = [(ASSETS / "book.js").read_text(encoding="utf-8")]
    return "<!doctype html>" + root.html()


def merge_books(html_books, title, theme="bunko"):
    if len(html_books) < 2 or not title.strip():
        raise ValueError("请选择至少两本歌词本，并填写合集名称。")
    articles, songs = [], []
    state = dict(version=1, revision=0, custom=[], removed=[])
    for html in html_books:
        _, source_articles, source_state = _read(html)
        mapping = {}
        for article in source_articles:
            number = len(articles) + 1
            sid = "song-" + str(number)
            old_sid = article.attrs.get("id")
            if not old_sid:
                raise ValueError("歌词本缺少歌曲编号。")
            for node in article.walk():
                old = node.attrs.get("id")
                if old:
                    if old in mapping:
                        raise ValueError("歌词本存在重复编号，无法合并。")
                    mapping[old] = sid if old == old_sid else (
                        "custom-" + uuid.uuid4().hex if old.startswith("custom-") else sid + "-" + uuid.uuid4().hex)
            heading = next((n for n in article.walk() if n.tag == "h2"), None)
            songs.append({"title": heading.text() if heading else "歌曲 " + str(number)})
            eyebrow = next((n for n in article.walk() if n.has_class("eyebrow")), None)
            if eyebrow:
                eyebrow.children = ["SONG / " + str(number).zfill(2)]
            footer = next((n for n in article.walk() if n.has_class("song-footer")), None)
            if footer:
                anchor = Node("a", [("href", "#contents")])
                anchor.children = ["目录"]
                footer.children = [anchor, " · " + str(number).zfill(2)]
            articles.append(article)
        for entry in source_state["custom"]:
            if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                    or not isinstance(entry.get("song"), str) or entry["song"] not in mapping):
                raise ValueError("手动词条关联无效，无法合并。")
            mapping.setdefault(entry["id"], "custom-" + uuid.uuid4().hex)
            state["custom"].append(dict(entry, id=mapping[entry["id"]], song=mapping[entry["song"]]))
        for removed in source_state["removed"]:
            if isinstance(removed, str) and removed in mapping:
                state["removed"].append(mapping[removed])
        for article in source_articles:
            for node in article.walk():
                if "id" in node.attrs:
                    node.attrs["id"] = mapping[node.attrs["id"]]
                for attr in ("href", "data-restore-word", "for", "aria-controls", "aria-labelledby", "aria-describedby"):
                    value = node.attrs.get(attr)
                    if not value:
                        continue
                    if attr == "href":
                        if value.startswith("#") and value[1:] in mapping:
                            node.attrs[attr] = "#" + mapping[value[1:]]
                    else:
                        node.attrs[attr] = " ".join(mapping.get(v, v) for v in value.split())
                # Reader scripts are supplied once by our shell, never by an imported article.
                node.children = [c for c in node.children if not isinstance(c, Node) or c.tag not in {"script", "style", "iframe", "object", "embed"}]
                node.attrs = {k:v for k,v in node.attrs.items() if not k.lower().startswith("on")}
    return render_layout(songs, "".join(a.html() for a in articles), title.strip(),
                         "日语歌词合集", theme, uuid.uuid4().hex, state)
