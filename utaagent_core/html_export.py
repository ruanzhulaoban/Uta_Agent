"""Offline, single-file lyric book export. Never calls MeCab or an LLM."""
from html import escape
import json
from pathlib import Path
import re
from .kana import katakana_to_hiragana
from .schemas import FINAL_SCHEMA, validate

THEMES = ("bunko", "cards", "lyrics")
ASSETS = Path(__file__).with_name("templates")
def esc(value):
    return escape(str(value), quote=True)

def ruby(surface, reading):
    """Align kana anchors; ambiguous kanji groups retain whole-word ruby."""
    if not reading or reading == surface or not re.search(r"[\u3400-\u9fff々]", surface):
        return esc(surface)
    target = katakana_to_hiragana(reading)
    runs = re.findall(r"[\u3040-\u309f\u30a0-\u30ffー]+|[^\u3040-\u309f\u30a0-\u30ffー]+", surface)
    solutions = []
    def align(i, offset, parts):
        if len(solutions) > 1:
            return
        if i == len(runs):
            if offset == len(target):
                solutions.append(parts)
            return
        run = runs[i]
        if not re.search(r"[\u3400-\u9fff々]", run):
            literal = katakana_to_hiragana(run)
            if target.startswith(literal, offset):
                align(i + 1, offset + len(literal), parts + [(run, None)])
        else:
            for end in range(offset + 1, len(target) + 1):
                align(i + 1, end, parts + [(run, target[offset:end])])
                if len(solutions) > 1:
                    break
    align(0, 0, [])
    parts = solutions[0] if len(solutions) == 1 else [(surface, target)]
    return "".join(esc(base) if rt is None else
        "<ruby>" + esc(base) + "<rp>（</rp><rt>" + esc(rt) + "</rt><rp>）</rp></ruby>"
        for base, rt in parts)

def _grammar_anchor(sid, value):
    bid, gid = value.split(":")
    return sid + "-" + bid + "-" + gid

def _song(song, number):
    doc = song["document"]
    validate(doc, FINAL_SCHEMA)
    sid = "song-" + str(number)
    chorus = set()
    for pair in song.get("chorus_ranges", []):
        if not isinstance(pair, list) or len(pair) != 2 or any(type(i) is not int for i in pair):
            raise ValueError("chorus_ranges 应为一基闭区间数组，如 [[8, 9]]")
        start, end = pair
        if not 1 <= start <= end <= len(doc["lines"]):
            raise ValueError("副歌行范围越界")
        chorus.update(range(start - 1, end))
    lines, notes = [], []
    pending = 0
    for li, line in enumerate(doc["lines"]):
        if not line["text"].strip():
            lines.append('<div class="stanza-gap" id="' + sid + '-line-' + str(li) + '" aria-label="段落间隔"></div>')
            continue
        pieces, cursor = [], 0
        for wi, word in enumerate(line["words"]):
            surface = word["surface"]
            at = line["text"].find(surface, cursor)
            if at < 0:
                raise ValueError("第 " + str(li + 1) + " 行分词无法与原文对齐")
            pieces.append(esc(line["text"][cursor:at]))
            cursor = at + len(surface)
            wid = sid + "-l" + str(li) + "-w" + str(wi)
            if word["source"] == "symbol":
                pieces.append(esc(surface))
                continue
            pending += word["source"] == "pending"
            pieces.append('<a class="word" id="' + wid + '" href="#' + wid + '-note" title="' +
                          esc(word["gloss"]) + '">' + ruby(surface, word["reading"]) + '</a>')
            level = '<span class="level">' + esc(word["jlpt"]) + '</span>' if word["jlpt"] else ""
            refs = " ".join('<a href="#' + _grammar_anchor(sid, gid) + '">语法 ' +
                            esc(gid.split(":")[1][1:]) + '</a>' for gid in word["grammar_ids"])
            notes.append('<li class="word-note" id="' + wid + '-note"><div><a lang="ja" href="#' + wid +
                         '">' + ruby(surface, word["reading"]) + '</a>' + level + '</div><p>' +
                         esc(word["gloss"]) + '</p><small>' + ("待补充 · " if word["source"] == "pending" else "") +
                         '第 ' + str(li + 1) + ' 行' + (' · ' + refs if refs else "") + '</small></li>')
        pieces.append(esc(line["text"][cursor:]))
        is_chorus = li in chorus
        tag = '<span class="chorus-label">副歌</span>' if is_chorus and li - 1 not in chorus else ""
        lines.append('<div class="lyric-line' + (' chorus' if is_chorus else '') + '" id="' + sid +
                     '-line-' + str(li) + '"><span class="line-number" aria-hidden="true">' +
                     str(li + 1).zfill(2) + '</span><div class="line-content">' + tag +
                     '<p lang="ja" class="japanese">' + "".join(pieces) + '</p></div></div>')
    grammar = []
    for block in doc["blocks"]:
        for point in block["grammar"]:
            gid = "b" + str(block["id"]) + ":g" + str(point["id"])
            refs = []
            for ref in point["word_refs"]:
                li = block["line_indices"][ref["line_index"]]
                wi = ref["word_index"]
                w = doc["lines"][li]["words"][wi]
                # Symbol references point to their line, which always has a visible anchor.
                target = sid + "-line-" + str(li) if w["source"] == "symbol" else sid + "-l" + str(li) + "-w" + str(wi)
                refs.append('<a href="#' + target + '">' + esc(w["surface"]) + ' <small>L' + str(li + 1) + '</small></a>')
            grammar.append('<li id="' + _grammar_anchor(sid, gid) + '"><h4 lang="ja">' +
                esc(point["pattern"]) + '</h4><p class="quote" lang="ja">' + esc(point["text"]) +
                '</p><p>' + esc(point["meaning"]) + '</p><div class="grammar-refs">' + " ".join(refs) + '</div></li>')
    grammar_html = '<ol class="grammar-list">' + "".join(grammar) + '</ol>' if grammar else '<p class="muted">本曲暂无语法标注。</p>'
    notice = '<p class="notice">本曲有 ' + str(pending) + ' 个词的释义待补充。</p>' if pending else ""
    failures = doc["llm"]["failures"]
    if failures:
        notice += '<p class="notice">有 ' + str(failures) + ' 个分析块未完成，语法说明可能不完整。</p>'
    return ('<article class="song" id="' + sid + '"><header class="song-heading"><p class="eyebrow">SONG / ' +
            str(number).zfill(2) + '</p><h2>' + esc(song["title"]) + '</h2><p class="artist">' +
            esc(song.get("artist", "")) + '</p><a class="back" href="#contents">返回目录 ↑</a></header>' +
            notice + '<section class="lyric-text" aria-label="歌词正文">' + "".join(lines) + '</section>' +
            '<section class="annotations" aria-label="学习笔记"><h3><span>01</span> 词语手帖</h3><ul class="word-notes">' +
            "".join(notes) + '</ul><h3><span>02</span> 语法与表达</h3>' + grammar_html +
            '</section><footer class="song-footer"><a href="#contents">目录</a> · ' + str(number).zfill(2) + '</footer></article>')

