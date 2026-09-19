"""Qt bridge. All UI state changes are delivered on the main thread."""
import json
import shutil
import threading
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog
from .library import Library, generate
from .credentials import read_key, save_key

DEFAULTS = dict(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-plus", api_key_env="DASHSCOPE_API_KEY", output_mode="auto",
    theme="bunko", timeout="120", mecab="", no_llm=False)

class Backend(QObject):
    changed = Signal()
    booksChanged = Signal()
    settingsChanged = Signal()
    notice = Signal(str)
    lyricsLoaded = Signal(str)
    event = Signal(str, object)

    def __init__(self, library=None):
        super().__init__()
        self.library = library or Library(Path(__file__).resolve().parent.parent / "data/desktop")
        self._settings = dict(DEFAULTS)
        try:
            saved = json.loads((self.library.root / "settings.json").read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                self._settings.update({k:v for k,v in saved.items() if k in DEFAULTS and type(v) is type(DEFAULTS[k])})
        except (OSError, ValueError):
            pass
        self._books = []
        self._busy = False
        self._trash = False
        self._status = "准备好，把喜欢的歌词收藏起来。"
        self._logs = []
        self._key = ""
        self.event.connect(self.receive)
        self.refresh()

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self): return dict(self._settings)
    @Property("QVariantList", notify=booksChanged)
    def books(self): return self._books
    @Property(bool, notify=changed)
    def busy(self): return self._busy
    @Property(bool, notify=changed)
    def trash(self): return self._trash
    @Property(str, notify=changed)
    def status(self): return self._status
    @Property(str, notify=changed)
    def logs(self): return "\n".join(self._logs)
    @Property(str, notify=settingsChanged)
    def modelLabel(self):
        return "仅词典" if self._settings["no_llm"] else self._settings["model"]

    @Slot(str, result=str)
    def keyFor(self, name): return read_key(name)

    @Slot("QVariantMap", str, bool, result=bool)
    def configure(self, values, key, persist):
        try:
            config = dict(DEFAULTS)
            for name, default in DEFAULTS.items():
                value = values.get(name, default)
                if type(value) is not type(default): raise ValueError()
                config[name] = value
            from .llm import CompatibleClient
            if config["theme"] not in ("bunko","cards","lyrics"): raise ValueError()
            CompatibleClient(model=config["model"], base_url=config["base_url"],
                output_mode=config["output_mode"], timeout=float(config["timeout"]),
                api_key_env=config["api_key_env"], api_key=key, cache_path="")
            if persist: save_key(config["api_key_env"], key.strip())
            temp = self.library.root / "settings.tmp"
            temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.library.root / "settings.json")
            self._settings = config
            self._key = key.strip()
            self.settingsChanged.emit()
            self.notice.emit("设置已保存" + ("，密钥已写入用户环境变量。" if persist else "。"))
            return True
        except (OSError, ValueError, TypeError):
            self.notice.emit("保存失败，请检查接口、模型、超时、环境变量名和文件权限。")
            return False

    @Slot(str, str)
    def start(self, text, title):
        if self._busy: return
        if not text.strip():
            self.notice.emit("请先粘贴歌词。")
            return
        config = dict(self._settings)
        key = self._key or read_key(config["api_key_env"])
        if not config["no_llm"] and not key:
            self.notice.emit("请在右上角设置中填写密钥，并保存到环境变量。")
            return
        title = title.strip() or text.strip().splitlines()[0][:32]
        self._busy = True
        self._logs = []
        self._status = "正在准备生成…"
        self.changed.emit()
        def work():
            try:
                result = generate(self.library, text, title, config, key,
                    lambda m:self.event.emit("progress", str(m)))
                self.event.emit("done", result)
            except Exception as exc:
                self.event.emit("error", "生成未完成（" + type(exc).__name__ + "），请检查 MeCab、接口设置与文件权限。")
        threading.Thread(target=work, daemon=True).start()

    @Slot(str, object)
    def receive(self, kind, value):
        if kind == "progress":
            self._status = value
            self._logs.append(value)
        else:
            self._busy = False
            if kind == "done":
                _, pending, failures = value
                self._status = f"已加入书架 · 待补充词 {pending} · 失败块 {failures}"
                self._trash = False
                self.refresh()
            else:
                self._status = value
                self.notice.emit(value)
        self.changed.emit()

    @Slot()
    def refresh(self):
        self._books = self.library.items(self._trash)
        self.booksChanged.emit()

    @Slot()
    def toggleTrash(self):
        self._trash = not self._trash
        self.changed.emit()
        self.refresh()

    @Slot(str, str, str, result=bool)
    def mergeBooks(self, first, second, title):
        try:
            self.library.merge(first, second, title, self._settings["theme"])
            self._trash = False
            self.refresh()
            self.changed.emit()
            self.notice.emit("合集已加入书架，两本原书已保留。")
            return True
        except ValueError as exc:
            self.notice.emit(str(exc))
        except OSError:
            self.notice.emit("合并失败，请检查原书是否存在及书架目录权限。")
        return False

    @Slot(str, str, str)
    def bookAction(self, action, book_id, title):
        try:
            path = self.library.path(book_id, self._trash) / "book.html"
            if action in ("open", "export"):
                path = self.library.update_reader(book_id, self._trash)
            if action == "open":
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
                    raise OSError()
            elif action == "export":
                target, _ = QFileDialog.getSaveFileName(None,"另存手帖","手帖.html","HTML (*.html)")
                if target and Path(target).resolve() != path.resolve(): shutil.copyfile(path,target)
            elif action == "rename" and not self._trash:
                self.library.rename(book_id,title)
            elif action == "move":
                self.library.move(book_id,restore=self._trash)
            self.refresh()
        except (OSError, ValueError):
            self.notice.emit("操作未完成，请检查名称、文件和路径权限。")

    @Slot()
    def importHtml(self):
        filename, _ = QFileDialog.getOpenFileName(None,"导入手帖","","HTML (*.html)")
        if filename:
            try:
                path = Path(filename)
                self.library.add(path.stem,path.read_text(encoding="utf-8-sig"))
                self._trash = False
                self.changed.emit()
                self.refresh()
            except (OSError, ValueError):
                self.notice.emit("无法读取 HTML，请检查编码和文件权限。")

    @Slot()
    def importLyrics(self):
        filename, _ = QFileDialog.getOpenFileName(None,"导入歌词","","歌词 (*.txt)")
        if filename:
            try: self.lyricsLoaded.emit(Path(filename).read_text(encoding="utf-8-sig"))
            except (OSError, ValueError): self.notice.emit("无法读取歌词，请使用 UTF-8 文本。")