def render_book(songs, title="言葉の余白", subtitle="日语歌词学习手帖", theme="bunko"):
    if theme not in THEMES:
        raise ValueError("未知主题")
    if not songs:
        raise ValueError("至少需要一首歌")
    for song in songs:
        if not isinstance(song.get("title"), str) or not song["title"].strip():
            raise ValueError("歌曲标题不能为空")
        if not isinstance(song.get("artist", ""), str):
            raise ValueError("artist 必须为字符串")
    contents = "".join('<li><a href="#song-' + str(i) + '"><span>' + str(i).zfill(2) +
                       '</span><strong>' + esc(s["title"]) + '</strong><span aria-hidden="true">↗</span></a></li>'
                       for i, s in enumerate(songs, 1))
    body = "".join(_song(s, i) for i, s in enumerate(songs, 1))
    css = (ASSETS / "book.css").read_text(encoding="utf-8")
    js = (ASSETS / "book.js").read_text(encoding="utf-8")
    options = "".join('<option value="' + key + '"' + (' selected' if theme == key else '') + '>' + label + '</option>'
                      for key, label in zip(THEMES, ("文库本", "学习卡片", "歌词本")))
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' +
            '<title>' + esc(title) + '</title><style>' + css + '</style></head><body class="theme-' + theme + '">' +
            '<a class="skip" href="#contents">跳转目录</a><nav class="toolbar" aria-label="阅读设置"><a href="#cover">UTA / 歌词手帖</a>' +
            '<div><label for="theme">主题</label><select id="theme">' + options +
            '</select><button id="ruby-toggle" aria-pressed="true">注音</button><button id="notes-toggle" aria-pressed="true">释义与语法</button></div></nav>' +
            '<main><section class="cover" id="cover"><div class="cover-rule"></div><p class="eyebrow">A JAPANESE LYRIC READER</p>' +
            '<h1>' + esc(title) + '</h1><p class="subtitle">' + esc(subtitle) +
            '</p><div class="cover-mark" aria-hidden="true">詩</div><div class="cover-bottom"><span>読む · 知る · 味わう</span><span>' +
            str(len(songs)).zfill(2) + ' SONGS</span></div></section><nav class="contents" id="contents" aria-label="目录">' +
            '<p class="eyebrow">CONTENTS</p><h2>目次 <small>目录</small></h2><ol>' + contents +
            '</ol></nav>' + body + '</main><footer class="book-footer">UTAAGENT · 歌词学习手帖</footer><script>' +
            js + '</script></body></html>')

def load_songs(paths):
    return [{"title": Path(path).stem, "document": json.loads(Path(path).read_text(encoding="utf-8-sig"))}
            for path in paths]

def load_manifest(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or set(data) - {"title", "subtitle", "songs"}:
        raise ValueError("出版配置仅支持 title/subtitle/songs")
    if not isinstance(data.get("songs"), list) or not data["songs"]:
        raise ValueError("songs 必须是非空数组")
    for key in ("title", "subtitle"):
        if key in data and not isinstance(data[key], str):
            raise ValueError(key + " 必须是字符串")
    songs, sources = [], []
    for entry in data["songs"]:
        if not isinstance(entry, dict) or set(entry) - {"input", "title", "artist", "chorus_ranges"}:
            raise ValueError("歌曲配置字段无效")
        if not isinstance(entry.get("input"), str) or not entry["input"]:
            raise ValueError("歌曲缺少 input 路径")
        if not isinstance(entry.get("chorus_ranges", []), list):
            raise ValueError("chorus_ranges 必须为数组")
        source = (path.parent / entry["input"]).resolve()
        songs.append(dict(entry, title=entry.get("title", source.stem),
                          document=json.loads(source.read_text(encoding="utf-8-sig"))))
        sources.append(source)
    return data, songs, sources
